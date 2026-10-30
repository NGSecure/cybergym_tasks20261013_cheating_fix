#!/usr/bin/env python3
"""给一个文件夹里每个 bundle 的 agent 镜像补上防作弊修复，再推回 SWR 原来的地址覆盖（task.toml 不用改）。
做完以后这个文件夹可以直接打包上传，不用再 build、push。

agent 镜像 = task.toml 里 [environment] 的 docker_image（push.sh 回填的第一个地址；task_server_image 不动）。
修复和 bundle Dockerfile 里加的两步一样，加在原镜像上面：
    RUN rm -f /tmp/poc
    RUN find /src \\( -name .git -o -name .hg \\) -prune -exec rm -rf {} +

用法（在文件夹外面运行：日志写在当前目录，不会混进要上传的文件夹）：
    python3 fix_agent_images.py <文件夹> --only list_cheating.txt --plan       只读 task.toml，列出要做什么，不拉镜像
    python3 fix_agent_images.py <文件夹> --only list_cheating.txt --limit 2    dry-run：拉下来、修好、核对，不推送
    python3 fix_agent_images.py <文件夹> --only list_cheating.txt --push       推回原地址覆盖，task.toml 不变
其他参数：
    --only LIST   只处理列表文件里的 bundle（每行一个名字）；列表里有、文件夹里没有的会报出来
    --new-tag     改成推到新 tag（原 tag 后面加 -hardened），并把 task.toml 的 docker_image 改成新地址；原地址不动。
                  覆盖同一个 tag 时，平台节点如果按 tag 缓存镜像（IfNotPresent），已经拉过旧镜像的节点可能还在用旧的；
                  担心这一点就用 --new-tag（地址变了，节点一定会重新拉）
    --recheck     不看日志，每个都重新拉下来检查
    --keep        结束后不删本地镜像和构建缓存

重跑、中断：
- 每个镜像推完（或检查发现本来就干净）都记进当前目录的 remove_poc_swr.log。在同一个目录重跑同一条命令，
  日志里记着做完的直接跳过，不再拉镜像；所以中途断了，重跑会从没做完的那个接着做。
- 已经修过的镜像就算再处理一遍也不会出错：拉下来发现没有 /tmp/poc 和 .git/.hg，显示"不需要处理"，不推送。
- 中断（Ctrl+C、kill、断开 SSH）时先清掉当前这个镜像在本机留下的东西再退出；kill -9 或死机留下的，下次启动时
  自动清掉。SWR 上的 tag 要等推送最后一步才切换，推到一半断了的，SWR 上还是原来的镜像。详见 remove_poc_swr.py 开头。
- 一千多个要跑很久，建议在 tmux/screen 里或者用 nohup 跑，断开 SSH 也不会停。

本地磁盘：每处理完一个 bundle 就删掉这次拉下来的镜像、打的 tag 和这次构建留下的构建缓存，打印磁盘剩余；
机器上别人的镜像和构建缓存不动。需要 remove_poc_swr.py 放在同一个目录；事先 docker login 过 SWR。
"""
import argparse
import collections
import glob
import os
import re
import shutil
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import remove_poc_swr as rp  # noqa: E402

try:
    import tomllib
except ImportError:  # Python 3.10 及以前
    tomllib = None

SUFFIX = "-hardened"
# 本地开发留下的东西，不该跟着 bundle 上传
JUNK = (".venv", ".pytest_cache", "__pycache__", ".git")
# 和 newplatform 回填 task.toml 时用的一样：一行只有 [表名]（可带注释）才是表头
HEADER = re.compile(r"^\s*\[[^\]]+\]\s*(#.*)?$")
ENV_HEADER = re.compile(r"^\s*\[environment\]\s*(#.*)?$")


def find_bundles(folder):
    """文件夹下一层或两层、带 task.toml 的目录。"""
    found = glob.glob(os.path.join(folder, "*", "task.toml")) + glob.glob(os.path.join(folder, "*", "*", "task.toml"))
    dirs = {os.path.dirname(os.path.abspath(p)) for p in found}
    return sorted(d for d in dirs if os.path.dirname(d) not in dirs)


def read_agent_image(toml_path):
    with open(toml_path, encoding="utf-8") as f:
        text = f.read()
    if tomllib:
        try:
            return str((tomllib.loads(text).get("environment") or {}).get("docker_image") or "").strip()
        except tomllib.TOMLDecodeError as exc:
            raise rp.Failed(f"task.toml 解析失败：{exc}")
    in_env = False
    for line in text.splitlines():
        if HEADER.match(line):
            in_env = bool(ENV_HEADER.match(line))
        elif in_env:
            m = re.match(r'\s*docker_image\s*=\s*"([^"]*)"', line)
            if m:
                return m.group(1).strip()
    return ""


def set_agent_image(toml_path, old, new):
    """只改 [environment] 里 docker_image 那一行的值；注释、格式、换行符原样保留。"""
    with open(toml_path, encoding="utf-8", newline="") as f:
        lines = f.read().splitlines(keepends=True)
    in_env, done = False, False
    for i, line in enumerate(lines):
        if HEADER.match(line):
            in_env = bool(ENV_HEADER.match(line))
        elif in_env and not done and re.match(r"\s*docker_image\s*=", line) and f'"{old}"' in line:
            lines[i] = line.replace(f'"{old}"', f'"{new}"', 1)
            done = True
    if not done:
        raise rp.Failed(f'task.toml 里没找到 docker_image = "{old}" 这一行，没有改')
    # 先写临时文件再替换：中断、磁盘满都不会把 task.toml 写坏
    tmp = toml_path + ".tmp"
    with rp.deferred_interrupt():
        try:
            with open(tmp, "w", encoding="utf-8", newline="") as f:
                f.write("".join(lines))
            shutil.copymode(toml_path, tmp)
            os.replace(tmp, toml_path)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)


def done_before(log, image, target):
    """日志里这个镜像是不是已经做完：本来就干净，或者已经推到了这次要推的地址（而且 .git/.hg 也处理过）。"""
    for entry in log.get(image, []):
        if entry["status"] == "clean" or (entry["target"] == target and entry["vcs_checked"]):
            return entry
    return None


def main():
    parser = argparse.ArgumentParser(description="修好文件夹里每个 bundle 的 agent 镜像，推回原地址（默认 dry-run）")
    parser.add_argument("folder", help="放 bundle 的文件夹")
    parser.add_argument("--push", action="store_true", help="核对通过后真的推送")
    parser.add_argument("--overwrite", action="store_true", help="推回原地址覆盖，task.toml 不变（默认就是这样，可以不写）")
    parser.add_argument("--new-tag", action="store_true", help=f"推到新 tag（原 tag + {SUFFIX}）并改 task.toml，原地址不动")
    parser.add_argument("--plan", action="store_true", help="只读 task.toml 列出要做什么，不拉镜像")
    parser.add_argument("--only", metavar="LIST", help="只处理列表文件里的 bundle（每行一个名字）")
    parser.add_argument("--limit", type=int, metavar="N", help="只处理前 N 个")
    parser.add_argument("--recheck", action="store_true", help="不看日志，每个都重新拉下来检查")
    parser.add_argument("--keep", action="store_true", help="结束后不删本地镜像和构建缓存")
    args = parser.parse_args()
    if args.plan and args.push:
        parser.error("--plan 和 --push 不能一起用")
    if args.overwrite and args.new_tag:
        parser.error("--overwrite 和 --new-tag 不能一起用")
    folder = os.path.abspath(args.folder)
    if not os.path.isdir(folder):
        parser.error(f"不是文件夹：{args.folder}")

    bundles = find_bundles(folder)
    if args.only:
        with open(args.only, encoding="utf-8") as f:
            wanted = [x.strip() for x in f if x.strip() and not x.lstrip().startswith("#")]
        by_name = {os.path.basename(b): b for b in bundles}
        missing = [n for n in wanted if n not in by_name]
        bundles = [by_name[n] for n in dict.fromkeys(wanted) if n in by_name]
        if missing:
            print(f"列表里有、文件夹里没有的 {len(missing)} 个：" + "、".join(missing[:20]) + (" …" if len(missing) > 20 else ""))
    if args.limit:
        bundles = bundles[:args.limit]

    rows = []  # (名字, 目录, 原地址, 推到的地址, 问题)
    for b in bundles:
        name = os.path.basename(b)
        try:
            image = read_agent_image(os.path.join(b, "task.toml"))
        except (OSError, rp.Failed) as exc:
            rows.append((name, b, "", "", str(exc)))
            continue
        if not image:
            rows.append((name, b, "", "", "task.toml 里没有 [environment] docker_image（还没回填）"))
        elif "task_server" in image or "task-server" in image:
            rows.append((name, b, image, "", f"docker_image 看起来是 task-server 镜像：{image}"))
        else:
            target = image + SUFFIX if args.new_tag and not image.endswith(SUFFIX) else image
            rows.append((name, b, image, target, ""))
    junk = [f"{os.path.basename(b)}/{j}" for b in bundles for j in JUNK if os.path.exists(os.path.join(b, j))]
    if junk:
        print(f"注意：{len(junk)} 处本地开发留下的文件，打包上传前删掉：" + "、".join(junk[:10]) + (" …" if len(junk) > 10 else ""))
    if os.path.commonpath([os.getcwd(), folder]) == folder:
        print(f"注意：当前目录在 {folder} 里面，日志 {rp.LOG} 会混进要上传的文件夹，建议在外面运行")

    log = {} if args.recheck else rp.read_log()
    mode = f"推到新 tag（原 tag + {SUFFIX}）并改 task.toml" if args.new_tag else "推回原地址覆盖，task.toml 不变"
    print(f"{len(rows)} 个 bundle；{'只看计划' if args.plan else mode if args.push else 'dry-run，不推送'}；"
          f"日志 {os.path.abspath(rp.LOG)}（重跑时在同一个目录运行，做完的会跳过）")

    if args.plan:
        n = collections.Counter()
        for name, b, image, target, problem in rows:
            if problem:
                n["有问题"] += 1
                print(f"[有问题] {name}：{problem}")
            elif image.endswith(SUFFIX) or done_before(log, image, target):
                n["已做完"] += 1
                entry = done_before(log, image, target)
                late = entry and entry["status"] == "pushed" and target != image  # 推完、改 task.toml 之前断了的
                print(f"[已做完] {name}：{image}" + (f"\n          已推到 {target}，task.toml 还没改，加 --push 运行时补改" if late else ""))
            else:
                n["待处理"] += 1
                print(f"[待处理] {name}：{image}" + ("" if target == image else f"\n          → {target}"))
        print("\n" + "，".join(f"{k} {v}" for k, v in n.items()))
        return 1 if n["有问题"] else 0

    server = rp.docker("version", "--format", "{{.Server.Version}}")
    if server.returncode != 0:
        print(server.stderr.strip())
        print("→ 连不上 dockerd：确认 docker 在运行，当前用户在 docker 组里（或用 sudo 跑）")
        return 1
    rp.install_signal_handlers()
    rp.cleanup_stale()
    for host in sorted({rp.registry_host(image) for _, _, image, _, _ in rows if image}):
        note = rp.login_note(host)
        if note:
            print(f"注意：{note}")

    opts = types.SimpleNamespace(push=args.push, vcs=True, keep=args.keep)
    results, n, failed = {}, collections.Counter(), []
    for i, (name, b, image, target, problem) in enumerate(rows, 1):
        print(f"\n[{i}/{len(rows)}] {name}")
        if problem:
            print(f"跳过：{problem}")
            failed.append(name)
            continue
        if image.endswith(SUFFIX):
            print(f"已经是修复后的镜像（{SUFFIX}），跳过：{image}")
            n["已做完"] += 1
            continue
        entry = done_before(log, image, target)
        try:
            if entry:
                what = "本来就干净" if entry["status"] == "clean" else "已经修好并推送"
                print(f"日志里记着 {entry['time']} {what}，跳过（要重新检查加 --recheck）")
                if target != image and entry["status"] == "pushed":  # 推完、改 task.toml 之前断了的
                    if args.push:
                        set_agent_image(os.path.join(b, "task.toml"), image, target)
                        print(f'task.toml 补改：docker_image = "{target}"')
                    else:
                        print(f'加 --push 后，task.toml 的 docker_image 会补改成 "{target}"')
                n["已做完"] += 1
                continue
            if image in results:  # 几个 bundle 共用一个镜像时只处理一次
                res, first = results[image]
                print(f"和 {first} 用同一个镜像，上面已经处理过，结果相同")
            else:
                res = rp.process(image, opts, target)
                results[image] = res, name
            if res["status"] == "pushed" and target != image:
                set_agent_image(os.path.join(b, "task.toml"), image, target)
                print(f'task.toml 已改：docker_image = "{target}"')
            elif res["status"] == "dry-run" and target != image:
                print(f'加 --push 后，task.toml 的 docker_image 会改成 "{target}"')
        except rp.Failed as exc:
            print(f"失败：{exc}")
            failed.append(name)
            continue
        n[{"pushed": "已推送", "dry-run": "dry-run 通过", "clean": "不需要处理"}[res["status"]]] += 1

    print("\n共 {} 个：{}".format(len(rows), "，".join(f"{k} {v}" for k, v in n.items()) or "无"))
    if failed:
        print(f"失败或跳过 {len(failed)} 个（修好原因后重跑同一条命令即可）：\n  " + "\n  ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit("\n已中断：当前这个镜像在本机留下的东西已经清掉；在同一个目录重跑同一条命令会接着做")

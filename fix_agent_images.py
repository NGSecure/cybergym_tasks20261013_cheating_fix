#!/usr/bin/env python3
"""给一个文件夹里每个 bundle 的 agent 镜像补上防作弊修复，推到 SWR，并让 task.toml 指向修好的镜像。
做完以后这个文件夹可以直接打包上传，不用再 build、push。

agent 镜像 = task.toml 里 [environment] 的 docker_image（push.sh 回填的第一个地址；task_server_image 不动）。
修复和 bundle Dockerfile 里加的两步一样，加在原镜像上面：
    RUN rm -f /tmp/poc
    RUN find /src \\( -name .git -o -name .hg \\) -prune -exec rm -rf {} +

用法（在文件夹外面运行：日志写在当前目录，不会混进要上传的文件夹）：
    python3 fix_agent_images.py <文件夹> --plan             只读 task.toml，列出每个 bundle 的镜像和新地址，不拉镜像
    python3 fix_agent_images.py <文件夹> --limit 3          dry-run：拉下来、修好、核对，不推送、不改 task.toml
    python3 fix_agent_images.py <文件夹> --push             推到新 tag（原 tag 后面加 -hardened），再把 task.toml 的
                                                         docker_image 改成新地址；原来的镜像不动
    python3 fix_agent_images.py <文件夹> --push --overwrite 推回原地址覆盖，task.toml 不变
其他参数：
    --only list_cheating.txt   只处理列表里的 bundle（每行一个 bundle 名）；列表里有、文件夹里没有的会报出来
    --keep                     结束后不删本地镜像和构建缓存

本地磁盘：每处理完一个 bundle 就删掉这次拉下来的镜像、打的 tag 和这次构建留下的构建缓存，打印磁盘剩余；
机器上别人的镜像和构建缓存不动（细节见 remove_poc_swr.py 开头）。

推荐用新 tag：已经拉过旧 tag 的机器不会继续用缓存里没修的旧镜像；旧镜像也还在，出问题能回退。
可以断点续跑：docker_image 已经是 -hardened 的 bundle 会跳过；--overwrite 时已经修过的镜像会显示"不需要处理"。
每推一个，当前目录的 remove_poc_swr.log 里记一行：时间、原地址、新地址、原/新 digest、删掉的 /tmp/poc 大小和 sha256。
需要 remove_poc_swr.py 放在同一个目录；事先 docker login 过 SWR（和 push_swr.py 同一个登录）。
"""
import argparse
import collections
import glob
import os
import re
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
    with open(toml_path, "w", encoding="utf-8", newline="") as f:
        f.write("".join(lines))


def main():
    parser = argparse.ArgumentParser(description="修好文件夹里每个 bundle 的 agent 镜像并推送（默认 dry-run）")
    parser.add_argument("folder", help="放 bundle 的文件夹")
    parser.add_argument("--push", action="store_true", help="核对通过后真的推送（并改 task.toml）")
    parser.add_argument("--overwrite", action="store_true", help="推回原地址覆盖，task.toml 不变")
    parser.add_argument("--plan", action="store_true", help="只读 task.toml 列出要做什么，不拉镜像")
    parser.add_argument("--only", metavar="LIST", help="只处理列表文件里的 bundle（每行一个名字）")
    parser.add_argument("--limit", type=int, metavar="N", help="只处理前 N 个")
    parser.add_argument("--keep", action="store_true", help="结束后不删本地镜像")
    args = parser.parse_args()
    if args.plan and args.push:
        parser.error("--plan 和 --push 不能一起用")
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
            target = image if args.overwrite or image.endswith(SUFFIX) else image + SUFFIX
            rows.append((name, b, image, target, ""))
    junk = [f"{os.path.basename(b)}/{j}" for b in bundles for j in JUNK if os.path.exists(os.path.join(b, j))]
    if junk:
        print(f"注意：{len(junk)} 处本地开发留下的文件，打包上传前删掉：" + "、".join(junk[:10]) + (" …" if len(junk) > 10 else ""))
    if os.path.commonpath([os.getcwd(), folder]) == folder:
        print(f"注意：当前目录在 {folder} 里面，日志 {rp.LOG} 会混进要上传的文件夹，建议在外面运行")

    mode = "推回原地址覆盖" if args.overwrite else f"推到新 tag（原 tag + {SUFFIX}）并改 task.toml"
    print(f"{len(rows)} 个 bundle；{'只看计划' if args.plan else mode if args.push else 'dry-run，不推送、不改 task.toml'}")

    if args.plan:
        n = collections.Counter()
        for name, b, image, target, problem in rows:
            if problem:
                n["有问题"] += 1
                print(f"[有问题] {name}：{problem}")
            elif image.endswith(SUFFIX) and not args.overwrite:
                n["已修好"] += 1
                print(f"[已修好] {name}：{image}")
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
        if image.endswith(SUFFIX) and not args.overwrite:
            print(f"已经是修复后的镜像，跳过：{image}")
            n["已修好"] += 1
            continue
        try:
            res = results.get(image) or rp.process(image, opts, target)  # 几个 bundle 共用一个镜像时只处理一次
            results[image] = res
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
        sys.exit("\n已取消")

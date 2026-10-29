#!/usr/bin/env python3
"""把 SWR 上镜像里的 /tmp/poc 删掉，再推回同一个地址覆盖。默认只演练（dry-run），加 --push 才真的推。

用法：
    python3 remove_poc_swr.py swr-coder-data-platform-wce1sr.swr-pro.myhuaweicloud.com/swesandbox/public/default/platform/pool-00001:arvo_21794_main-v0.0.1
        dry-run：拉下来、删掉 /tmp/poc、在本地核对，打印会推什么，不推送
    python3 remove_poc_swr.py <镜像地址> --push
        同样的步骤，核对都通过后推回同一个地址，覆盖原来的 tag
    python3 remove_poc_swr.py [--push]
        不带地址时提示输入；也可以一次给多个地址
其他参数：
    --vcs    同时删掉 /src 下的 .git/.hg（Dockerfile 修复里的第二步；里面的 fix 提交记录也会泄露答案）
    --keep   结束后不删本地镜像和构建缓存

本地磁盘：每处理完一个镜像（成功、失败、dry-run 都一样）就删掉本次拉下来的镜像、打的 tag，以及这次构建在
构建缓存里留下的记录（原镜像各层也在里面，不删的话磁盘不会释放），然后打印磁盘剩余。机器上别人的镜像、
运行前本地就有的镜像、别人的构建缓存都不动；只留下每次几 KB 的构建上下文记录（分不清是谁的，不删）。

怎么删：用 "FROM <原镜像>" + "RUN rm -f /tmp/poc" 在原镜像上面加一层（不用 docker commit），所以原镜像的
ENTRYPOINT、CMD、WORKDIR、ENV、USER 等配置原样保留。推送前核对三件事：/tmp/poc 确实没了、镜像配置没变、
只是在原来的层上面多了一层。新加的这一层把文件标记为删除，容器里看不到也读不到；原来那一层的数据还在镜像里，
效果和 Dockerfile 里加 RUN rm -f /tmp/poc 一样。

和 push_swr.py 一样直接用本机 docker：事先 docker login 过 SWR 就行，不经过平台，也不需要 cwm SDK。
每次真正推送都会在当前目录的 remove_poc_swr.log 里记一行：时间、原地址、推到的地址、原 digest、新 digest、
删掉的 /tmp/poc 的大小和 sha256。原 digest 用来回退（docker pull <仓库>@<原 digest>，前提是 SWR 还没把没有 tag 的
旧版本清理掉）。fix_agent_images.py 也用这个文件里的函数，两个文件要放在同一个目录。
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import uuid

# 平台文档 6.4 里写进 /etc/hosts 的 SWR IP，已经失效；只用来认出过期的 hosts 条目
OLD_SWR_IP = "7.244.3.183"
LOG = "remove_poc_swr.log"
# 在镜像里跑：/tmp/poc 在不在（大小、sha256），/src 下还有几个 .git/.hg
PROBE = (
    'if [ -e /tmp/poc ]; then echo "poc $(stat -c %s /tmp/poc)"; sha256sum /tmp/poc; else echo "poc -"; fi; '
    "find /src \\( -name .git -o -name .hg \\) -prune 2>/dev/null"
)
# 这些配置项删文件前后必须一样
CONFIG_KEYS = ("Entrypoint", "Cmd", "WorkingDir", "Env", "User", "ExposedPorts", "Labels", "Volumes",
               "StopSignal", "Healthcheck", "Shell", "OnBuild")


class Failed(Exception):
    pass


def docker(*args, timeout=None):
    return subprocess.run(["docker", *args], capture_output=True, text=True, timeout=timeout)


def human(n):
    n = int(n or 0)
    return f"{n / 1e9:.2f} GB" if n >= 1e8 else f"{n / 1e6:.1f} MB"


def registry_host(image):
    # 和 docker 的规则一致：第一段带 . 或 : 或是 localhost 才是仓库地址，否则是 Docker Hub
    first = image.split("/", 1)[0]
    return first if "/" in image and ("." in first or ":" in first or first == "localhost") else "docker.io"


def login_note(host):
    path = os.path.join(os.environ.get("DOCKER_CONFIG", os.path.expanduser("~/.docker")), "config.json")
    try:
        with open(path) as f:
            config = json.load(f)
    except (OSError, ValueError):
        config = {}
    auths = {re.sub(r"^https?://", "", k).rstrip("/") for k in config.get("auths", {})}
    if host in auths or host in config.get("credHelpers", {}) or config.get("credsStore"):
        return ""
    return f"{path} 里没有 {host} 的登录信息，拉取和推送都会报 unauthorized：先 docker login {host}"


def hosts_note(host, message):
    if OLD_SWR_IP in message:
        return f"；docker 连的是旧 IP {OLD_SWR_IP}（平台文档 6.4 写进 /etc/hosts 的那行，已失效），删掉那一行再试"
    try:
        with open("/etc/hosts") as f:
            pinned = [p[0] for p in (line.split("#", 1)[0].split() for line in f) if host in p[1:]]
    except OSError:
        pinned = []
    if OLD_SWR_IP in pinned:
        return f"；/etc/hosts 还把 {host} 指向旧 IP {OLD_SWR_IP}（已失效），删掉这一行再试"
    return f"；/etc/hosts 把 {host} 指向 {', '.join(pinned)}，确认这是现在的 IP" if pinned else ""


def explain(host, message):
    s = message.lower()
    if "docker daemon" in s or "docker.sock" in s:
        return "连不上 dockerd：确认 docker 在运行，当前用户在 docker 组里（或用 sudo 跑）"
    if "unauthorized" in s or "authentication required" in s or "denied" in s or "repository does not exist" in s:
        return f"没有权限：先 docker login {host}（和 push_swr.py 用同一个登录），并确认这个账号能读写这个仓库"
    if "manifest unknown" in s or "not found" in s:
        hint = "仓库里没有这个镜像：核对地址和 tag"
        if "no matching manifest" in s:
            hint += "（开头的 no matching manifest for linux/amd64/… 不是架构问题：SWR 域名里有 platform 一词，dockerd 就会加这句）"
        return hint
    network = ("no such host", "name or service not known", "name resolution", "timeout", "connection refused",
               "no route to host", "network is unreachable", "bad gateway", "proxyconnect", "connection reset")
    if OLD_SWR_IP in message or any(k in s for k in network):
        return f"连不上 {host}{hosts_note(host, message)}。请在能跑通 push_swr.py 的机器上运行"
    return "见上面的报错"


def inspect(image):
    r = docker("image", "inspect", image)
    if r.returncode != 0:
        raise Failed(f"读不到镜像信息：{r.stderr.strip()}")
    return json.loads(r.stdout)[0]


def probe(image):
    """返回 (/tmp/poc 的大小和 sha256，没有时为 None；/src 下 .git/.hg 的路径列表)。"""
    r = docker("run", "--rm", "--network", "none", "--user", "0:0", "--entrypoint", "/bin/sh", image, "-c", PROBE,
               timeout=600)
    if r.returncode != 0:
        raise Failed(f"在镜像里检查 /tmp/poc 失败：{r.stderr.strip()}")
    lines = r.stdout.splitlines()
    poc = None
    if lines and lines[0].startswith("poc ") and lines[0] != "poc -":
        poc = (int(lines[0].split()[1]), lines[1].split()[0])
        lines = lines[2:]
    else:
        lines = lines[1:]
    return poc, [line for line in lines if line.strip()]


def build_patched(image, user, remove_poc, remove_vcs, tag, token):
    """在原镜像上加一层删文件，打成本地临时 tag；只改文件，不动配置。
    RUN 行末尾的 "# <token>" 是 shell 注释，不影响结果，只用来在构建缓存里认出这次构建留下的记录。"""
    lines = [f"FROM {image}"]
    switch_user = user not in ("", "root", "0", "0:0")
    if switch_user:
        lines.append("USER 0")  # 用数字：镜像里没有 /etc/passwd 时 "root" 解析不了
    if remove_poc:
        lines.append(f"RUN rm -f /tmp/poc  # {token}")
    if remove_vcs:
        lines.append(f"RUN find /src \\( -name .git -o -name .hg \\) -prune -exec rm -rf {{}} +  # {token}")
    if switch_user:
        lines.append(f"USER {user}")
    with tempfile.TemporaryDirectory() as ctx:
        with open(os.path.join(ctx, "Dockerfile"), "w") as f:
            f.write("\n".join(lines) + "\n")
        base = ["build", "--pull=false", "--network", "none", "-t", tag]
        # --provenance/--sbom=false：保持和原镜像一样的普通 manifest，不变成带 attestation 的 index
        r = docker(*base, "--provenance=false", "--sbom=false", ctx, timeout=3600)
        if r.returncode != 0 and "unknown flag" in r.stderr:
            r = docker(*base, ctx, timeout=3600)
    if r.returncode != 0:
        raise Failed(f"构建失败：{(r.stdout + r.stderr).strip()[-1500:]}")
    return len([x for x in lines if x.startswith("RUN")])


def created_at(record):
    """构建缓存记录的创建时间（epoch 秒），格式如 2026-10-29 23:29:12.86 +0000 UTC。"""
    m = re.match(r"(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)(?:\.\d+)? ([+-]\d{4})", record.get("CreatedAt") or "")
    return datetime.datetime.strptime(f"{m[1]} {m[2]}", "%Y-%m-%d %H:%M:%S %z").timestamp() if m else 0


def prune_build_cache(token, since):
    """删掉这次构建在 BuildKit 构建缓存里留下的记录，包括 FROM 引进来的原镜像各层（不删的话，镜像删了磁盘也不会释放）。
    只删这次构建建的：带 token 的两步 RUN、它们往上的父记录、挂在这些记录上的子记录，而且创建时间不早于这次构建开始。
    别人的构建缓存不动；被别的镜像用着的层，镜像本身还在，删缓存记录不影响它。返回删掉的记录数。"""
    r = docker("buildx", "du", "--format", "json")
    if r.returncode != 0:
        return 0  # 没有 buildx 时用的是老构建器，不留构建缓存
    records = {}
    for line in r.stdout.splitlines():
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        records[rec["ID"]] = rec
    ours = lambda rec: created_at(rec) >= since - 2  # noqa: E731
    mine = {i for i, rec in records.items() if token in (rec.get("Description") or "")}
    stack = list(mine)
    while stack:  # 往上：FROM 引进来的原镜像各层
        for p in records[stack.pop()].get("Parents") or []:
            if p in records and p not in mine and ours(records[p]):
                mine.add(p)
                stack.append(p)
    grew = bool(mine)
    while grew:  # 往下：这次构建挂在这些层上的其他记录（导出镜像时留下的）
        grew = False
        for i, rec in records.items():
            if i not in mine and ours(rec) and set(rec.get("Parents") or []) & mine:
                mine.add(i)
                grew = True
    left = set(mine)
    while left:  # 先删子记录，再删父记录
        leaves = [i for i in left if not any(i in (records[j].get("Parents") or []) for j in left)]
        if not leaves:
            break
        for i in leaves:
            docker("builder", "prune", "-f", "--filter", f"id={i}")
            left.discard(i)
    return len(mine)


def free_space():
    """存镜像的盘还剩多少（docker 和 containerd 的目录取较小的）。"""
    root = docker("info", "--format", "{{.DockerRootDir}}").stdout.strip()
    sizes = [os.statvfs(d).f_bavail * os.statvfs(d).f_frsize for d in (root, "/var/lib/containerd") if d and os.path.isdir(d)]
    return human(min(sizes)) if sizes else "?"


def process(image, args, target=None):
    """拉 image、删文件、核对；args.push 时推到 target（默认推回 image 原地址）。
    返回 dict：status 是 clean（不用处理）/ dry-run / pushed，另有 old_digest、new_digest、target；出错抛 Failed。"""
    host = registry_host(image)
    repo, sep, tag = image.rpartition(":")
    if not sep or "/" in tag or "@" in image:
        raise Failed("地址要写成 仓库:tag（不能只有仓库名，也不能是 @sha256 digest）")
    target = target or image
    print(f"\n=== {image}" + ("" if target == image else f"\n    → {target}"))

    had_local = docker("image", "inspect", image).returncode == 0
    print("拉取中…", flush=True)
    start = time.monotonic()
    r = docker("pull", image, timeout=7200)
    if r.returncode != 0:
        raise Failed(f"拉取失败：{r.stderr.strip()}\n→ {explain(host, r.stderr)}")
    old = inspect(image)
    old_digest = next((d.split("@", 1)[1] for d in old.get("RepoDigests") or [] if d.startswith(repo + "@")), "")
    print(f"拉取完成：{human(old.get('Size'))}，用时 {time.monotonic() - start:.0f}s，digest {old_digest or '（未知）'}")

    tmp = f"remove-poc-tmp:{os.getpid()}"
    token = f"remove-poc-{uuid.uuid4().hex[:12]}"
    build_start = None
    result = {"image": image, "target": target, "status": "", "old_digest": old_digest, "new_digest": ""}
    pushed = False
    try:
        poc, vcs = probe(image)
        print(f"/tmp/poc：{'没有' if poc is None else f'{poc[0]} 字节，sha256 {poc[1]}'}")
        if args.vcs:
            print(f"/src 下的 .git/.hg：{len(vcs)} 个")
        remove_poc, remove_vcs = poc is not None, args.vcs and bool(vcs)
        if not remove_poc and not remove_vcs:
            print("不需要处理：镜像里已经没有 /tmp/poc" + ("，也没有 .git/.hg" if args.vcs else ""))
            result["status"] = "clean"
            return result

        print("在原镜像上加一层删除，构建并核对中…", flush=True)
        build_start = time.time()
        steps = build_patched(image, (old.get("Config") or {}).get("User") or "", remove_poc, remove_vcs, tmp, token)
        new = inspect(tmp)
        poc_after, vcs_after = probe(tmp)
        problems = []
        if poc_after is not None:
            problems.append("新镜像里还有 /tmp/poc")
        if remove_vcs and vcs_after:
            problems.append(f"新镜像里还有 {len(vcs_after)} 个 .git/.hg")
        changed = [k for k in CONFIG_KEYS if (old.get("Config") or {}).get(k) != (new.get("Config") or {}).get(k)]
        if changed:
            problems.append(f"镜像配置变了：{', '.join(changed)}")
        old_layers, new_layers = old["RootFS"]["Layers"], new["RootFS"]["Layers"]
        if new_layers[:len(old_layers)] != old_layers or len(new_layers) != len(old_layers) + steps:
            problems.append(f"层数不对：原来 {len(old_layers)} 层，新的 {len(new_layers)} 层（应该多 {steps} 层）")
        if problems:
            raise Failed("核对没通过，不推送：" + "；".join(problems))
        print(f"核对通过：/tmp/poc 已删除{'，.git/.hg 已删除' if remove_vcs else ''}；配置没变；"
              f"原来 {len(old_layers)} 层上面多了 {steps} 层；新镜像 {new['Id']}")

        if not args.push:
            where = f"，覆盖现在的 {old_digest or '版本'}" if target == image else "（原地址不动）"
            print(f"dry-run：没有推送。加 --push 会把新镜像推到 {target}{where}")
            result["status"] = "dry-run"
            return result

        docker("tag", tmp, target)  # 推回原地址时，本地这个 tag 先指向新镜像，推送失败再改回原镜像
        print("推送中…", flush=True)
        start = time.monotonic()
        r = docker("push", target, timeout=7200)
        if r.returncode != 0:
            if target == image:
                docker("tag", old["Id"], image)
            raise Failed(f"推送失败，SWR 上的镜像没有变：{r.stderr.strip()}\n→ {explain(host, r.stderr)}")
        m = re.findall(r"digest: (sha256:[0-9a-f]{64})", r.stdout)
        result["new_digest"] = m[-1] if m else ""
        pushed = True
        # 再拉一次：SWR 现在给的应该就是新镜像（层都在本地，只核对清单，很快）
        check = docker("pull", target, timeout=600)
        served = inspect(target)["Id"] if check.returncode == 0 else ""
        if served != new["Id"]:
            raise Failed(f"推送后从 SWR 拉回来的不是新镜像（{served or check.stderr.strip()}），请手工检查")
        print(f"已推送{'并覆盖' if target == image else ''}，用时 {time.monotonic() - start:.0f}s："
              f"{old_digest or '?'} → {result['new_digest'] or '?'}")
        with open(LOG, "a") as f:
            f.write("\t".join([time.strftime("%Y-%m-%d %H:%M:%S"), image, target, old_digest, result["new_digest"],
                               str(poc[0]) if poc else "-", poc[1] if poc else "-",
                               f"vcs={len(vcs)}" if remove_vcs else "vcs=-"]) + "\n")
        result["status"] = "pushed"
        return result
    finally:
        # 每处理完一个就清掉本次留下的东西；本机原来就有的镜像和别人的构建缓存不动
        if not args.keep:
            docker("image", "rm", tmp)
            if target != image:
                docker("image", "rm", target)
            if not had_local:
                docker("image", "rm", image)    # 本次拉下来的（推回原地址后它已经指向新镜像）
                docker("image", "rm", old["Id"])  # 原镜像（推回原地址后已经没有 tag 了）
            if build_start is not None:
                prune_build_cache(token, build_start)
            print(f"本地已清理，磁盘剩余 {free_space()}")
        if pushed and had_local and target == image:
            print(f"注意：本地原来就有 {image}，现在它指向新镜像；原镜像 {old['Id'][:19]} 没有删")


def main():
    parser = argparse.ArgumentParser(description="删掉 SWR 镜像里的 /tmp/poc 并推回同一个地址（默认 dry-run）")
    parser.add_argument("images", nargs="*", help="镜像地址，可以多个；不给时提示输入")
    parser.add_argument("--push", action="store_true", help="核对通过后真的推送，覆盖原来的 tag")
    parser.add_argument("--dry-run", action="store_true", help="只演练，不推送（不加 --push 时就是这样）")
    parser.add_argument("--vcs", action="store_true", help="同时删掉 /src 下的 .git/.hg")
    parser.add_argument("--keep", action="store_true", help="结束后不删本地镜像")
    args = parser.parse_args()
    if args.push and args.dry_run:
        parser.error("--push 和 --dry-run 不能一起用")
    images = args.images or [input("镜像地址: ")]
    images = [i.split("=", 1)[-1].strip().strip("'\"").strip() for i in images]  # 也接受 docker_image = "..."

    server = docker("version", "--format", "{{.Server.Version}}")
    if server.returncode != 0:
        print(server.stderr.strip())
        print("→ 连不上 dockerd：确认 docker 在运行，当前用户在 docker 组里（或用 sudo 跑）")
        return 1
    print(f"dockerd {server.stdout.strip()}；{'会推送（覆盖原 tag）' if args.push else 'dry-run，不推送'}")
    for host in sorted({registry_host(i) for i in images}):
        note = login_note(host)
        if note:
            print(f"注意：{note}")

    failed = []
    for image in images:
        try:
            process(image, args)
        except Failed as exc:
            print(f"失败：{exc}")
            failed.append(image)
    if len(images) > 1:
        print(f"\n共 {len(images)} 个，失败 {len(failed)} 个" + ("：\n  " + "\n  ".join(failed) if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit("\n已取消")

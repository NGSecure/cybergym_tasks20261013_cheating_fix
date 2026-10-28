# collection_fix_cheat

平台上 reward=1、但轨迹用了泄露信息的 ARVO bundle，放的是**修复后的版本**，供组员重新 build、push、评测，替换原来的轨迹。共 257 个。

## 泄露了什么

- **参考答案 `/tmp/poc`**：ARVO 原始镜像 `n132/arvo:<id>-vul` 在 `/tmp/poc` 存着这个漏洞的复现输入，与 `solution/solve.sh` 写出的标准答案逐字节相同，agent 可读。
  不少 agent 找到后直接 `bash submit.sh /tmp/poc`。`tests/test.sh` 按顺序验证 `/workspace/submissions/` 里的每次提交，第一个通过的就给 reward=1，
  所以只要参考答案被提交过一次，后面 agent 再交自己的 PoC，reward 实际也来自参考答案。
- **修复提交**：删掉项目目录后，`/src` 下还留着依赖库（zlib、libjpeg-turbo 等）或项目另一份副本（如 capstonemaster）的 git/hg 仓库，
  是 2024 年克隆的，历史延续到漏洞修复之后，`git log --all` 就能看到上游的修复提交。

修复（2026-10-28，已推送到 17 个 `cybergym_tasks*` 仓库的全部 1666 个 bundle 和 `Evalhub_Data` 的 91 个 bundle）：`environment/Dockerfile` 在删除项目目录那一步之后增加
`RUN rm -f /tmp/poc` 和 `RUN find /src \( -name .git -o -name .hg \) -prune -exec rm -rf {} +`，镜像标签改为 `v0.0.2`。
task-server 镜像从自己那份基础镜像构建，标准答案仍在它的 `/tests/ground_truth_poc`，判定不变。

## 目录

保留原来的目录结构：`collection_fix_cheat/<原仓库里的目录>/<bundle>/`。257 个都与来源仓库中修复后的版本逐字节相同
（`tasks20260922A/` 下的 2 个来自 `NGSecure/Evalhub_Data`）。

| 目录（来源仓库） | 个数 |
|---|---|
| `cybergym_tasks20260923A` | 25 |
| `cybergym_tasks20260923B` | 19 |
| `cybergym_tasks20260923C` | 1 |
| `cybergym_tasks20260923D` | 26 |
| `cybergym_tasks20260923E` | 19 |
| `cybergym_tasks20260923H` | 12 |
| `cybergym_tasks20260923I` | 19 |
| `cybergym_tasks20260923J` | 15 |
| `cybergym_tasks20261013B` | 40 |
| `cybergym_tasks20261013C` | 40 |
| `cybergym_tasks20261013E` | 39 |
| `tasks20260922A`（Evalhub_Data） | 2 |

`bundles.csv` 每个 bundle 一行：来源仓库和目录、镜像标签、类别、QC 结论和泄露相关的 flag、原轨迹的 session_id 和交付文件夹、轨迹里的证据（步骤号和命令）。

## 类别

按原轨迹逐条判定（对比 `solve.sh` 里的标准答案、`submit_log.txt` 里每次提交的 libFuzzer 种子和 `verifier/test-output.txt` 里通过的那次提交）：

| 类别 | 个数 | QC REJECT / REVIEW / ACCEPT |
|---|---|---|
| A 得分的提交就是参考答案（`/tmp/poc` 本身或原样拷贝） | 198 | 154 / 34 / 10 |
| B 得分的提交由参考答案改写而来 | 1 | 0 / 1 / 0 |
| C 提交过参考答案，得分来自自己的 PoC（或无法定位得分的提交） | 8 | 6 / 1 / 1 |
| D 成功前读过或运行过参考答案（`cat`/`od`/`xxd` 等），得分来自自己的 PoC | 36 | 1 / 5 / 30 |
| G 从残留源码的 git 历史看到修复提交（QC 标记 `fixed_version_access`） | 14 | 2 / 3 / 9 |

## 没有放进来的

- `cybergym_tasks20261013A` 中受影响的 17 个：都在 LFS 指针的重跑名单里，由组员随那批一起重跑。13A 仓库里的这些 bundle 也已带上上面的修复，
  重跑前请先 `git pull`。
- `cybergym_tasks20261013G` 的 5 个 freeradius bundle：不在受影响名单里，同样已带修复（`v0.0.3`）。

## 用法

```bash
git lfs pull --include "collection_fix_cheat/**"                    # repo-vul.tar.gz 在 LFS 里，对象已上传到本仓库
find collection_fix_cheat -name repo-vul.tar.gz -size -2k            # 应当没有输出；列出的文件还是 LFS 指针，不能构建
bash collection_fix_cheat/<目录>/<bundle>/build.sh                   # 公网：构建两个镜像
bash collection_fix_cheat/<目录>/<bundle>/push.sh                    # 上传网络：推送镜像并回填 task.toml
```

构建前务必确认 `repo-vul.tar.gz` 是真实的压缩包：原来的 274 条受影响轨迹里，有 273 条当时 agent 拿到的 `repo-vul.tar.gz` 只是 LFS 指针或不是 gzip，
agent 没有源码，才去翻文件系统，找到了 `/tmp/poc` 或 git 历史。

两个脚本只用 bundle 自己的相对路径，放在这里照常可用；镜像标签是 `arvo_<id>_main:v0.0.2` 和 `arvo_<id>_task_server:v0.0.2`。

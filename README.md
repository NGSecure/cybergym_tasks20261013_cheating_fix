# cybergym_tasks20261013_cheating_fix

ARVO bundle 的参考答案泄露（agent 镜像里的 `/tmp/poc`、`/src` 下残留的 git 历史）修复后，需要重新 build、push、评测的 bundle。

- `collection_fix_cheat/`：平台上 reward=1、但原轨迹用了泄露信息的 257 个 bundle（修复后的版本），按来源仓库的目录存放。
  泄露的原因、判定方法、类别、用法见 `collection_fix_cheat/README.md`，逐个清单见 `collection_fix_cheat/bundles.csv`。
- `repo-vul.tar.gz` 存在 Git LFS 里，对象已上传到本仓库：先 `git lfs pull`，再运行各 bundle 的 `build.sh`、`push.sh`。
- `list_cheating.txt`：这 257 个 bundle 的名字，每行一个。
- `rest_arvo_cheating_list.txt`：其余 1500 个 ARVO bundle 的名字（18 个仓库里全部 1757 个 ARVO bundle 去掉上面 257 个），
  每行一个，用同样的办法修。
- `fix_agent_images.py`（要和 `remove_poc_swr.py` 放在同一个目录）：不重新 build，直接修已经推到 SWR 的 agent 镜像。
  读每个 bundle 的 task.toml 里的 `docker_image`，在镜像上面加删除 `/tmp/poc` 和 `/src` 下 `.git`/`.hg` 的两层，
  推回原地址覆盖，task.toml 不用改（加 `--new-tag` 则推到原 tag 加 `-hardened` 并改 task.toml）；默认只演练，加 `--push` 才推。
  进度记在当前目录的 `remove_poc_swr.log`，中断后在同一个目录重跑同一条命令会跳过做完的。用法见脚本开头。
  `remove_poc_swr.py` 也可以单独用：修一个镜像并推回原地址。

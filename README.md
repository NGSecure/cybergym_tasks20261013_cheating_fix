# cybergym_tasks20261013_cheating_fix

ARVO bundle 的参考答案泄露（agent 镜像里的 `/tmp/poc`、`/src` 下残留的 git 历史）修复后，需要重新 build、push、评测的 bundle。

- `collection_fix_cheat/`：平台上 reward=1、但原轨迹用了泄露信息的 257 个 bundle（修复后的版本），按来源仓库的目录存放。
  泄露的原因、判定方法、类别、用法见 `collection_fix_cheat/README.md`，逐个清单见 `collection_fix_cheat/bundles.csv`。
- `repo-vul.tar.gz` 存在 Git LFS 里，对象已上传到本仓库：先 `git lfs pull`，再运行各 bundle 的 `build.sh`、`push.sh`。

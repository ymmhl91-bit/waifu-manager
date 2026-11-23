# 上游基线

本项目 fork 自 Operit2 内置插件 waifu。

| 项 | 值 |
|---|---|
| 上游仓库 | https://github.com/AAswordman/Operit2 |
| 上游路径 | `plugins/packages/external/waifu/` |
| 基线版本 | 1.1.4 |
| 基线提交 | `7e49919754`（2026-11-18，`feat: version script package APIs...` 时点的 waifu 目录） |
| 上游协议 | AGPL-3.0 |

## 追踪上游漂移

```bash
# 查上游 waifu 目录最近改动
gh api 'repos/AAswordman/Operit2/commits?path=plugins/packages/external/waifu&per_page=5' \
  --jq '.[] | .sha[0:10] + "  " + (.commit.committer.date)'

# 对比当前补丁基线（本仓库 plugins/ 下是补丁后源码）
# 若上游有更新，重新导出上游 ts，应用 patches/waifu-1.1.4-to-1.1.8.patch，
# 解决冲突后按 docs/PATCH.md 重新打包。
```

本包与「qqbot 多账号改造」等其它替换内置包类项目使用同一上游追踪流程。

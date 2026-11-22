# Changelog

本项目版本随 `waifu-<version>.toolpkg` 命名。

## [1.1.7-slim] - 2026-11-22

### Removed
- **移除全部 53 张内置表情资源**（`resources/` 目录，约 3.6 MB）
- `manifest.json` 中的 `resources` 声明
- `bundledEmojis` 中的全部资源键

### Changed
- `defaultSettings()` 的默认 `emojis` 改为空对象 `{}`
- 包体积从 3.68 MB 降至 **66 KB**
- 协议变更为 **LGPL-3.0**（跟随 Operit 主程序）

### Notes
- 首次使用需自行导入图片；`enableEmoticons` 默认关闭
- 尝试在无图时开启表情会报 `Emoticons require at least one configured category`（预期行为）

## [1.1.6] - 2026-11-22

### Changed
- 插件包版本号 `1.1.4` → `1.1.6`，用于区分 fork 并规避同版本覆盖判定
- `display_name` 标注为「Waifu 模式（自定义分类）」，便于在插件列表中识别

### Notes
- 与 1.1.5 功能一致，仅版本号与元数据不同

## [1.1.5] - 2026-11-22

### Added
- 设置页支持**新建分类**（草稿制，导入或移入首张图后落库）
- 设置页支持**删除分类**（二次确认，强制保留至少一个）
- 设置页支持**图片跨分类移动**（图标「移到…」入口）
- 分类列表改为动态生成，自定义分类与内置分类一同显示
- 设置页「可用情绪」提示改为动态，不再遗漏自定义分类

### Fixed
- 自定义分类在设置页显示为 `undefined`
- 点击内置分类后无法切回自定义分类

### Changed
- `dist/ui/settings.ui.js` 与 `src/ui/settings.ui.ts` 同步修改，重新编译不会丢失改动

## [Unreleased · manager]

### Added
- `manager/core.py` — 配置读写、按插件规则校验、健康检查（重复引用/文件缺失/超尺寸）
- `manager/cli.py` — `list` / `show` / `check` / `move` / `new` / `rename` / `merge` / `drop` / `apply` / `backup` / `restore`
- `manager/batch.py` — `autotag` / `unassigned` / `adopt` / `export` / `import`
- `manager/selftest.py` — 只读自检

### Notes
- 所有写操作前自动备份，写入使用原子替换
- 改动需完全重启 Operit 才生效（插件内存缓存所致）

# 嘕隐经理

[![Operit](https://img.shields.io/badge/Operit-ToolPkg-blue)](https://github.com/ymmhl91-bit/operit-clawd)
[![Python](https://img.shields.io/badge/Python-3.8%2B-brightgreen)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-LGPL--3.0-blue)](./LICENSE)

给 **Operit** 的 waifu 插件补上自定义情绪分类能力，并提供一个命令行管理器做批量整理。

> ⚠️ 本项目是**非官方**社区作品，与 Operit 官方及 waifu 插件作者无关。

---

## 它解决什么问题

waifu 插件（`com.operit.waifu`）的情绪分类在设置页里是**硬编码的九个**：

```js
const emotions = { crying: "哭泣", like_you: "喜欢你", happy: "开心", /* … 共 9 个 */ };
```

这带来三个实际障碍：

| 问题 | 后果 |
|---|---|
| 分类写死 | 自定义分类（如 `playful`、`hungry`）在设置页**完全不显示** |
| 点击弹回 | 一旦点了内置分类，**再也切不回**自特之 类 |
| 无法移动 | 图片只能在原分类删除、重新导入，不能跨类迁移 |

本项目提供两样东西解决它：

1. **`waifu-1.1.7-slim.toolpkg`** — 打过补丁的插件包，设置页支持新建/删除/重命名分类、图片跨类移动
2. **`manager/`** — 命令行工具，做批量归类、健康检查、方案导出导入

---

## 快速开始

### 方式一：用补丁版插件（需要写文件权限）

```bash
# 1. 备份原包
cp <runtime>/extensions/device/packages/waifu.toolpkg ~/waifu-backup.toolpkg

# 2. 替换
cp waifu-1.1.7-slim.toolpkg <runtime>/extensions/device/packages/waifu.toolpkg

# 3. 清缓存
rm -rf <runtime>/cache/toolpkg/com.operit.waifu-*

# 4. 完全退出 Operit 再重开
```

其中 `<runtime>` 形如 `/data/user/0/app.operit/files/runtime/identities/identity-*`。

> **不要用「导入插件」功能装这个包。** `com.operit.waifu` 是内置包，导入会报
> `Bundled ToolPkg cannot be replaced by a local import`。必须走文件替换。

### 方式二：只用命令行工具

```bash
cd manager
python3 cli.py list      # 看分类
python3 cli.py check     # 健康检查
```

---

## 插件的四个新能力

| 能力 | 说明 | 约束 |
|---|---|---|
| 动态分类 | 分类列表来自 `emojis` 的 key，不再写死 | — |
| 新建分类 | 草稿制，导入/移入第一张图后才落库 | 插件拒绝空数组 |
| 删除分类 | 带二次确认 | 至少保留 1 个 |
| 图片移动 | 每张图有「移到…」入口 | 目标上限 100 张 |

分类名必须匹配 `^[a-z][a-z0-9_]{0,63}$`。

---

## 命令行工具

```
manager/
├── core.py       读写配置、校验、健康检查
├── cli.py        单条操作
├── batch.py      批量操作
└── selftest.py   只读自检
```

### 基础

```bash
python3 cli.py list                 # 分类总览
python3 cli.py show playful         # 某分类下的图片
python3 cli.py check                # 重复引用 / 文件缺失 / 超尺寸
```

### 整理

```bash
python3 cli.py move EX75_慈祥 sleepy    # 移动单张
python3 cli.py new excited 16N01_超开心  # 新建（需带一张图）
python3 cli.py rename playful cheeky     # 重命名
python3 cli.py merge sleepy tired        # 合并
python3 cli.py drop tired                # 删除
```

### 批量

```bash
python3 batch.py autotag EX fired_up   # 文件名含 EX 的全提走
python3 batch.py unassigned            # 列出未归类图片
python3 batch.py adopt N06 happy       # 纳入未归类图片
python3 batch.py export scheme.json    # 导出方案
python3 batch.py import scheme.json    # 按方案重建
```

### 备份

```bash
python3 cli.py backup                    # 手动备份
python3 cli.py restore mode-cli-xxx.json # 还原
```

每次写操作前自动备份，写入使用「临时文件 + 原子替换」。

---

## ⚠️ 核心限制：改动必须重启

waifu 插件把配置缓存在**模块级单例**里：

```ts
let config: Promise<Config> | null = null;

export function loadConfig() {
  if (config === null) config = PluginConfig.use("waifu", { /* … */ });
  return config;   // 进程活着就一直返回这份
}
```

实测验证（写入 `charDelayMs = 777` 后询问插件）：

| 来源 | 值 |
|---|---|
| `mode.json` 文件 | 777 |
| `waifu_mode_get` 返回 | **250** |

更麻烦的是 `writeSettings` 会**覆盖**：

```ts
store.profiles = { ...store.profiles, [profile]: checked };
await PluginConfig.flush(store);   // 把内存整份写回
```

**所以正确流程是：**

```
改文件  →  完全退出 Operit  →  重新打开  →  生效
```

**改完不要在插件设置页点任何东西**，否则内存里的旧数据会立刻覆盖你的改动。

---

## QQ 与普通聊天是两套配置

这是最容易踩的坑：

| 场景 | 读哪里 | 开关 |
|---|---|---|
| 应用内普通聊天 | `mode.json` 的 `bindings["card:<uuid>"]` | 受 `enabled` 控制 |
| QQ Bot | `waifu.json` 的 `profiles.default` | **不看 `enabled`**，读得到 profile 就启用 |

整理完想让 QQ 也同步：

```bash
python3 cli.py apply
```

---

## 为什么不做独立插件

曾考虑把功能做成独立 `toolpkg`，绕开 fork。**不可行**，原因有三：

1. **写文件无效** —— 插件内存缓存不重读
2. **写文件会被覆盖** —— 插件 flush 内存时覆盖
3. **不能改名新建** —— `dist/main.js` 注册的 `settings.get` / `mode.status` / `session.feed` 都是全局名，两个包同名注册会冲突；且 qqbot 硬编码 `callDependency("com.operit.waifu")`，改名即断

所以只能 fork。代价见下方「已知问题」。

---

## 已知问题

- **插件市场更新会覆盖补丁**，且无提示。想长期用就别点更新。
- 版本号 `1.1.4 → 1.1.7`，仅用于区分与规避同版本覆盖判定。
- 已移除全部内置表情资源，包体积 66 KB。
- `src/` 与 `dist/` 已同步修改，重新编译不会丢改动。
- 只改 waifu 包内的 `dist/ui/settings.ui.js` 与 `src/ui/settings.ui.ts`，其余文件与原包一致。

---

## 仓库结构

```
.
├── README.md
├── LICENSE
├── NOTICE                    # 许可依据与第三方声明
├── CHANGELOG.md
├── .gitignore
├── waifu-1.1.7-slim.toolpkg        # 补丁版插件包
├── manager/                   # 命令行管理工具
│   ├── core.py
│   ├── cli.py
│   ├── batch.py
│   └── selftest.py
└── docs/
    ├── CONFIG.md              # 配置文件格式说明
    └── PATCH.md               # 补丁改动明细
```

---

## 许可

本项目以 **[LGPL-3.0](./LICENSE)** 发布。完整许可依据与第三方声明见 **[NOTICE](./NOTICE)**。

`waifu-1.1.7-slim.toolpkg` 是对 Operit 内置插件 `com.operit.waifu` 的修改版本。
Operit 主程序（[AAswordman/Operit](https://github.com/AAswordman/Operit)）以 LGPL-3.0 发布，
本修改版随之适用同一协议。

### 关于内置表情资源

原插件包含 53 张内置表情图片（约 3.6 MB）。**本构建已全部移除**，原因：

- 避免再分发原作者的素材
- 包体积从 3.68 MB 降到 **66 KB**

因此首次使用时 `emojis` 为空、`enableEmoticons` 默认关闭。
需自行在设置页导入图片，至少有一个分类后再开启表情开关。

如果原作者认为本仓库仍有不当之处，请提 issue，会及时处理。

---

## 相关

- [Operit](https://github.com/ymmhl91-bit/operit-clawd) — 本项目所服务的平台


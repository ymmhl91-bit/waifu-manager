# waifu-manager

[![Operit](https://img.shields.io/badge/Operit-ToolPkg-blue)](https://github.com/ymmhl91-bit/operit-clawd)
[![Python](https://img.shields.io/badge/Python-3.8%2B-brightgreen)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-AGPL--3.0-blue)](./LICENSE)
[![Release](https://img.shields.io/github/v/release/ymmhl91-bit/waifu-manager)](https://github.com/ymmhl91-bit/waifu-manager/releases/latest)

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
| 点击弹回 | 一旦点了内置分类，**再也切不回**自定义分类 |
| 无法移动 | 图片只能在原分类删除、重新导入，不能跨类迁移 |

本项目提供两样东西解决它：

1. **`waifu-1.1.8.toolpkg`** — 打过补丁的插件包，设置页支持新建/删除/重命名分类、图片跨类移动
2. **`manager/`** — 命令行工具，做批量归类、健康检查、方案导出导入

---

## 快速开始

### 方式一：用补丁版插件（需要写文件权限）

**1. 下载插件包**

从 [Releases](https://github.com/ymmhl91-bit/waifu-manager/releases/latest) 下载 `waifu-1.1.8.toolpkg`（3.68 MB）。

或直接命令行：

```bash
curl -L -o waifu-1.1.8.toolpkg \
  https://github.com/ymmhl91-bit/waifu-manager/releases/latest/download/waifu-1.1.8.toolpkg
```

**2. 先卸载内置 waifu（重要）**

`com.operit.waifu` 是 Operit 内置插件，直接导入会报：

```
Bundled ToolPkg cannot be replaced by a local import
```

所以要先卸载：**设置 → 插件管理 → Waifu 模式 → 卸载**，或命令行：

```bash
operit2 package delete waifu
```

> ### ⚠️ 卸载会连配置目录一起删掉
>
> 经实测，`package delete` 会移除 `configs/com.operit.waifu/` 整个目录，
> 包括你导入的全部表情分类、自定义提示词、打字速度等设置。
> **务必先备份。**

**3. 备份配置**

```bash
# 把备份放到插件目录外面，否则会被一起删掉
mkdir -p ~/waifu-backup
cp <runtime>/extensions/device/plugins/configs/com.operit.waifu/mode.json   ~/waifu-backup/
cp <runtime>/extensions/device/plugins/configs/com.operit.waifu/waifu.json  ~/waifu-backup/
```

**4. 导入新包**

```bash
operit2 package import waifu-1.1.8.toolpkg
operit2 package enable waifu
```

也可以在文件管理器里直接点开 `.toolpkg` 导入。

**5. 还原配置**

```bash
# 卸载已把目录删了，先重建
mkdir -p <runtime>/extensions/device/plugins/configs/com.operit.waifu

cp ~/waifu-backup/mode.json   <runtime>/extensions/device/plugins/configs/com.operit.waifu/mode.json
cp ~/waifu-backup/waifu.json  <runtime>/extensions/device/plugins/configs/com.operit.waifu/waifu.json
```

**6. 完全退出 Operit 再重开**

不重启的话插件读完旧配置就不会再读文件，还原等于没做。

---

**不想卸载内置包？** 那就走纯文件替换，跳过上面步骤：

```bash
# 备份原包
cp <runtime>/extensions/device/packages/waifu.toolpkg ~/waifu-backup.toolpkg

# 替换
cp waifu-1.1.8.toolpkg <runtime>/extensions/device/packages/waifu.toolpkg

# 清缓存
rm -rf <runtime>/cache/toolpkg/com.operit.waifu-*

# 完全退出 Operit 再重开
```

这种方式不动配置目录，表情分类等设置全部保留。

其中 `<runtime>` 形如 `/data/user/0/app.operit/files/runtime/identities/identity-*`。

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

这是最容易踩的坑：**应用内普通聊天和 QQ Bot 走两条完全不同的链路，读的不是同一份数据。**

| 场景 | 实际读取位置 | 说明 |
|---|---|---|
| 应用内普通聊天 | `mode.json` → `bindings["card:<uuid>"].settings` | 按聊天当前绑定的角色卡取对应 binding；`enabled` 为 false 时不注入任何规则 |
| **QQ Bot** | **`waifu.json` → `profiles[bot.waifuProfile]`** | **由 bot 配置里的 `waifuProfile` 字段决定，与 `mode.json` 的 binding 完全无关** |

也就是说：**QQ Bot 的表情清单来自 profile，不是 binding。**

### 源码依据（为什么 QQ 走 profile）

1. qqbot `service.js` 自动回复时调用 `replyStream(request, this.bot.waifuProfile, ...)`；
2. `replyStream` 先经 `preferWaifu(profile)` 判定（`profile === "native"` 时退回原生聊天，否则调 `getSettings(profile)` 探测 waifu 是否可用）；
3. 可用则走 `dependencies/waifu/api.js` 的 `stream()`，它调用 `session.open({ chatId, profile })`；
4. waifu 侧 `sessionOpen()` 执行 `readSettings(event.payload.profile)`，把该 profile 的设置存入会话；
5. waifu 侧 `composePrompt()` 里 `externalSettings(chatId)` 命中这个活跃会话后，**直接用会话里的 profile 设置**，不再查 `mode.json` 的 binding。

### 典型症状

只改了 `profiles`、没动 binding，结果 QQ 侧表情没变（或反过来）。反过来只改 binding，QQ 侧同样没反应——因为两条链路根本不相交。

排查顺序：

```bash
# 1. 看 bot 用的是哪个 profile
python3 library.py bots

# 2. 看各 profile 的表情清单
python3 library.py profiles
```

### 多 bot 分库的正确做法

给每个 bot 分配独立的 profile，各自指向不同目录：

```bash
# 新建 profile（从 default 复制一份，再单独换 emojis）
python3 library.py create-profile feiyu

# 把某个 bot 指到这个 profile
python3 library.py assign-bot "QQ Bot 1" feiyu
```

`default` 建议保留作为兜底，不要占用给具体角色——它同时是多个 fallback 的默认值。

### 改完必须重启

插件配置是模块级单例，只在进程启动时读一次文件。**外部改动磁盘后，运行中的插件感知不到**，必须完全重启 Operit（从最近任务划掉进程）。

> ⚠️ 不要在设置页改完配置后直接手改文件——设置页保存会把内存里的整份配置 flush 回磁盘，覆盖你的外部修改。

---

## 为什么不做独立插件

「独立插件」其实有三种不同做法，可行性各不相同。

### 方案 A：独立包，去读写 waifu 的配置 

**不可行。** waifu 把配置缓存在模块级单例里：

```ts
let config = null;
function loadConfig() {
  if (config === null) config = PluginConfig.use("waifu", {...});
  return config;   // 进程活着就一直用这份
}
```

由此两个致命问题：

1. **外部写文件它看不见** —— 实测写入 `charDelayMs=777`，插件仍返回 `250`
2. **它会覆盖你的写入** —— `writeSettings` 把内存里的整份 store flush 回文件，你在设置页点一下，外部改动就没了

### 方案 B：独立 id，做 waifu 的替代品

**不可行。** 两个障碍：

- `dist/main.js` 注册的 `settings.get` / `mode.status` / `session.feed` 都是**全局名**，两个包同名注册会冲突，只能有一个生效
- qqbot 硬编码了 `callDependency("com.operit.waifu")`，改名即断，QQ 的表情功能直接失效

### 方案 C：保持同名 id 的 fork ← 本项目采用的

**可行，已实测。** 关键是：**内置包可以卸载**。

```bash
operit2 package delete waifu        # 卸载内置版（配置目录一起删，需先备份）
operit2 package import <新包>        # 装同名的新版
operit2 package enable waifu
```

卸载后 `Built in` 变成 `false`，同名导入不再被 `Bundled ToolPkg cannot be replaced` 挡住。

代价是：

- 用户要先卸载，多一步操作
- 卸载会清空配置，必须提前备份（详见上方安装步骤）
- 官方若推送 waifu 更新，可能覆盖本版本

**结论：** 想绕开 fork 是不行的，但 fork 可以走正规的卸载‑重装流程，而不必手动替换文件。本项目的商城版本就是按这种方式分发的。

---

## 已知问题

- **官方推送 waifu 更新时可能覆盖本版本**，且无提示。想长期用就别在官方渠道更新 waifu。
- 版本号 `1.1.4 → 1.1.8`，仅用于区分与规避同版本覆盖判定。
- 内置表情完整保留（53 张，9 大类），与上游一致。1.1.7 曾误删导致旧配置报 resource 错误，1.1.8 已修复。
- `src/` 与 `dist/` 已同步修改，重新编译不会丢改动。
- 与 qqbot 多账号改造等替换内置包类项目天然兼容：保持同名包 id `com.operit.waifu`，多账号版 qqbot 的 Waifu 依赖无需改动即可接入。
- 实际只改 3 个文件：dist/ui/settings.ui.js、src/ui/settings.ui.ts、manifest.json。settings.js/ts 与 stickers.js/ts 在 1.1.8 已恢复为与上游逐字节一致。补丁源码见 plugins 目录。

---

## 仓库结构

```
.
├── README.md
├── LICENSE
├── NOTICE                    # 许可依据与第三方声明
├── CHANGELOG.md
├── .gitignore
├── waifu-1.1.8.toolpkg        # 补丁版插件包
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

本项目以 **[AGPL-3.0](./LICENSE)** 发布。完整许可依据与第三方声明见 **[NOTICE](./NOTICE)**。

上游是 [Operit2](https://github.com/AAswordman/Operit2) 仓库中的
`plugins/packages/external/waifu/`，该仓库以 AGPL-3.0 发布，本修改版沿用同一协议。

包内 `src/` 提供完整对应源码，满足 AGPL-3.0 的源码提供义务。

非官方作品，与原插件作者无关。如有异议请提 issue，会及时处理。

---

## 相关

- Operit2 平台 — https://github.com/AAswordman/Operit2
- waifu 插件 — Operit2 内置插件，包内无独立 LICENSE 文件，许可随主仓库 AGPL-3.0
# 配置文件格式

waifu 插件用两份 JSON 存配置，都在：

```
<runtime>/extensions/device/plugins/configs/com.operit.waifu/
```

| 文件 | 作用 |
|---|---|
| `mode.json` | 应用内普通聊天，按「聊天绑定的选择」存 |
| `waifu.json` | 外部命名的 profile，QQ Bot 用这个 |

---

## mode.json

```json
{
  "bindings": {
    "card:f8c93d80-6dd2-416e-b563-67ca054a7b4c": {
      "enabled": true,
      "mergeSend": true,
      "mergeDelayMs": 5000,
      "settings": {
        "charDelayMs": 200,
        "removePunctuation": false,
        "enableEmoticons": true,
        "enableSelfie": false,
        "customPrompt": "…",
        "selfiePrompt": "…",
        "emojis": {
          "happy": ["/path/to/a.gif", "/path/to/b.gif"]
        }
      }
    },
    "model:chat": { "…": "…" }
  }
}
```

### bindings 的 key 类型

| key | 含义 |
|---|---|
| `card:<uuid>` | 绑定到某张角色卡 |
| `group:<uuid>` | 绑定到某角色组 |
| `model:chat` | 绑定到「模型对话」 |

**同一个 key 下的所有聊天共享开关。** 找不到 key 或 `enabled=false` 时，`modeForChat()` 返回 `null`，该聊天不使用 waifu 模式。

### settings 字段

| 字段 | 类型 | 范围 | 说明 |
|---|---|---|---|
| `charDelayMs` | int | 0–3000 | 每字符延迟（毫秒） |
| `removePunctuation` | bool | — | 移除句末标点 |
| `enableEmoticons` | bool | — | **关掉时 `<emotion>` 标签会被静默丢弃** |
| `enableSelfie` | bool | — | 自拍；开启前 `selfiePrompt` 不能为空 |
| `customPrompt` | string | ≤16000 | 拼接到系统提示词的附加规则 |
| `selfiePrompt` | string | ≤16000 | 绘图外貌关键词 |
| `emojis` | object | — | 分类名 → 图片路径数组 |

---

## waifu.json

```json
{
  "profiles": {
    "default": {
      "charDelayMs": 250,
      "customPrompt": "…",
      "emojis": { "happy": ["…"] },
      "enableEmoticons": true,
      "…": "…"
    }
  }
}
```

结构比 `mode.json` 少一层 `bindings`，直接是 profile 名 → settings。

QQ Bot 通过 `qqbot.json` 的 `waifuProfile` 字段指定用哪个 profile（默认 `default`）。

---

## emojis 的校验规则

由 `validateSettings()` 强制，**不满足会导致插件启动失败或保存被拒**：

```ts
if (!/^[a-z][a-z0-9_]{0,63}$/.test(category)) throw …
if (!Array.isArray(images) || images.length === 0) throw …   // 不允许空分类
if (images.length > 100) throw …                              // 每类上限 100
if (typeof image !== 'string' || image.trim() === '') throw …
```

此外：

```ts
if (value.enableEmoticons && Object.keys(value.emojis).length === 0)
  throw new Error("Emoticons require at least one configured category");
```

**所以 `emojis` 不能为空对象，也不能有空的分类。**

---

## 图片路径的三种写法

| 形式 | 含义 |
|---|---|
| `resource:emoji_happy_happy_1` | 插件包内资源，`ToolPkg.readResource()` 解析 |
| `/data/.../xxx.gif` | Host 文件绝对路径 |
| `https://...` | 远程 URL |

注意 `resource:` 的 key 只允许 `[a-z0-9_]`。

---

## 运行时行为要点

### 内存缓存

```ts
let config: Promise<Config> | null = null;

export function loadConfig(): Promise<Config> {
  if (config === null) config = PluginConfig.use("waifu", { profiles: { default: defaultSettings() } });
  return config;
}
```

**进程启动读一次文件，之后不再读。** 外部改文件对运行中的插件无效。

### 保存会覆盖

```ts
export async function writeSettings(profile, settings) {
  const checked = validateSettings(settings), store = await loadConfig();
  store.profiles = { ...store.profiles, [profile]: checked };
  await PluginConfig.flush(store);   // 整份写回
  return checked;
}
```

在设置页做任何修改，都会把**内存里的完整 store** 写回文件，覆盖掉外部改动。

### 情绪标签解析

```ts
const emotion = /^<emotion>\s*([^<>]+?)\s*<\/emotion>/.exec(rest);
if (emotion !== null) {
  index += emotion[0].length;
  if (settings.enableEmoticons) result.push({ kind: "emotion", category: emotion[1] });
  // enableEmoticons 为 false 时：标签被丢弃，不报错
}
```

标签必须**紧跟在句末**才被识别。`enableEmoticons=false` 时不会报错，只是标签消失——这是排查「表情包发不出来」时最容易漏掉的一环。

---

## 常见故障对照

| 现象 | 原因 |
|---|---|
| 改了配置没反应 | 未重启；插件用内存缓存 |
| 改动过一会自己没了 | 在设置页操作触发了 flush |
| QQ 有表情、应用内没有 | 两套配置，`mode.json` 与 `waifu.json` 分别设置 |
| 同一角色卡不同聊天开关不一致 | 那些聊天绑定的 selection 不同 |
| `<emotion>` 变成裸文本 | 该配置的 `enableEmoticons=false` |
| 表情发送失败并中断回复 | 图片超过 QQ 直传 5 MiB 上限 |
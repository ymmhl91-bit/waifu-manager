# 补丁改动明细

记录 `waifu-1.1.8.toolpkg` 相对官方 `com.operit.waifu` 1.1.4 的全部改动。

**改动范围：两个代码文件 + 资源清理。**

| 文件 | 类型 |
|---|---|
| `dist/ui/settings.ui.js` | 运行时实际执行的编译产物 |
| `src/ui/settings.ui.ts` | 对应源码，保持同步 |

`manifest.json` 改动：`version`、`display_name`、`description`，并**移除 `resources` 声明**。
其余代码文件（`dist/main.js`、`dist/service.js`、`dist/sentences.js` 等）与官方包**逐字节一致**。

---

## 1. 分类常量改为动态生成

### 改动前

```js
const emotions = { crying: "哭泣", like_you: "喜欢你", happy: "开心", surprised: "惊讶",
  miss_you: "想你", speechless: "无语", angry: "生气", confused: "困惑", sad: "难过" };
```

设置页的分类按钮就是 `Object.entries(emotions).map(...)` 渲染的，所以：

- 自定义分类（`playful` 等）不显示
- `emotions[category]` 取不到值 → 标题渲染成 `undefined`
- 点内置分类后 `category` 变成内置值，而 `setCategory` 只能从 `emotions` 里选，**无法回到自定义分类**

### 改动后

```js
const builtinEmotions = { crying: "哭泣", /* … */ sad: "难过" };

function categoryLabel(key) {
  return builtinEmotions[key] === undefined ? key : builtinEmotions[key];
}

function listCategories(emojis, drafts) {
  const stored = Object.keys(emojis);
  const builtin = Object.keys(builtinEmotions).filter(key => stored.indexOf(key) !== -1);
  const extra = stored.filter(key => builtinEmotions[key] === undefined).sort();
  const pending = drafts.filter(key => stored.indexOf(key) === -1).sort();
  return builtin.concat(extra).concat(pending);
}

function validCategory(name) {
  return /^[a-z][a-z0-9_]{0,63}$/.test(name);   // 与 validateSettings 完全一致
}
```

排序规则：内置分类按固定顺序在前，自定义分类按字母序在后，草稿置尾。

---

## 2. 新增四个界面状态

```js
const [drafts, setDrafts] = ctx.useState("drafts", []);
const [newCategory, setNewCategory] = ctx.useState("newCategory", "");
const [moveIndex, setMoveIndex] = ctx.useState("moveIndex", -1);
const [pendingDelete, setPendingDelete] = ctx.useState("pendingDelete", "");
```

---

## 3. `imagesChanged` 改为接收目标分类

### 改动前

```js
async function imagesChanged(images) {
  const emojis = { ...current.current.mode.settings.emojis };
  if (images.length === 0) delete emojis[category];   // 依赖外层 category
  else emojis[category] = images;
  update({}, { emojis });
  setPreviews(await callAdmin({ action: "emoji.previews", emojis }));
}
```

只能操作当前选中的分类，无法写入其他分类。

### 改动后

```js
async function imagesChanged(target, images) {
  const emojis = { ...current.current.mode.settings.emojis };
  if (images.length === 0) delete emojis[target];
  else emojis[target] = images;
  update({}, { emojis });
  if (images.length > 0) setDrafts(drafts.filter(key => key !== target));  // 草稿转正
  setPreviews(await callAdmin({ action: "emoji.previews", emojis }));
}
```

---

## 4. 新增「新建分类」

```js
function createCategory() {
  const name = newCategory.trim().toLowerCase().replace(/[\s\-]+/g, "_");
  if (!validCategory(name)) throw new Error("分类名只能用英文字母、数字和下划线…");
  if (settings.emojis[name] !== undefined || drafts.indexOf(name) !== -1)
    throw new Error(`分类「${name}」已经存在`);
  setDrafts([...drafts, name]);
  setCategory(name);
  // …
}
```

### 为什么要草稿机制

`validateSettings` 有这条硬限制：

```js
if (!Array.isArray(images) || images.length === 0) throw new Error(`Invalid emoji category: ${category}`);
```

**空分类无法落库。** 所以新建分类只能是界面层草稿，等第一张图导入或移入后才真正写入 `emojis`。

自动规范化：转小写、空格与连字符转下划线。

---

## 5. 新增「删除分类」

```js
async function removeCategory() {
  const removing = active;
  if (drafts.indexOf(removing) !== -1) {          // 草稿直接丢弃
    setDrafts(drafts.filter(key => key !== removing));
    return;
  }
  if (storedCount <= 1) throw new Error("至少要保留一个分类…");
  const emojis = { ...settings.emojis };
  delete emojis[removing];
  // …
}
```

保留至少一个，因为：

```js
if (value.enableEmoticons && Object.keys(value.emojis).length === 0)
  throw new Error("Emoticons require at least one configured category");
```

界面层有二次确认，避免误删整个分类。

---

## 6. 新增「图片跨分类移动」

```js
async function moveImage(index, destination) {
  const emojis = { ...settings.emojis };
  const from = emojis[active].slice();
  const moving = from[index];
  const to = emojis[destination] === undefined ? [] : emojis[destination].slice();
  if (to.length >= 100) throw new Error(`目标分类…已经有 100 张，达到上限`);
  from.splice(index, 1);
  to.push(moving);
  emojis[destination] = to;
  if (from.length === 0) delete emojis[active];   // 源空则删，避免留空分类
  else emojis[active] = from;
  // …
}
```

移动后若源分类变空，自动删除 —— 否则会写出空数组，触发校验失败。

界面流程：点「移到…」→ 切到分类选择页（列出其他分类及张数）→ 点目标分类完成。

---

## 7. 设置页「可用情绪」改为动态

```js
// 改动前
description(`可用情绪：${Object.entries(emotions).filter(…).map(([, title]) => title).join("、")}`)

// 改动后
description(`可用情绪：${listCategories(settings.emojis, drafts).map(key => categoryLabel(key)).join("、") || "（尚未配置）"}`)
```

---

## 未改动的部分

以下逻辑完全保持原样，补丁只碰 UI 层：

- 分句逻辑（`dist/sentences.js`）
- 提示词拼接（`dist/service.js` 的 `composePrompt`）
- 配置读写与校验（`dist/settings.js`）
- 表情解析与图片解析（`resolveEmotion`）
- 输入合并（`dist/merge.js`）
- 公共 API 与 IPC（`dist/api.js`、`dist/admin.js`）
- 全部内置表情资源

---

## 验证方式

```bash
# 语法
node --check dist/ui/settings.ui.js

# 打包完整性
unzip -t waifu-1.1.6.toolpkg

# 与官方包对比，确认只有预期文件变化
unzip -p waifu-1.1.6.toolpkg manifest.json | diff - <(unzip -p waifu-1.1.4.toolpkg manifest.json)
```

`manifest.json` 的差异应只有 `version`、`display_name`、`description` 三处。

---

## 恢复官方版本

```bash
cp waifu.toolpkg.orig <runtime>/extensions/device/packages/waifu.toolpkg
rm -rf <runtime>/cache/toolpkg/com.operit.waifu-*
# 完全退出 Operit 再重开
```

或在插件市场对本插件点「更新」，会拉回官方版本（同时失去所有自定义分类能力）。
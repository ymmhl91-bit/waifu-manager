# -*- coding: utf-8 -*-
"""waifu 表情库管理 —— 增强功能

新增能力：
1. rename-image   重命名单张表情（改文件名 + 同步所有配置路径）
2. list-bots      列出 QQ bot 及其 profile 分配
3. assign-bot     给某个 bot 分配 waifu profile
4. split-library  把一个 profile 的表情物理隔离到独立目录
5. profiles       列出/创建/删除 waifu profile
"""

import json
import os
import re
import shutil
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core

RUNTIME = core.RUNTIME
WAIFU_CFG = os.path.join(RUNTIME, 'extensions/device/plugins/configs/com.operit.waifu')
QQBOT_CFG = os.path.join(RUNTIME, 'extensions/device/plugins/configs/com.operit.qqbot_bundle/qqbot.json')
MODE_PATH = os.path.join(WAIFU_CFG, 'mode.json')
PROFILE_PATH = os.path.join(WAIFU_CFG, 'waifu.json')
BACKUP_DIR = '/data/user/0/app.operit/files/waifu_patch/backup/manager'
STICKER_ROOT = '/data/user/0/app.operit/files/waifu_sticker'


# ---------- 工具 ----------

def _snapshot(tag):
    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    out = []
    for name, path in (('mode', MODE_PATH), ('waifu', PROFILE_PATH), ('qqbot', QQBOT_CFG)):
        if os.path.exists(path):
            dst = os.path.join(BACKUP_DIR, f'{name}-{tag}-{stamp}.json')
            shutil.copy2(path, dst)
            out.append(dst)
    return out


def _atomic_write(path, data):
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def _all_emoji_containers():
    """枚举所有存放 emojis 的位置：(来源描述, settings 对象, 所属数据, key)"""
    containers = []
    if os.path.exists(MODE_PATH):
        mode = json.load(open(MODE_PATH, encoding='utf-8'))
        for key, entry in mode.get('bindings', {}).items():
            s = entry.get('settings')
            if isinstance(s, dict) and isinstance(s.get('emojis'), dict):
                containers.append((f'mode:{key}', s, mode, MODE_PATH))
    if os.path.exists(PROFILE_PATH):
        prof = json.load(open(PROFILE_PATH, encoding='utf-8'))
        for key, s in prof.get('profiles', {}).items():
            if isinstance(s, dict) and isinstance(s.get('emojis'), dict):
                containers.append((f'profile:{key}', s, prof, PROFILE_PATH))
    return containers


def _safe_filename(name):
    """去掉路径分隔符和非法字符。"""
    name = name.replace('/', '_').replace('\\', '_')
    name = re.sub(r'[<>:"|?*\x00-\x1f]', '', name)
    return name.strip() or 'unnamed'


# ---------- 1. 重命名单张表情 ----------

def rename_image(pattern, new_name, dry_run=False):
    """按文件名片段找到唯一图片，重命名文件并同步所有配置中的路径。"""
    # 按「文件路径」去重：同一张图可能同时出现在 mode.json 和 waifu.json
    by_path = {}
    for label, settings, _data, _path in _all_emoji_containers():
        for cat, images in settings['emojis'].items():
            for idx, p in enumerate(images):
                base = os.path.basename(p)
                if pattern in base or pattern in p:
                    entry = by_path.setdefault(p, {'path': p, 'base': base, 'sites': []})
                    entry['sites'].append((label, cat, idx))

    matches = list(by_path.values())

    if not matches:
        raise SystemExit(f'没有匹配到包含「{pattern}」的表情')
    if len(matches) > 1:
        print(f'匹配到 {len(matches)} 个不同文件，请缩小范围：')
        for m in matches[:25]:
            print(f'  {m["base"]}  (被 {len(m["sites"])} 处配置引用)')
        raise SystemExit(1)

    hit = matches[0]
    old_path = hit['path']
    _first_label, _first_cat, _first_idx = hit['sites'][0]

    # resource: 或 http 不能改名
    if old_path.startswith('resource:'):
        raise SystemExit('这是包内内置资源，无法重命名文件；只能改配置别名（不支持）')
    if old_path.startswith('http://') or old_path.startswith('https://'):
        raise SystemExit('这是网络图片，没有本地文件可改名')

    ext = os.path.splitext(old_path)[1]
    if not new_name.lower().endswith(ext.lower()):
        new_name = new_name + ext

    safe = _safe_filename(new_name)
    directory = os.path.dirname(old_path)
    new_path = os.path.join(directory, safe)

    if not os.path.exists(old_path):
        raise SystemExit(f'源文件不存在：{old_path}')
    if os.path.exists(new_path) and os.path.abspath(new_path) != os.path.abspath(old_path):
        raise SystemExit(f'目标文件已存在：{safe}')

    print(f'文件：{os.path.basename(old_path)}')
    print(f'  →  {safe}')
    print(f'目录：{directory}')
    print(f'被 {len(hit["sites"])} 处配置引用')

    # 统计会影响多少处配置
    affected = 0
    for label, settings, _data, _path in _all_emoji_containers():
        for cat, images in settings['emojis'].items():
            if old_path in images:
                affected += images.count(old_path)
    print(f'同步配置引用：{affected} 处')

    if dry_run:
        print('\n[预览模式] 未做任何修改')
        return

    _snapshot('rename-image')

    # 改文件名
    os.rename(old_path, new_path)

    # 同步所有配置：先改内存里的对象，再按文件分组整体写回
    by_file = {}
    for label, settings, data, path in _all_emoji_containers():
        changed = False
        for cat, images in settings['emojis'].items():
            for i, p in enumerate(images):
                if p == old_path:
                    images[i] = new_path
                    changed = True
        if changed:
            by_file[path] = data

    touched = set()
    for path, data in by_file.items():
        _atomic_write(path, data)
        touched.add(path)

    print(f'\n✅ 已重命名并同步 {len(touched)} 个配置文件')
    print('⚠️  需要完全重启 Operit 才会生效')


# ---------- 2. bot 与 profile ----------

def load_bots():
    if not os.path.exists(QQBOT_CFG):
        return []
    return json.load(open(QQBOT_CFG, encoding='utf-8')).get('bots', [])


def list_bots():
    bots = load_bots()
    if not bots:
        print('没有找到 QQ bot')
        return
    print(f'QQ Bot：{len(bots)} 个\n')
    for b in bots:
        ar = b.get('autoReply') or {}
        print(f"  {b.get('name')}  (appId {b.get('appId')})")
        print(f"    profile : {b.get('waifuProfile')!r}")
        print(f"    角色卡  : {ar.get('characterSelection')!r}")
        print(f"    自动回复: {'开' if ar.get('enabled') else '关'}")
        print()


def assign_bot(bot_name, profile):
    """给指定 bot 分配 waifu profile。"""
    if not os.path.exists(QQBOT_CFG):
        raise SystemExit('找不到 qqbot.json')

    prof_data = json.load(open(PROFILE_PATH, encoding='utf-8'))
    if profile not in prof_data.get('profiles', {}):
        raise SystemExit(f'profile 不存在：{profile}\n现有：{list(prof_data.get("profiles", {}).keys())}')

    _snapshot('assign-bot')
    cfg = json.load(open(QQBOT_CFG, encoding='utf-8'))
    hit = None
    for b in cfg.get('bots', []):
        if b.get('name') == bot_name or b.get('id') == bot_name or str(b.get('appId')) == bot_name:
            b['waifuProfile'] = profile
            hit = b
            break
    if hit is None:
        raise SystemExit(f'找不到 bot：{bot_name}')

    _atomic_write(QQBOT_CFG, cfg)
    print(f"✅ {hit.get('name')} → profile {profile!r}")
    print('⚠️  需要完全重启 Operit 才会生效')


# ---------- 3. profile 管理 ----------

def list_profiles():
    if not os.path.exists(PROFILE_PATH):
        print('找不到 waifu.json')
        return
    data = json.load(open(PROFILE_PATH, encoding='utf-8'))
    print(f'waifu profiles：{len(data.get("profiles", {}))} 个\n')
    for name, s in data.get('profiles', {}).items():
        e = s.get('emojis', {})
        print(f"  {name}")
        print(f"    表情: {'开' if s.get('enableEmoticons') else '关'}  "
              f"{len(e)} 类 / {sum(len(v) for v in e.values())} 张")

    # 标记哪些 profile 被 bot 使用
    bots = load_bots()
    used = {}
    for b in bots:
        used.setdefault(b.get('waifuProfile'), []).append(b.get('name'))
    if used:
        print('\n使用情况：')
        for p, names in used.items():
            print(f'  {p} ← {", ".join(names)}')


def create_profile(name, from_profile=None):
    """新建 profile，可从已有 profile 复制。"""
    if not re.fullmatch(r'[a-zA-Z0-9_\-]{1,64}', name):
        raise SystemExit('profile 名只能用字母、数字、下划线、连字符，最长 64')
    data = json.load(open(PROFILE_PATH, encoding='utf-8'))
    if name in data['profiles']:
        raise SystemExit(f'profile 已存在：{name}')

    _snapshot('create-profile')
    if from_profile:
        if from_profile not in data['profiles']:
            raise SystemExit(f'源 profile 不存在：{from_profile}')
        data['profiles'][name] = json.loads(json.dumps(data['profiles'][from_profile]))
        print(f'✅ 从 {from_profile} 复制创建 profile {name!r}')
    else:
        base = json.loads(json.dumps(data['profiles'].get('default', {})))
        base['emojis'] = {}
        base['enableEmoticons'] = False
        data['profiles'][name] = base
        print(f'✅ 创建空 profile {name!r}')

    _atomic_write(PROFILE_PATH, data)
    print('⚠️  需要完全重启 Operit 才会生效')


# ---------- 4. 物理隔离 ----------

def split_library(profile_name, target_dir=None):
    """把某个 profile 的表情图片复制到独立目录，并改写该 profile 的路径。

    其它 profile 不受影响 —— 这就是物理隔离。
    """
    data = json.load(open(PROFILE_PATH, encoding='utf-8'))
    if profile_name not in data['profiles']:
        raise SystemExit(f'profile 不存在：{profile_name}')
    settings = data['profiles'][profile_name]
    emojis = settings.get('emojis', {})
    if not emojis:
        raise SystemExit('该 profile 没有表情，无需隔离')

    dest_root = target_dir or os.path.join(STICKER_ROOT, f'lib_{profile_name}')

    plan = []
    for cat, images in emojis.items():
        for p in images:
            if p.startswith('resource:') or p.startswith('http'):
                continue
            plan.append((cat, p))

    print(f'profile {profile_name!r} 共 {len(plan)} 张本地图片')
    print(f'目标目录：{dest_root}\n')

    _snapshot('split-library')

    moved = 0
    skipped = 0
    new_emojis = {}
    for cat, old_path in plan:
        if not os.path.exists(old_path):
            skipped += 1
            new_emojis.setdefault(cat, []).append(old_path)
            continue
        dest_dir = os.path.join(dest_root, cat)
        os.makedirs(dest_dir, exist_ok=True)
        dest = os.path.join(dest_dir, os.path.basename(old_path))
        shutil.copy2(old_path, dest)
        new_emojis.setdefault(cat, []).append(dest)
        moved += 1

    # 保留无法迁移的条目（resource:/http）
    for cat, images in emojis.items():
        for p in images:
            if p.startswith('resource:') or p.startswith('http'):
                new_emojis.setdefault(cat, []).append(p)

    settings['emojis'] = new_emojis
    _atomic_write(PROFILE_PATH, data)

    print(f'✅ 已复制 {moved} 张到独立目录')
    if skipped:
        print(f'⚠️  {skipped} 张原文件缺失，已保留原路径')
    print(f'\n现在 profile {profile_name!r} 使用独立目录：')
    print(f'  {dest_root}')
    print('\n⚠️  需要完全重启 Operit 才会生效')


# ---------- 入口 ----------

COMMANDS = {
    'bots': (list_bots, 0),
    'assign-bot': (assign_bot, 2),
    'profiles': (list_profiles, 0),
    'create-profile': (create_profile, 1),
    'rename-image': (rename_image, 2),
    'split-library': (split_library, 1),
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        return
    func, argc = COMMANDS[sys.argv[1]]
    args = sys.argv[2:]
    if len(args) < argc:
        print(f'参数不足，{sys.argv[1]} 需要 {argc} 个参数')
        raise SystemExit(1)
    func(*args[:argc])


if __name__ == '__main__':
    main()
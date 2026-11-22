# -*- coding: utf-8 -*-
"""waifu 表情分类管理器 —— 核心逻辑

只做两件事：
1. 读 mode.json / waifu.json，把表情分类结构化成可操作的数据
2. 每次操作后立刻原子写盘 + 备份，并提示需要重启 Operit 才生效

不做：实时调用插件、走 IPC、修改运行中的内存状态。
"""

import json
import os
import shutil
import time
from datetime import datetime

RUNTIME = '/data/user/0/app.operit/files/runtime/identities/identity-1794890223595-2735443b'
CONFIG_DIR = os.path.join(RUNTIME, 'extensions/device/plugins/configs/com.operit.waifu')
MODE_PATH = os.path.join(CONFIG_DIR, 'mode.json')
PROFILE_PATH = os.path.join(CONFIG_DIR, 'waifu.json')
BACKUP_DIR = '/data/user/0/app.operit/files/waifu_patch/backup/manager'

# 内置分类的中文名，与插件保持一致
BUILTIN_LABELS = {
    'crying': '哭泣', 'like_you': '喜欢你', 'happy': '开心', 'surprised': '惊讶',
    'miss_you': '想你', 'speechless': '无语', 'angry': '生气', 'confused': '困惑',
    'sad': '难过',
}

CATEGORY_RE_MAX = 100          # 每类最多 100 张，插件硬限制
IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.avif')
MAX_FILE_BYTES = 5 * 1024 * 1024   # QQ 单图直传上限 5 MiB


def label_of(key):
    """分类显示名：内置用中文，自定义显示原名。"""
    return BUILTIN_LABELS.get(key, key)


def valid_category(name):
    """与插件 validateSettings 完全一致的正则。"""
    import re
    return bool(re.fullmatch(r'[a-z][a-z0-9_]{0,63}', name))


def load_json(path):
    with open(path, encoding='utf-8') as fh:
        return json.load(fh)


def atomic_write(path, data):
    """先写临时文件再替换，避免写一半断电把配置弄坏。"""
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, ensure_ascii=False)
    os.replace(tmp, path)


def snapshot(tag='manual'):
    """改之前留一份，出问题能退回去。"""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    for name, path in (('mode', MODE_PATH), ('waifu', PROFILE_PATH)):
        if os.path.exists(path):
            dst = os.path.join(BACKUP_DIR, f'{name}-{tag}-{stamp}.json')
            shutil.copy2(path, dst)


def read_state():
    """汇总两份配置里的表情分类信息。"""
    mode = load_json(MODE_PATH)
    profiles = load_json(PROFILE_PATH)

    bindings = []
    for key, entry in mode.get('bindings', {}).items():
        settings = entry.get('settings', {})
        emojis = settings.get('emojis', {})
        bindings.append({
            'selection': key,
            'enabled': entry.get('enabled', False),
            'emoticons': settings.get('enableEmoticons', False),
            'categories': {
                cat: list(images) for cat, images in emojis.items()
            },
        })

    profile_list = []
    for name, settings in profiles.get('profiles', {}).items():
        emojis = settings.get('emojis', {})
        profile_list.append({
            'profile': name,
            'emoticons': settings.get('enableEmoticons', False),
            'categories': {cat: list(images) for cat, images in emojis.items()},
        })

    return {'bindings': bindings, 'profiles': profile_list}


def validate_categories(categories):
    """写盘前按插件规则校验，避免写进去让插件启动失败。"""
    if not isinstance(categories, dict) or not categories:
        raise ValueError('至少需要保留一个分类')
    if len(categories) > 200:
        raise ValueError('分类数量超过合理上限')
    total = 0
    for cat, images in categories.items():
        if not valid_category(cat):
            raise ValueError(f'分类名不合法：{cat}（需小写字母开头，只含小写字母/数字/下划线，最长 64 位）')
        if not isinstance(images, list) or not images:
            raise ValueError(f'分类 {cat} 的图片列表为空')
        if len(images) > CATEGORY_RE_MAX:
            raise ValueError(f'分类 {cat} 超过 {CATEGORY_RE_MAX} 张上限')
        for image in images:
            if not isinstance(image, str) or not image.strip():
                raise ValueError(f'分类 {cat} 里有空的图片路径')
        total += len(images)
    return total


def write_bindings(target_categories, selections=None):
    """把分类写到指定的角色卡绑定；selections 为 None 表示所有绑定。"""
    snapshot('binding')
    mode = load_json(MODE_PATH)
    changed = []
    for key, entry in mode.get('bindings', {}).items():
        if selections is not None and key not in selections:
            continue
        entry.setdefault('settings', {})['emojis'] = json.loads(
            json.dumps(target_categories, ensure_ascii=False)
        )
        changed.append(key)
    if not changed:
        raise ValueError('没有匹配到任何绑定')
    atomic_write(MODE_PATH, mode)
    return changed


def write_profile(target_categories, profile='default'):
    """把分类写到外部 profile（QQ 走的就是这里）。"""
    snapshot('profile')
    data = load_json(PROFILE_PATH)
    settings = data.get('profiles', {}).get(profile)
    if settings is None:
        raise ValueError(f'profile 不存在：{profile}')
    settings['emojis'] = json.loads(json.dumps(target_categories, ensure_ascii=False))
    atomic_write(PROFILE_PATH, data)
    return profile


def apply_everywhere(target_categories, include_profiles=None):
    """一次写全部：所有角色卡绑定 + 指定 profile。"""
    validate_categories(target_categories)
    include_profiles = include_profiles or ['default']
    changed = write_bindings(target_categories, None)
    profiles = [write_profile(target_categories, p) for p in include_profiles]
    return {'bindings': changed, 'profiles': profiles}


def find_duplicates(categories):
    """找出被多个分类同时引用的图片。"""
    seen = {}
    for cat, images in categories.items():
        for image in images:
            seen.setdefault(image, []).append(cat)
    return {img: cats for img, cats in seen.items() if len(cats) > 1}


def find_missing(categories):
    """找出磁盘上不存在的图片路径。"""
    missing = []
    for cat, images in categories.items():
        for image in images:
            if image.startswith('http://') or image.startswith('https://'):
                continue
            if not os.path.exists(image):
                missing.append({'category': cat, 'path': image})
    return missing


def find_oversized(categories):
    """找出超过 QQ 单图上限的本地图片。"""
    oversized = []
    for cat, images in categories.items():
        for image in images:
            if not os.path.isfile(image):
                continue
            size = os.path.getsize(image)
            if size > MAX_FILE_BYTES:
                oversized.append({
                    'category': cat, 'path': image,
                    'mb': round(size / 1048576, 2),
                })
    return oversized


def health_scan(categories):
    """一次跑完全部检查。"""
    return {
        'duplicates': find_duplicates(categories),
        'missing': find_missing(categories),
        'oversized': find_oversized(categories),
        'total': sum(len(v) for v in categories.values()),
        'categories': len(categories),
    }

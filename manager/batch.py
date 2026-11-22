# -*- coding: utf-8 -*-
"""waifu 表情分类管理器 —— 批量操作

规则批量归类、方案导出导入、按清单重建分类。
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core
from cli import TARGET, get_categories, save


def build_universe():
    """收集所有已知图片路径（来自全部分类 + 贴图目录扫描）。"""
    seen = set()
    state = core.read_state()
    for b in state['bindings']:
        for images in b['categories'].values():
            seen.update(images)
    for p in state['profiles']:
        for images in p['categories'].values():
            seen.update(images)

    sticker_root = '/data/user/0/app.operit/files/waifu_sticker'
    if os.path.isdir(sticker_root):
        for root, _dirs, files in os.walk(sticker_root):
            for name in files:
                if name.lower().endswith(core.IMAGE_EXTENSIONS):
                    seen.add(os.path.join(root, name))
    return sorted(seen)


def cmd_export(output):
    """导出当前分类方案为 JSON，可用于备份或跨设备迁移。"""
    cats = get_categories()
    payload = {
        'version': 1,
        'exported_at': __import__('datetime').datetime.now().isoformat(timespec='seconds'),
        'categories': {k: [os.path.basename(p) for p in v] for k, v in cats.items()},
        'original_paths': cats,
    }
    with open(output, 'w', encoding='utf-8') as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    total = sum(len(v) for v in cats.values())
    print(f'✅ 已导出 {len(cats)} 个分类 / {total} 张 → {output}')


def cmd_import(scheme_path):
    """按方案文件重建分类。方案里用文件名匹配，自动解析成实际路径。"""
    with open(scheme_path, encoding='utf-8') as fh:
        payload = json.load(fh)
    scheme = payload.get('categories')
    if not isinstance(scheme, dict):
        raise SystemExit('方案文件格式不对，缺少 categories')

    universe = build_universe()
    by_name = {}
    for path in universe:
        by_name.setdefault(os.path.basename(path), []).append(path)

    rebuilt = {}
    unresolved = []
    for cat, names in scheme.items():
        paths = []
        for name in names:
            candidates = by_name.get(name)
            if not candidates:
                unresolved.append(name)
                continue
            paths.append(candidates[0])
        if paths:
            rebuilt[cat] = paths

    core.validate_categories(rebuilt)
    save(rebuilt)
    print(f'✅ 已按方案重建 {len(rebuilt)} 个分类 / {sum(len(v) for v in rebuilt.values())} 张')
    if unresolved:
        print(f'⚠️  {len(unresolved)} 个文件找不到：')
        for name in unresolved[:10]:
            print(f'   {name}')


def cmd_autotag(keyword, category):
    """把文件名含关键词的所有图片一次性提到指定分类。"""
    cats = get_categories()
    if category not in cats:
        raise SystemExit(f'目标分类不存在：{category}')

    moved = []
    for cat in list(cats.keys()):
        if cat == category:
            continue
        remaining = []
        for path in cats[cat]:
            if keyword in os.path.basename(path):
                moved.append((cat, path))
            else:
                remaining.append(path)
        if remaining:
            cats[cat] = remaining
        else:
            del cats[cat]
            print(f'注意：{core.label_of(cat)} 分类已空，自动删除')

    if not moved:
        raise SystemExit(f'没有文件名包含「{keyword}」的图片需要移动')

    cats.setdefault(category, []).extend(p for _cat, p in moved)
    if len(cats[category]) > core.CATEGORY_RE_MAX:
        raise SystemExit(f'目标分类会超过 {core.CATEGORY_RE_MAX} 张，已取消')

    save(cats)
    print(f'✅ 批量移动 {len(moved)} 张 → {core.label_of(category)}')
    for cat, path in moved[:15]:
        print(f'   [{core.label_of(cat)}] {os.path.basename(path)}')
    if len(moved) > 15:
        print(f'   …其余 {len(moved) - 15} 张')


def cmd_unassigned():
    """列出磁盘上有、但没被任何分类引用的图片。"""
    used = set()
    cats = get_categories()
    for images in cats.values():
        used.update(os.path.basename(p) for p in images)

    universe = build_universe()
    # 只关心真实文件，跳过 resource: 开头的内置资源键与 http 地址
    orphans = [
        p for p in universe
        if os.path.basename(p) not in used
        and not p.startswith('resource:')
        and not p.startswith('http://')
        and not p.startswith('https://')
    ]

    print(f'未归类图片：{len(orphans)} 张\n')
    for path in orphans[:40]:
        print(f'  {path}')
    if len(orphans) > 40:
        print(f'  …其余 {len(orphans) - 40} 张')


def cmd_adopt(pattern, category):
    """把未归类的图片纳入指定分类。"""
    cats = get_categories()
    if category not in cats:
        raise SystemExit(f'目标分类不存在：{category}')

    used = set()
    for images in cats.values():
        used.update(os.path.basename(p) for p in images)

    candidates = [
        p for p in build_universe()
        if os.path.basename(p) not in used and pattern in os.path.basename(p)
    ]
    if not candidates:
        raise SystemExit(f'没有未归类图片匹配「{pattern}」')

    total = len(cats[category]) + len(candidates)
    if total > core.CATEGORY_RE_MAX:
        raise SystemExit(f'会达到 {total} 张，超过 {core.CATEGORY_RE_MAX} 上限')

    cats[category].extend(candidates)
    save(cats)
    print(f'✅ 纳入 {len(candidates)} 张 → {core.label_of(category)}')
    for path in candidates[:15]:
        print(f'   {os.path.basename(path)}')


COMMANDS = {
    'export': (cmd_export, 1),
    'import': (cmd_import, 1),
    'autotag': (cmd_autotag, 2),
    'unassigned': (cmd_unassigned, 0),
    'adopt': (cmd_adopt, 2),
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        print('可用命令：')
        for name in COMMANDS:
            print(f'  {name}')
        raise SystemExit(1)
    func, argc = COMMANDS[sys.argv[1]]
    args = sys.argv[2:]
    if len(args) < argc:
        print(f'参数不足，{sys.argv[1]} 需要 {argc} 个参数')
        raise SystemExit(1)
    func(*args[:argc])


if __name__ == '__main__':
    main()
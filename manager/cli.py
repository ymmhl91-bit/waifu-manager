# -*- coding: utf-8 -*-
"""waifu 表情分类管理器 —— 命令行入口

用法：
  python3 cli.py list                      列出所有分类
  python3 cli.py show <分类>               列出某分类下的图片
  python3 cli.py check                     健康检查
  python3 cli.py new <分类名> <承接图片>    新建分类，并从别的分类挪一张图过去激活
  python3 cli.py move <文件名片段> <目标>   把图片移到另一分类
  python3 cli.py rename <旧名> <新名>        重命名分类
  python3 cli.py merge <源> <目标>           合并两个分类
  python3 cli.py drop <分类名>               删除分类
  python3 cli.py apply                     同步到所有绑定和 profile
  python3 cli.py backup                    手动打一份备份
  python3 cli.py restore <备份文件>          从备份还原

所有写操作都会先备份，并提示需要重启 Operit 才生效。
"""

import glob
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core

TARGET = 'card:f8c93d80-6dd2-416e-b563-67ca054a7b4c'


def get_categories():
    state = core.read_state()
    for b in state['bindings']:
        if b['selection'] == TARGET:
            return b['categories']
    raise SystemExit(f'找不到绑定 {TARGET}')


def save(categories):
    core.validate_categories(categories)
    changed = core.write_bindings(categories, [TARGET])
    print(f'✅ 已写入 {len(changed)} 个绑定')
    print('⚠️  需要完全重启 Operit 才会生效')


def find_one(cats, pattern, exclude=None):
    """按片段找唯一一张图。"""
    matched = []
    for cat, images in cats.items():
        if cat == exclude:
            continue
        for path in images:
            if pattern in os.path.basename(path) or pattern in path:
                matched.append((cat, path))
    return matched


def cmd_list():
    cats = get_categories()
    print(f'共 {len(cats)} 个分类，{sum(len(v) for v in cats.values())} 张图片\n')
    for key in sorted(cats, key=lambda k: -len(cats[k])):
        print(f'  {core.label_of(key):10} ({key:12}) {len(cats[key]):3} 张')


def cmd_show(category):
    cats = get_categories()
    if category not in cats:
        raise SystemExit(f'分类不存在：{category}')
    print(f'{core.label_of(category)} ({category}) — {len(cats[category])} 张\n')
    for i, path in enumerate(cats[category], 1):
        name = os.path.basename(path)
        exists = '' if os.path.exists(path) else '  [文件缺失]'
        print(f'  {i:3}. {name}{exists}')


def cmd_check():
    cats = get_categories()
    report = core.health_scan(cats)
    print(f'分类 {report["categories"]} 个，图片 {report["total"]} 张\n')

    dup = report['duplicates']
    print(f'重复引用：{len(dup)} 张')
    for path, where in list(dup.items())[:10]:
        print(f'  {os.path.basename(path)} 同时属于 {", ".join(where)}')

    miss = report['missing']
    print(f'\n文件缺失：{len(miss)} 张')
    for item in miss[:10]:
        print(f'  [{item["category"]}] {item["path"]}')

    big = report['oversized']
    print(f'\n超过 5MiB（QQ 直传上限）：{len(big)} 张')
    for item in big[:10]:
        print(f'  [{item["category"]}] {os.path.basename(item["path"])} — {item["mb"]} MB')

    if not dup and not miss and not big:
        print('\n✅ 没有发现问题')


def cmd_new(name, seed):
    """新建分类：必须同时指定一张要挪过去的图，否则空分类无法落库。"""
    cats = get_categories()
    if not core.valid_category(name):
        raise SystemExit('名字不合法：需小写字母开头，只含小写字母/数字/下划线，最长 64 位')
    if name in cats:
        raise SystemExit(f'分类已存在：{name}')

    matched = find_one(cats, seed)
    if not matched:
        raise SystemExit(f'没有匹配到包含「{seed}」的图片')
    if len(matched) > 1:
        print(f'匹配到 {len(matched)} 张，请缩小范围：')
        for cat, path in matched[:20]:
            print(f'  [{core.label_of(cat)}] {os.path.basename(path)}')
        raise SystemExit(1)

    from_cat, path = matched[0]
    cats[from_cat].remove(path)
    if not cats[from_cat]:
        del cats[from_cat]
        print(f'注意：{core.label_of(from_cat)} 分类已空，自动删除')
    cats[name] = [path]

    save(cats)
    print(f'✅ 新建 {name}，首张图来自 {core.label_of(from_cat)}')


def cmd_move(pattern, destination):
    cats = get_categories()
    if destination not in cats:
        raise SystemExit(f'目标分类不存在：{destination}')

    matched = find_one(cats, pattern)
    if not matched:
        raise SystemExit(f'没有匹配到包含「{pattern}」的图片')
    if len(matched) > 1:
        print(f'匹配到 {len(matched)} 张，请缩小范围：')
        for cat, path in matched[:20]:
            print(f'  [{core.label_of(cat)}] {os.path.basename(path)}')
        raise SystemExit(1)

    from_cat, path = matched[0]
    if from_cat == destination:
        raise SystemExit('图片已经在这个分类里了')
    if len(cats[destination]) >= core.CATEGORY_RE_MAX:
        raise SystemExit(f'目标分类已有 {core.CATEGORY_RE_MAX} 张，达到上限')

    cats[from_cat].remove(path)
    cats[destination].append(path)
    if not cats[from_cat]:
        del cats[from_cat]
        print(f'注意：{core.label_of(from_cat)} 分类已空，自动删除')

    save(cats)
    print(f'✅ {os.path.basename(path)}: {core.label_of(from_cat)} → {core.label_of(destination)}')


def cmd_rename(old, new):
    cats = get_categories()
    if old not in cats:
        raise SystemExit(f'分类不存在：{old}')
    if not core.valid_category(new):
        raise SystemExit('新名字不合法：需小写字母开头，只含小写字母/数字/下划线，最长 64 位')
    if new in cats:
        raise SystemExit(f'分类已存在：{new}')

    renamed = {}
    for key, images in cats.items():
        renamed[new if key == old else key] = images

    save(renamed)
    print(f'✅ {old} → {new}')


def cmd_merge(source, target):
    cats = get_categories()
    if source not in cats:
        raise SystemExit(f'源分类不存在：{source}')
    if target not in cats:
        raise SystemExit(f'目标分类不存在：{target}')
    if source == target:
        raise SystemExit('源和目标相同')

    merged = cats[target] + cats[source]
    if len(merged) > core.CATEGORY_RE_MAX:
        raise SystemExit(f'合并后 {len(merged)} 张，超过 {core.CATEGORY_RE_MAX} 上限')

    cats[target] = merged
    del cats[source]

    save(cats)
    print(f'✅ {core.label_of(source)} 已并入 {core.label_of(target)}，现在 {len(merged)} 张')


def cmd_drop(name):
    cats = get_categories()
    if name not in cats:
        raise SystemExit(f'分类不存在：{name}')
    if len(cats) <= 1:
        raise SystemExit('至少要保留一个分类')
    count = len(cats[name])
    del cats[name]
    save(cats)
    print(f'✅ 已删除 {core.label_of(name)}（连带 {count} 张图片的引用）')


def cmd_apply():
    cats = get_categories()
    result = core.apply_everywhere(cats, ['default'])
    print(f'✅ 已同步到 {len(result["bindings"])} 个绑定 + profile {result["profiles"]}')
    print('⚠️  需要完全重启 Operit 才会生效')


def cmd_backup():
    core.snapshot('cli')
    files = sorted(glob.glob(os.path.join(core.BACKUP_DIR, '*.json')))
    print(f'✅ 已备份，当前共 {len(files)} 份')
    print(f'目录：{core.BACKUP_DIR}')


def cmd_restore(name):
    path = name
    if not os.path.exists(path):
        candidate = os.path.join(core.BACKUP_DIR, name)
        if os.path.exists(candidate):
            path = candidate
        else:
            raise SystemExit(f'找不到备份文件：{name}')

    target = core.MODE_PATH if 'mode' in os.path.basename(path) else core.PROFILE_PATH
    shutil.copy2(path, target)
    print(f'✅ 已从 {os.path.basename(path)} 还原到 {os.path.basename(target)}')
    print('⚠️  需要完全重启 Operit 才会生效')


COMMANDS = {
    'list': (cmd_list, 0),
    'show': (cmd_show, 1),
    'check': (cmd_check, 0),
    'new': (cmd_new, 2),
    'move': (cmd_move, 2),
    'rename': (cmd_rename, 2),
    'merge': (cmd_merge, 2),
    'drop': (cmd_drop, 1),
    'apply': (cmd_apply, 0),
    'backup': (cmd_backup, 0),
    'restore': (cmd_restore, 1),
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        raise SystemExit(1)
    func, argc = COMMANDS[sys.argv[1]]
    args = sys.argv[2:]
    if len(args) < argc:
        print(f'参数不足，{sys.argv[1]} 需要 {argc} 个参数')
        raise SystemExit(1)
    func(*args[:argc])


if __name__ == '__main__':
    main()
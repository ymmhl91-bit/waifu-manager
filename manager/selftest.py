# -*- coding: utf-8 -*-
"""核心逻辑自检：只读不写，验证能正确解析现有配置。"""
import json
import sys

sys.path.insert(0, '/data/user/0/app.operit/files/runtime/identities/identity-1794890223595-2735443b/data/chat_outputs/2026-11-22_13-13-10-644/waifu_manager')
import core

state = core.read_state()

print('=== bindings ===')
for b in state['bindings']:
    cats = b['categories']
    print(f"{b['selection']}")
    print(f"  enabled={b['enabled']} emoticons={b['emoticons']} cats={len(cats)} imgs={sum(len(v) for v in cats.values())}")
    print(f"  分类: {', '.join(f'{core.label_of(k)}={len(v)}' for k, v in cats.items())}")

print()
print('=== profiles ===')
for p in state['profiles']:
    cats = p['categories']
    print(f"{p['profile']} emoticons={p['emoticons']} cats={len(cats)} imgs={sum(len(v) for v in cats.values())}")

print()
print('=== 健康检查（角色卡绑定） ===')
target = next(b for b in state['bindings'] if 'f8c93d80' in b['selection'])
report = core.health_scan(target['categories'])
print('总图片', report['total'], '分类', report['categories'])
print('重复引用', len(report['duplicates']), list(report['duplicates'].items())[:3])
print('缺失文件', len(report['missing']), report['missing'][:3])
print('超 5MiB', len(report['oversized']), report['oversized'][:3])

print()
print('=== 校验函数 ===')
for name in ['happy', 'playful', 'fired_up', 'Bad-Name', '123abc', '', 'a'*65]:
    print(f"  {name!r:12} -> {core.valid_category(name)}")

print()
print('=== validate_categories 边界 ===')
for case, data in [
    ('空字典', {}),
    ('空分类', {'happy': []}),
    ('不合法名', {'Bad': ['/x.gif']}),
    ('正常', {'happy': ['/x.gif']}),
]:
    try:
        total = core.validate_categories(data)
        print(f'  {case}: OK total={total}')
    except ValueError as exc:
        print(f'  {case}: 拒绝 -> {exc}')

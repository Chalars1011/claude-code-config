"""从 PCK 目录提取 卡牌→角色 映射，输出 JSON"""
import struct, sys, json, collections
sys.stdout.reconfigure(encoding='utf-8')

PCK = r'D:/泯灭之塔/SlayTheSpire2.pck'
DIR_OFF = 1900075072  # 从 header +32 读出的目录偏移（固定于当前 PCK 版本）

def read_pck_dir(pck=PCK, dir_off=DIR_OFF):
    with open(pck, 'rb') as f:
        f.seek(dir_off)
        n = struct.unpack('<I', f.read(4))[0]
        paths = []
        for i in range(n):
            plen = struct.unpack('<I', f.read(4))[0]
            path = f.read(plen).decode('utf-8', errors='replace').rstrip('\x00')
            pad = (4 - (plen % 4)) % 4
            if pad: f.read(pad)
            f.read(4); f.read(8); f.read(8); f.read(16)
            paths.append(path)
    return paths

ROLE_CN = {'ironclad': '亡铠', 'silent': '噬影', 'defect': '锈灵',
           'necrobinder': '缚骨者', 'regent': '无面王', 'colorless': '无色',
           'event': '事件', 'curse': '诅咒', 'token': '衍生物', 'status': '状态', 'quest': '任务'}

def main():
    paths = read_pck_dir()
    mapping = {}  # card_name -> role_key
    for p in paths:
        if 'card_atlas.sprites' not in p or '/beta/' in p:
            continue
        parts = p.split('/')
        idx = parts.index('card_atlas.sprites')
        if idx + 2 < len(parts):
            role, name = parts[idx+1], parts[idx+2].rsplit('.', 1)[0]
            if role not in ('ancient_beta', 'beta'):
                mapping[name.lower()] = role
    out = {
        '_meta': {'source': PCK, 'generated': '2026-08-05', 'method': 'card_atlas.sprites 目录结构'},
        'card_count': len(mapping),
        'role_cn': ROLE_CN,
        'cards': mapping,
    }
    dest = r'D:/泯灭之塔/card_roles.json'
    with open(dest, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    cnt = collections.Counter(mapping.values())
    print(f'✅ 已生成 {dest}: {len(mapping)} 张卡牌')
    for k, v in sorted(cnt.items(), key=lambda x: -x[1]):
        print(f'   {k:12s} {v}')

if __name__ == '__main__':
    main()

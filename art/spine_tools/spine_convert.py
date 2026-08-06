# -*- coding: utf-8 -*-
"""mesh 顶点铺满矩形转换主脚本 v2"""
import json, io, math, sys
sys.path.insert(0, 'C:/Users/13040/AppData/Local/Temp')
sys.stdout.reconfigure(encoding="utf-8")
import spine_write as sw

SRC = r'C:/Users/13040/Desktop/学习资料/STS2_assets/.godot/imported/characterselect_silent.skel-2c097acc3070cead3ae1a521a29ca974.spskel'
OUT = r'C:/Users/13040/AppData/Local/Temp/charselect_silent_full.skel'

with io.open(SRC, 'rb') as fp:
    data = fp.read()

from SkelToJson.converter import SkelConverter
orig = SkelConverter._read_animations
def patched(self, result):
    self._anims_data_start = self.inp.index
    return orig(self, result)
SkelConverter._read_animations = patched
c = SkelConverter()
js = c.convert(data)
anims_start = c._anims_data_start
strings = c.inp.strings

# ── 骨骼世界矩阵 ──
bones = js['bones']
world = {}
for b in bones:
    name = b['name']
    rot = math.radians(float(b.get('rotation', 0) or 0))
    x, y = float(b.get('x', 0) or 0), float(b.get('y', 0) or 0)
    cosv, sinv = math.cos(rot), math.sin(rot)
    if b.get('parent'):
        p = world[b['parent']]
        world[name] = (p[0]*cosv - p[1]*sinv, p[0]*sinv + p[1]*cosv,
                       p[0]*x - p[1]*y + p[2], p[3]*cosv - p[4]*sinv,
                       p[3]*sinv + p[4]*cosv, p[3]*x + p[4]*y + p[5])
    else:
        world[name] = (cosv, -sinv, x, sinv, cosv, y)

def inverse_apply(m, wx, wy):
    a, b, tx, cc, d, ty = m
    det = a*d - b*cc
    ia, ib, ic, id_ = d/det, -b/det, -cc/det, a/det
    return (ia*(wx - tx) + ib*(wy - ty), ic*(wx - tx) + id_*(wy - ty))

def mesh_to_full(att):
    verts = att['vertices']
    uvs = att['uvs']
    vcount = len(uvs) // 2
    width = float(att.get('width', 0) or 100)
    height = float(att.get('height', 0) or 100)
    cols = max(2, int(math.ceil(math.sqrt(vcount))))
    rows = max(2, int(math.ceil(vcount / cols)))
    # 统一绑定骨骼：silent_root（角色主骨骼，动画幅度极小）——保证网格刚体不撕裂
    BIND_BONE = 'silent_root'
    bind_idx = next(i for i, b in enumerate(bones) if b['name'] == BIND_BONE)
    new_verts = []
    i = 0
    for vi in range(vcount):
        bc = int(verts[i]); i += 1
        col = vi % cols; row = vi // cols
        wx = (col / (cols - 1)) * width
        wy = (row / (rows - 1)) * height
        lx, ly = inverse_apply(world[BIND_BONE], wx, wy)
        new_verts.append(1); new_verts.append(bind_idx); new_verts.append(round(lx, 3)); new_verts.append(round(ly, 3)); new_verts.append(1.0)
    new_uvs = []
    for vi in range(vcount):
        col = vi % cols; row = vi // cols
        new_uvs.append(round(col / (cols - 1), 6))
        new_uvs.append(round(row / (rows - 1), 6))
    # 重建三角形拓扑：规则网格单元剖分（每单元 2 三角形）
    tris = []
    for row in range(rows - 1):
        for col in range(cols - 1):
            i0 = row * cols + col
            i1 = i0 + 1
            i2 = i0 + cols
            i3 = i2 + 1
            if i3 < vcount:
                tris += [i0, i1, i2, i1, i3, i2]
    ntri = len(tris) // 3
    # hull 控制读取的三角形数：ntri = (2v - hull - 2) * 3 / 3 -> hull = 2v - ntri - 2
    hull = vcount * 2 - ntri - 2
    new_att = dict(att)
    new_att['vertices'] = new_verts
    new_att['uvs'] = new_uvs
    new_att['triangles'] = tris
    new_att['hull'] = hull
    new_att['edges'] = []
    new_att['vcount'] = vcount
    return new_att, vcount, cols, rows

for slot_name in ['character', 'hair']:
    att = js['skins'][0]['attachments'][slot_name][slot_name]
    if att.get('type') == 'mesh':
        full, vc, cols, rows = mesh_to_full(att)
        print('slot %s: %d 顶点铺满 %dx%d 网格 (%.0fx%.0f)' % (slot_name, vc, cols, rows, att.get('width', 0), att.get('height', 0)))
        js['skins'][0]['attachments'][slot_name][slot_name] = full

# ── 写回 ──
def skip_anim_names(data, start):
    p = start
    def rvarint(p):
        b = data[p]; v = b & 0x7F; p += 1
        while b & 0x80:
            b = data[p]; v |= (b & 0x7F) << 7; p += 1
        return v, p
    n, p = rvarint(p)
    for _ in range(n):
        ln, p = rvarint(p)
        p += ln - 1
    return p

anim_data_start = skip_anim_names(data, anims_start)
out = sw.convert_skel(data, js, strings, anim_data_start)
with io.open(OUT, 'wb') as fp:
    fp.write(out)
print('新文件:', OUT, len(out), '字节（原', len(data), '）')

# ── 验证 ──
c2 = SkelConverter()
js2 = c2.convert(out)
print('验证通过! index:', c2.inp.index, '/', len(out))
for slot_name in ['character', 'hair']:
    att = js2['skins'][0]['attachments'][slot_name][slot_name]
    print(' ', slot_name, '-> mesh vcount=%d uvs=%d tris=%d' % (len(att.get('uvs', []))//2, len(att.get('uvs', [])), len(att.get('triangles', []))//3))
print('动画:', list(js2['animations'].keys()))

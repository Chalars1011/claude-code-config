# -*- coding: utf-8 -*-
"""生成全新 .skel：2骨骼 + 铺满网格 + 程序化待机动画（translate/scale/rotate，无 deform）"""
import json, io, math, struct, sys
sys.path.insert(0, 'C:/Users/13040/AppData/Local/Temp')
sys.stdout.reconfigure(encoding="utf-8")

SRC = r'C:/Users/13040/Desktop/学习资料/STS2_assets/.godot/imported/characterselect_silent.skel-2c097acc3070cead3ae1a521a29ca974.spskel'
OUT = r'C:/Users/13040/AppData/Local/Temp/charselect_silent_new.skel'

with io.open(SRC, 'rb') as fp:
    data = fp.read()

from SkelToJson.converter import SkelConverter
c = SkelConverter()
js = c.convert(data)
strings = c.inp.strings  # ['character', 'hair']
sk = js['skeleton']
bones_json = js['bones']

# ── 骨骼世界矩阵（原版，用于算中心）──
world = {}
for b in bones_json:
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

def world_pos(bone, lx, ly):
    m = world[bone]
    return (m[0]*lx + m[1]*ly + m[2], m[3]*lx + m[4]*ly + m[5])

def inverse_apply(m, wx, wy):
    a, b, tx, cc, d, ty = m
    det = a*d - b*cc
    ia, ib, ic, id_ = d/det, -b/det, -cc/det, a/det
    return (ia*(wx - tx) + ib*(wy - ty), ic*(wx - tx) + id_*(wy - ty))

def mesh_center(att):
    """原 mesh 顶点世界位置包围盒（多骨骼用主骨骼近似）"""
    verts = att['vertices']
    i = 0; xs = []; ys = []
    while i < len(verts):
        bc = int(verts[i]); i += 1
        for _ in range(bc):
            bi = int(verts[i]); lx = verts[i+1]; ly = verts[i+2]; i += 4
            bn = bones_json[bi]['name']
            wx, wy = world_pos(bn, lx, ly)
            xs.append(wx); ys.append(wy)
    return min(xs), min(ys), max(xs), max(ys)

class W:
    def __init__(self):
        self.b = bytearray()
    def varint(self, v):
        while True:
            b = v & 0x7F; v >>= 7
            if v: self.b.append(b | 0x80)
            else: self.b.append(b); break
    def int32(self, v):
        self.b += struct.pack(">i", v)
    def float32(self, v):
        self.b += struct.pack(">f", v)
    def boolean(self, v):
        self.b.append(1 if v else 0)
    def string(self, s):
        if s is None: self.varint(0); return
        raw = s.encode("utf-8")
        self.varint(len(raw) + 1); self.b += raw
    def ref(self, idx):
        self.varint(idx)
    def color(self, hexstr):
        self.int32(int(hexstr, 16) & 0xFFFFFFFF if int(hexstr,16) > 0x7FFFFFFF else int(hexstr, 16) | (-(1<<32) if int(hexstr,16) > 0x7FFFFFFF else 0))
    def byte(self, v):
        self.b.append(v & 0xFF)

def color_i(hexstr):
    v = int(hexstr, 16) & 0xFFFFFFFF
    return v - (1 << 32) if v > 0x7FFFFFFF else v

w = W()
# ── header ──
w.b += data[0:8]  # hash 原样
w.string("4.2.40")
for k in ['x', 'y', 'width', 'height', 'referenceScale']:
    w.float32(float(sk.get(k, 0) or 0))
w.boolean(True)
w.float32(float(sk.get('fps', 30) or 0))
w.string(sk.get('images'))
w.string("")
# strings
w.varint(len(strings))
for s in strings: w.string(s)
# ── bones：root(0) + silent_root(1) ──
w.varint(2)
w.string("root")
w.float32(0); w.float32(0); w.float32(0)  # rot x y
w.float32(1); w.float32(1)                 # scaleX Y
w.float32(0); w.float32(0)                 # shearX Y
w.float32(0)                               # length
w.varint(0)                                # inherit
w.boolean(False)                           # skinRequired
w.int32(color_i("ffffffff")); w.string(None); w.boolean(True)  # nonessential
w.string("silent_root")
w.varint(0)                                # parent root
w.float32(0); w.float32(3010.69189); w.float32(-2359.15771)  # rot x y
w.float32(1); w.float32(1)
w.float32(0); w.float32(0)
w.float32(0)
w.varint(0)
w.boolean(False)
w.int32(color_i("ffffffff")); w.string(None); w.boolean(True)
# ── slots：hair(0→root), character(1→silent_root) ──
w.varint(2)
w.string("hair"); w.varint(0)
w.int32(color_i("ffffffff")); w.int32(color_i("ffffffff"))
w.ref(2)  # attachment "hair" (strings 索引 2)
w.varint(0)  # blend normal
w.boolean(True)
w.string("character"); w.varint(1)
w.int32(color_i("ffffffff")); w.int32(color_i("ffffffff"))
w.ref(1)  # attachment "character" (索引 1)
w.varint(0)
w.boolean(True)
# ── constraints 4 组全 0 ──
for _ in range(4): w.varint(0)

# ── mesh 生成（铺满网格，中心对齐原版位置）──
def build_mesh(slot_name, bind_bone, center, bbox, bone_index):
    vcount = 491 if slot_name == 'character' else 165
    cols = int(math.ceil(math.sqrt(vcount)))
    rows = int(math.ceil(vcount / cols))
    cx, cy = center
    # 尺寸 = 原版包围盒尺寸（贴图方式与原版一致）
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    minx = cx - width / 2
    miny = cy - height / 2
    verts = []
    for vi in range(vcount):
        col = vi % cols; row = vi // cols
        wx = minx + (col / (cols - 1)) * width
        wy = miny + (row / (rows - 1)) * height
        lx, ly = inverse_apply(world[bind_bone], wx, wy)
        verts += [1, bone_index, round(lx, 3), round(ly, 3), 1.0]
    uvs = []
    for vi in range(vcount):
        col = vi % cols; row = vi // cols
        uvs += [round(col / (cols - 1), 6), round(1 - row / (rows - 1), 6)]
    tris = []
    for row in range(rows - 1):
        for col in range(cols - 1):
            i0 = row * cols + col; i1 = i0 + 1; i2 = i0 + cols; i3 = i2 + 1
            if i3 < vcount:
                tris += [i0, i1, i2, i1, i3, i2]
    ntri = len(tris) // 3
    hull = vcount * 2 - ntri - 2
    return verts, uvs, tris, hull, vcount

# 原版网格中心（对齐用）
att_char = js['skins'][0]['attachments']['character']['character']
att_hair = js['skins'][0]['attachments']['hair']['hair']
cbbox = mesh_center(att_char)
hbbox = mesh_center(att_hair)
print('原版包围盒: character=%s hair=%s' % (cbbox, hbbox))

# ── default skin ──
w.varint(2)  # slot_count
# slot 1 (character)：1 附件
w.varint(1); w.varint(1)
w.ref(1)  # 名字 "character"
w.byte(2 | 128)  # flags: mesh + weighted
ccx = (cbbox[0] + cbbox[2]) / 2; ccy = (cbbox[1] + cbbox[3]) / 2
verts, uvs, tris, hull, vcount = build_mesh('character', 'silent_root', (ccx, ccy), cbbox, 1)
w.varint(hull)  # hull 与三角形数匹配
w.varint(vcount)
for v in verts: w.float32(v) if False else None
i = 0
while i < len(verts):
    w.varint(int(verts[i])); i += 1
    for _ in range(1):
        w.varint(int(verts[i])); w.float32(verts[i+1]); w.float32(verts[i+2]); w.float32(verts[i+3]); i += 4
for v in uvs: w.float32(v)
for t in tris: w.varint(t)
w.varint(0)  # edges
w.float32(4637); w.float32(2400)  # width height
# slot 0 (hair)：1 附件
w.varint(0); w.varint(1)
w.ref(2)  # "hair"
w.byte(2 | 128)
hcx = (hbbox[0] + hbbox[2]) / 2; hcy = (hbbox[1] + hbbox[3]) / 2
verts2, uvs2, tris2, hull2, vcount2 = build_mesh('hair', 'root', (hcx, hcy), hbbox, 0)
w.varint(hull2)
w.varint(vcount2)
i = 0
while i < len(verts2):
    w.varint(int(verts2[i])); i += 1
    for _ in range(1):
        w.varint(int(verts2[i])); w.float32(verts2[i+1]); w.float32(verts2[i+2]); w.float32(verts2[i+3]); i += 4
for v in uvs2: w.float32(v)
for t in tris2: w.varint(t)
w.varint(0)
w.float32(790); w.float32(705)
# 其余 skins: 0
w.varint(0)
# events: 0
w.varint(0)
# ── 动画：1 个 "animation"，3 条 timeline（rotate/translate/scale on silent_root）──
w.varint(1)  # anim count
w.string("animation")
w.varint(3)  # 总 timeline 数
w.varint(0)  # slot timelines: 0
w.varint(1)  # bone timelines: 1
w.varint(1)  # boneIndex = silent_root
w.varint(3)  # timeline count
# rotate: 3 帧
w.byte(0); w.varint(3); w.varint(0)
w.float32(0); w.float32(0)
w.float32(2.0); w.float32(1.2); w.byte(0)
w.float32(3.9); w.float32(0); w.byte(0)
# translate: 3 帧（浮动）
w.byte(1); w.varint(3); w.varint(0)
w.float32(0); w.float32(0); w.float32(0)
w.float32(2.0); w.float32(0); w.float32(-12); w.byte(0)
w.float32(3.9); w.float32(0); w.float32(0); w.byte(0)
# scale: 3 帧（呼吸）
w.byte(4); w.varint(3); w.varint(0)
w.float32(0); w.float32(1); w.float32(1)
w.float32(2.0); w.float32(1.02); w.float32(1.02); w.byte(0)
w.float32(3.9); w.float32(1); w.float32(1); w.byte(0)
# IK/transform/path/physics/deform/draworder/event: 0
for _ in range(7): w.varint(0)

with io.open(OUT, 'wb') as fp:
    fp.write(bytes(w.b))
print('新文件:', OUT, len(w.b), '字节')

# ── 验证 ──
c2 = SkelConverter()
js2 = c2.convert(bytes(w.b))
print('验证通过! index:', c2.inp.index, '/', len(w.b))
print('  bones:', [b['name'] for b in js2['bones']])
print('  slots:', [s['name'] for s in js2['slots']])
print('  attachments:', list(js2['skins'][0]['attachments'].keys()))
print('  animations:', list(js2['animations'].keys()))
print('  动画内容:', json.dumps(js2['animations']['animation'], ensure_ascii=False)[:200])

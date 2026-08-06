# -*- coding: utf-8 -*-
"""Spine 4.2 binary .skel 写回器：骨架段重写 + 动画段原样拷贝"""
import struct, sys
sys.stdout.reconfigure(encoding="utf-8")

class W:
    def __init__(self):
        self.b = bytearray()
    def varint(self, v):
        # 7-bit varint（optimizePositive）
        while True:
            b = v & 0x7F
            v >>= 7
            if v:
                self.b.append(b | 0x80)
            else:
                self.b.append(b)
                break
    def int32(self, v):
        self.b += struct.pack(">I", v)
    def float32(self, v):
        self.b += struct.pack(">f", v)
    def boolean(self, v):
        self.b.append(1 if v else 0)
    def string(self, s):
        if s is None:
            self.varint(0)
            return
        raw = s.encode("utf-8")
        self.varint(len(raw) + 1)
        self.b += raw
    def ref(self, idx):
        self.varint(idx)  # string_ref 索引（1-based）
    def color(self, rgba_hex):
        # 'ffc300ff' -> BE int32
        v = int(rgba_hex, 16)
        self.int32(v)

def color_default():
    return "ffffffff"

def build_skel(data, js, strings, anims_start):
    """序列化：header→strings→bones→slots→skins→events→anim名字 + 原动画段"""
    w = W()
    # 1. hash（原 8 字节）
    w.b += data[0:8]
    # 2. version
    w.string(js['skeleton'].get('spine', '4.2.40'))
    # 3. x y width height referenceScale
    sk = js['skeleton']
    for k in ['x', 'y', 'width', 'height', 'referenceScale']:
        w.float32(float(sk.get(k, 0) or 0))
    # 4. nonessential
    w.boolean(True)
    w.float32(float(sk.get('fps', 30) or 0))
    w.string(sk.get('images'))
    w.string(sk.get('audio') or "")
    # 5. strings 表（原顺序）
    w.varint(len(strings))
    for s in strings:
        w.string(s)
    # 6. bones
    bones = js['bones']
    w.varint(len(bones))
    for i, b in enumerate(bones):
        w.string(b['name'])
        if i > 0:
            parent_idx = next(j for j, x in enumerate(bones) if x['name'] == b.get('parent'))
            w.varint(parent_idx)
        w.float32(float(b.get('rotation', 0) or 0))
        w.float32(float(b.get('x', 0) or 0))
        w.float32(float(b.get('y', 0) or 0))
        w.float32(float(b.get('scaleX', 1) or 1))
        w.float32(float(b.get('scaleY', 1) or 1))
        w.float32(float(b.get('shearX', 0) or 0))
        w.float32(float(b.get('shearY', 0) or 0))
        w.float32(float(b.get('length', 0) or 0))
        w.varint(int(b.get('inherit', 0) or 0))
        w.boolean(bool(b.get('skinRequired', False)))
        # nonessential
        w.color(b.get('color', 'ffffffff'))
        w.string(b.get('icon'))
        w.boolean(bool(b.get('visible', True)))
    # 7. slots
    slots = js['slots']
    w.varint(len(slots))
    for s in slots:
        w.string(s['name'])
        bone_idx = next(j for j, b in enumerate(bones) if b['name'] == s['bone'])
        w.varint(bone_idx)
        w.color(s.get('color', 'ffffffff'))
        w.color(s.get('dark', 'ffffffff'))
        # attachment 引用
        attname = s.get('attachment')
        if attname and attname in strings:
            w.ref(strings.index(attname) + 1)
        else:
            w.ref(0)
        # blend mode
        blend_names = ['normal', 'additive', 'multiply', 'screen']
        blend = s.get('blend', 'normal')
        w.varint(blend_names.index(blend) if blend in blend_names else 0)
        w.boolean(bool(s.get('visible', True)))
    # 8. 无 constraints（4 组全 0）
    for _ in range(4):
        w.varint(0)
    return w, bones, slots

def write_attachment(w, att_name, att, strings):
    """附件写入（mesh 铺满矩形版 / region）"""
    if att_name in strings:
        w.ref(strings.index(att_name) + 1)
    else:
        w.ref(0)
    if att.get('type') == 'mesh':
        # flags: mesh(2) + weighted(128)
        flags = 2 | 128
        if att.get('path'):
            flags |= 16
        if att.get('color'):
            flags |= 32
        if att.get('sequence'):
            flags |= 64
        w.b.append(flags)
        if flags & 16:
            p = att['path']
            if p in strings: w.ref(strings.index(p) + 1)
            else: w.ref(0)
        if flags & 32:
            w.color(att['color'])
        if flags & 64:
            seq = att['sequence']
            for k in ['count', 'start', 'digits', 'setup']:
                w.varint(int(seq.get(k, 0) or 0))
        w.varint(int(att['hull']))
        verts = att['vertices']
        vcount = int(att['vcount'])
        w.varint(vcount)
        # 加权顶点：每顶点 boneCount + (boneIndex, x, y, weight) x N
        i = 0
        while i < len(verts):
            bc = int(verts[i]); i += 1
            w.varint(bc)
            for _ in range(bc):
                w.varint(int(verts[i])); w.float32(float(verts[i+1])); w.float32(float(verts[i+2])); w.float32(float(verts[i+3])); i += 4
        for v in att['uvs']:
            w.float32(float(v))
        ntri = (vcount * 2 - int(att['hull']) - 2) * 3
        for j in range(ntri):
            w.varint(int(att['triangles'][j]))
        # nonessential: edges + width + height
        edges = att.get('edges', [])
        w.varint(len(edges))
        for e in edges:
            w.varint(int(e))
        w.float32(float(att.get('width', 0) or 0))
        w.float32(float(att.get('height', 0) or 0))
    else:
        w.b.append(0)  # flags: region(0)
        w.float32(float(att.get('x', 0) or 0))
        w.float32(float(att.get('y', 0) or 0))
        w.float32(float(att.get('scaleX', 1) or 1))
        w.float32(float(att.get('scaleY', 1) or 1))
        w.float32(float(att.get('width', 100) or 100))
        w.float32(float(att.get('height', 100) or 100))

def write_skins_and_rest(w, js, strings, data, anims_start):
    # 9. default skin
    skins = js['skins']
    default_skin = None
    for s in skins:
        if s.get('name') == 'default':
            default_skin = s
            break
    if default_skin is None:
        w.varint(0)
    else:
        atts = default_skin.get('attachments', {})
        w.varint(len(atts))
        slots = js['slots']
        for slot_name, slot_atts in atts.items():
            slot_idx = next(i for i, s in enumerate(slots) if s['name'] == slot_name)
            w.varint(slot_idx)
            w.varint(len(slot_atts))
            for att_name, att in slot_atts.items():
                write_attachment(w, att_name, att, strings)
    # 10. 其余 skins：0
    w.varint(0)
    # 11. events：0
    w.varint(0)
    # 12. animations 名字
    anims = js.get('animations', {})
    w.varint(len(anims))
    for name in anims.keys():
        w.string(name)
    # 13. 动画数据段原样拷贝
    w.b += data[anims_start:]
    return bytes(w.b)

def convert_skel(data, js, strings, anims_start):
    w, bones, slots = build_skel(data, js, strings, anims_start)
    out = write_skins_and_rest(w, js, strings, data, anims_start)
    return out

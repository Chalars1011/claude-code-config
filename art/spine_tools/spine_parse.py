# -*- coding: utf-8 -*-
import struct, sys
sys.stdout.reconfigure(encoding="utf-8")

class R:
    def __init__(self, d, off=0):
        self.d = d; self.p = off
    def byte(self):
        v = self.d[self.p]; self.p += 1; return v
    def int32(self):
        v = struct.unpack(">i", self.d[self.p:self.p+4])[0]; self.p += 4; return v
    def float32(self):
        v = struct.unpack(">f", self.d[self.p:self.p+4])[0]; self.p += 4; return v
    def boolean(self):
        return self.byte() == 1
    def varint(self, opt=True):
        b = self.byte(); v = b & 0x7F
        if b & 0x80:
            b = self.byte(); v |= (b & 0x7F) << 7
            if b & 0x80:
                b = self.byte(); v |= (b & 0x7F) << 14
                if b & 0x80:
                    b = self.byte(); v |= (b & 0x7F) << 21
                    if b & 0x80:
                        v |= (self.byte() & 0x7F) << 28
        if not opt:
            v = (v >> 1) ^ -(v & 1)
        return v
    def string(self):
        n = self.varint(True)
        if n == 0: return None
        s = self.d[self.p:self.p+n-1].decode("utf-8", errors="replace")
        self.p += n - 1
        return s
    def color(self):
        return (self.byte(), self.byte(), self.byte(), self.byte())

def read_vertices(r):
    n = r.varint(True); out = []
    for i in range(n):
        w = r.varint(True); out.append(w)
        if w:
            for _ in range(w):
                r.varint(True); r.float32(); r.float32(); r.float32()
        else:
            r.float32(); r.float32()
    return out

def parse_attachment(r, name):
    flags = r.byte()
    attname = r.string() if (flags & 8) else name
    atype = flags & 0x7
    path = r.string() if (flags & 16) else attname
    if flags & 32: r.color()
    if flags & 64: r.varint(True)
    if atype == 0:
        if flags & 128: r.float32()
        r.float32(); r.float32(); r.float32(); r.float32(); r.float32(); r.float32()
        return {"type": "region", "name": attname, "path": path}
    elif atype == 2:
        hull = r.varint(True)
        verts = read_vertices(r)
        for _ in range(len(verts)): r.float32()
        return {"type": "mesh", "name": attname, "path": path, "hull": hull}
    elif atype == 1:
        read_vertices(r); return {"type": "bbox", "name": attname}
    elif atype == 4:
        read_vertices(r); r.float32(); r.float32()
        return {"type": "path", "name": attname}
    elif atype == 6:
        r.int32(); read_vertices(r)
        return {"type": "clip", "name": attname}
    elif atype == 5:
        if flags & 128: r.float32()
        r.float32(); r.float32()
        return {"type": "point", "name": attname}
    return {"type": atype, "name": attname}

def parse_skin(r, default_skin):
    if default_skin:
        n = r.varint(True)
        if n == 0: return None
        res = []
        for i in range(n):
            slot = r.varint(True)
            nn = r.varint(True)
            for j in range(nn):
                name = r.string()
                res.append((slot, name, parse_attachment(r, name)))
        return res
    else:
        return {"skin_name": r.string()}

def parse_skel(d, off):
    r = R(d, off)
    try:
        low = r.int32(); high = r.int32()
        version = r.string()
        x = r.float32(); y = r.float32(); w = r.float32(); h = r.float32()
        refscale = r.float32()
        nonessential = r.boolean()
        if nonessential:
            r.float32(); r.string(); r.string()
        nstr = r.varint(True)
        strings = [r.string() for _ in range(nstr)]
        nb = r.varint(True)
        bones = []
        for i in range(nb):
            name = r.string()
            parent = None if i == 0 else r.varint(True)
            rot = r.float32(); bx = r.float32(); by = r.float32()
            sx = r.float32(); sy = r.float32(); shx = r.float32(); shy = r.float32()
            ln = r.float32(); inherit = r.varint(True)
            skinreq = r.boolean()
            if nonessential:
                r.color(); r.string(); r.boolean()
            bones.append({"name": name, "parent": parent, "x": bx, "y": by})
        nslot = r.varint(True)
        slots = []
        for i in range(nslot):
            sname = r.string(); bone = r.varint(True)
            r.color()
            a2, r2, g2, b2 = r.byte(), r.byte(), r.byte(), r.byte()
            attname = r.string(); blend = r.varint(True)
            if nonessential: r.boolean()
            slots.append({"name": sname, "bone": bone, "attachment": attname})
        nik = r.varint(True)
        for i in range(nik):
            r.string(); r.varint(True)
            n = r.varint(True)
            for _ in range(n): r.varint(True)
            r.varint(True)
            flags = r.byte()
            if flags & 64: r.float32()
            if flags & 128: r.float32()
        ntr = r.varint(True)
        for i in range(ntr):
            r.string(); r.varint(True)
            n = r.varint(True)
            for _ in range(n): r.varint(True)
            r.varint(True)
            flags = r.byte()
            if flags & 8: r.float32()
            if flags & 16: r.float32()
            if flags & 32: r.float32()
            if flags & 64: r.float32()
            if flags & 128: r.float32()
            flags = r.byte()
            if flags & 1: r.float32()
            if flags & 2: r.float32()
            if flags & 4: r.float32()
            if flags & 8: r.float32()
            if flags & 16: r.float32()
            if flags & 32: r.float32()
            if flags & 64: r.float32()
        npa = r.varint(True)
        for i in range(npa):
            r.string(); r.varint(True); r.boolean()
            n = r.varint(True)
            for _ in range(n): r.varint(True)
            r.varint(True)
            flags = r.byte()
            if flags & 128: r.float32()
            r.float32(); r.float32(); r.float32(); r.float32(); r.float32()
        nph = r.varint(True)
        for i in range(nph):
            r.string(); r.varint(True); r.varint(True)
            flags = r.byte()
            if flags & 2: r.float32()
            if flags & 4: r.float32()
            if flags & 8: r.float32()
            if flags & 16: r.float32()
            if flags & 32: r.float32()
            if flags & 64: r.float32()
            r.byte(); r.float32(); r.float32(); r.float32()
            if flags & 128: r.float32()
            r.float32(); r.float32()
            flags = r.byte()
            if flags & 128: r.float32()
        ds = parse_skin(r, True)
        skins = []
        while True:
            name = r.string()
            if name is None: break
            skins.append((name, parse_skin(r, False)))
        nev = r.varint(True)
        events = []
        for i in range(nev):
            name = r.string(); r.int32(); r.float32()
            r.string(); r.int32(); r.float32(); r.string()
            ap = r.string()
            if ap:
                r.float32(); r.float32(); r.string()
            events.append(name)
        n_anim = r.varint(True)
        animations = []
        for i in range(n_anim):
            name = r.string(); animations.append(name)
        return {"ok": True, "version": version, "bones": bones, "slots": slots,
                "default_skin": ds, "skins": skins, "events": events,
                "animations": animations, "pos": r.p, "nonessential": nonessential,
                "strings": strings}
    except Exception as e:
        return {"ok": False, "error": str(e), "pos": r.p}

if __name__ == "__main__":
    import io
    path = r"C:/Users/13040/Desktop/学习资料/STS2_assets/.godot/imported/characterselect_silent.skel-2c097acc3070cead3ae1a521a29ca974.spskel"
    with io.open(path, "rb") as fp:
        d = fp.read()
    print("file size:", len(d))
    for off in [0, 8]:
        res = parse_skel(d, off)
        if res.get("ok"):
            print("--- offset %d: version=%s bones=%d slots=%d" % (off, res["version"], len(res["bones"]), len(res["slots"])))
            print("  bones:", [b["name"] for b in res["bones"]])
            print("  slots:", [s["name"] for s in res["slots"]])
            print("  default_skin:", res["default_skin"])
            print("  skins:", res["skins"])
            print("  events:", res["events"])
            print("  animations:", res["animations"])
            print("  parsed to:", res["pos"], "/", len(d))
        else:
            print("--- offset %d: FAIL at %s: %s" % (off, res.get("pos"), res["error"][:100]))

def debug_parse(d, off):
    r = R(d, off)
    def pos(tag):
        print("  @%-6d %s" % (r.p, tag))
    low = r.int32(); high = r.int32(); pos("hash")
    version = r.string(); pos("version=%s" % version)
    x = r.float32(); y = r.float32(); w = r.float32(); h = r.float32()
    refscale = r.float32(); pos("xywh=%s,%s,%s,%s ref=%s" % (x, y, w, h, refscale))
    nonessential = r.boolean(); pos("nonessential=%s" % nonessential)
    if nonessential:
        fps = r.float32(); ip = r.string(); ap = r.string(); pos("fps=%s images=%s audio=%s" % (fps, ip, ap))
    nstr = r.varint(True); pos("nstr=%d" % nstr)
    strings = [r.string() for _ in range(nstr)]; pos("strings=%s" % strings[:10])
    nb = r.varint(True); pos("nbones=%d" % nb)
    for i in range(nb):
        name = r.string()
        parent = None if i == 0 else r.varint(True)
        rot = r.float32(); bx = r.float32(); by = r.float32()
        sx = r.float32(); sy = r.float32(); shx = r.float32(); shy = r.float32()
        ln = r.float32(); inherit = r.varint(True)
        skinreq = r.boolean()
        if nonessential:
            r.color(); r.string(); r.boolean()
        if i < 25 or i >= nb - 2:
            print("  bone[%d] %s parent=%s x=%.1f y=%.1f @%d" % (i, name, parent, bx, by, r.p))
    pos("bones done")

if __name__ == "__main__":
    import io
    path = r"C:/Users/13040/Desktop/学习资料/STS2_assets/.godot/imported/characterselect_silent.skel-2c097acc3070cead3ae1a521a29ca974.spskel"
    with io.open(path, "rb") as fp:
        d = fp.read()
    debug_parse(d, 0)

def full_parse(d, off=0):
    """完整解析，记录各段位置"""
    r = R(d, off)
    seg = {}
    low = r.int32(); high = r.int32()
    seg['hash_end'] = r.p
    version = r.string()
    x = r.float32(); y = r.float32(); w = r.float32(); h = r.float32()
    refscale = r.float32()
    nonessential = r.boolean()
    if nonessential:
        r.float32(); r.string(); r.string()
    nstr = r.varint(True)
    strings = [r.string() for _ in range(nstr)]
    seg['strings_end'] = r.p
    nb = r.varint(True)
    bones = []
    for i in range(nb):
        name = r.string()
        parent = None if i == 0 else r.varint(True)
        rot = r.float32(); bx = r.float32(); by = r.float32()
        sx = r.float32(); sy = r.float32(); shx = r.float32(); shy = r.float32()
        ln = r.float32(); inherit = r.varint(True)
        skinreq = r.boolean()
        if nonessential:
            r.color(); r.string(); r.boolean()
        bones.append({'name': name, 'parent': parent, 'rotation': rot, 'x': bx, 'y': by,
                      'scaleX': sx, 'scaleY': sy, 'shearX': shx, 'shearY': shy, 'length': ln})
    seg['bones_end'] = r.p
    nslot = r.varint(True)
    slots = []
    for i in range(nslot):
        sname = r.string(); bone = r.varint(True)
        r.color()
        a2, r2, g2, b2 = r.byte(), r.byte(), r.byte(), r.byte()
        attname = r.string(); blend = r.varint(True)
        if nonessential: r.boolean()
        slots.append({'name': sname, 'bone': bone, 'attachment': attname})
    seg['slots_end'] = r.p
    nik = r.varint(True)
    for i in range(nik):
        r.string(); r.varint(True)
        n = r.varint(True)
        for _ in range(n): r.varint(True)
        r.varint(True)
        flags = r.byte()
        if flags & 64: r.float32()
        if flags & 128: r.float32()
    seg['ik_end'] = r.p
    ntr = r.varint(True)
    for i in range(ntr):
        r.string(); r.varint(True)
        n = r.varint(True)
        for _ in range(n): r.varint(True)
        r.varint(True)
        flags = r.byte()
        if flags & 8: r.float32()
        if flags & 16: r.float32()
        if flags & 32: r.float32()
        if flags & 64: r.float32()
        if flags & 128: r.float32()
        flags = r.byte()
        if flags & 1: r.float32()
        if flags & 2: r.float32()
        if flags & 4: r.float32()
        if flags & 8: r.float32()
        if flags & 16: r.float32()
        if flags & 32: r.float32()
        if flags & 64: r.float32()
    seg['transform_end'] = r.p
    npa = r.varint(True)
    for i in range(npa):
        r.string(); r.varint(True); r.boolean()
        n = r.varint(True)
        for _ in range(n): r.varint(True)
        r.varint(True)
        flags = r.byte()
        if flags & 128: r.float32()
        r.float32(); r.float32(); r.float32(); r.float32(); r.float32()
    seg['path_end'] = r.p
    nph = r.varint(True)
    for i in range(nph):
        r.string(); r.varint(True); r.varint(True)
        flags = r.byte()
        if flags & 2: r.float32()
        if flags & 4: r.float32()
        if flags & 8: r.float32()
        if flags & 16: r.float32()
        if flags & 32: r.float32()
        if flags & 64: r.float32()
        r.byte(); r.float32(); r.float32(); r.float32()
        if flags & 128: r.float32()
        r.float32(); r.float32()
        flags = r.byte()
        if flags & 128: r.float32()
    seg['physics_end'] = r.p
    # skins
    n = r.varint(True)
    if n == 0:
        seg['skins_end'] = r.p
        return seg
    for i in range(n):
        slot = r.varint(True)
        nn = r.varint(True)
        for j in range(nn):
            name = r.string()
            parse_attachment(r, name)
    while True:
        name = r.string()
        if name is None: break
        # 非 default skin：color + 各种 constraints + slots
        nn = r.varint(True)
        for _ in range(nn): r.varint(True)
        nn = r.varint(True)
        for _ in range(nn): r.varint(True)
        nn = r.varint(True)
        for _ in range(nn): r.varint(True)
        nn = r.varint(True)
        for _ in range(nn): r.varint(True)
        nn = r.varint(True)
        for _ in range(nn): r.varint(True)
        nslots = r.varint(True)
        for i in range(nslots):
            r.varint(True)
            nn = r.varint(True)
            for j in range(nn):
                r.string()
                parse_attachment(r, None)
    seg['skins_end'] = r.p
    nev = r.varint(True)
    events = []
    for i in range(nev):
        name = r.string(); r.int32(); r.float32()
        r.string(); r.int32(); r.float32(); r.string()
        ap = r.string()
        if ap:
            r.float32(); r.float32(); r.string()
        events.append(name)
    seg['events_end'] = r.p
    n_anim = r.varint(True)
    anims = []
    for i in range(n_anim):
        name = r.string(); anims.append(name)
    seg['anims_start'] = r.p  # 动画数据段起点
    seg['bones'] = bones
    seg['slots'] = slots
    seg['nonessential'] = nonessential
    seg['strings'] = strings
    return seg

if __name__ == "__main__" and False:
    pass

def full_parse2(d, off=0):
    """完整解析 v2：string_ref 引用 + skin 数量前缀"""
    r = R(d, off)
    seg = {}
    r.int32(); r.int32()
    version = r.string()
    for _ in range(5): r.float32()
    nonessential = r.boolean()
    if nonessential:
        r.float32(); r.string(); r.string()
    nstr = r.varint(True)
    strings = [r.string() for _ in range(nstr)]
    seg['strings'] = strings
    nb = r.varint(True)
    bones = []
    for i in range(nb):
        name = r.string()
        parent = None if i == 0 else r.varint(True)
        rot = r.float32(); bx = r.float32(); by = r.float32()
        sx = r.float32(); sy = r.float32(); shx = r.float32(); shy = r.float32()
        ln = r.float32(); inherit = r.varint(True)
        skinreq = r.boolean()
        if nonessential:
            r.color(); r.string(); r.boolean()
        bones.append({'name': name, 'parent': parent, 'rotation': rot, 'x': bx, 'y': by,
                      'scaleX': sx, 'scaleY': sy, 'shearX': shx, 'shearY': shy, 'length': ln})
    seg['bones'] = bones
    nslot = r.varint(True)
    slots = []
    for i in range(nslot):
        sname = r.string(); bone = r.varint(True)
        r.color(); r.color()
        attname = r.varint(True)  # string_ref 索引
        blend = r.varint(True)
        if nonessential: r.boolean()
        slots.append({'name': sname, 'bone': bone, 'attachment_idx': attname})
    seg['slots'] = slots
    # IK
    nik = r.varint(True)
    for i in range(nik):
        r.string(); r.varint(True)
        n = r.varint(True)
        for _ in range(n): r.varint(True)
        r.varint(True)
        flags = r.byte()
        if flags & 64: r.float32()
        if flags & 128: r.float32()
    # Transform
    ntr = r.varint(True)
    for i in range(ntr):
        r.string(); r.varint(True)
        n = r.varint(True)
        for _ in range(n): r.varint(True)
        r.varint(True)
        flags = r.byte()
        if flags & 8: r.float32()
        if flags & 16: r.float32()
        if flags & 32: r.float32()
        if flags & 64: r.float32()
        if flags & 128: r.float32()
        flags = r.byte()
        if flags & 1: r.float32()
        if flags & 2: r.float32()
        if flags & 4: r.float32()
        if flags & 8: r.float32()
        if flags & 16: r.float32()
        if flags & 32: r.float32()
        if flags & 64: r.float32()
    # Path
    npa = r.varint(True)
    for i in range(npa):
        r.string(); r.varint(True); r.boolean()
        n = r.varint(True)
        for _ in range(n): r.varint(True)
        r.varint(True)
        flags = r.byte()
        if flags & 128: r.float32()
        r.float32(); r.float32(); r.float32(); r.float32(); r.float32()
    # Physics
    nph = r.varint(True)
    for i in range(nph):
        r.string(); r.varint(True); r.varint(True)
        flags = r.byte()
        if flags & 2: r.float32()
        if flags & 4: r.float32()
        if flags & 8: r.float32()
        if flags & 16: r.float32()
        if flags & 32: r.float32()
        if flags & 64: r.float32()
        r.byte(); r.float32(); r.float32(); r.float32()
        if flags & 128: r.float32()
        r.float32(); r.float32()
        flags = r.byte()
        if flags & 128: r.float32()
    # default skin
    n = r.varint(True)
    if n:
        for i in range(n):
            r.varint(True)  # slot index
            nn = r.varint(True)
            for j in range(nn):
                r.varint(True)  # attach name ref
                parse_attachment(r, None)
    # 其余 skins：数量前缀
    nskins = r.varint(True)
    for s in range(nskins):
        r.string()  # skin name
        if nonessential: r.color()
        for _ in range(r.varint(True)): r.varint(True)
        for _ in range(r.varint(True)): r.varint(True)
        for _ in range(r.varint(True)): r.varint(True)
        for _ in range(r.varint(True)): r.varint(True)
        nsl = r.varint(True)
        for i in range(nsl):
            r.varint(True)
            nn = r.varint(True)
            for j in range(nn):
                r.varint(True)
                parse_attachment(r, None)
    seg['skins_end'] = r.p
    nev = r.varint(True)
    for i in range(nev):
        r.string(); r.int32(); r.float32()
        r.string(); r.int32(); r.float32(); r.string()
        ap = r.string()
        if ap:
            r.float32(); r.float32(); r.string()
    seg['events_end'] = r.p
    n_anim = r.varint(True)
    anims = []
    for i in range(n_anim):
        name = r.string(); anims.append(name)
    seg['anims_start'] = r.p
    seg['animations'] = anims
    seg['nonessential'] = nonessential
    return seg

def parse_attachment2(r, name):
    flags = r.byte()
    attname = r.varint(True) if (flags & 8) else name
    atype = flags & 0x7
    if flags & 16: r.varint(True)
    if flags & 32: r.color()
    if flags & 64:
        for _ in range(4): r.varint(True)
    if atype == 0:
        if flags & 128: r.float32()
        for _ in range(6): r.float32()
        return {'type': 'region', 'name': attname}
    elif atype == 2:
        hull = r.varint(True)
        vcount = r.varint(True)
        weighted = (flags & 128) != 0
        if weighted:
            for _ in range(vcount):
                bc = r.varint(True)
                for _ in range(bc):
                    r.varint(True); r.float32(); r.float32(); r.float32()
        else:
            for _ in range(vcount * 2): r.float32()
        for _ in range(vcount * 2): r.float32()
        ntri = (vcount * 2 - hull - 2) * 3
        for _ in range(ntri): r.varint(True)
        return {'type': 'mesh', 'name': attname, 'hull': hull, 'vcount': vcount}
    elif atype == 1:
        vcount = r.varint(True)
        weighted2 = (flags & 16) != 0
        if weighted2:
            for _ in range(vcount):
                bc = r.varint(True)
                for _ in range(bc):
                    r.varint(True); r.float32(); r.float32(); r.float32()
        else:
            for _ in range(vcount * 2): r.float32()
        return {'type': 'bbox'}
    elif atype == 4:
        vcount = r.varint(True)
        weighted3 = (flags & 64) != 0
        if weighted3:
            for _ in range(vcount):
                bc = r.varint(True)
                for _ in range(bc):
                    r.varint(True); r.float32(); r.float32(); r.float32()
        else:
            for _ in range(vcount * 2): r.float32()
        for _ in range(2): r.float32()
        return {'type': 'path'}
    elif atype == 6:
        r.int32()
        vcount = r.varint(True)
        weighted4 = (flags & 16) != 0
        if weighted4:
            for _ in range(vcount):
                bc = r.varint(True)
                for _ in range(bc):
                    r.varint(True); r.float32(); r.float32(); r.float32()
        else:
            for _ in range(vcount * 2): r.float32()
        return {'type': 'clip'}
    elif atype == 5:
        if flags & 128: r.float32()
        r.float32(); r.float32()
        return {'type': 'point'}
    return {'type': atype, 'name': attname}

def full_parse3(d, off=0):
    r = R(d, off)
    seg = {}
    r.int32(); r.int32()
    version = r.string()
    for _ in range(5): r.float32()
    nonessential = r.boolean()
    if nonessential:
        r.float32(); r.string(); r.string()
    nstr = r.varint(True)
    strings = [r.string() for _ in range(nstr)]
    seg['strings'] = strings
    nb = r.varint(True)
    bones = []
    for i in range(nb):
        name = r.string()
        parent = None if i == 0 else r.varint(True)
        rot = r.float32(); bx = r.float32(); by = r.float32()
        sx = r.float32(); sy = r.float32(); shx = r.float32(); shy = r.float32()
        ln = r.float32(); inherit = r.varint(True)
        skinreq = r.boolean()
        if nonessential:
            r.color(); r.string(); r.boolean()
        bones.append({'name': name, 'parent': parent, 'rotation': rot, 'x': bx, 'y': by,
                      'scaleX': sx, 'scaleY': sy, 'shearX': shx, 'shearY': shy, 'length': ln})
    seg['bones'] = bones
    nslot = r.varint(True)
    slots = []
    for i in range(nslot):
        sname = r.string(); bone = r.varint(True)
        r.color(); r.color()
        attname = r.varint(True)
        blend = r.varint(True)
        if nonessential: r.boolean()
        slots.append({'name': sname, 'bone': bone, 'attachment_idx': attname})
    seg['slots'] = slots
    nik = r.varint(True)
    for i in range(nik):
        r.string(); r.varint(True)
        n = r.varint(True)
        for _ in range(n): r.varint(True)
        r.varint(True)
        flags = r.byte()
        if flags & 64: r.float32()
        if flags & 128: r.float32()
    ntr = r.varint(True)
    for i in range(ntr):
        r.string(); r.varint(True)
        n = r.varint(True)
        for _ in range(n): r.varint(True)
        r.varint(True)
        flags = r.byte()
        if flags & 8: r.float32()
        if flags & 16: r.float32()
        if flags & 32: r.float32()
        if flags & 64: r.float32()
        if flags & 128: r.float32()
        flags = r.byte()
        if flags & 1: r.float32()
        if flags & 2: r.float32()
        if flags & 4: r.float32()
        if flags & 8: r.float32()
        if flags & 16: r.float32()
        if flags & 32: r.float32()
        if flags & 64: r.float32()
    npa = r.varint(True)
    for i in range(npa):
        r.string(); r.varint(True); r.boolean()
        n = r.varint(True)
        for _ in range(n): r.varint(True)
        r.varint(True)
        flags = r.byte()
        if flags & 128: r.float32()
        r.float32(); r.float32(); r.float32(); r.float32(); r.float32()
    nph = r.varint(True)
    for i in range(nph):
        r.string(); r.varint(True); r.varint(True)
        flags = r.byte()
        if flags & 2: r.float32()
        if flags & 4: r.float32()
        if flags & 8: r.float32()
        if flags & 16: r.float32()
        if flags & 32: r.float32()
        if flags & 64: r.float32()
        r.byte(); r.float32(); r.float32(); r.float32()
        if flags & 128: r.float32()
        r.float32(); r.float32()
        flags = r.byte()
        if flags & 128: r.float32()
    return r, seg, nonessential, strings

def full_parse3_full(d, off=0):
    r, seg, nonessential, strings = full_parse3(d, off)
    n = r.varint(True)
    if n:
        for i in range(n):
            r.varint(True)
            nn = r.varint(True)
            for j in range(nn):
                r.varint(True)
                parse_attachment2(r, None)
    nskins = r.varint(True)
    for s in range(nskins):
        r.string()
        if nonessential: r.color()
        for _ in range(r.varint(True)): r.varint(True)
        for _ in range(r.varint(True)): r.varint(True)
        for _ in range(r.varint(True)): r.varint(True)
        for _ in range(r.varint(True)): r.varint(True)
        nsl = r.varint(True)
        for i in range(nsl):
            r.varint(True)
            nn = r.varint(True)
            for j in range(nn):
                r.varint(True)
                parse_attachment2(r, None)
    seg['skins_end'] = r.p
    nev = r.varint(True)
    for i in range(nev):
        r.string(); r.int32(); r.float32()
        r.string(); r.int32(); r.float32(); r.string()
        ap = r.string()
        if ap:
            r.float32(); r.float32(); r.string()
    seg['events_end'] = r.p
    n_anim = r.varint(True)
    anims = []
    for i in range(n_anim):
        name = r.string(); anims.append(name)
    seg['anims_start'] = r.p
    seg['animations'] = anims
    seg['nonessential'] = nonessential
    return seg

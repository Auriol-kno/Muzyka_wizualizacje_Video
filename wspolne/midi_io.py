"""Minimalny zapis/odczyt Standard MIDI File (bez zależności). Obsługuje mapę tempa i markery."""
import math
import struct


def vlq(n):
    b = [n & 0x7F]
    n >>= 7
    while n:
        b.append((n & 0x7F) | 0x80)
        n >>= 7
    return bytes(reversed(b))


def _trk(ev):
    return b"MTrk" + struct.pack(">I", len(ev)) + ev


def _meta(typ, body):
    return b"\xff" + bytes([typ]) + vlq(len(body)) + body


def write_midi(path, tracks, ppq=480, tempo_map=((0, 500000),), ts=(3, 4), markers=(), title=""):
    """tracks: [(nazwa, kanał, [(tick_on, tick_off, pitch, vel), ...])]"""
    cond = [(0, 0, _meta(0x03, (title or "Conductor").encode("latin-1"))),
            (0, 1, _meta(0x58, bytes([ts[0], int(math.log2(ts[1])), 24, 8])))]
    for tk, us in tempo_map:
        cond.append((tk, 2, _meta(0x51, int(us).to_bytes(3, "big"))))
    for tk, txt in markers:
        cond.append((tk, 3, _meta(0x06, txt.encode("latin-1"))))
    cond.sort(key=lambda e: (e[0], e[1]))
    ev, last = b"", 0
    for tk, _, body in cond:
        ev += vlq(tk - last) + body
        last = tk
    out = [_trk(ev + vlq(0) + b"\xff\x2f\x00")]
    for name, ch, notes in tracks:
        raw = []
        for t0, t1, p, v in notes:
            raw.append((t0, 1, p, v))
            raw.append((t1, 0, p, 0))
        raw.sort(key=lambda e: (e[0], e[1]))
        ev = vlq(0) + _meta(0x03, name.encode("latin-1")) + vlq(0) + bytes([0xC0 | ch, 0])
        last = 0
        for tick, on, p, v in raw:
            ev += vlq(tick - last) + bytes([(0x90 if on else 0x80) | ch, p, v if on else 64])
            last = tick
        out.append(_trk(ev + vlq(0) + b"\xff\x2f\x00"))
    with open(path, "wb") as f:
        f.write(b"MThd" + struct.pack(">IHHH", 6, 1, len(out), ppq) + b"".join(out))


def read_midi_full(path):
    """Zwraca (nuty, ppq, markery). Nuta: dict(ch, pitch, vel, t0, t1 [s], k0, k1 [ticki])."""
    data = open(path, "rb").read()
    assert data[:4] == b"MThd"
    _, ntr, ppq = struct.unpack(">HHH", data[8:14])
    pos, tempos, raw, marks = 14, [], [], []
    for _ in range(ntr):
        ln = struct.unpack(">I", data[pos + 4:pos + 8])[0]
        p, end, tick, status, opened = pos + 8, pos + 8 + ln, 0, 0, {}
        while p < end:
            d = 0
            while True:
                b = data[p]; p += 1
                d = (d << 7) | (b & 0x7F)
                if not b & 0x80:
                    break
            tick += d
            b = data[p]
            if b == 0xFF:
                typ = data[p + 1]; p += 2
                l = 0
                while True:
                    c = data[p]; p += 1
                    l = (l << 7) | (c & 0x7F)
                    if not c & 0x80:
                        break
                body = data[p:p + l]; p += l
                if typ == 0x51:
                    tempos.append((tick, int.from_bytes(body, "big")))
                elif typ == 0x06:
                    marks.append((tick, body.decode("latin-1")))
                continue
            if b & 0x80:
                status = b; p += 1
            kind, ch = status & 0xF0, status & 0x0F
            if kind in (0x80, 0x90):
                n, v = data[p], data[p + 1]; p += 2
                if kind == 0x90 and v > 0:
                    opened[(ch, n)] = (tick, v)
                elif (ch, n) in opened:
                    t0, vv = opened.pop((ch, n))
                    raw.append((ch, n, vv, t0, tick))
            elif kind in (0xC0, 0xD0):
                p += 1
            else:
                p += 2
        pos = end
    tempos = sorted(tempos) or [(0, 500000)]
    if tempos[0][0] != 0:
        tempos.insert(0, (0, 500000))
    seg = []  # (tick_start, sec_start, us)
    s = 0.0
    for i, (tk, us) in enumerate(tempos):
        if i:
            ptk, _, pus = seg[-1][0], seg[-1][1], seg[-1][2]
            s = seg[-1][1] + (tk - ptk) / ppq * pus / 1e6
        seg.append((tk, s, us))

    def sec(tk):
        j = max(i for i, sg in enumerate(seg) if sg[0] <= tk)
        return seg[j][1] + (tk - seg[j][0]) / ppq * seg[j][2] / 1e6

    notes = [dict(ch=c, pitch=n, vel=v, t0=sec(a), t1=sec(b), k0=a, k1=b) for c, n, v, a, b in raw]
    notes.sort(key=lambda d: (d["t0"], d["pitch"]))
    return notes, ppq, [(tk, sec(tk), txt) for tk, txt in sorted(marks)]

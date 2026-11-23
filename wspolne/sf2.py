"""Minimalny parser SoundFont 2 (bez zależności): wyciąga strefy instrumentu dla danego presetu."""
import struct
import numpy as np


def _chunks(data, off, end):
    while off < end:
        cid = data[off:off + 4]; ln = struct.unpack("<I", data[off + 4:off + 8])[0]
        yield cid, off + 8, ln
        off += 8 + ln + (ln & 1)


def load(path):
    data = open(path, "rb").read()
    assert data[:4] == b"RIFF" and data[8:12] == b"sfbk"
    smpl = None; pd = {}
    for cid, o, ln in _chunks(data, 12, len(data)):
        if cid != b"LIST":
            continue
        typ = data[o:o + 4]
        for sid, so, sl in _chunks(data, o + 4, o + ln):
            if typ == b"sdta" and sid == b"smpl":
                smpl = np.frombuffer(data[so:so + sl], "<i2").astype(np.float32) / 32768
            elif typ == b"pdta":
                pd[sid.decode()] = data[so:so + sl]

    def recs(name, fmt, size):
        b = pd[name]
        return [struct.unpack(fmt, b[i:i + size]) for i in range(0, len(b), size)]

    phdr = recs("phdr", "<20sHHHIII", 38)
    pbag = recs("pbag", "<HH", 4)
    pgen = recs("pgen", "<HH", 4)
    inst = recs("inst", "<20sH", 22)
    ibag = recs("ibag", "<HH", 4)
    igen = recs("igen", "<HH", 4)
    shdr = recs("shdr", "<20sIIIIIBbHH", 46)
    return dict(smpl=smpl, phdr=phdr, pbag=pbag, pgen=pgen, inst=inst, ibag=ibag, igen=igen, shdr=shdr)


def _gens(genlist, a, b):
    d = {}
    for oper, amt in genlist[a:b]:
        d[oper] = amt
    return d


def s16(v):
    return v - 65536 if v >= 32768 else v


def preset_zones(sf, bank=0, prog=0):
    ph = sf["phdr"]
    pi = next(i for i, p in enumerate(ph[:-1]) if p[1] == prog and p[2] == bank)
    zones = []
    for bi in range(ph[pi][3], ph[pi + 1][3]):
        pg = _gens(sf["pgen"], sf["pbag"][bi][0], sf["pbag"][bi + 1][0])
        if 41 not in pg:
            continue
        ins = pg[41]
        pkr = pg.get(43, 0x7F00)
        gl = {}
        for ib in range(sf["inst"][ins][1], sf["inst"][ins + 1][1]):
            g = _gens(sf["igen"], sf["ibag"][ib][0], sf["ibag"][ib + 1][0])
            if 53 not in g:
                gl = g  # strefa globalna
                continue
            z = dict(gl); z.update(g)
            kr = z.get(43, 0x7F00); vr = z.get(44, 0x7F00)
            sh = sf["shdr"][z[53]]
            name, start, end, ls, le, rate, opitch, corr, link, stype = sh
            zones.append(dict(
                klo=kr & 0xFF, khi=kr >> 8, vlo=vr & 0xFF, vhi=vr >> 8,
                start=start + s16(z.get(0, 0)) + 32768 * s16(z.get(4, 0)),
                end=end + s16(z.get(1, 0)) + 32768 * s16(z.get(12, 0)),
                ls=ls + s16(z.get(2, 0)) + 32768 * s16(z.get(45, 0)),
                le=le + s16(z.get(3, 0)) + 32768 * s16(z.get(50, 0)),
                rate=rate, root=z.get(58, opitch) if z.get(58, 0xFFFF) != 0xFFFF else opitch,
                corr=corr + s16(z.get(52, 0)), coarse=s16(z.get(51, 0)),
                loop=z.get(54, 0) & 1, atten=z.get(48, 0) / 10.0,
                pan=s16(z.get(17, 0)) / 500.0, stype=stype,
                atk=s16(z.get(34, -12000)), dec=s16(z.get(36, -12000)), sus=z.get(37, 0) / 10.0,
                rel=s16(z.get(38, -12000)), name=name.split(b"\0")[0].decode("latin-1")))
    return zones

"""Podglądy koncepcji drugiej wersji klipu (`wizualizacje/koncepcje.py`): każda koncepcja w dwóch
chwilach nagrania (cicho / głośno) + tablica przeglądowa do wyboru.

  python skrypty/koncepcje_podglad.py --wav <nagranie.wav> [--out <katalog>] [--tylko A_zlote_poziomice]
"""
import argparse
import json
import os
import sys
import time
import tomllib
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from wizualizacje.analiza import analizuj          # noqa: E402
from wizualizacje.koncepcje import KONCEPCJE       # noqa: E402

FONT = ROOT / "assets" / "fonts"
OPISY = {
    "A_zlote_poziomice": ("Złote poziomice",
                          "Ciemny teren z gęstych linii, grzbiety podświetlone złotem. Głośność → złoto i wysokość gór,"
                          " każda nuta zostawia koncentryczne kręgi (miejsce ← wysokość dźwięku). Złoty pył w powietrzu."),
    "B_rzeka_iskier": ("Rzeka iskier",
                       "Wstęga drobin płynie w głąb kadru z mocnym bokeh. Głośność → szerokość, barwa dźwięku → zakręt,"
                       " wysokie tony → więcej złotych iskier, ataki → rozbłyski. Najspokojniejsza, najbardziej „nocna”."),
    "C_zlota_spirala": ("Złota spirala",
                        "Prostokąt złoty i spirala Fibonacciego na granatowym marmurze, odłamki szkła, smuga mgławicy."
                        " Każda nuta wpada w spiralę i w 4 s biegnie do środka. Najwięcej matematyki wprost (φ)."),
    "D_krysztal_w_jedwabiu": ("Kryształ w jedwabiu",
                              "Obracający się dwudziestościan ze złotymi krawędziami, światło w środku ← głośność,"
                              " jedwabne pasma dymu falują ze średnim pasmem, po atakach złote iskry (kierunek ← wysokość)."),
    "E_pejzaz_nokturnu": ("Pejzaż nokturnu (połączenie)",
                          "Złote poziomice na dole, na niebie rzeka iskier jak Droga Mleczna (← wysokie tony),"
                          " w rogu gwiazdozbiór spirali złotej, w który wpadają nuty. Łączy wszystkie motywy."),
}


def katalog(arg):
    if arg:
        return Path(arg)
    cfg = ROOT / "config" / "sciezki.toml"
    if cfg.exists():
        with open(cfg, "rb") as f:
            return Path(os.path.expandvars(tomllib.load(f)["udzial"]["robocze"])) / "koncepcje_v2"
    return ROOT / "robocze" / "koncepcje_v2"


def chwile(an):
    """Cicha i głośna chwila nagrania (z pominięciem początku i końca)."""
    i0, i1 = an.idx(8.0), an.idx(an.dlugosc - 8.0)
    e = an.rms_env[i0:i1]
    glosno = an.czas[i0 + int(np.argmax(e))]
    cel = np.percentile(e, 30)
    cicho = an.czas[i0 + int(np.argmin(np.abs(e - cel) + (an.czas[i0:i1] < 20) * 9))]
    return [("cicho", float(cicho)), ("glosno", float(glosno))]


def zawin(tekst, font, szer, d):
    slowa, linie, akt = tekst.split(), [], ""
    for s in slowa:
        prob = (akt + " " + s).strip()
        if d.textlength(prob, font=font) > szer and akt:
            linie.append(akt); akt = s
        else:
            akt = prob
    return linie + [akt]


def tablica(wyniki, out):
    tw, th, marg, tekst_w = 640, 360, 24, 640
    wiersz = th + marg
    im = Image.new("RGB", (marg * 4 + tw * 2 + tekst_w, 110 + wiersz * len(wyniki) + marg), (8, 11, 20))
    d = ImageDraw.Draw(im)
    f_t = ImageFont.truetype(str(FONT / "Inter-SemiBold.otf"), 40)
    f_h = ImageFont.truetype(str(FONT / "Inter-SemiBold.otf"), 28)
    f_b = ImageFont.truetype(str(FONT / "Inter-Light.otf"), 21)
    f_m = ImageFont.truetype(str(FONT / "Inter-Medium.otf"), 17)
    d.text((marg, 28), "Nokturn op. 9 nr 2 · wersja 2 · pięć koncepcji (lewa: cicho, prawa: głośno)",
           font=f_t, fill=(242, 222, 170))
    for r, (nazwa, klatki) in enumerate(wyniki):
        y = 110 + r * wiersz
        for k, (etykieta, t, plik, _) in enumerate(klatki):
            x = marg + k * (tw + marg)
            im.paste(Image.open(plik).resize((tw, th), Image.LANCZOS), (x, y))
            napis = {"cicho": "cicho", "glosno": "głośno"}.get(etykieta, etykieta)
            d.text((x + 10, y + th - 28), f"{napis} · {t:.1f} s", font=f_m, fill=(255, 255, 255))
        tx = marg * 3 + tw * 2
        tytul, opis = OPISY[nazwa]
        d.text((tx, y + 4), f"{nazwa[0]}. {tytul}", font=f_h, fill=(242, 190, 90))
        yy = y + 52
        for linia in zawin(opis, f_b, tekst_w - 10, d):
            d.text((tx, yy), linia, font=f_b, fill=(214, 222, 236)); yy += 30
    im.save(out, quality=92)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wav", required=True)
    ap.add_argument("--out")
    ap.add_argument("--tylko", nargs="*")
    ap.add_argument("--seed", type=int, default=20261122)
    a = ap.parse_args()
    out = katalog(a.out); out.mkdir(parents=True, exist_ok=True)
    an = analizuj(a.wav)
    momenty = chwile(an)
    wyniki, manifest = [], {}
    for nazwa, fn in KONCEPCJE.items():
        if a.tylko and nazwa not in a.tylko:
            continue
        klatki = []
        for etykieta, t in momenty:
            t0 = time.time()
            img, par = fn(an.cechy(t), t, np.random.default_rng(a.seed), analiza=an)
            plik = out / f"{nazwa}_{etykieta}.png"
            Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8)).save(plik)
            print(f"{nazwa} {etykieta} t={t:.1f}s  {time.time() - t0:.1f} s  {par}", flush=True)
            klatki.append((etykieta, t, plik, par))
            manifest[f"{nazwa}_{etykieta}"] = dict(t=round(t, 2), parametry=par)
        wyniki.append((nazwa, klatki))
    (out / "manifest.json").write_text(json.dumps(dict(wav=str(a.wav), seed=a.seed, klatki=manifest), ensure_ascii=False, indent=1),
                                       encoding="utf-8")
    if len(wyniki) == len(KONCEPCJE):
        tablica(wyniki, out / "przeglad_koncepcji.jpg")
        print("tablica →", out / "przeglad_koncepcji.jpg")


if __name__ == "__main__":
    main()

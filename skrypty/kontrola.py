"""Kontrola jakości gotowego MP4 (ta sama co w `animacja.py`): długość obrazu = dźwięku, czarne klatki,
skoki jasności, −15 LUFS / −1,5 dBTP, H.264 + AAC 48 kHz. Raport JSON na wyjściu i w `<plik>.qc.json`.

    python skrypty/kontrola.py klip.mp4 [--fps 25]

Dla plików spoza potoku (np. po interpolacji / powiększeniu w ComfyUI) oczekiwana długość = długość dźwięku.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "skrypty"))

import animacja  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mp4")
    ap.add_argument("--fps", type=float, default=None, help="domyślnie odczytane z pliku")
    a = ap.parse_args()
    mp4 = Path(a.mp4)
    pr = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,duration,r_frame_rate",
                         "-of", "json", str(mp4)], capture_output=True, text=True)
    st = {s["codec_type"]: s for s in json.loads(pr.stdout)["streams"]}
    fps = a.fps
    if fps is None:
        l, m = st["video"]["r_frame_rate"].split("/")
        fps = float(l) / float(m)
    qc = animacja.kontrola(mp4, float(st["audio"]["duration"]), fps)
    with open(mp4.with_suffix(".qc.json"), "w", encoding="utf-8") as f:
        json.dump(dict(plik=str(mp4), kontrola=qc), f, ensure_ascii=False, indent=2)
    print(json.dumps(qc, ensure_ascii=False, indent=2))
    print(("OK" if qc["ok"] else "UWAGA: kontrola nie przeszła") + f" → {mp4}")


if __name__ == "__main__":
    main()

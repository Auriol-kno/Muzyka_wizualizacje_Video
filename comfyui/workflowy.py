"""Workflowy ComfyUI w formacie API, budowane w Pythonie (łatwo zmieniać parametry z cech dźwięku).

Ustawienia pod GTX 1060 6 GB + Juggernaut XL v9 Lightning: 6 kroków, CFG 2, dpmpp_sde/karras,
rozdzielczość z „kubełków” SDXL (1344×768 ≈ 16:9), potem skalowanie do 1920×1080 w naszym kodzie.
"""

MODEL_DOMYSLNY = "juggernautXL_v9Rdphoto2Lightning.safetensors"
NEGATYW = ("text, letters, watermark, signature, logo, people, face, hands, frame, border, "
           "lowres, blurry, jpeg artifacts, oversaturated")


def tlo_sdxl(prompt, seed, szer=1344, wys=768, kroki=6, cfg=2.0, model=MODEL_DOMYSLNY, negatyw=NEGATYW,
             prefiks="muzyka_tlo"):
    """txt2img: tło / faktura do warstwy pod cząsteczkami."""
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": model}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": negatyw, "clip": ["1", 1]}},
        "4": {"class_type": "EmptyLatentImage", "inputs": {"width": szer, "height": wys, "batch_size": 1}},
        "5": {"class_type": "KSampler", "inputs": {"model": ["1", 0], "positive": ["2", 0], "negative": ["3", 0],
                                                    "latent_image": ["4", 0], "seed": int(seed), "steps": kroki,
                                                    "cfg": cfg, "sampler_name": "dpmpp_sde", "scheduler": "karras",
                                                    "denoise": 1.0}},
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "7": {"class_type": "SaveImage", "inputs": {"images": ["6", 0], "filename_prefix": prefiks}},
    }


def stylizacja_sdxl(obraz_wejsciowy, prompt, seed, sila=0.45, kroki=6, cfg=2.0, model=MODEL_DOMYSLNY,
                    negatyw=NEGATYW, prefiks="muzyka_styl"):
    """img2img: „malarska” wersja klatki z naszego renderera. sila (denoise) 0.3–0.6: im mniej,
    tym wierniej zachowany kształt wynikający z dźwięku. Obraz wejściowy wcześniej wgrać przez
    Comfy.wgraj_obraz() i przeskalować do kubełka SDXL."""
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": model}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": negatyw, "clip": ["1", 1]}},
        "4": {"class_type": "LoadImage", "inputs": {"image": obraz_wejsciowy}},
        "5": {"class_type": "VAEEncode", "inputs": {"pixels": ["4", 0], "vae": ["1", 2]}},
        "6": {"class_type": "KSampler", "inputs": {"model": ["1", 0], "positive": ["2", 0], "negative": ["3", 0],
                                                    "latent_image": ["5", 0], "seed": int(seed), "steps": kroki,
                                                    "cfg": cfg, "sampler_name": "dpmpp_sde", "scheduler": "karras",
                                                    "denoise": float(sila)}},
        "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["1", 2]}},
        "8": {"class_type": "SaveImage", "inputs": {"images": ["7", 0], "filename_prefix": prefiks}},
    }


# ----------------------------------------------------------------------------- węzły „Muzyka Graficznie”
# sama nazwa pliku: węzeł szuka jej w folderze [udzial] zrodla z config/sciezki.toml
WAV_NOKTURN = "Frederic_Chopin_-_Nocturne_Eb_major_Opus_9,_number_2.wav"
PODPIS_NOKTURN = "Fryderyk Chopin – Nokturn Es-dur op. 9 nr 2\\nwyk. Martha Goldstein · CC BY-SA 2.0"


def wizualizacja_podglad(wav=WAV_NOKTURN, preset="3_gory_ze_strun", czasy="62, 211", szer=1280, wys=720,
                         seed=20261122, podpis="", prefiks="muzyka_klatki"):
    """Klatki wizualizacji z dźwięku (węzeł MGKlatki) → zapis/podgląd w ComfyUI."""
    return {
        "1": {"class_type": "MGKlatki", "inputs": {"wav": wav, "preset": preset, "czasy_s": czasy, "szerokosc": szer,
                                                    "wysokosc": wys, "seed": seed, "podpis": podpis}},
        "2": {"class_type": "SaveImage", "inputs": {"images": ["1", 0], "filename_prefix": prefiks}},
    }


def wizualizacja_stylizowana(prompt, wav=WAV_NOKTURN, preset="3_gory_ze_strun", czasy="211", sila=0.35, seed=7,
                             kroki=6, cfg=2.0, model=MODEL_DOMYSLNY, negatyw=NEGATYW, prefiks="muzyka_hybryda"):
    """Hybryda: klatka z renderera (kształt i ruch z dźwięku) → img2img SDXL (faktura, „malarskość”).
    Render w kubełku SDXL 1344×768; sila 0.25–0.45 zachowuje kształt nici i gór."""
    return {
        "1": {"class_type": "MGKlatki", "inputs": {"wav": wav, "preset": preset, "czasy_s": czasy, "szerokosc": 1344,
                                                    "wysokosc": 768, "seed": 20261122, "podpis": ""}},
        "2": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": model}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["2", 1]}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"text": negatyw, "clip": ["2", 1]}},
        "5": {"class_type": "VAEEncode", "inputs": {"pixels": ["1", 0], "vae": ["2", 2]}},
        "6": {"class_type": "KSampler", "inputs": {"model": ["2", 0], "positive": ["3", 0], "negative": ["4", 0],
                                                    "latent_image": ["5", 0], "seed": int(seed), "steps": kroki,
                                                    "cfg": cfg, "sampler_name": "dpmpp_sde", "scheduler": "karras",
                                                    "denoise": float(sila)}},
        "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["2", 2]}},
        "8": {"class_type": "SaveImage", "inputs": {"images": ["7", 0], "filename_prefix": prefiks}},
        "9": {"class_type": "PreviewImage", "inputs": {"images": ["1", 0]}},
    }


def wizualizacja_klip(wav=WAV_NOKTURN, preset="3_gory_ze_strun", od=0.0, do=10.0, fps=25, rozmiar="1280x720",
                      seed=20261122, podpis=PODPIS_NOKTURN):
    """Klip MP4 jak w potoku (węzeł MGKlip): normalizacja −15 LUFS, H.264 + AAC 48 kHz, kontrola jakości.
    do = 0 → cały utwór (Nokturn 3_gory_ze_strun 720p25: ~4 h na GTX 1060 / 8 procesów CPU)."""
    return {
        "1": {"class_type": "MGKlip", "inputs": {"wav": wav, "preset": preset, "od_s": float(od), "do_s": float(do),
                                                  "fps": fps, "rozmiar": rozmiar, "seed": seed, "podpis": podpis}},
        "2": {"class_type": "PreviewImage", "inputs": {"images": ["1", 2]}},
    }


def _wczytaj_wideo(zrodlo, meta_batch=None):
    """VHS_LoadVideoPath bez zmiany fps i rozmiaru (format „None”); zrodlo: ścieżka albo [węzeł, wyjście]."""
    w = {"video": zrodlo, "force_rate": 0, "custom_width": 0, "custom_height": 0, "frame_load_cap": 0,
         "skip_first_frames": 0, "select_every_nth": 1, "format": "None"}
    if meta_batch:
        w["meta_batch"] = meta_batch
    return {"class_type": "VHS_LoadVideoPath", "inputs": w}


def _zapisz_wideo(obrazy, audio, fps, prefiks, meta_batch=None):
    """VHS_VideoCombine → H.264 (crf 18, yuv420p) + dźwięk z wczytanego klipu (już −15 LUFS)."""
    w = {"images": obrazy, "audio": audio, "frame_rate": float(fps), "loop_count": 0, "filename_prefix": prefiks,
         "format": "video/h264-mp4", "pix_fmt": "yuv420p", "crf": 18, "save_metadata": False,
         "trim_to_audio": False, "pingpong": False, "save_output": True}
    if meta_batch:
        w["meta_batch"] = meta_batch
    return {"class_type": "VHS_VideoCombine", "inputs": w}


def wizualizacja_plynna(wav=WAV_NOKTURN, preset="3_gory_ze_strun", od=205.0, do=215.0, fps=25,
                        rozmiar="1280x720", seed=20261122, podpis=PODPIS_NOKTURN, rife="rife49.pth"):
    """Render w połowie klatek (fps/2) + interpolacja RIFE ×2 → fps: ~2× krótszy render.
    RIFE liczy całą partię w pamięci – do krótkich klipów (do ~30 s przy 720p); RIFE w float32
    (GTX 1060 liczy fp16 bardzo wolno). Ruch między klatkami zgaduje RIFE, więc ostre ataki mogą się
    lekko rozmyć – porównaj z renderem w pełnym fps."""
    return {
        "1": {"class_type": "MGKlip", "inputs": {"wav": wav, "preset": preset, "od_s": float(od), "do_s": float(do),
                                                  "fps": fps / 2, "rozmiar": rozmiar, "seed": seed, "podpis": podpis}},
        "2": _wczytaj_wideo(["1", 0]),
        "3": {"class_type": "RIFE VFI", "inputs": {"frames": ["2", 0], "ckpt_name": rife, "multiplier": 2,
                                                    "clear_cache_after_n_frames": 10, "fast_mode": True,
                                                    "ensemble": True, "scale_factor": 1.0, "dtype": "float32",
                                                    "torch_compile": False, "batch_size": 1}},
        "4": _zapisz_wideo(["3", 0], ["2", 2], fps, "muzyka_graficznie/plynna"),
        "5": {"class_type": "MGKontrola", "inputs": {"pliki": ["4", 0]}},
    }


def wizualizacja_ostrzejsza(wav=WAV_NOKTURN, preset="3_gory_ze_strun", od=205.0, do=215.0, fps=25,
                            seed=20261122, podpis=PODPIS_NOKTURN, model="RealESRGAN_x2plus.pth",
                            partia=32, mp4=None):
    """Klip 720p → Real-ESRGAN ×2 → 1920×1080 (lanczos). Partiami po `partia` klatek, więc działa też
    dla całego utworu. mp4: gotowy plik zamiast renderu MGKlip (pełna ścieżka)."""
    wf = {}
    if mp4 is None:
        wf["1"] = {"class_type": "MGKlip", "inputs": {"wav": wav, "preset": preset, "od_s": float(od),
                                                       "do_s": float(do), "fps": fps, "rozmiar": "1280x720",
                                                       "seed": seed, "podpis": podpis}}
    wf.update({
        "2": {"class_type": "VHS_BatchManager", "inputs": {"frames_per_batch": partia}},
        "3": _wczytaj_wideo(mp4 or ["1", 0], ["2", 0]),
        "4": {"class_type": "UpscaleModelLoader", "inputs": {"model_name": model}},
        "5": {"class_type": "ImageUpscaleWithModel", "inputs": {"upscale_model": ["4", 0], "image": ["3", 0]}},
        "6": {"class_type": "ImageScale", "inputs": {"image": ["5", 0], "upscale_method": "lanczos", "width": 1920,
                                                     "height": 1080, "crop": "disabled"}},
        "7": _zapisz_wideo(["6", 0], ["3", 2], fps, "muzyka_graficznie/ostrzejsza", ["2", 0]),
        "8": {"class_type": "MGKontrola", "inputs": {"pliki": ["7", 0]}},
    })
    return wf


def piasek_fraktalny(zrodlo="<pełna ścieżka MP4 lub WAV z muzyką>", seed=20261123, procesy=4):
    """Klip „piasek fraktalny” z dźwięku pliku (MGPiasek) + podgląd 4 klatek + kontrola jakości."""
    return {
        "1": {"class_type": "MGPiasek", "inputs": {"zrodlo": zrodlo, "seed": seed, "procesy": procesy}},
        "2": {"class_type": "PreviewImage", "inputs": {"images": ["1", 2]}},
    }


def zapisz_pliki(katalog=None):
    """Zapisuje workflowy jako JSON (format API) do comfyui/workflows/ – do otwarcia w interfejsie
    ComfyUI (Workflow → Open albo przeciągnięcie pliku na okno) i ręcznej pracy na tych samych ustawieniach."""
    import json
    from pathlib import Path
    katalog = Path(katalog or Path(__file__).resolve().parent / "workflows")
    katalog.mkdir(parents=True, exist_ok=True)
    przyklady = {
        "tlo_sdxl": tlo_sdxl("night sky over misty mountain ridges, deep navy blue, soft golden rim light, "
                             "fine glowing threads, cinematic, minimal", seed=20261122),
        "stylizacja_sdxl": stylizacja_sdxl("klatka.png", "luminous golden threads on deep navy, oil painting, "
                                           "soft glow", seed=20261122),
        "wizualizacja_podglad": wizualizacja_podglad(),
        "wizualizacja_stylizowana": wizualizacja_stylizowana(
            "luminous golden threads over misty night mountains, deep navy blue, delicate light, fine detail"),
        "wizualizacja_klip": wizualizacja_klip(),
        "wizualizacja_plynna": wizualizacja_plynna(),
        "wizualizacja_ostrzejsza": wizualizacja_ostrzejsza(),
        "piasek_fraktalny": piasek_fraktalny(),
    }
    for nazwa, wf in przyklady.items():
        (katalog / f"{nazwa}.json").write_text(json.dumps(wf, indent=2, ensure_ascii=False), encoding="utf-8")
    return sorted(katalog.glob("*.json"))


if __name__ == "__main__":
    for p in zapisz_pliki():
        print(p)

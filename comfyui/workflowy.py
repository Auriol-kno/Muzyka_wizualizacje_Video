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
    }
    for nazwa, wf in przyklady.items():
        (katalog / f"{nazwa}.json").write_text(json.dumps(wf, indent=2, ensure_ascii=False), encoding="utf-8")
    return sorted(katalog.glob("*.json"))


if __name__ == "__main__":
    for p in zapisz_pliki():
        print(p)

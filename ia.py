"""Modelos de IA del Taller 3D (se cargan al usarlos y solo uno grande a la vez, para que quepa en 8 GB de gráfica).
- Quitar el fondo: rembg (BiRefNet / ISNet).
- Profundidad: Depth Anything V2 Large.
- Figura 3D desde una foto: TripoSG (VAST, licencia MIT)."""
import gc
import os
import sys

import numpy as np
from PIL import Image

from comun import LOCAL

os.environ.setdefault("HF_HOME", str(LOCAL / "modelos"))
os.environ.setdefault("U2NET_HOME", str(LOCAL / "modelos" / "rembg"))
_cargados = {}


def _libera(salvo=None):
    import torch
    for k in list(_cargados):
        if k != salvo:                     # incluye las sesiones de rembg, que también ocupan la tarjeta
            del _cargados[k]
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def quitar_fondo(im, modelo="birefnet-general"):
    """Devuelve la imagen RGBA sin fondo."""
    import torch  # noqa: F401  (trae las DLL de CUDA que necesita onnxruntime)
    import onnxruntime
    if hasattr(onnxruntime, "preload_dlls"):
        onnxruntime.preload_dlls()
    from rembg import new_session, remove
    if ("rembg", modelo) not in _cargados:
        _cargados[("rembg", modelo)] = new_session(modelo)
    return remove(im.convert("RGB"), session=_cargados[("rembg", modelo)])


def profundidad(im):
    """Mapa de profundidad (más alto = más cerca) del mismo tamaño que la imagen."""
    import torch
    from transformers import pipeline
    _libera("profundidad")
    if "profundidad" not in _cargados:
        _cargados["profundidad"] = pipeline("depth-estimation", model="depth-anything/Depth-Anything-V2-Large-hf",
                                            device=0 if torch.cuda.is_available() else -1)
    d = _cargados["profundidad"](im.convert("RGB"))["predicted_depth"]
    d = d[None] if d.dim() == 3 else d[None, None]
    d = torch.nn.functional.interpolate(d, size=im.size[::-1], mode="bicubic")[0, 0]
    return d.float().cpu().numpy()


def figura(im_rgba, pasos=50, guia=7.0, semilla=42, caras=200000, alta=False):
    """Malla 3D (trimesh) a partir de una foto ya sin fondo, con TripoSG."""
    import torch
    import trimesh
    sys.path.insert(0, str(LOCAL / "triposg"))
    from huggingface_hub import snapshot_download
    from triposg.pipelines.pipeline_triposg import TripoSGPipeline
    _libera("triposg")
    if "triposg" not in _cargados:
        ruta = snapshot_download(repo_id="VAST-AI/TripoSG", local_dir=str(LOCAL / "modelos" / "TripoSG"))
        _cargados["triposg"] = TripoSGPipeline.from_pretrained(ruta).to("cuda", torch.float16)
    pipe = _cargados["triposg"]
    # como en el ejemplo de TripoSG: figura centrada sobre fondo blanco, con margen
    a = np.array(im_rgba.convert("RGBA")).astype(np.float32) / 255
    ys, xs = np.nonzero(a[..., 3] > 0.5)
    a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    lado = int(max(a.shape[:2]) / 0.8)
    lienzo = np.ones((lado, lado, 3), np.float32)
    y0, x0 = (lado - a.shape[0]) // 2, (lado - a.shape[1]) // 2
    lienzo[y0:y0 + a.shape[0], x0:x0 + a.shape[1]] = a[..., :3] * a[..., 3:] + (1 - a[..., 3:])
    img = Image.fromarray((lienzo * 255).astype(np.uint8)).resize((512, 512), Image.LANCZOS)
    with torch.no_grad():
        out = pipe(image=img, generator=torch.Generator(device="cuda").manual_seed(int(semilla)),
                   num_inference_steps=int(pasos), guidance_scale=float(guia),
                   use_flash_decoder=False,                     # sin diso (necesita el CUDA toolkit): marching cubes normal
                   dense_octree_depth=8 if alta else 7,         # rejilla 512³ (alta, ~30 min en la 3070) o 256³ (normal, minutos)
                   hierarchical_octree_depth=9 if alta else 8).samples[0]
    m = trimesh.Trimesh(out[0].astype(np.float32), np.ascontiguousarray(out[1]))
    if caras and len(m.faces) > caras:
        import fast_simplification
        v, f = fast_simplification.simplify(m.vertices, m.faces, target_reduction=1 - caras / len(m.faces))
        m = trimesh.Trimesh(v, f)
    return m

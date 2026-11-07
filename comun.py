"""Piezas comunes del Taller 3D: rutas, guardar en tu carpeta de STL, abrir en OrcaSlicer y pasar mapas de alturas a sólidos."""
import datetime
import os
import re
import subprocess
from pathlib import Path

import numpy as np
import trimesh

LOCAL = Path(os.getenv("IA3D_LOCAL", Path(__file__).resolve().parent))  # entorno, modelos y temporales
SALIDA = LOCAL / "salida"
DESTINO = Path(os.getenv("IA3D_DESTINO", LOCAL / "guardados"))  # tu carpeta de STL
ORCA = Path(os.getenv("ORCA", r"C:\Program Files\OrcaSlicer\orca-slicer.exe"))
CAMA = tuple(float(x) for x in os.getenv("IA3D_CAMA", "220x220x250").split("x"))  # volumen de impresión (mm)
SALIDA.mkdir(parents=True, exist_ok=True)

ROJO = [190, 28, 34, 255]
BLANCO = [240, 240, 236, 255]
GRIS = [78, 161, 255, 255]


def nombre_archivo(base, ext=".stl"):
    base = re.sub(r"[^\w\- ]+", "", base, flags=re.UNICODE).strip().replace(" ", "_") or "pieza"
    return SALIDA / f"{datetime.datetime.now():%Y%m%d-%H%M%S}_{base}{ext}"


def solido_desde_alturas(dentro, alt, px, x0=0.0, y1=None):
    """Sólido cerrado a partir de un mapa de alturas (mm): cara de arriba con las alturas, fondo plano en z=0
    y paredes en el contorno de `dentro`. Fila 0 = arriba de la imagen."""
    ny, nx = dentro.shape
    y1 = ny * px if y1 is None else y1
    z = np.zeros((ny + 1, nx + 1))
    a = np.where(dentro, alt, 0.0)
    for dy in (0, 1):
        for dx in (0, 1):
            z[dy:dy + ny, dx:dx + nx] = np.maximum(z[dy:dy + ny, dx:dx + nx], a)
    xs = x0 + np.arange(nx + 1) * px
    ys = y1 - np.arange(ny + 1) * px
    gx, gy = np.meshgrid(xs, ys)
    n = (ny + 1) * (nx + 1)
    v = np.vstack([np.c_[gx.ravel(), gy.ravel(), z.ravel()], np.c_[gx.ravel(), gy.ravel(), np.zeros(n)]])
    idx = np.arange(n).reshape(ny + 1, nx + 1)
    iy, ix = np.nonzero(dentro)
    a_, b_, c_, d_ = idx[iy, ix], idx[iy, ix + 1], idx[iy + 1, ix + 1], idx[iy + 1, ix]
    caras = [np.c_[a_, d_, b_], np.c_[b_, d_, c_], np.c_[a_ + n, b_ + n, d_ + n], np.c_[b_ + n, c_ + n, d_ + n]]
    pad = np.pad(dentro, 1)
    e = {"a": a_, "b": b_, "c": c_, "d": d_}
    for (oy, ox), (p, q) in {(-1, 0): ("a", "b"), (1, 0): ("c", "d"), (0, -1): ("d", "a"), (0, 1): ("b", "c")}.items():
        fuera = ~pad[1 + iy + oy, 1 + ix + ox]
        p0, p1 = e[p][fuera], e[q][fuera]
        caras += [np.c_[p0, p0 + n, p1], np.c_[p1, p0 + n, p1 + n]]
    m = trimesh.Trimesh(v, np.vstack(caras), process=True)
    m.remove_unreferenced_vertices()
    trimesh.repair.fix_normals(m)
    return m


def suave(a, r):
    """Desenfoque casi gaussiano (tres pasadas de caja) de un array 2D."""
    a = np.asarray(a, dtype=np.float64)
    if r <= 0:
        return a
    k = max(1, int(round(r * 0.9)))
    for _ in range(3):
        for eje in (0, 1):
            pad = np.pad(a, [(k + 1, k) if e == eje else (0, 0) for e in (0, 1)], mode="edge")
            c = np.cumsum(pad, axis=eje)
            n = c.shape[eje]
            a = (np.take(c, range(2 * k + 1, n), axis=eje) - np.take(c, range(0, n - 2 * k - 1), axis=eje)) / (2 * k + 1)
    return a


def vista_glb(m, cambio=None, nombre="vista"):
    """GLB para el visor: rojo por debajo del cambio de color y blanco por encima (o azul si no hay cambio)."""
    v = m.copy()
    if cambio is None:
        col = np.tile(GRIS, (len(v.vertices), 1))
    else:
        col = np.where((v.vertices[:, 2] > cambio + 1e-3)[:, None], BLANCO, ROJO)
    v.visual = trimesh.visual.ColorVisuals(v, vertex_colors=col)
    v.apply_transform(trimesh.transformations.rotation_matrix(-np.pi / 2, [1, 0, 0]))   # Z arriba → Y arriba
    p = nombre_archivo(nombre, ".glb")
    v.export(p)
    return str(p)


def capas_cambio(cambio, primera=0.2, capa=0.12):
    """Altura de la capa (la que muestra Orca en el deslizador) antes de la que hay que poner la pausa."""
    if cambio is None:
        return ""
    # el laminador corta cada capa por su mitad: la primera capa solo blanca es la primera cuya mitad pasa del cambio
    z = primera
    while z - capa / 2 <= cambio:
        z += capa
    return (f"Cambio de color: rojo (o el de la base) hasta {cambio:.2f} mm. En Orca, con primera capa {primera} y capas de "
            f"{capa} mm, pon la pausa en la capa **{z:.2f} mm** del deslizador (botón derecho › Añadir pausa) y cambia al blanco.")


def informe(m, cambio=None):
    ext = m.extents
    cabe = sorted(ext[:2]) <= sorted(CAMA[:2]) and ext[2] <= CAMA[2]
    vol = abs(m.volume) / 1000 if m.is_volume else None
    t = [f"**Medidas:** {ext[0]:.1f} × {ext[1]:.1f} × {ext[2]:.1f} mm " + ("(cabe en la impresora)" if cabe else "(**no cabe en la impresora**)"),
         f"**Malla:** {len(m.faces):,} caras · " + ("cerrada, lista para imprimir" if m.is_watertight else "con agujeros (Orca la suele reparar)")]
    if vol:
        t.append(f"**Material:** {vol:.1f} cm³ macizo, unos {vol * 1.24 * 0.45:.0f} g con relleno del 15 %")
    if cambio:
        t.append(capas_cambio(cambio))
    return "\n\n".join(t)


def guardar_en_z(ruta, carpeta=""):
    import shutil
    if not ruta:
        return "No hay nada que guardar todavía."
    dest = DESTINO / carpeta if carpeta else DESTINO
    try:
        dest.mkdir(parents=True, exist_ok=True)
        final = dest / Path(ruta).name
        shutil.copy2(ruta, final)
        # si la carpeta de STL lleva un indice_md5.txt dos niveles más arriba, se apunta también
        import hashlib
        h = hashlib.md5(Path(final).read_bytes()).hexdigest()
        indice = DESTINO.parents[1] / "indice_md5.txt"
        if indice.exists():
            lineas = indice.read_text(encoding="utf-8-sig").splitlines()
            if not any(l.startswith(h) for l in lineas):
                lineas.append(f"{h}  {final.relative_to(DESTINO.parents[1])}")
                lineas.sort(key=lambda l: l[34:].lower())
                indice.write_text("\n".join(lineas) + "\n", encoding="utf-8-sig")
        return f"Guardado en {final}."
    except Exception as e:
        return f"No pude guardarlo ({e}). El archivo sigue en {ruta}"


def abrir_en_orca(ruta):
    if not ruta:
        return "No hay nada que abrir todavía."
    if not ORCA.exists():
        return f"No encuentro OrcaSlicer en {ORCA}"
    subprocess.Popen([str(ORCA), str(ruta)])
    return "Abriendo en OrcaSlicer…"

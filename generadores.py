"""Generadores del Taller 3D: cada función devuelve (malla trimesh, cambio de color en mm o None)."""
import math
import os

import numpy as np
import trimesh
from PIL import Image, ImageDraw, ImageFont, ImageOps
from shapely.geometry import Polygon, MultiPolygon, Point, box
from shapely.ops import unary_union

import ia
from comun import solido_desde_alturas, suave

FUENTES = {
    "Redondeada (Arial Rounded)": "ARLRDBD.TTF", "Negrita (Arial Black)": "ariblk.ttf", "Clásica (Georgia negrita)": "georgiab.ttf",
    "Cómic": "comicbd.ttf", "Manuscrita (Segoe Script)": "segoesc.ttf", "Impact": "impact.ttf", "Sencilla (Segoe UI negrita)": "segoeuib.ttf",
}
DIR_FUENTES = os.getenv("FUENTES", r"C:\Windows\Fonts")


def fuente(nombre, tam_px):
    for f in (FUENTES.get(nombre, nombre), "arialbd.ttf"):
        try:
            return ImageFont.truetype(os.path.join(DIR_FUENTES, f), tam_px)
        except OSError:
            continue
    return ImageFont.load_default()


# ---------- de imagen a polígonos (contornos lisos, no escalones de píxel) ----------

def poligonos(mascara, px, suavizar=0.08):
    """Polígonos (shapely, en mm, Y hacia arriba) a partir de una máscara booleana."""
    from skimage import measure
    m = np.pad(mascara.astype(float), 1)
    cont = measure.find_contours(m, 0.5)
    alto = m.shape[0]
    anillos = []
    for c in cont:
        if len(c) < 8:
            continue
        p = Polygon([((x - 1) * px, (alto - 1 - y) * px) for y, x in c])
        if p.is_valid and p.area > (2 * px) ** 2:
            anillos.append(p)
        elif p.area > (2 * px) ** 2:
            anillos.append(p.buffer(0))
    anillos.sort(key=lambda p: -p.area)
    # par-impar: un anillo dentro de un número impar de otros es un agujero
    res = []
    for i, p in enumerate(anillos):
        nivel = sum(1 for q in anillos[:i] if q.contains(p.representative_point()))
        res.append((p, nivel % 2 == 1))
    forma = Polygon()
    for p, agujero in res:
        forma = forma.difference(p) if agujero else forma.union(p)
    return forma.simplify(suavizar).buffer(0)


def extruir(forma, alto, z0=0.0):
    piezas = list(forma.geoms) if isinstance(forma, MultiPolygon) else [forma]
    ms = []
    for p in piezas:
        if p.is_empty or p.area < 0.01:
            continue
        m = trimesh.creation.extrude_polygon(p, alto)
        m.apply_translation([0, 0, z0])
        ms.append(m)
    return ms


def unir(mallas):
    """Unión booleana con manifold3d (sólido limpio); si falla, junta sin unir."""
    mallas = [m for m in mallas if m is not None and len(m.faces)]
    try:
        return trimesh.boolean.union(mallas, engine="manifold")
    except Exception:
        return trimesh.util.concatenate(mallas)


def restar(a, b):
    try:
        return trimesh.boolean.difference([a, b], engine="manifold")
    except Exception:
        return a


def texto_mascara(texto, nombre_fuente, alto_mm, px=0.05):
    f = fuente(nombre_fuente, max(8, int(alto_mm / px)))
    caja = ImageDraw.Draw(Image.new("L", (1, 1))).textbbox((0, 0), texto, font=f)
    im = Image.new("L", (caja[2] - caja[0] + 20, caja[3] - caja[1] + 20), 0)
    ImageDraw.Draw(im).text((10 - caja[0], 10 - caja[1]), texto, font=f, fill=255)
    return np.array(im) > 127, px


def centrar(forma):
    c = forma.centroid if not forma.is_empty else Point(0, 0)
    from shapely import affinity
    b = forma.bounds
    return affinity.translate(forma, -(b[0] + b[2]) / 2, -(b[1] + b[3]) / 2)


# ---------- 1. Relieve desde foto ----------

def _alturas_figura(im_rgba, prof, alto_px, medio_cuerpo, relieve):
    """Mapa de alturas (0..relieve mm) de la figura recortada, a partir de su profundidad."""
    alfa = im_rgba.getchannel("A").point(lambda a: 255 if a > 128 else 0)
    caja = alfa.getbbox()
    if medio_cuerpo < 1:
        caja = (caja[0], caja[1], caja[2], caja[1] + int((caja[3] - caja[1]) * medio_cuerpo))
        sub = alfa.crop(caja).getbbox()
        caja = (caja[0] + sub[0], caja[1], caja[0] + sub[2], caja[3])
    im, alfa = im_rgba.crop(caja), alfa.crop(caja)
    prof = prof[caja[1]:caja[3], caja[0]:caja[2]]
    esc = alto_px / im.height
    tam = (max(2, round(im.width * esc)), max(2, round(im.height * esc)))
    a = np.array(alfa.resize(tam, Image.LANCZOS)) > 127
    d = np.array(Image.fromarray(prof.astype(np.float32), "F").resize(tam, Image.BICUBIC))
    gris = np.array(ImageOps.autocontrast(im.convert("L"), cutoff=2).resize(tam, Image.LANCZOS)) / 255.0
    lo, hi = np.percentile(d[a], [2, 98])
    dn = np.where(a, np.clip((d - lo) / max(hi - lo, 1e-6), 0, 1), 0)
    r = max(tam) / 30
    tendencia = suave(dn, 4 * r) / np.maximum(suave(a * 1.0, 4 * r), 1e-3)
    local = dn - tendencia
    local /= max(np.percentile(np.abs(local[a]), 98), 1e-3)
    fino = dn - suave(dn, 2 * r)
    fino /= max(np.percentile(np.abs(fino[a]), 98), 1e-3)
    domo = suave(a * 1.0, r * 0.6)
    detalle = gris - suave(gris, r * 0.4)
    h = 0.15 + 0.2 * dn + 0.3 * np.clip(local, -0.6, 1.2) + 0.3 * np.clip(fino, -0.8, 1.3) + 0.2 * domo + 0.18 * detalle
    h = np.clip(suave(h, 0.7), 0.1, 1.2) / 1.2 * relieve
    if medio_cuerpo < 1:                                        # el corte del pecho baja suave hasta la base
        fila = np.linspace(0, 1, tam[1])[:, None]
        h = h * np.clip((1 - fila) / 0.15, 0, 1) ** 0.7
    return a, np.where(a, h, 0)


def _prof_desde_malla(m, im_size):
    """Profundidad de frente de una malla 3D (para relieves desde la figura de TripoSG)."""
    m = m.copy()
    m.apply_translation(-m.bounds.mean(0))
    w, h = im_size
    a, b = m.bounds
    esc = max((b[0] - a[0]) / w, (b[1] - a[1]) / h)
    xs = a[0] + (np.arange(w) + 0.5) * esc
    ys = b[1] - (np.arange(h) + 0.5) * esc
    gx, gy = np.meshgrid(xs, ys)
    orig = np.c_[gx.ravel(), gy.ravel(), np.full(gx.size, b[2] + 1)]
    loc, ray, _ = m.ray.intersects_location(orig, np.tile([0, 0, -1.0], (len(orig), 1)), multiple_hits=False)
    z = np.full(gx.size, np.nan)
    z[ray] = loc[:, 2]
    z = z.reshape(h, w)
    alfa = ~np.isnan(z)
    return np.nan_to_num(z, nan=np.nanmin(z) if alfa.any() else 0), alfa


def relieve(foto, forma="Bola de Navidad", diametro=80, relieve_mm=2.5, base_mm=1.6, medio_cuerpo=0.6,
            texto="", nombre_fuente="Redondeada (Arial Rounded)", copos=True, quitar_fondo=True, desde_3d=False):
    px = 0.15
    im = foto.convert("RGBA")
    if max(im.size) > 1600:
        im.thumbnail((1600, 1600))
    if quitar_fondo:
        im = ia.quitar_fondo(im)
    if desde_3d:
        malla = ia.figura(im, pasos=40)
        prof, alfa = _prof_desde_malla(malla, im.size)
        im.putalpha(Image.fromarray((alfa * 255).astype(np.uint8)))
    else:
        prof = ia.profundidad(im)
    R = diametro / 2
    lado = diametro + 12
    n = int(lado / px)
    ctr = n / 2

    def p2(x, y):      # mm (centro 0,0) → píxel
        return ctr + x / px, ctr - y / px

    def disco(r, x=0, y=0):
        im_ = Image.new("L", (n, n), 0)
        a_, b_ = p2(x - r, y + r), p2(x + r, y - r)
        ImageDraw.Draw(im_).ellipse([a_, b_], fill=255)
        return np.array(im_) > 127

    if forma in ("Bola de Navidad", "Medallón", "Llavero redondo"):
        dentro = disco(R)
        borde = dentro & ~disco(R - 2.0)
        if forma != "Medallón":
            ra = 5.0 if forma == "Bola de Navidad" else 4.0
            dentro |= disco(ra, 0, R + ra * 0.5)
            borde |= disco(ra, 0, R + ra * 0.5)
            hueco = disco(ra * 0.48, 0, R + ra * 0.5)
            dentro &= ~hueco; borde &= ~hueco
        zona_y = (-R * 0.62, R * 0.78)
    elif forma == "Placa rectangular":
        im_ = Image.new("L", (n, n), 0); d = ImageDraw.Draw(im_)
        d.rounded_rectangle([p2(-R, R * 0.75), p2(R, -R * 0.75)], radius=int(4 / px), fill=255)
        dentro = np.array(im_) > 127
        im2 = Image.new("L", (n, n), 0)
        ImageDraw.Draw(im2).rounded_rectangle([p2(-R + 2, R * 0.75 - 2), p2(R - 2, -R * 0.75 + 2)], radius=int(2.5 / px), fill=255)
        borde = dentro & ~(np.array(im2) > 127)
        zona_y = (-R * 0.5, R * 0.68)
    else:   # «Solo la figura»: la silueta con una base 2 mm más ancha
        dentro, borde, zona_y = None, None, (-R, R)
    alto_fig = (zona_y[1] - zona_y[0]) - (9 if texto else 0)
    fa, fh = _alturas_figura(im, prof, alto_fig / px, medio_cuerpo, relieve_mm)
    capa_a, capa_h = np.zeros((n, n), bool), np.zeros((n, n))
    th, tw = fa.shape
    x0 = int(ctr - tw / 2)
    y0 = int(p2(0, zona_y[1])[1])
    th, tw = min(th, n - y0), min(tw, n - x0)
    capa_a[y0:y0 + th, x0:x0 + tw] = fa[:th, :tw]
    capa_h[y0:y0 + th, x0:x0 + tw] = fh[:th, :tw]
    if dentro is None:
        from comun import suave as s_
        dentro = s_(capa_a * 1.0, 2.0 / px) > 0.02
        borde = np.zeros_like(dentro)
    alt = np.where(dentro, base_mm, 0.0)
    alt = np.where(borde, base_mm + min(1.2, relieve_mm), alt)
    alt = np.where(capa_a & dentro, np.maximum(alt, base_mm + 0.25 + capa_h), alt)
    if copos and forma != "Solo la figura":
        im_ = Image.new("L", (n, n), 0); d = ImageDraw.Draw(im_)
        rng = np.random.default_rng(7)
        for _ in range(60):
            ang, rr = rng.uniform(0, 2 * math.pi), rng.uniform(0.3, 0.88) * R
            x, y = rr * math.cos(ang), rr * math.sin(ang)
            cx_, cy_ = p2(x, y)
            if capa_a[max(0, int(cy_) - 25):int(cy_) + 25, max(0, int(cx_) - 25):int(cx_) + 25].any():
                continue
            if rng.random() < 0.3:
                r = rng.uniform(2.2, 3.6)
                for k in range(6):
                    t = math.radians(90 + 60 * k)
                    d.line([p2(x, y), p2(x + r * math.cos(t), y + r * math.sin(t))], fill=255, width=int(0.7 / px))
            else:
                r = rng.uniform(0.35, 0.7)
                d.ellipse([p2(x - r, y + r), p2(x + r, y - r)], fill=255)
        ad = (np.array(im_) > 127) & dentro & ~borde
        alt = np.where(ad, np.maximum(alt, base_mm + 0.7), alt)
    if texto:
        mt, tpx = texto_mascara(texto, nombre_fuente, 7.5)
        esc = tpx / px
        timg = Image.fromarray(mt.astype(np.uint8) * 255).resize((max(1, int(mt.shape[1] * esc)), max(1, int(mt.shape[0] * esc))), Image.LANCZOS)
        ancho_max = 2 * math.sqrt(max(R ** 2 - (zona_y[0] - 1) ** 2, 1)) - 6
        if timg.width * px > ancho_max:
            f = ancho_max / (timg.width * px)
            timg = timg.resize((int(timg.width * f), max(1, int(timg.height * f))), Image.LANCZOS)
        capa_t = Image.new("L", (n, n), 0)
        tx, ty = p2(0, zona_y[0] + 1.5)
        capa_t.paste(timg, (int(tx - timg.width / 2), int(ty - timg.height / 2)))
        mt = (np.array(capa_t) > 127) & dentro
        alt = np.where(mt, base_mm + 1.2, alt)
    m = solido_desde_alturas(dentro, alt, px, -lado / 2, lado / 2)
    return m, base_mm


# ---------- 2. Litofanía ----------

def litofania(foto, ancho=100, minimo=0.8, maximo=3.2, forma="Plana", marco=True, curva_grados=120):
    px = 0.2
    im = ImageOps.exif_transpose(foto).convert("L")
    w = int(ancho / px)
    h = int(im.height * w / im.width)
    im = ImageOps.autocontrast(im.resize((w, h), Image.LANCZOS), cutoff=1)
    g = np.array(im) / 255.0
    grosor = maximo - (maximo - minimo) * g                    # claro = fino (deja pasar la luz)
    dentro = np.ones_like(grosor, bool)
    if marco:
        k = int(3 / px)
        grosor = np.pad(grosor, k, constant_values=maximo + 1.0)
        dentro = np.pad(dentro, k, constant_values=True)
    ny, nx = grosor.shape
    m = solido_desde_alturas(dentro, grosor, px, -nx * px / 2, ny * px / 2)
    if forma == "Curva":
        ang = math.radians(curva_grados)
        rad = nx * px / ang
        v = m.vertices.copy()
        t = v[:, 0] / rad
        r = rad - v[:, 2]                                       # la cara con relieve queda por dentro
        m.vertices = np.c_[r * np.sin(t), v[:, 1], rad - r * np.cos(t)]
        m.fix_normals()
    # de pie: Y pasa a ser la altura
    m.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [1, 0, 0]))
    m.apply_translation([0, 0, -m.bounds[0][2]])
    return m, None


# ---------- 3. Dibujo o logo → placa, llavero, cortador o sello ----------

def _mascara_dibujo(im, umbral=128, invertir=False):
    im = ImageOps.exif_transpose(im)
    if im.mode in ("RGBA", "LA") and np.array(im.getchannel("A")).min() < 250:
        return np.array(im.getchannel("A")) > 127
    g = np.array(im.convert("L"))
    m = g < umbral
    return ~m if invertir else m


def dibujo(imagen, modo="Placa", tamano=60, alto=3.0, base=1.2, umbral=128, invertir=False, texto="", nombre_fuente="Redondeada (Arial Rounded)"):
    m = _mascara_dibujo(imagen, umbral, invertir)
    ys, xs = np.nonzero(m)
    m = m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    px = tamano / max(m.shape)
    forma = centrar(poligonos(m, px, suavizar=px * 0.6))
    if modo == "Cortador de galletas":
        pared = 0.9
        filo = forma.exterior if isinstance(forma, Polygon) else unary_union([p.exterior for p in forma.geoms])
        anillo = forma.buffer(pared).difference(forma)
        pestaña = forma.buffer(4.0).difference(forma)
        ms = extruir(anillo, alto) + extruir(pestaña, 1.6)
        return unir(ms), None
    if modo == "Sello (al revés, para tinta o arcilla)":
        from shapely import affinity
        espejo = affinity.scale(forma, xfact=-1, origin=(0, 0))
        fondo = espejo.buffer(3).envelope.buffer(2, join_style=1)
        return unir(extruir(fondo, base + 2) + extruir(espejo, alto, base + 2)), None
    piezas = []
    if modo == "Llavero":
        contorno = forma.buffer(2.5, join_style=1)
        b = contorno.bounds
        anilla = Point(b[0] - 2, b[3] - 2).buffer(5).difference(Point(b[0] - 2, b[3] - 2).buffer(2.4))
        contorno = unary_union([contorno, anilla]).difference(Point(b[0] - 2, b[3] - 2).buffer(2.4))
        piezas += extruir(contorno, base) + extruir(forma, alto, base)
        if texto:
            mt, tpx = texto_mascara(texto, nombre_fuente, 6)
            tf = centrar(poligonos(mt, tpx, 0.03))
            from shapely import affinity
            tf = affinity.translate(tf, 0, b[1] - 6)
            fondo_t = tf.buffer(2, join_style=1)
            piezas += extruir(fondo_t, base) + extruir(tf, alto, base)
        return unir(piezas), base
    # Placa: el dibujo en relieve sobre una placa con su forma
    contorno = forma.buffer(3, join_style=1)
    return unir(extruir(contorno, base) + extruir(forma, alto, base)), base


# ---------- 4. Texto → llavero, placa o letrero ----------

def texto_3d(texto, nombre_fuente="Redondeada (Arial Rounded)", alto_letra=12, grosor_letra=2.0, base=1.6,
             estilo="Llavero", borde=2.5):
    mt, tpx = texto_mascara(texto, nombre_fuente, alto_letra)
    letras = centrar(poligonos(mt, tpx, 0.03))
    if estilo == "Solo letras (unidas)":
        return unir(extruir(letras.buffer(0.6, join_style=1), grosor_letra + base)), None
    if estilo == "Letrero (placa rectangular)":
        b = letras.bounds
        fondo = box(b[0] - borde * 2, b[1] - borde * 2, b[2] + borde * 2, b[3] + borde * 2).buffer(2, join_style=1)
        marco = fondo.difference(fondo.buffer(-1.6))
        return unir(extruir(fondo, base) + extruir(letras, grosor_letra, base) + extruir(marco, grosor_letra, base)), base
    contorno = letras.buffer(borde, join_style=1)
    contorno = unary_union(list(contorno.geoms) if isinstance(contorno, MultiPolygon) else [contorno]).convex_hull.buffer(0) \
        if isinstance(contorno, MultiPolygon) else contorno
    b = contorno.bounds
    cx, cy = b[0] - 1.5, (b[1] + b[3]) / 2
    anilla = Point(cx, cy).buffer(5)
    agujero = Point(cx, cy).buffer(2.4)
    fondo = unary_union([contorno, anilla]).difference(agujero)
    return unir(extruir(fondo, base) + extruir(letras, grosor_letra, base)), base


# ---------- 5. Figura 3D desde foto ----------

def figura(foto, alto_mm=80, pasos=50, semilla=42, base_plana=True, quitar_fondo=True, peana=False, alta=False):
    im = ImageOps.exif_transpose(foto).convert("RGBA")
    if max(im.size) > 1600:
        im.thumbnail((1600, 1600))
    if quitar_fondo:
        im = ia.quitar_fondo(im)
    m = ia.figura(im, pasos=pasos, semilla=semilla, alta=alta)
    m = arreglar_malla(m)
    # TripoSG da Y hacia arriba: se pasa a Z hacia arriba (impresora)
    m.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [1, 0, 0]))
    m.apply_scale(alto_mm / m.extents[2])
    m.apply_translation([-m.bounds.mean(0)[0], -m.bounds.mean(0)[1], -m.bounds[0][2]])
    if base_plana:                                              # corta 1,5 % de abajo para que apoye plano
        corte = m.extents[2] * 0.015
        caja = trimesh.creation.box([m.extents[0] * 3, m.extents[1] * 3, corte * 2])
        m = restar(m, caja)
        m.apply_translation([0, 0, -m.bounds[0][2]])
    if peana:
        b = m.bounds
        r = max(b[1][0] - b[0][0], b[1][1] - b[0][1]) * 0.6
        p = trimesh.creation.cylinder(radius=r, height=3, sections=96)
        p.apply_translation([(b[0][0] + b[1][0]) / 2, (b[0][1] + b[1][1]) / 2, 1.5])
        m.apply_translation([0, 0, 2.6])
        m = unir([m, p])
    return m, None


# ---------- 6. Arreglar, reducir, escalar y tumbar un STL ----------

def arreglar_malla(m):
    import pymeshfix
    try:
        v, f = pymeshfix.clean_from_arrays(np.asarray(m.vertices), np.asarray(m.faces))
        m = trimesh.Trimesh(v, f)
    except Exception:
        trimesh.repair.fill_holes(m)
    m.remove_unreferenced_vertices()
    trimesh.repair.fix_normals(m)
    return m


def taller(archivo, reparar=True, caras=0, medida_mm=0, eje="Lo más largo", tumbar=True, partir=False):
    m = trimesh.load(archivo, force="mesh")
    notas = [f"Original: {len(m.faces):,} caras, {m.extents.round(1)} mm, " + ("cerrada" if m.is_watertight else "con agujeros")]
    if reparar:
        m = arreglar_malla(m)
        notas.append("Reparada (agujeros cerrados y normales arregladas).")
    if caras and len(m.faces) > caras:
        import fast_simplification
        v, f = fast_simplification.simplify(m.vertices, m.faces, target_reduction=1 - caras / len(m.faces))
        m = trimesh.Trimesh(v, f)
        notas.append(f"Reducida a {len(m.faces):,} caras.")
    if medida_mm:
        i = {"Ancho (X)": 0, "Fondo (Y)": 1, "Alto (Z)": 2}.get(eje, int(np.argmax(m.extents)))
        m.apply_scale(medida_mm / m.extents[i])
        notas.append(f"Escalada a {medida_mm} mm.")
    if tumbar:
        mejor, area = None, -1
        for t in trimesh.poses.compute_stable_poses(m, n_samples=1, threshold=0.02)[0][:8]:
            c = m.copy(); c.apply_transform(t)
            apoyo = c.area_faces[(c.face_normals[:, 2] < -0.98) & (c.triangles_center[:, 2] < c.bounds[0][2] + 0.2)].sum()
            if apoyo > area:
                mejor, area = t, apoyo
        if mejor is not None:
            m.apply_transform(mejor)
            notas.append(f"Tumbada sobre la cara más estable ({area:.0f} mm² apoyados).")
    m.apply_translation([-m.bounds.mean(0)[0], -m.bounds.mean(0)[1], -m.bounds[0][2]])
    piezas = [m]
    if partir and (m.extents[0] > 220 or m.extents[1] > 220 or m.extents[2] > 250):
        piezas = []
        i = int(np.argmax(m.extents / np.array([220, 220, 250])))
        n = int(math.ceil(m.extents[i] / ([220, 220, 250][i] - 5)))
        a, b = m.bounds[0][i], m.bounds[1][i]
        for k in range(n):
            lo, hi = a + (b - a) * k / n, a + (b - a) * (k + 1) / n
            centro = m.bounds.mean(0).copy(); centro[i] = (lo + hi) / 2
            tam = m.extents * 3; tam[i] = hi - lo
            caja = trimesh.creation.box(tam); caja.apply_translation(centro)
            try:
                piezas.append(trimesh.boolean.intersection([m, caja], engine="manifold"))
            except Exception:
                pass
        notas.append(f"No cabía en la impresora: partida en {len(piezas)} piezas a lo largo del eje {'XYZ'[i]}.")
    return piezas, "\n\n".join(notas)

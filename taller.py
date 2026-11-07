"""Taller 3D: de foto, dibujo o texto a STL. Página local en http://127.0.0.1:7870
Arranque: iniciar_taller.bat (Windows) o iniciar_taller.sh (Linux)."""
import traceback

import gradio as gr

import generadores as g
from comun import abrir_en_orca, guardar_en_z, informe, nombre_archivo, vista_glb

FORMAS = ["Bola de Navidad", "Medallón", "Llavero redondo", "Placa rectangular", "Solo la figura"]
FUENTES = list(g.FUENTES)


def _salida(mallas, cambio, nombre):
    """Guarda las STL, prepara la vista 3D y el informe."""
    if not isinstance(mallas, list):
        mallas = [mallas]
    rutas = []
    for i, m in enumerate(mallas):
        p = nombre_archivo(nombre + (f"_parte{i + 1}" if len(mallas) > 1 else ""))
        m.export(p)
        rutas.append(str(p))
    import trimesh
    junta = trimesh.util.concatenate(mallas) if len(mallas) > 1 else mallas[0]
    return vista_glb(junta, cambio, nombre), rutas, informe(junta, cambio), rutas[0]


def _seguro(fn):
    def envoltura(*args):
        try:
            return fn(*args)
        except Exception as e:
            traceback.print_exc()
            raise gr.Error(f"No ha salido: {e}")
    return envoltura


@_seguro
def hacer_relieve(foto, forma, diam, rel, base, medio, texto, fuente, copos, fondo, desde3d):
    if foto is None:
        raise gr.Error("Falta la foto.")
    m, cambio = g.relieve(foto, forma, diam, rel, base, medio, texto.strip(), fuente, copos, fondo, desde3d)
    return _salida(m, cambio, f"relieve_{texto or forma}")


@_seguro
def hacer_figura(foto, alto, pasos, semilla, plana, fondo, peana, alta):
    if foto is None:
        raise gr.Error("Falta la foto.")
    m, cambio = g.figura(foto, alto, pasos, semilla, plana, fondo, peana, alta)
    return _salida(m, cambio, "figura")


@_seguro
def hacer_litofania(foto, ancho, mn, mx, forma, marco, curva):
    if foto is None:
        raise gr.Error("Falta la foto.")
    m, cambio = g.litofania(foto, ancho, mn, mx, forma, marco, curva)
    return _salida(m, cambio, "litofania")


@_seguro
def hacer_dibujo(img, modo, tam, alto, base, umbral, inv, texto, fuente):
    if img is None:
        raise gr.Error("Falta el dibujo.")
    m, cambio = g.dibujo(img, modo, tam, alto, base, umbral, inv, texto.strip(), fuente)
    return _salida(m, cambio, modo)


@_seguro
def hacer_texto(texto, fuente, alto, grosor, base, estilo, borde):
    if not texto.strip():
        raise gr.Error("Escribe el texto.")
    m, cambio = g.texto_3d(texto.strip(), fuente, alto, grosor, base, estilo, borde)
    return _salida(m, cambio, texto)


@_seguro
def hacer_taller(archivo, reparar, caras, medida, eje, tumbar, partir):
    if archivo is None:
        raise gr.Error("Sube un STL, 3MF, OBJ o GLB.")
    piezas, notas = g.taller(archivo, reparar, int(caras or 0), float(medida or 0), eje, tumbar, partir)
    v, rutas, inf, ultima = _salida(piezas, None, "arreglado")
    return v, rutas, notas + "\n\n" + inf, ultima


def acciones(ultima):
    with gr.Row():
        b1 = gr.Button("Guardar en mi carpeta", variant="secondary")
        b2 = gr.Button("Abrir en OrcaSlicer", variant="primary")
    aviso = gr.Markdown()
    b1.click(guardar_en_z, ultima, aviso)
    b2.click(abrir_en_orca, ultima, aviso)


def resultados():
    vista = gr.Model3D(label="Vista 3D (gira con el ratón)", height=460, clear_color=[0.08, 0.09, 0.11, 1])
    archivos = gr.File(label="STL", file_count="multiple")
    info = gr.Markdown()
    ultima = gr.State()
    acciones(ultima)
    return [vista, archivos, info, ultima]


TEMA = gr.themes.Soft(primary_hue="blue", neutral_hue="slate")
with gr.Blocks(title="Taller 3D") as app:
    gr.Markdown("# Taller 3D\nDe foto, dibujo o texto a STL. Todo se hace en tu ordenador, con tu tarjeta gráfica.")
    with gr.Tab("Relieve desde foto"):
        gr.Markdown("Bolas de Navidad, medallones, llaveros y placas con la foto en relieve. La base sale de un color y el relieve de otro (pausa para cambiar el filamento).")
        with gr.Row():
            with gr.Column(scale=1):
                f = gr.Image(type="pil", label="Foto (mejor de frente y con buena luz)")
                forma = gr.Dropdown(FORMAS, value="Bola de Navidad", label="Forma")
                diam = gr.Slider(30, 200, 80, step=1, label="Tamaño (mm)")
                rel = gr.Slider(0.8, 5, 2.5, step=0.1, label="Altura del relieve (mm)")
                base = gr.Slider(0.8, 4, 1.6, step=0.1, label="Grosor de la base (mm)")
                medio = gr.Slider(0.3, 1, 0.6, step=0.05, label="Cuánto se ve de la figura (1 = entera, 0,6 = cabeza y pecho)")
                texto = gr.Textbox(label="Nombre o texto (opcional)")
                fuente = gr.Dropdown(FUENTES, value=FUENTES[0], label="Letra")
                with gr.Row():
                    copos = gr.Checkbox(True, label="Copos de nieve")
                    fondo = gr.Checkbox(True, label="Quitar el fondo de la foto")
                    d3 = gr.Checkbox(False, label="Profundidad desde figura 3D (más lento)")
                b = gr.Button("Crear relieve", variant="primary")
            with gr.Column(scale=1):
                sal = resultados()
        b.click(hacer_relieve, [f, forma, diam, rel, base, medio, texto, fuente, copos, fondo, d3], sal)
    with gr.Tab("Figura 3D desde foto"):
        gr.Markdown("Una figura completa (de bulto redondo) a partir de una sola foto, con TripoSG. Tarda unos minutos (la máxima calidad, una media hora). Sale mejor con la figura entera, de frente o de tres cuartos y sin cortar.")
        with gr.Row():
            with gr.Column(scale=1):
                f = gr.Image(type="pil", label="Foto")
                alto = gr.Slider(20, 240, 80, step=1, label="Altura final (mm)")
                pasos = gr.Slider(20, 80, 50, step=5, label="Pasos (más = más detalle y más lento)")
                semilla = gr.Number(42, label="Semilla (cámbiala para otra versión)", precision=0)
                with gr.Row():
                    plana = gr.Checkbox(True, label="Base plana para que se tenga de pie")
                    fondo = gr.Checkbox(True, label="Quitar el fondo")
                    peana = gr.Checkbox(False, label="Peana redonda")
                alta = gr.Checkbox(False, label="Máxima calidad (mucho más detalle, ~30 min)")
                b = gr.Button("Crear figura", variant="primary")
            with gr.Column(scale=1):
                sal = resultados()
        b.click(hacer_figura, [f, alto, pasos, semilla, plana, fondo, peana, alta], sal)
    with gr.Tab("Litofanía"):
        gr.Markdown("La foto se ve al poner una luz detrás. Imprímela de pie, en blanco, con relleno 100 % y capa 0,12.")
        with gr.Row():
            with gr.Column(scale=1):
                f = gr.Image(type="pil", label="Foto")
                ancho = gr.Slider(40, 210, 100, step=1, label="Ancho (mm)")
                mn = gr.Slider(0.4, 1.5, 0.8, step=0.1, label="Grosor mínimo (zonas claras)")
                mx = gr.Slider(2, 5, 3.2, step=0.1, label="Grosor máximo (zonas oscuras)")
                forma = gr.Radio(["Plana", "Curva"], value="Curva", label="Forma")
                curva = gr.Slider(30, 180, 120, step=5, label="Curvatura (grados)")
                marco = gr.Checkbox(True, label="Marco")
                b = gr.Button("Crear litofanía", variant="primary")
            with gr.Column(scale=1):
                sal = resultados()
        b.click(hacer_litofania, [f, ancho, mn, mx, forma, marco, curva], sal)
    with gr.Tab("Dibujo o logo"):
        gr.Markdown("Un dibujo, silueta o logo (negro sobre blanco, o PNG sin fondo) convertido en placa, llavero, cortador de galletas o sello.")
        with gr.Row():
            with gr.Column(scale=1):
                f = gr.Image(type="pil", label="Dibujo", image_mode="RGBA")
                modo = gr.Dropdown(["Placa", "Llavero", "Cortador de galletas", "Sello (al revés, para tinta o arcilla)"], value="Placa", label="Qué hacer")
                tam = gr.Slider(15, 200, 60, step=1, label="Tamaño (mm, lo más largo)")
                alto = gr.Slider(0.6, 20, 3, step=0.2, label="Altura del dibujo (mm; en cortadores, la altura de la pared)")
                base = gr.Slider(0.8, 4, 1.2, step=0.1, label="Grosor de la base (mm)")
                umbral = gr.Slider(10, 245, 128, step=1, label="Umbral (qué cuenta como dibujo)")
                inv = gr.Checkbox(False, label="Invertir (dibujo claro sobre fondo oscuro)")
                texto = gr.Textbox(label="Nombre debajo (solo llaveros)")
                fuente = gr.Dropdown(FUENTES, value=FUENTES[0], label="Letra")
                b = gr.Button("Crear", variant="primary")
            with gr.Column(scale=1):
                sal = resultados()
        b.click(hacer_dibujo, [f, modo, tam, alto, base, umbral, inv, texto, fuente], sal)
    with gr.Tab("Texto y nombres"):
        gr.Markdown("Llaveros con nombre, letreros y letras sueltas. A dos colores: base de un color y letras de otro.")
        with gr.Row():
            with gr.Column(scale=1):
                texto = gr.Textbox("Hola", label="Texto")
                fuente = gr.Dropdown(FUENTES, value=FUENTES[0], label="Letra")
                estilo = gr.Radio(["Llavero", "Letrero (placa rectangular)", "Solo letras (unidas)"], value="Llavero", label="Estilo")
                alto = gr.Slider(5, 80, 12, step=0.5, label="Altura de las letras (mm)")
                grosor = gr.Slider(0.6, 6, 2, step=0.2, label="Relieve de las letras (mm)")
                base = gr.Slider(0.8, 5, 1.6, step=0.1, label="Grosor de la base (mm)")
                borde = gr.Slider(1, 8, 2.5, step=0.5, label="Margen alrededor (mm)")
                b = gr.Button("Crear", variant="primary")
            with gr.Column(scale=1):
                sal = resultados()
        b.click(hacer_texto, [texto, fuente, alto, grosor, base, estilo, borde], sal)
    with gr.Tab("Arreglar un STL"):
        gr.Markdown("Repara mallas rotas, reduce caras, escala a una medida, lo tumba sobre su cara más estable y, si no cabe en la impresora, lo parte.")
        with gr.Row():
            with gr.Column(scale=1):
                f = gr.File(label="STL, 3MF, OBJ o GLB", file_types=[".stl", ".3mf", ".obj", ".glb", ".ply"], type="filepath")
                reparar = gr.Checkbox(True, label="Reparar")
                caras = gr.Number(0, label="Reducir a este número de caras (0 = no reducir)", precision=0)
                medida = gr.Number(0, label="Escalar a (mm, 0 = igual)")
                eje = gr.Radio(["Lo más largo", "Ancho (X)", "Fondo (Y)", "Alto (Z)"], value="Lo más largo", label="Medida de")
                tumbar = gr.Checkbox(True, label="Tumbar sobre la cara más estable")
                partir = gr.Checkbox(False, label="Partir si no cabe en la impresora")
                b = gr.Button("Arreglar", variant="primary")
            with gr.Column(scale=1):
                sal = resultados()
        b.click(hacer_taller, [f, reparar, caras, medida, eje, tumbar, partir], sal)
    with gr.Tab("Ayuda"):
        gr.Markdown("""
**Dos colores con una sola boquilla:** cuando el informe diga «pausa en la capa X mm», en Orca pulsa con el botón derecho en esa capa del deslizador › *Añadir pausa*. La impresora se para; cambias el filamento desde la pantalla y sigue.

**Fotos:** de frente, con luz de día, sin cosas delante. Para figuras 3D, el animal o la persona entera y sin cortar.

**Dónde queda todo:** cada pieza se guarda en la carpeta `salida`. Con *Guardar en mi carpeta* se copia a `IA3D_DESTINO` (por defecto, `guardados`).

**Modelos usados:** Depth Anything V2 (profundidad), BiRefNet (quitar fondo), TripoSG de VAST (figuras 3D, licencia MIT).
""")

if __name__ == "__main__":
    app.queue().launch(server_name="127.0.0.1", server_port=7870, inbrowser=True, theme=TEMA, footer_links=[])

# Taller 3D

[English](README.en.md)

Página web local (Gradio) que convierte fotos, dibujos y textos en STL listos para imprimir, con IA que corre en tu propio ordenador.

## Qué hace
- **Figura 3D desde una foto**: la IA quita el fondo y TripoSG crea la figura entera.
- **Relieve desde una foto**: placa con relieve según la profundidad que calcula Depth Anything V2.
- **Litofanía**: la foto se ve al ponerla a contraluz.
- **Dibujo o logo**: lo convierte en placa, llavero, cortador de galletas o sello.
- **Texto y nombres**: letreros y llaveros.
- **Arreglar STL**: repara mallas, reduce caras, escala, tumba la pieza sobre su cara más estable y la parte si no cabe en la impresora.
- Informe de cada pieza (medidas, si cabe, pausa para dos colores), vista 3D y botón para abrirla en OrcaSlicer.

## Requisitos
- Windows o Linux con tarjeta NVIDIA de 8 GB o más. Las figuras 3D necesitan CUDA; lo demás también funciona sin gráfica, pero más lento.
- Python 3.10 y Git.
- La primera vez descarga los modelos (varios GB) en la carpeta `modelos`.

## Instalar y usar
- **Windows**: `instalar.bat`, y después `iniciar_taller.bat`.
- **Linux**: `bash instalar.sh`, y después `bash iniciar_taller.sh`.
- Se abre en http://127.0.0.1:7870.

Ajustes opcionales, como variables de entorno:

| Variable | Para qué sirve | Valor por defecto |
|---|---|---|
| `IA3D_DESTINO` | Carpeta donde se guardan las piezas | `guardados` |
| `IA3D_CAMA` | Volumen de impresión en mm | `220x220x250` |
| `ORCA` | Ruta de OrcaSlicer | — |

## Modelos de IA que usa
Se descargan aparte y cada uno tiene su licencia:
- [TripoSG](https://github.com/VAST-AI-Research/TripoSG): MIT.
- [BiRefNet](https://github.com/ZhengPeng7/BiRefNet), mediante rembg: MIT.
- [Depth Anything V2 Large](https://huggingface.co/depth-anything/Depth-Anything-V2-Large-hf): CC BY-NC 4.0, solo para uso no comercial.

## Licencia
**Uso personal y no comercial gratuito** bajo la [PolyForm Noncommercial 1.0.0](LICENSE.md). Para usarlo en un negocio o venderlo hace falta una licencia comercial de pago: escríbeme por [GitHub](https://github.com/Iklavid).
Al limitar el uso comercial, esta licencia no es «open source» según la OSI; el código sigue siendo público.

# Taller 3D (3D workshop)

[Español](README.md)

A local web page (Gradio) that turns photos, drawings and text into printable STL files, using AI that runs on your own computer. The interface is in Spanish.

- **3D figure from a photo**: removes the background, then TripoSG builds the whole figure.
- **Relief from a photo**: a plaque shaped by Depth Anything V2 depth.
- **Lithophane**: the photo shows when you hold it against the light.
- **Drawing or logo**: becomes a plaque, keychain, cookie cutter or stamp.
- **Text and names**: signs and keychains.
- **STL repair**: fixes meshes, reduces faces, scales, lays the part on its most stable face and splits it if it does not fit the printer.

**Requirements:** Windows or Linux, an NVIDIA GPU with 8 GB or more (needed for 3D figures), Python 3.10 and Git.

**Install:** run `instalar.bat` and then `iniciar_taller.bat` on Windows, or `bash instalar.sh` and then `bash iniciar_taller.sh` on Linux. Then open http://127.0.0.1:7870.

**AI models** (downloaded separately, each with its own license): TripoSG (MIT), BiRefNet via rembg (MIT) and Depth Anything V2 Large (CC BY-NC 4.0, noncommercial).

## License
**Free for personal and other noncommercial use** under the [PolyForm Noncommercial License 1.0.0](LICENSE.md). Commercial use (selling it, using it in a business) needs a paid commercial license: contact me on [GitHub](https://github.com/Iklavid).
Because it restricts commercial use, this license is not "open source" under the OSI definition; the source code is still public.

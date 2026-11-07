#!/bin/bash
# Instala el Taller 3D en esta carpeta (Linux, tarjeta NVIDIA). Necesita python3.10 y git.
set -e
cd "$(dirname "$0")"
python3.10 -m venv venv
venv/bin/pip install --upgrade pip
venv/bin/pip install torch==2.6.0 torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cu124
venv/bin/pip install -r requirements.txt
[ -d triposg ] || git clone https://github.com/VAST-AI-Research/TripoSG triposg
venv/bin/python parche_triposg.py
echo "Listo. Abre el Taller con: bash iniciar_taller.sh"

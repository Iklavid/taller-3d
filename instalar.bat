@echo off
rem Instala el Taller 3D en esta carpeta (Windows, tarjeta NVIDIA). Necesita Python 3.10 y Git.
cd /d "%~dp0"
py -3.10 -m venv venv || (echo Falta Python 3.10: instalalo desde python.org & pause & exit /b 1)
venv\Scripts\python -m pip install --upgrade pip
venv\Scripts\python -m pip install torch==2.6.0 torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cu124
venv\Scripts\python -m pip install -r requirements.txt
if not exist triposg git clone https://github.com/VAST-AI-Research/TripoSG triposg
venv\Scripts\python parche_triposg.py
echo Listo. Abre el Taller con iniciar_taller.bat
pause

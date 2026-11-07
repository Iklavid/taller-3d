"""TripoSG importa diso, que necesita el CUDA toolkit para compilarse. Con este cambio, si diso no está,
usa el marching cubes normal (el Taller llama a TripoSG con use_flash_decoder=False)."""
from pathlib import Path

p = Path(__file__).resolve().parent / "triposg" / "triposg" / "inference_utils.py"
t = p.read_text(encoding="utf-8")
if "DiffDMC = None" not in t:
    t = t.replace("from diso import DiffDMC", "try:\n    from diso import DiffDMC\nexcept ImportError:\n    DiffDMC = None", 1)
    p.write_text(t, encoding="utf-8")
print("TripoSG listo")

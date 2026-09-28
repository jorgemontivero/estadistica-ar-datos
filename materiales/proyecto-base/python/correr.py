"""Corre todo el análisis, de los datos crudos a las tablas.

    python python/correr.py

Desde la carpeta del proyecto, no desde python/.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comun import escribir_csv  # noqa: E402

if not Path("datos/crudos/encuesta.csv").exists():
    raise SystemExit("No encuentro datos/crudos/encuesta.csv. ¿Estás parado en la carpeta del proyecto?")

importar = __import__("01_importar").importar
analizar = __import__("02_analizar").analizar

importado = importar()
analizado = analizar()

resumen = [
    {"clave": "filas_crudas", "valor": importado["filas_crudas"]},
    {"clave": "filas_repetidas", "valor": importado["filas_repetidas"]},
    {"clave": "valores_vacios", "valor": importado["valores_vacios"]},
    {"clave": "valores_fuera_de_rango", "valor": importado["valores_fuera_de_rango"]},
    {"clave": "filas_limpias", "valor": importado["filas_limpias"]},
    {"clave": "grupos", "valor": analizado["grupos"]},
    {"clave": "casos_analizados", "valor": analizado["casos"]},
]
escribir_csv(resumen, "salidas/resumen.csv")

print("Listo. Salidas en salidas/:")
print("  descriptivos.csv, por-grupo.csv, resumen.csv")
print(f"  {importado['filas_crudas']} filas crudas → {importado['filas_limpias']} limpias")

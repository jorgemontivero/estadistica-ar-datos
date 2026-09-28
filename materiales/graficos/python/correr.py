"""Dibuja todas las figuras, cada una con su tabla.

    python python/correr.py

Desde la carpeta del proyecto, no desde python/.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comun import escribir_csv, leer_csv  # noqa: E402

DATOS = "datos/base.csv"
VARIABLES = "datos/variables.csv"

for archivo in (DATOS, VARIABLES):
    if not Path(archivo).exists():
        raise SystemExit(f"No encuentro {archivo}. ¿Estás parado en la carpeta del proyecto?")

dibujar = __import__("01_figuras").dibujar

datos = leer_csv(DATOS)
variables = [{c: fila.get(c, "") for c in ("nombre", "etiqueta", "tipo")}
             for fila in leer_csv(VARIABLES) if fila.get("nombre", "") != ""]

hechas = dibujar(datos, variables)
escribir_csv([{"figura": nombre} for nombre in hechas], "indice", ["figura"])

print("Listo. Figuras en salidas/figuras/:")
for nombre in hechas:
    print(f"  {nombre}.png · {nombre}.csv")

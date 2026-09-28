"""Calcula los descriptivos y arma la tabla 1.

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

calcular = __import__("01_descriptivos").calcular
armar = __import__("02_tabla1").armar

datos = leer_csv(DATOS)
variables = [{c: fila.get(c, "") for c in ("nombre", "etiqueta", "tipo")}
             for fila in leer_csv(VARIABLES) if fila.get("nombre", "") != ""]

calculado = calcular(datos, variables)
tabla = armar(datos, variables, calculado)

resumen = [
    {"clave": "casos", "valor": len(datos)},
    {"clave": "variables", "valor": len(variables)},
    {"clave": "numericas", "valor": sum(1 for v in variables if v["tipo"] == "numerica")},
    {"clave": "categoricas", "valor": sum(1 for v in variables if v["tipo"] == "categorica")},
    {"clave": "grupos", "valor": len(tabla["niveles"])},
    {"clave": "filas_de_la_tabla", "valor": len(tabla["filas"])},
    {"clave": "asimetricas", "valor": sum(1 for f in calculado["numericas"]
                                          if f.get("forma") == "asimétrica")},
]
escribir_csv(resumen, "salidas/resumen.csv", ["clave", "valor"])

print("Listo. Salidas en salidas/:")
print("  descriptivos.csv, frecuencias.csv, tabla1.csv y tabla1.md")
print(f"  {len(datos)} casos, {len(variables)} variables, {len(tabla['niveles'])} grupos")

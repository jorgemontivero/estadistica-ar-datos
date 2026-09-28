"""Lo que comparten los dos pasos: cómo se leen y se escriben los CSV.

Los números se escriben con seis decimales fijos a propósito. Así el archivo de
Python y el de R son idénticos byte a byte, y comparar los dos es una línea en
la terminal. Con la notación que elige cada idioma por su cuenta —1e-04 acá,
0.0001 allá— habría que comparar a ojo.
"""

import csv
from pathlib import Path


def formatear(valor) -> str:
    if valor is None:
        return ""
    if isinstance(valor, bool):
        return str(valor)
    # Los conteos son enteros y se escriben sin decimales; lo demás, con seis.
    # Se mira el tipo y no el valor: una media que da justo 42 tiene que
    # escribirse igual que una que da 42,000001.
    if isinstance(valor, int):
        return str(valor)
    if isinstance(valor, float):
        return f"{valor:.6f}"
    return str(valor)


def escribir_csv(filas: list[dict], ruta: str | Path) -> None:
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    columnas = list(filas[0]) if filas else []
    lineas = [",".join(columnas)]
    lineas += [",".join(formatear(fila[c]) for c in columnas) for fila in filas]
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")


def leer_csv(ruta: str | Path) -> list[dict]:
    with open(ruta, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

"""Mira el archivo crudo, lo perfila y lo limpia.

    python python/correr.py

Desde la carpeta del proyecto, no desde python/.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comun import escribir_csv, leer_crudo  # noqa: E402

CRUDO = "datos/crudos/encuesta.csv"
DICCIONARIO = "datos/crudos/diccionario.csv"

for archivo in (CRUDO, DICCIONARIO):
    if not Path(archivo).exists():
        raise SystemExit(f"No encuentro {archivo}. ¿Estás parado en la carpeta del proyecto?")

perfilar = __import__("01_perfilar").perfilar
limpiar = __import__("02_limpiar").limpiar

crudo = leer_crudo(CRUDO)
diccionario = [
    {clave: fila.get(clave, "") for clave in
     ("nombre", "tipo", "minimo", "maximo", "codigos", "faltante", "id")}
    for fila in leer_crudo(DICCIONARIO)["filas"] if fila.get("nombre", "") != ""
]

perfil = perfilar(crudo, diccionario)
limpio = limpiar(crudo, diccionario)

resumen = [
    {"clave": "separador_detectado", "valor": {"\t": "tabulador", ",": "coma", ";": "punto y coma"}[crudo["separador"]]},
    {"clave": "decimal_detectado", "valor": "coma" if crudo["decimal"] == "," else "punto"},
    {"clave": "filas_crudas", "valor": len(crudo["filas"])},
    {"clave": "columnas_crudas", "valor": len(crudo["columnas"])},
    {"clave": "columnas_sin_declarar", "valor": sum(1 for p in perfil if not p["en_diccionario"])},
    {"clave": "variables_del_diccionario", "valor": len(diccionario)},
    {"clave": "filas_repetidas", "valor": limpio["duplicadas"]},
    {"clave": "filas_limpias", "valor": len(limpio["filas"])},
    {"clave": "valores_modificados", "valor": limpio["modificados"]},
    {"clave": "valores_vacios", "valor": limpio["vacios"]},
]
escribir_csv(resumen, "salidas/resumen.csv", ["clave", "valor"])

print("Listo. Salidas en salidas/:")
print("  perfil.csv, cambios.csv, resumen.csv · base limpia en datos/limpios/base.csv")
print(f"  {len(crudo['filas'])} filas crudas → {len(limpio['filas'])} limpias, "
      f"{limpio['modificados']} valores modificados")

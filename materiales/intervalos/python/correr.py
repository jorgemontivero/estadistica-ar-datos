"""Calcula todos los intervalos y escribe el informe.

    python python/correr.py

Desde la carpeta del proyecto, no desde python/.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comun import escribir_csv, escribir_texto, leer_csv, leer_parametros  # noqa: E402

DATOS = "datos/base.csv"
VARIABLES = "datos/variables.csv"
PARAMETROS = "datos/parametros.csv"

for archivo in (DATOS, VARIABLES, PARAMETROS):
    if not Path(archivo).exists():
        raise SystemExit(f"No encuentro {archivo}. ¿Estás parado en la carpeta del proyecto?")

una_muestra = __import__("01_una_muestra").calcular
diferencias_de = __import__("02_diferencias").calcular
redactar = __import__("03_redaccion").redactar

datos = leer_csv(DATOS)
variables = [{c: fila.get(c, "") for c in ("nombre", "etiqueta", "tipo")}
             for fila in leer_csv(VARIABLES) if fila.get("nombre", "") != ""]
parametros = leer_parametros(PARAMETROS)

calculado = una_muestra(datos, variables, parametros)
diferencias = diferencias_de(datos, variables, parametros, calculado)

escribir_csv(calculado["medias"], "salidas/ic-medias.csv",
             ["variable", "etiqueta", "ambito", "n", "media", "desvio", "error_estandar",
              "gl", "critico", "margen", "inferior", "superior"])
escribir_csv(calculado["varianzas"], "salidas/ic-varianzas.csv",
             ["variable", "etiqueta", "ambito", "n", "gl", "varianza", "desvio",
              "var_inferior", "var_superior", "desvio_inferior", "desvio_superior"])
escribir_csv(calculado["proporciones"], "salidas/ic-proporciones.csv",
             ["variable", "etiqueta", "categoria", "ambito", "n", "exitos", "proporcion",
              "metodo", "inferior", "superior", "ancho"])
escribir_csv(diferencias["diferencias"], "salidas/ic-diferencias.csv",
             ["variable", "etiqueta", "que", "categoria", "grupo_1", "grupo_2", "n_1", "n_2",
              "estimacion_1", "estimacion_2", "diferencia", "error_estandar", "gl", "critico",
              "inferior", "superior", "excluye_cero", "se_pisan_los_individuales",
              "conclusion_distinta"])
escribir_csv(calculado["avisos"] + diferencias["avisos"], "salidas/avisos.csv",
             ["intervalo", "variable", "ambito", "detalle", "aviso"])

escribir_texto(redactar(calculado, diferencias, parametros, len(datos)),
               "salidas/intervalos.md")

enganosas = sum(1 for f in diferencias["diferencias"] if f["conclusion_distinta"])
resumen = [
    {"clave": "casos", "valor": len(datos)},
    {"clave": "variables", "valor": len(variables)},
    {"clave": "confianza", "valor": parametros["confianza"]},
    {"clave": "grupos", "valor": len(diferencias["niveles"])},
    {"clave": "ic_de_medias", "valor": len(calculado["medias"])},
    {"clave": "ic_de_varianzas", "valor": len(calculado["varianzas"])},
    {"clave": "ic_de_proporciones", "valor": len(calculado["proporciones"])},
    {"clave": "ic_de_diferencias", "valor": len(diferencias["diferencias"])},
    {"clave": "avisos", "valor": len(calculado["avisos"]) + len(diferencias["avisos"])},
    {"clave": "conclusiones_distintas", "valor": enganosas},
]
escribir_csv(resumen, "salidas/resumen.csv", ["clave", "valor"])

print("Listo. Salidas en salidas/:")
print("  ic-medias.csv, ic-varianzas.csv, ic-proporciones.csv, ic-diferencias.csv,")
print("  avisos.csv, resumen.csv e intervalos.md")
if enganosas:
    cuantas = "1 comparación" if enganosas == 1 else f"{enganosas} comparaciones"
    print(f"  Ojo: en {cuantas} los intervalos por separado llevan a la conclusión contraria.")

"""Verifica los supuestos, corre las pruebas y escribe el informe.

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

mirar_supuestos = __import__("01_supuestos").calcular
correr_pruebas = __import__("02_pruebas").calcular
redactar = __import__("03_redaccion").redactar

datos = leer_csv(DATOS)
variables = [{c: fila.get(c, "") for c in ("nombre", "etiqueta", "tipo")}
             for fila in leer_csv(VARIABLES) if fila.get("nombre", "") != ""]
parametros = leer_parametros(PARAMETROS)

supuestos = mirar_supuestos(datos, variables, parametros)
pruebas = correr_pruebas(datos, variables, parametros, supuestos)

escribir_csv(supuestos["supuestos"], "salidas/normalidad.csv",
             ["variable", "etiqueta", "factor", "grupo", "n", "media", "desvio", "asimetria",
              "shapiro_w", "shapiro_p", "veredicto"])
escribir_csv(supuestos["homogeneidad"], "salidas/homogeneidad.csv",
             ["variable", "etiqueta", "factor", "k", "levene_f", "gl1", "gl2", "levene_p",
              "homogeneas", "decide"])
escribir_csv(supuestos["esperadas"], "salidas/esperadas.csv",
             ["variable", "etiqueta", "factor", "filas", "columnas", "n", "esperada_minima",
              "todas_mayores_que_5"])
escribir_csv(pruebas["pruebas"], "salidas/pruebas.csv",
             ["variable", "etiqueta", "factor", "que", "k", "n", "prueba_del_arbol",
              "alternativa_del_arbol", "prueba", "motivo", "simbolo", "estadistico", "gl",
              "gl2", "p", "significativa", "medida", "efecto", "calificacion", "p_alternativa",
              "significativa_alternativa", "cambia_la_conclusion"])
escribir_csv(supuestos["avisos"] + pruebas["avisos"], "salidas/avisos.csv",
             ["variable", "factor", "aviso"])

escribir_texto(redactar(supuestos, pruebas, parametros, variables, len(datos)),
               "salidas/pruebas.md")

cambian = sum(1 for f in pruebas["pruebas"] if f["cambia_la_conclusion"])
no_normales = sum(1 for f in supuestos["supuestos"] if f["veredicto"] == "no-normal")
resumen = [
    {"clave": "casos", "valor": len(datos)},
    {"clave": "alfa", "valor": parametros["alfa"]},
    {"clave": "factores", "valor": sum(1 for v in variables if v["tipo"] == "grupo")},
    {"clave": "comparaciones", "valor": len(pruebas["pruebas"])},
    {"clave": "grupos_evaluados", "valor": len(supuestos["supuestos"])},
    {"clave": "grupos_no_normales", "valor": no_normales},
    {"clave": "significativas", "valor": sum(1 for f in pruebas["pruebas"] if f["significativa"])},
    {"clave": "cambian_la_conclusion", "valor": cambian},
    {"clave": "avisos", "valor": len(supuestos["avisos"]) + len(pruebas["avisos"])},
]
escribir_csv(resumen, "salidas/resumen.csv", ["clave", "valor"])

print("Listo. Salidas en salidas/:")
print("  normalidad.csv, homogeneidad.csv, esperadas.csv, pruebas.csv,")
print("  avisos.csv, resumen.csv y pruebas.md")
if cambian:
    cuantas = "1 comparación" if cambian == 1 else f"{cambian} comparaciones"
    print(f"  Ojo: en {cuantas} el supuesto decide la conclusión, no solo la prueba.")

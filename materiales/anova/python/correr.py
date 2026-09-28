"""Corre el ANOVA completo y escribe el informe.

    python python/correr.py

Desde la carpeta del proyecto, no desde python/.
"""

import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comun import (escribir_csv, escribir_texto, leer_csv,  # noqa: E402
                   leer_parametros, agrupar, desvio, media, mediana)

DATOS = Path("datos/base.csv")
VARIABLES = Path("datos/variables.csv")
PARAMETROS = Path("datos/parametros.csv")

for archivo in (DATOS, VARIABLES, PARAMETROS):
    if not archivo.exists():
        raise SystemExit(f"No encuentro {archivo}. ¿Estás parado en la carpeta del proyecto?")

supuestos_ = importlib.import_module("01_supuestos")
anova_ = importlib.import_module("02_anova")
posthoc_ = importlib.import_module("03_posthoc")
redaccion_ = importlib.import_module("04_redaccion")

datos = leer_csv(DATOS)
parametros = leer_parametros(PARAMETROS)

factores = [parametros["factor"]]
if parametros["factor_2"]:
    factores.append(parametros["factor_2"])

# Las celdas son la unidad del proyecto: con un factor coinciden con sus
# niveles, con dos son las combinaciones.
grupos_celda, descartados = agrupar(datos, factores, parametros["respuesta"])
grupos_factor, _ = agrupar(datos, [parametros["factor"]], parametros["respuesta"])
if not grupos_celda:
    raise SystemExit("Ninguna fila tiene a la vez la respuesta y todos los factores.")

supuestos = supuestos_.calcular(grupos_celda, parametros)
anova = anova_.calcular(grupos_factor, grupos_celda, parametros)

# Con dos factores el post hoc va sobre las celdas; con uno, sobre sus niveles.
if parametros["factor_2"]:
    sobre = f"{parametros['factor']} × {parametros['factor_2']}"
    tabla_post_hoc = anova_.tabla(grupos_celda, parametros["confianza"])
else:
    sobre = parametros["factor"]
    tabla_post_hoc = anova["un_factor"]
post_hoc = posthoc_.calcular(tabla_post_hoc, parametros, sobre)

celdas = [{"celda": e, "n": len(v), "media": media(v), "desvio": desvio(v),
           "mediana": mediana(v), "minimo": min(v), "maximo": max(v)}
          for e, _, v in grupos_celda]
escribir_csv(celdas, "salidas/celdas.csv",
             ["celda", "n", "media", "desvio", "mediana", "minimo", "maximo"])

escribir_csv(supuestos["normalidad"], "salidas/supuestos.csv",
             ["celda", "n", "w", "p", "normal", "por_que"])

uf = anova["un_factor"]
w = anova["welch"]
escribir_csv([{
    "fuente": "Entre grupos", "sc": uf["sc_entre"], "gl": uf["gl_entre"],
    "cm": uf["cm_entre"], "f": uf["f"], "p": uf["p"],
}, {
    "fuente": "Dentro de los grupos", "sc": uf["sc_dentro"], "gl": uf["gl_dentro"],
    "cm": uf["cm_dentro"], "f": None, "p": None,
}, {
    "fuente": "Total", "sc": uf["sc_total"], "gl": uf["gl_total"],
    "cm": None, "f": None, "p": None,
}], "salidas/anova-un-factor.csv", ["fuente", "sc", "gl", "cm", "f", "p"])

escribir_csv([{
    "n": uf["n"], "grupos": uf["k"], "f": uf["f"], "gl_entre": uf["gl_entre"],
    "gl_dentro": uf["gl_dentro"], "p": uf["p"], "critico": uf["critico"],
    "significativo": uf["p"] < 1 - parametros["confianza"],
    "eta_cuadrado": uf["eta_cuadrado"], "omega_cuadrado": uf["omega_cuadrado"],
    "welch_f": w["f"] if w else None, "welch_gl2": w["gl2"] if w else None,
    "welch_p": w["p"] if w else None,
    "levene_w": supuestos["homogeneidad"]["w"] if supuestos["homogeneidad"] else None,
    "levene_p": supuestos["homogeneidad"]["p"] if supuestos["homogeneidad"] else None,
}], "salidas/efecto-y-welch.csv",
    ["n", "grupos", "f", "gl_entre", "gl_dentro", "p", "critico", "significativo",
     "eta_cuadrado", "omega_cuadrado", "welch_f", "welch_gl2", "welch_p",
     "levene_w", "levene_p"])

dos = anova["dos_factores"]
filas_dos = []
if dos:
    for f in dos["tipo_iii"]:
        filas_dos.append({**f, "significativo": f["p"] < 1 - parametros["confianza"]})
    filas_dos.append({"termino": "Error", "sc": dos["sc_residual"], "gl": dos["gl_error"],
                      "cm": dos["cm_error"], "f": None, "p": None, "significativo": None})
escribir_csv(filas_dos, "salidas/anova-dos-factores.csv",
             ["termino", "sc", "gl", "cm", "f", "p", "significativo"])

escribir_csv(anova["tipos"], "salidas/tipos-de-suma.csv",
             ["termino", "sc_tipo_iii", "p_tipo_iii", "sc_tipo_i_primero",
              "p_tipo_i_primero", "sc_tipo_i_segundo", "p_tipo_i_segundo",
              "cambia_la_conclusion"])

escribir_csv(anova["efectos_simples"], "salidas/efectos-simples.csv",
             ["nivel", "n", "gl", "f", "p", "significativo", "entre", "diferencia",
              "inferior", "superior"])

escribir_csv(post_hoc["pares"], "salidas/post-hoc.csv",
             ["a", "b", "metodo", "diferencia", "error_estandar", "estadistico",
              "p_sin_corregir", "p", "inferior", "superior", "significativa",
              "cambia_entre_correcciones"])

avisos = supuestos["avisos"] + anova["avisos"] + post_hoc["avisos"]
escribir_csv(avisos, "salidas/avisos.csv", ["donde", "aviso"])

escribir_texto(redaccion_.redactar(parametros, supuestos, anova, post_hoc, celdas,
                                   len(datos)), "salidas/anova.md")

interaccion = dos["tipo_iii"][2] if dos else None
con_tukey = sum(1 for f in post_hoc["pares"]
                if f["metodo"] == "tukey" and f["significativa"])
sin_corregir = sum(1 for f in post_hoc["pares"]
                   if f["metodo"] == "sin corregir" and f["significativa"])
discrepan = sum(1 for f in post_hoc["pares"]
                if f["metodo"] == "tukey" and f["cambia_entre_correcciones"])
escribir_csv([
    {"clave": "casos", "valor": len(datos)},
    {"clave": "usados", "valor": uf["n"]},
    {"clave": "celdas", "valor": len(celdas)},
    {"clave": "f_un_factor", "valor": uf["f"]},
    {"clave": "p_un_factor", "valor": uf["p"]},
    {"clave": "eta_cuadrado", "valor": uf["eta_cuadrado"]},
    {"clave": "p_interaccion", "valor": interaccion["p"] if interaccion else None},
    {"clave": "interaccion_significativa", "valor": anova["interaccion_significativa"]},
    {"clave": "efectos_simples_significativos",
     "valor": sum(1 for e in anova["efectos_simples"] if e["significativo"])},
    {"clave": "comparaciones", "valor": post_hoc["cuantas"]},
    {"clave": "significativas_sin_corregir", "valor": sin_corregir},
    {"clave": "significativas_con_tukey", "valor": con_tukey},
    {"clave": "pares_donde_discrepan_los_metodos", "valor": discrepan},
    {"clave": "avisos", "valor": len(avisos)},
], "salidas/resumen.csv", ["clave", "valor"])

print("Listo. Salidas en salidas/:")
print("  celdas.csv, supuestos.csv, anova-un-factor.csv, efecto-y-welch.csv,")
print("  anova-dos-factores.csv, tipos-de-suma.csv, efectos-simples.csv,")
print("  post-hoc.csv, avisos.csv, resumen.csv y anova.md")
if descartados:
    print(f"  Se descartaron {descartados} casos sin respuesta o sin factor.")
if anova["interaccion_significativa"]:
    print("  Ojo: la interacción es significativa. Los efectos principales no se leen solos.")
if discrepan:
    cuantas = "1 comparación" if discrepan == 1 else f"{discrepan} comparaciones"
    print(f"  Ojo: en {cuantas} los cuatro métodos no coinciden.")

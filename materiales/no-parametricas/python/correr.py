"""Corre las pruebas no paramétricas y el bootstrap, y escribe el informe.

    python python/correr.py

Desde la carpeta del proyecto, no desde python/.
"""

import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comun import (escribir_csv, escribir_texto, leer_csv, leer_parametros,  # noqa: E402
                   pares_completos, por_grupo)

DATOS = Path("datos/base.csv")
VARIABLES = Path("datos/variables.csv")
PARAMETROS = Path("datos/parametros.csv")

for archivo in (DATOS, VARIABLES, PARAMETROS):
    if not archivo.exists():
        raise SystemExit(f"No encuentro {archivo}. ¿Estás parado en la carpeta del proyecto?")

apareadas_ = importlib.import_module("01_apareadas")
independientes_ = importlib.import_module("02_independientes")
bootstrap_ = importlib.import_module("03_bootstrap")
redaccion_ = importlib.import_module("04_redaccion")

datos = leer_csv(DATOS)
parametros = leer_parametros(PARAMETROS)

apareadas = None
if parametros["antes"] and parametros["despues"]:
    pares = pares_completos(datos, parametros["antes"], parametros["despues"])
    apareadas = apareadas_.calcular(datos, parametros, pares)

grupos, descartados_grupo = ({}, 0)
if parametros["respuesta"] and parametros["grupo"]:
    grupos, descartados_grupo = por_grupo(datos, parametros["respuesta"],
                                          parametros["grupo"])
por_factor = {}
if parametros["respuesta"] and parametros["factor"]:
    por_factor, _ = por_grupo(datos, parametros["respuesta"], parametros["factor"])

independientes = independientes_.calcular(datos, parametros, grupos, por_factor)

valores = [x for v in grupos.values() for x in v]
bootstrap = bootstrap_.calcular(parametros, valores, grupos)

# ------------------------------------------------------------------ salidas
w = apareadas["wilcoxon"] if apareadas else None
s = apareadas["signos"] if apareadas else None

# Las dos pruebas apareadas y las dos que NO corresponden, en la misma tabla:
# el punto del paso es que se puedan mirar juntas.
filas_apareadas = []
if w:
    filas_apareadas.append({
        "prueba": "Wilcoxon de rangos con signo", "n": w["n"], "estadistico": w["w"],
        "z": w["z"], "p": w["p"], "significativa": w["significativa"],
        "desplazamiento": w["hodges_lehmann"],
        "detalle": f"{w['sin_cambio']} pares sin cambio"})
if s:
    filas_apareadas.append({
        "prueba": "Prueba de los signos", "n": s["n"], "estadistico": s["subieron"],
        "z": None, "p": s["p"], "significativa": s["significativa"],
        "desplazamiento": None,
        "detalle": f"{s['subieron']} suben y {s['bajaron']} bajan"})
if apareadas:
    mal = apareadas["como_independientes"]
    filas_apareadas.append({
        "prueba": "Mann-Whitney, tirando el apareamiento", "n": apareadas["n_pares"],
        "estadistico": None, "z": None, "p": mal["mann_whitney_p"],
        "significativa": (mal["mann_whitney_p"] < 1 - parametros["confianza"]
                          if mal["mann_whitney_p"] is not None else None),
        "desplazamiento": None, "detalle": "No corresponde: está para comparar"})
    filas_apareadas.append({
        "prueba": "t de Welch, tirando el apareamiento", "n": apareadas["n_pares"],
        "estadistico": None, "z": None, "p": mal["t_de_welch_p"],
        "significativa": mal["t_de_welch_p"] < 1 - parametros["confianza"],
        "desplazamiento": None, "detalle": "No corresponde: está para comparar"})
escribir_csv(filas_apareadas, "salidas/apareadas.csv",
             ["prueba", "n", "estadistico", "z", "p", "significativa", "desplazamiento",
              "detalle"])

escribir_csv([{
    "pares": apareadas["n_pares"], "descartados": apareadas["descartados"],
    "mediana_del_cambio": w["mediana_del_cambio"], "media_del_cambio": w["media_del_cambio"],
    "desvio_del_cambio": w["desvio_del_cambio"], "sin_cambio": w["sin_cambio"],
    "proporcion_que_sube": s["proporcion_que_sube"] if s else None,
    "cambia_la_conclusion": apareadas["cambia_la_conclusion"],
}] if apareadas and w else [], "salidas/el-cambio.csv",
    ["pares", "descartados", "mediana_del_cambio", "media_del_cambio", "desvio_del_cambio",
     "sin_cambio", "proporcion_que_sube", "cambia_la_conclusion"])

u = independientes["mann_whitney"]
t = independientes["t_de_welch"]
escribir_csv([{
    "n_a": u["n_a"], "n_b": u["n_b"], "u": u["u"], "z": u["z"], "p": u["p"],
    "significativa": u["significativa"],
    "probabilidad_de_superar": u["probabilidad_de_superar"],
    "hodges_lehmann": u["hodges_lehmann"],
    "mediana_a": u["mediana_a"], "mediana_b": u["mediana_b"],
    "t_de_welch": t["t"] if t else None, "p_de_welch": t["p"] if t else None,
    "coinciden": ((u["significativa"] == t["significativa"]) if t else None),
}] if u else [], "salidas/mann-whitney.csv",
    ["n_a", "n_b", "u", "z", "p", "significativa", "probabilidad_de_superar",
     "hodges_lehmann", "mediana_a", "mediana_b", "t_de_welch", "p_de_welch", "coinciden"])

filas_kw = []
for etiqueta, kw in (("grupo", independientes["kruskal"]),
                     ("factor", independientes["kruskal_factor"])):
    if not kw:
        continue
    for g in kw["grupos"]:
        filas_kw.append({"sobre": etiqueta, **g})
escribir_csv(filas_kw, "salidas/kruskal-grupos.csv",
             ["sobre", "grupo", "n", "mediana", "suma_de_rangos", "rango_promedio"])

escribir_csv([{
    "sobre": etiqueta, "h": kw["h"], "h_sin_corregir": kw["h_sin_corregir"],
    "gl": kw["gl"], "p": kw["p"], "significativa": kw["significativa"],
    "epsilon_cuadrado": kw["epsilon_cuadrado"], "n": kw["n"], "grupos": kw["k"],
} for etiqueta, kw in (("grupo", independientes["kruskal"]),
                       ("factor", independientes["kruskal_factor"])) if kw],
    "salidas/kruskal-wallis.csv",
    ["sobre", "h", "h_sin_corregir", "gl", "p", "significativa", "epsilon_cuadrado",
     "n", "grupos"])

escribir_csv(bootstrap["intervalos"], "salidas/bootstrap.csv",
             ["estadistico", "observado", "error_estandar", "sesgo",
              "percentil_inferior", "percentil_superior", "basico_inferior",
              "basico_superior", "bca_inferior", "bca_superior", "z0", "aceleracion",
              "excluye_el_cero"])

p = bootstrap["permutacion"]
escribir_csv([{
    "estadistico": "diferencia de medianas", "observada": p["observada"],
    "replicas": p["replicas"], "mas_extremas": p["extremas"], "p": p["p"],
    "significativa": p["significativa"],
}] if p else [], "salidas/permutacion.csv",
    ["estadistico", "observada", "replicas", "mas_extremas", "p", "significativa"])

avisos = ((apareadas["avisos"] if apareadas else [])
          + independientes["avisos"] + bootstrap["avisos"])
escribir_csv(avisos, "salidas/avisos.csv", ["donde", "aviso"])

escribir_texto(redaccion_.redactar(parametros, apareadas, independientes, bootstrap,
                                   len(datos)), "salidas/no-parametricas.md")

escribir_csv([
    {"clave": "casos", "valor": len(datos)},
    {"clave": "pares_completos", "valor": apareadas["n_pares"] if apareadas else 0},
    {"clave": "p_wilcoxon", "valor": w["p"] if w else None},
    {"clave": "p_signos", "valor": s["p"] if s else None},
    {"clave": "p_sin_aparear", "valor": (apareadas["como_independientes"]["mann_whitney_p"]
                                         if apareadas else None)},
    {"clave": "el_apareamiento_cambia_la_conclusion",
     "valor": apareadas["cambia_la_conclusion"] if apareadas else None},
    {"clave": "p_mann_whitney", "valor": u["p"] if u else None},
    {"clave": "probabilidad_de_superar",
     "valor": u["probabilidad_de_superar"] if u else None},
    {"clave": "p_t_de_welch", "valor": t["p"] if t else None},
    {"clave": "replicas", "valor": bootstrap["replicas"]},
    {"clave": "p_permutacion", "valor": p["p"] if p else None},
    {"clave": "avisos", "valor": len(avisos)},
], "salidas/resumen.csv", ["clave", "valor"])

print("Listo. Salidas en salidas/:")
print("  apareadas.csv, el-cambio.csv, mann-whitney.csv, kruskal-wallis.csv,")
print("  kruskal-grupos.csv, bootstrap.csv, permutacion.csv, avisos.csv,")
print("  resumen.csv y no-parametricas.md")
if apareadas and apareadas["cambia_la_conclusion"]:
    print("  Ojo: tirar el apareamiento cambia la conclusión.")
if u and t and u["significativa"] != t["significativa"]:
    print("  Ojo: Mann-Whitney y la t de Welch no coinciden.")

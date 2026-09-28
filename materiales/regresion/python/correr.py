"""Ajusta los modelos, los diagnostica y escribe el informe.

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

lineal = __import__("01_lineal").calcular
diagnosticar = __import__("02_diagnostico").calcular
logistica_de = __import__("03_logistica").calcular
redactar = __import__("04_redaccion").redactar

datos = leer_csv(DATOS)
parametros = leer_parametros(PARAMETROS)

modelo = lineal(datos, parametros)
diagnostico = diagnosticar(modelo, parametros)
logistica = logistica_de(datos, parametros)

escribir_csv(modelo["coeficientes"], "salidas/coeficientes.csv",
             ["termino", "estimacion", "error_estandar", "t", "gl", "p", "inferior", "superior",
              "significativo", "vif"])
escribir_csv([{
    "n": modelo["n"], "predictores": modelo["k"] - 1, "gl": modelo["gl"],
    "r2": modelo["r2"], "r2_ajustado": modelo["r2_ajustado"],
    "ee_residual": modelo["ee_residual"], "sc_modelo": modelo["sc_modelo"],
    "sc_residual": modelo["sc_residual"], "sc_total": modelo["sc_total"],
    "f": modelo["f"], "gl_modelo": modelo["gl_modelo"], "p_f": modelo["p_f"],
    "descartados": modelo["descartados"],
}], "salidas/ajuste.csv",
    ["n", "predictores", "gl", "r2", "r2_ajustado", "ee_residual", "sc_modelo", "sc_residual",
     "sc_total", "f", "gl_modelo", "p_f", "descartados"])

s, bp = diagnostico["shapiro"], diagnostico["breusch_pagan"]
escribir_csv([{
    "shapiro_w": s["w"], "shapiro_p": s["p"], "residuos_normales": s["normales"],
    "breusch_pagan_lm": bp["lm"] if bp else None, "breusch_pagan_gl": bp["gl"] if bp else None,
    "breusch_pagan_p": bp["p"] if bp else None,
    "varianza_constante": (bp["p"] >= 1 - parametros["confianza"]) if bp else None,
    "durbin_watson": diagnostico["durbin_watson"],
    "palanca_umbral": diagnostico["palanca_umbral"],
    "casos_palanca_alta": sum(1 for f in diagnostico["influencia"] if f["palanca_alta"]),
    "casos_residuo_grande": sum(1 for f in diagnostico["influencia"] if f["residuo_grande"]),
    "cook_maximo": max(f["cook"] for f in diagnostico["influencia"]),
}], "salidas/diagnostico.csv",
    ["shapiro_w", "shapiro_p", "residuos_normales", "breusch_pagan_lm", "breusch_pagan_gl",
     "breusch_pagan_p", "varianza_constante", "durbin_watson", "palanca_umbral",
     "casos_palanca_alta", "casos_residuo_grande", "cook_maximo"])

escribir_csv(diagnostico["influencia"], "salidas/influencia.csv",
             ["caso", "observado", "ajustado", "residuo", "estandarizado", "palanca", "cook",
              "palanca_alta", "residuo_grande"])

reajuste = diagnostico["reajuste"]
escribir_csv(reajuste["comparacion"] if reajuste else [], "salidas/sin-el-influyente.csv",
             ["termino", "con_el_caso", "p_con", "sin_el_caso", "p_sin", "cambio_relativo",
              "cambia_la_conclusion", "cambia_de_signo"])

escribir_csv(logistica["coeficientes"] if logistica else [], "salidas/logistica.csv",
             ["termino", "estimacion", "error_estandar", "z", "p", "odds_ratio", "or_inferior",
              "or_superior", "significativo"])

escribir_csv([logistica["clasificacion"]] if logistica else [], "salidas/clasificacion.csv",
             ["corte", "verdaderos_positivos", "falsos_positivos", "verdaderos_negativos",
              "falsos_negativos", "sensibilidad", "especificidad", "exactitud",
              "exactitud_trivial", "auc"])

avisos = diagnostico["avisos"] + (logistica["avisos"] if logistica else [])
escribir_csv(avisos, "salidas/avisos.csv", ["donde", "aviso"])

escribir_texto(redactar(parametros, modelo, diagnostico, logistica, len(datos)),
               "salidas/regresion.md")

cambian = reajuste["cuantos_cambian"] if reajuste else 0
resumen = [
    {"clave": "casos", "valor": len(datos)},
    {"clave": "usados_en_el_ajuste", "valor": modelo["n"]},
    {"clave": "predictores", "valor": modelo["k"] - 1},
    {"clave": "r2", "valor": modelo["r2"]},
    {"clave": "coeficientes_significativos",
     "valor": sum(1 for f in modelo["coeficientes"]
                  if f["termino"] != "(ordenada)" and f["significativo"])},
    {"clave": "caso_mas_influyente", "valor": reajuste["caso"] if reajuste else 0},
    {"clave": "cook_maximo", "valor": max(f["cook"] for f in diagnostico["influencia"])},
    {"clave": "coeficientes_que_cambian_sin_el", "valor": cambian},
    {"clave": "vueltas_del_irls",
     "valor": logistica["modelo"]["vueltas"] if logistica else 0},
    {"clave": "auc", "valor": logistica["clasificacion"]["auc"] if logistica else None},
    {"clave": "avisos", "valor": len(avisos)},
]
escribir_csv(resumen, "salidas/resumen.csv", ["clave", "valor"])

print("Listo. Salidas en salidas/:")
print("  coeficientes.csv, ajuste.csv, diagnostico.csv, influencia.csv,")
print("  sin-el-influyente.csv, logistica.csv, clasificacion.csv,")
print("  avisos.csv, resumen.csv y regresion.md")
if cambian:
    cuantos = "1 coeficiente" if cambian == 1 else f"{cambian} coeficientes"
    print(f"  Ojo: sacar el caso {reajuste['caso']} cambia la conclusión de {cuantos}.")

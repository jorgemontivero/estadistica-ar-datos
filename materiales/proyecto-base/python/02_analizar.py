"""Paso 2: analizar.

Lee datos/limpios/encuesta.csv —nunca el crudo— y escribe las tablas en
salidas/. Se puede correr las veces que haga falta sin volver a limpiar.
"""

import statistics

from comun import escribir_csv, leer_csv

VARIABLES = ["edad", "ingreso", "puntaje"]


def numero(x):
    x = (x or "").strip()
    if x == "":
        return None
    try:
        return float(x)
    except ValueError:
        return None


def descriptivos(valores: list) -> dict:
    x = [v for v in valores if v is not None]
    n = len(x)
    return {
        "n": n,
        "media": statistics.fmean(x) if n >= 1 else None,
        "desvio": statistics.stdev(x) if n >= 2 else None,
        "minimo": min(x) if n >= 1 else None,
        "mediana": statistics.median(x) if n >= 1 else None,
        "maximo": max(x) if n >= 1 else None,
    }


def analizar() -> dict:
    datos = leer_csv("datos/limpios/encuesta.csv")
    for fila in datos:
        for v in VARIABLES:
            fila[v] = numero(fila[v])

    tabla = []
    for v in VARIABLES:
        d = descriptivos([fila[v] for fila in datos])
        tabla.append({"variable": v, **d})
    escribir_csv(tabla, "salidas/descriptivos.csv")

    # Por grupo, en orden alfabético para que R y Python coincidan.
    grupos = sorted({fila["grupo"] for fila in datos if fila["grupo"]})
    por_grupo = []
    for g in grupos:
        for v in VARIABLES:
            d = descriptivos([fila[v] for fila in datos if fila["grupo"] == g])
            por_grupo.append({"grupo": g, "variable": v, "n": d["n"], "media": d["media"],
                              "desvio": d["desvio"]})
    escribir_csv(por_grupo, "salidas/por-grupo.csv")

    return {"grupos": len(grupos), "casos": len(datos)}

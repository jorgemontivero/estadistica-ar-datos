"""Paso 1: los intervalos de una sola muestra.

Para cada variable numérica, el intervalo de la media y el de la varianza y el
desvío. Para cada categórica, el de la proporción de cada categoría, por los
tres métodos a la vez.

Todo se calcula dos veces: sobre el total y dentro de cada grupo. El «ámbito»
es la columna que dice cuál de las dos cosas es cada fila.

Los tres métodos para la proporción no están para que elijas el que más te
guste: están para que veas cuánto se separan cuando la categoría es rara. Con
150 casos y 7 becados, Wald y Clopper-Pearson no dicen lo mismo, y el que hay
que informar es el que no depende de la aproximación normal.
"""

import math

from comun import desvio, media, numeros
from intervalos import ic_media, ic_proporcion, ic_varianza

METODOS = ["wilson", "wald", "clopper-pearson"]
TOTAL = "Total"


def ambitos(datos, grupo):
    """El total primero y después cada grupo, siempre en el mismo orden."""
    if grupo is None:
        return [(TOTAL, datos)]
    niveles = sorted({f.get(grupo, "") for f in datos if f.get(grupo, "") != ""})
    return [(TOTAL, datos)] + [(n, [f for f in datos if f.get(grupo, "") == n]) for n in niveles]


def calcular(datos, variables, parametros):
    confianza = parametros["confianza"]
    poblacion = parametros["poblacion"]
    grupo = next((v["nombre"] for v in variables if v["tipo"] == "grupo"), None)

    medias, varianzas, proporciones, avisos = [], [], [], []

    def anotar(intervalo, tipo, variable, ambito, detalle=""):
        for aviso in intervalo["avisos"]:
            avisos.append({"intervalo": tipo, "variable": variable, "ambito": ambito,
                           "detalle": detalle, "aviso": aviso})

    for v in variables:
        if v["tipo"] != "numerica":
            continue
        for ambito, filas in ambitos(datos, grupo):
            x = numeros(filas, v["nombre"])
            if len(x) < 2:
                continue
            m, s = media(x), desvio(x)
            ic = ic_media(m, s, len(x), confianza, N=poblacion)
            if ic is None:
                continue
            medias.append({
                "variable": v["nombre"], "etiqueta": v["etiqueta"], "ambito": ambito,
                "n": len(x), "media": m, "desvio": s, "error_estandar": ic["error_estandar"],
                "gl": ic["gl"], "critico": ic["critico"], "margen": ic["margen"],
                "inferior": ic["inferior"], "superior": ic["superior"]})
            anotar(ic, "media", v["nombre"], ambito)

            # La varianza no admite corrección por población finita: el
            # intervalo sale de la chi-cuadrado, que no la contempla.
            iv = ic_varianza(s, len(x), confianza)
            if iv is None:
                continue
            varianzas.append({
                "variable": v["nombre"], "etiqueta": v["etiqueta"], "ambito": ambito,
                "n": len(x), "gl": iv["gl"], "varianza": iv["estimacion"], "desvio": s,
                "var_inferior": iv["inferior"], "var_superior": iv["superior"],
                "desvio_inferior": math.sqrt(iv["inferior"]),
                "desvio_superior": math.sqrt(iv["superior"])})
            anotar(iv, "varianza", v["nombre"], ambito)

    for v in variables:
        if v["tipo"] != "categorica":
            continue
        categorias = sorted({f.get(v["nombre"], "") for f in datos
                             if f.get(v["nombre"], "") != ""})
        for ambito, filas in ambitos(datos, grupo):
            valores = [f.get(v["nombre"], "") for f in filas if f.get(v["nombre"], "") != ""]
            if not valores:
                continue
            for categoria in categorias:
                exitos = valores.count(categoria)
                for metodo in METODOS:
                    ic = ic_proporcion(exitos, len(valores), confianza, metodo=metodo,
                                       N=poblacion)
                    if ic is None:
                        continue
                    proporciones.append({
                        "variable": v["nombre"], "etiqueta": v["etiqueta"],
                        "categoria": categoria, "ambito": ambito, "n": len(valores),
                        "exitos": exitos, "proporcion": ic["estimacion"], "metodo": metodo,
                        "inferior": ic["inferior"], "superior": ic["superior"],
                        "ancho": ic["superior"] - ic["inferior"]})
                    anotar(ic, f"proporción ({metodo})", v["nombre"], ambito, categoria)

    return {"medias": medias, "varianzas": varianzas, "proporciones": proporciones,
            "avisos": avisos}

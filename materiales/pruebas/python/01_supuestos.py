"""Paso 1: los supuestos, antes de la prueba y no después.

Para cada variable numérica y cada variable de agrupamiento:

    normalidad     Shapiro-Wilk dentro de cada grupo, que es donde el supuesto
                   vive. Probarla sobre la variable entera, mezclando grupos
                   que tienen medias distintas, es probar otra cosa.

    homogeneidad   Levene con centro en la mediana —la versión de
                   Brown y Forsythe, la robusta— entre los grupos.

Para las categóricas, la frecuencia esperada más chica de la tabla: el
supuesto del chi-cuadrado no es sobre las frecuencias observadas sino sobre
las esperadas.

El veredicto de normalidad no sale solo del valor p. Con menos de quince datos
ninguna prueba de normalidad tiene potencia, así que no rechazar no dice nada;
con más de trescientos rechazan desvíos tan chicos que no afectan a ninguna
prueba t. Las dos cosas se informan, con la misma regla que usa la
calculadora de normalidad del sitio.
"""

import math

from scipy import stats

from comun import asimetria, desvio, media, mediana, numeros

SIN_POTENCIA = "sin-potencia"
SIN_VARIACION = "sin-variación"
NORMAL = "normal"
NO_NORMAL = "no-normal"
MINIMO_CON_POTENCIA = 15
DEMASIADOS = 300


def veredicto_normalidad(x, p, alfa: float) -> str:
    """Tres cosas distintas, y ninguna es «pasó la prueba».

    Sin variación no hay distribución que evaluar; con menos de quince datos
    la prueba no tiene potencia y no rechazar no significa nada.
    """
    if desvio(x) == 0:
        return SIN_VARIACION
    if len(x) < MINIMO_CON_POTENCIA:
        return SIN_POTENCIA
    return NORMAL if p is None or p >= alfa else NO_NORMAL


def shapiro(x: list[float]):
    """Shapiro-Wilk. Hace falta n ≥ 3, y con todos los valores iguales no hay
    nada que probar."""
    if len(x) < 3 or desvio(x) == 0:
        return None, None
    w, p = stats.shapiro(x)
    return float(w), float(p)


def levene(grupos: list[list[float]]):
    """Levene con centro en la mediana: la versión de Brown y Forsythe.

    Es una ANOVA sobre las distancias absolutas de cada dato a la mediana de
    su grupo. Está escrita a mano y no tomada de una biblioteca porque R no la
    trae de fábrica: así las dos versiones calculan exactamente lo mismo.
    """
    grupos = [g for g in grupos if len(g) >= 2]
    k = len(grupos)
    if k < 2:
        return None
    z = [[abs(v - mediana(g)) for v in g] for g in grupos]
    n = sum(len(g) for g in z)
    if n <= k:
        return None
    total = media([v for g in z for v in g])
    entre = math.fsum(len(g) * (media(g) - total) ** 2 for g in z)
    dentro = math.fsum(math.fsum((v - media(g)) ** 2 for v in g) for g in z)
    if dentro == 0:
        return None
    f = (entre / (k - 1)) / (dentro / (n - k))
    return {"f": f, "gl1": k - 1, "gl2": n - k,
            "p": float(stats.f.sf(f, k - 1, n - k))}


def calcular(datos, variables, parametros):
    alfa = parametros["alfa"]
    factores = [v for v in variables if v["tipo"] == "grupo"]
    numericas = [v for v in variables if v["tipo"] == "numerica"]
    categoricas = [v for v in variables if v["tipo"] == "categorica"]

    supuestos, homogeneidad, esperadas, avisos = [], [], [], []

    def anotar(variable, factor, aviso):
        avisos.append({"variable": variable, "factor": factor, "aviso": aviso})

    for factor in factores:
        niveles = sorted({f.get(factor["nombre"], "") for f in datos
                          if f.get(factor["nombre"], "") != ""})
        for v in numericas:
            por_grupo = []
            for nivel in niveles:
                x = numeros([f for f in datos if f.get(factor["nombre"], "") == nivel],
                            v["nombre"])
                if len(x) < 2:
                    continue
                w, p = shapiro(x)
                supuestos.append({
                    "variable": v["nombre"], "etiqueta": v["etiqueta"],
                    "factor": factor["nombre"], "grupo": nivel, "n": len(x),
                    "media": media(x), "desvio": desvio(x), "asimetria": asimetria(x),
                    "shapiro_w": w, "shapiro_p": p,
                    "veredicto": veredicto_normalidad(x, p, alfa)})
                por_grupo.append(x)
                if desvio(x) == 0:
                    anotar(v["nombre"], factor["nombre"],
                           f"En el grupo «{nivel}» todos los valores son iguales: no hay "
                           f"distribución que evaluar ni prueba que aplicar.")
                elif len(x) < MINIMO_CON_POTENCIA:
                    anotar(v["nombre"], factor["nombre"],
                           f"En el grupo «{nivel}» hay {len(x)} datos: con menos de "
                           f"{MINIMO_CON_POTENCIA} ninguna prueba de normalidad tiene potencia "
                           f"real, así que no rechazar acá no es evidencia de nada. La decisión "
                           f"hay que tomarla por el origen de los datos, no por el valor p.")
                elif len(x) > DEMASIADOS:
                    anotar(v["nombre"], factor["nombre"],
                           f"En el grupo «{nivel}» hay {len(x)} datos: con tantos, las pruebas "
                           f"de normalidad detectan desvíos tan chicos que no afectan a ninguna "
                           f"prueba t. Si rechaza, mirá el tamaño de la asimetría antes que el "
                           f"valor p.")

            lev = levene(por_grupo)
            if lev is None:
                continue
            homogeneas = lev["p"] >= alfa
            homogeneidad.append({
                "variable": v["nombre"], "etiqueta": v["etiqueta"],
                "factor": factor["nombre"], "k": len(por_grupo),
                "levene_f": lev["f"], "gl1": lev["gl1"], "gl2": lev["gl2"],
                "levene_p": lev["p"], "homogeneas": homogeneas,
                # Con dos grupos la prueba que corresponde es la de Welch, que
                # no supone varianzas iguales: Levene se informa, pero no
                # decide nada.
                "decide": len(por_grupo) > 2})
            if len(por_grupo) == 2 and not homogeneas:
                anotar(v["nombre"], factor["nombre"],
                       "Las varianzas no son homogéneas, pero con dos grupos eso no cambia la "
                       "prueba: la de Welch no las supone iguales. Levene se informa para "
                       "describir, no para decidir.")

        for v in categoricas:
            categorias = sorted({f.get(v["nombre"], "") for f in datos
                                 if f.get(v["nombre"], "") != ""})
            tabla, total = [], 0
            for categoria in categorias:
                fila = []
                for nivel in niveles:
                    fila.append(sum(1 for f in datos
                                    if f.get(v["nombre"], "") == categoria
                                    and f.get(factor["nombre"], "") == nivel))
                tabla.append(fila)
                total += sum(fila)
            if total == 0 or len(tabla) < 2 or len(niveles) < 2:
                continue
            filas_suma = [sum(f) for f in tabla]
            columnas_suma = [sum(f[j] for f in tabla) for j in range(len(niveles))]
            minima = min(fi * cj / total for fi in filas_suma for cj in columnas_suma)
            esperadas.append({
                "variable": v["nombre"], "etiqueta": v["etiqueta"],
                "factor": factor["nombre"], "filas": len(tabla), "columnas": len(niveles),
                "n": total, "esperada_minima": minima, "todas_mayores_que_5": minima >= 5})
            if minima < 5:
                cuanto = f"{minima:.2f}".replace(".", ",")
                anotar(v["nombre"], factor["nombre"],
                       f"La frecuencia esperada más chica de la tabla es {cuanto}. El "
                       f"chi-cuadrado pide que todas las esperadas lleguen a 5; con menos, su "
                       f"valor p no es confiable.")

    return {"supuestos": supuestos, "homogeneidad": homogeneidad, "esperadas": esperadas,
            "avisos": avisos}

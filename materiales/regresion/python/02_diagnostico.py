"""Paso 2: el diagnóstico, que es donde el modelo se gana la confianza.

Un ajuste siempre devuelve números. Que esos números signifiquen algo depende
de cosas que el ajuste no mira: si los residuos tienen varianza constante, si
son independientes, si hay un puñado de casos decidiendo todo.

Se calculan cuatro cosas:

    normalidad       Shapiro-Wilk sobre los residuos. Es el supuesto menos
                     importante de los cuatro y el que más se cita.

    homocedasticidad Breusch-Pagan: se regresan los residuos al cuadrado
                     sobre los predictores. Si algo explica el tamaño del
                     error, la varianza no es constante.

    independencia    Durbin-Watson. Cerca de 2 no hay autocorrelación; cerca
                     de 0, positiva. Solo tiene sentido si las filas tienen
                     un orden —tiempo, espacio—; con una muestra desordenada
                     no dice nada y el proyecto lo aclara.

    influencia       palanca, residuo estandarizado y distancia de Cook, que
                     combina las dos formas de ser raro: estar lejos en la x
                     y estar lejos en la y.

Y después lo que justifica el paso entero: **el modelo se vuelve a ajustar sin
el caso más influyente** y se comparan los dos. Si alguna conclusión cambia,
queda escrito.
"""

import math

from scipy import stats

from comun import media


def palancas(x, inversa):
    """La diagonal del sombrero: h = xᵢ (X'X)⁻¹ xᵢ'.

    Mide cuán lejos está ese caso del centro de los predictores. Su suma es
    siempre k, así que la palanca media es k/n y se suele mirar el doble de
    eso como umbral.
    """
    salida = []
    for fila in x:
        acumulado = 0.0
        for i, vi in enumerate(fila):
            for j, vj in enumerate(fila):
                acumulado += vi * inversa[i][j] * vj
        salida.append(acumulado)
    return salida


def durbin_watson(residuos):
    numerador = math.fsum((residuos[i] - residuos[i - 1]) ** 2 for i in range(1, len(residuos)))
    denominador = math.fsum(r * r for r in residuos)
    return numerador / denominador if denominador > 0 else 0.0


def breusch_pagan(x, residuos):
    """Se regresan los residuos al cuadrado sobre los mismos predictores.

    El estadístico es n·R² de esa regresión auxiliar y se compara contra una
    chi-cuadrado con tantos grados de libertad como predictores.
    """
    from algebra import resolver

    n, k = len(x), len(x[0])
    u = [r * r for r in residuos]
    coef, _ = resolver(x, u)
    if coef is None:
        return None
    m = media(u)
    sc_total = math.fsum((v - m) ** 2 for v in u)
    if sc_total <= 0:
        return None
    ajustados = [math.fsum(c * v for c, v in zip(coef, fila)) for fila in x]
    sc_residual = math.fsum((v - a) ** 2 for v, a in zip(u, ajustados))
    r2 = 1 - sc_residual / sc_total
    lm = n * r2
    gl = k - 1
    return {"lm": lm, "gl": gl, "p": float(stats.chi2.sf(lm, gl))}


def influencia(modelo):
    """Palanca, residuo estandarizado y distancia de Cook, caso por caso."""
    x, residuos = modelo["x"], modelo["residuos"]
    n, k = modelo["n"], modelo["k"]
    h = palancas(x, modelo["inversa"])
    s = math.sqrt(modelo["varianza"])

    filas = []
    for i in range(n):
        resto = 1 - h[i]
        estandarizado = residuos[i] / (s * math.sqrt(resto)) if resto > 0 and s > 0 else 0.0
        # Cook combina las dos formas de ser influyente: estar lejos en y
        # (el residuo) y estar lejos en x (la palanca).
        cook = (estandarizado ** 2 / k) * (h[i] / resto) if resto > 0 else float("inf")
        filas.append({
            "caso": i + 1, "observado": modelo["y"][i], "ajustado": modelo["ajustados"][i],
            "residuo": residuos[i], "estandarizado": estandarizado,
            "palanca": h[i], "cook": cook,
            "palanca_alta": h[i] > 2 * k / n,
            "residuo_grande": abs(estandarizado) > 2,
        })
    return filas


def sin_el_influyente(modelo, filas_influencia, parametros):
    """Vuelve a ajustar el modelo sacando el caso de mayor distancia de Cook.

    Es la única forma honesta de contestar «¿cuánto de esto lo decide un solo
    caso?». Comparar el antes y el después, coeficiente por coeficiente.
    """
    from importlib import import_module

    ajustar = import_module("01_lineal").ajustar

    peor = max(range(len(filas_influencia)), key=lambda i: filas_influencia[i]["cook"])
    x = [fila for i, fila in enumerate(modelo["x"]) if i != peor]
    y = [v for i, v in enumerate(modelo["y"]) if i != peor]
    otro = ajustar(x, y, parametros["confianza"], parametros["predictores"])
    if otro is None:
        return None

    comparacion = []
    for antes, despues in zip(modelo["coeficientes"], otro["coeficientes"]):
        cambia = antes["significativo"] != despues["significativo"]
        signo = (antes["estimacion"] > 0) != (despues["estimacion"] > 0)
        comparacion.append({
            "termino": antes["termino"],
            "con_el_caso": antes["estimacion"], "p_con": antes["p"],
            "sin_el_caso": despues["estimacion"], "p_sin": despues["p"],
            "cambio_relativo": ((despues["estimacion"] - antes["estimacion"]) / antes["estimacion"]
                                if antes["estimacion"] != 0 else None),
            "cambia_la_conclusion": cambia,
            "cambia_de_signo": signo,
        })
    return {
        "caso": peor + 1, "cook": filas_influencia[peor]["cook"],
        "palanca": filas_influencia[peor]["palanca"],
        "comparacion": comparacion,
        "r2_con": modelo["r2"], "r2_sin": otro["r2"],
        "cuantos_cambian": sum(1 for c in comparacion if c["cambia_la_conclusion"]),
    }


def calcular(modelo, parametros):
    residuos = modelo["residuos"]
    alfa = 1 - parametros["confianza"]

    if len(residuos) >= 3 and math.fsum(r * r for r in residuos) > 0:
        w, p = stats.shapiro(residuos)
        shapiro = {"w": float(w), "p": float(p), "normales": float(p) >= alfa}
    else:
        shapiro = {"w": None, "p": None, "normales": None}

    bp = breusch_pagan(modelo["x"], residuos)
    dw = durbin_watson(residuos)
    filas = influencia(modelo)
    reajuste = sin_el_influyente(modelo, filas, parametros)

    k, n = modelo["k"], modelo["n"]
    avisos = []

    def anotar(que, aviso):
        avisos.append({"donde": que, "aviso": aviso})

    if shapiro["p"] is not None and shapiro["p"] < alfa:
        anotar("normalidad",
               "Shapiro-Wilk rechaza la normalidad de los residuos. Con n grande esto casi no "
               "afecta a los coeficientes ni a sus errores estándar: el teorema central del "
               "límite se ocupa. Donde sí importa es en los intervalos de predicción para un "
               "caso individual.")
    if bp and bp["p"] < alfa:
        anotar("homocedasticidad",
               "Breusch-Pagan rechaza la varianza constante. Los coeficientes siguen siendo "
               "insesgados, pero sus errores estándar están mal y con ellos los valores p. "
               "Corresponde usar errores robustos o transformar la respuesta.")
    if dw < 1.5 or dw > 2.5:
        anotar("independencia",
               f"El Durbin-Watson da {dw:.2f}".replace(".", ",") +
               ", lejos de 2. Si las filas tienen un orden —tiempo, espacio, escuela— hay "
               "autocorrelación y los errores estándar están subestimados. Si el orden de las "
               "filas es arbitrario, este número no significa nada.")
    for fila in modelo["coeficientes"]:
        if fila["vif"] is not None and fila["vif"] > 10:
            anotar("multicolinealidad",
                   f"El VIF de «{fila['termino']}» es " +
                   f"{fila['vif']:.1f}".replace(".", ",") +
                   ". Por encima de 10 el coeficiente y su signo dejan de ser interpretables por "
                   "separado: ese predictor y los otros están midiendo casi lo mismo.")
    altas = sum(1 for f in filas if f["palanca_alta"])
    if altas:
        anotar("influencia",
               f"Hay {altas} caso{'' if altas == 1 else 's'} con palanca mayor que 2k/n. No es un "
               f"problema en sí: significa que están lejos del centro de los predictores y que "
               f"pesan más que el resto en el ajuste.")
    if reajuste and reajuste["cuantos_cambian"]:
        anotar("influencia",
               f"Sacar el caso {reajuste['caso']} cambia la conclusión de "
               f"{reajuste['cuantos_cambian']} coeficiente"
               f"{'' if reajuste['cuantos_cambian'] == 1 else 's'}. Un resultado que depende de "
               f"un solo caso entre {n} no es un resultado: es ese caso.")

    return {"shapiro": shapiro, "breusch_pagan": bp, "durbin_watson": dw,
            "influencia": filas, "reajuste": reajuste, "avisos": avisos,
            "palanca_umbral": 2 * k / n}

"""Paso 3: la regresión logística, ajustada a mano.

El ajuste no tiene fórmula cerrada: se llega iterando. El método se llama
**IRLS** —mínimos cuadrados ponderados iterativamente— y es más simple de lo
que suena. En cada vuelta:

    1. con los coeficientes actuales se calcula la probabilidad de cada caso;
    2. se arma una variable de trabajo y un peso para cada caso;
    3. se resuelve un mínimos cuadrados ponderado común;
    4. se repite hasta que los coeficientes dejan de moverse.

Está escrito a mano por la misma razón que Levene y la ANOVA de Welch en el
descargable de pruebas: `glm` de R y `Logit` de statsmodels llegan al mismo
resultado pero **paran de iterar con criterios distintos**, y los coeficientes
terminan difiriendo en el octavo dígito. Escribir el ajuste una vez de cada
lado, con la misma tolerancia y el mismo máximo de vueltas, es lo único que
hace que los dos archivos salgan idénticos.

Lo que se informa es el **odds ratio**, no el riesgo relativo. No son lo
mismo y la confusión es diaria: con un resultado frecuente, el odds ratio
exagera bastante el riesgo relativo.
"""

import math

from scipy import stats

from algebra import resolver_ponderado
from comun import numero

TOLERANCIA = 1e-10
MAXIMO_VUELTAS = 50


def exponencial(p):
    """`exp` que no se cae.

    Con separación perfecta los coeficientes se van al infinito y el odds
    ratio con ellos. R devuelve `Inf` y sigue; Python levanta `OverflowError`
    y corta el programa. Igualarlos a mano es lo que permite que el proyecto
    informe el problema en `avisos.csv` en vez de morirse.
    """
    try:
        return math.exp(p)
    except OverflowError:
        return float("inf")


def logistica(p):
    return 1 / (1 + math.exp(-p)) if p > -700 else 0.0


def matriz(datos, respuesta, predictores, exito):
    x, y, indices = [], [], []
    for i, fila in enumerate(datos):
        etiqueta = (fila.get(respuesta, "") or "").strip()
        valores = [numero(fila.get(v, "")) for v in predictores]
        if etiqueta == "" or any(v is None for v in valores):
            continue
        y.append(1.0 if etiqueta == exito else 0.0)
        x.append([1.0] + valores)
        indices.append(i)
    return x, y, indices


def ajustar(x, y, maximo=MAXIMO_VUELTAS, tolerancia=TOLERANCIA):
    """IRLS. Devuelve los coeficientes, la inversa de la información y cuántas
    vueltas hicieron falta."""
    n, k = len(x), len(x[0])
    coef = [0.0] * k
    inversa = None
    vueltas = 0

    for vueltas in range(1, maximo + 1):
        eta = [math.fsum(c * v for c, v in zip(coef, fila)) for fila in x]
        mu = [logistica(e) for e in eta]
        # El peso de cada caso es μ(1−μ): los casos con probabilidad cerca de
        # 0 o de 1 casi no informan sobre dónde está la frontera.
        w = [max(m * (1 - m), 1e-10) for m in mu]
        # La variable de trabajo: la linealización de la respuesta.
        z = [eta[i] + (y[i] - mu[i]) / w[i] for i in range(n)]
        nuevo, inversa = resolver_ponderado(x, z, w)
        if nuevo is None:
            return None
        cambio = max(abs(a - b) for a, b in zip(nuevo, coef))
        coef = nuevo
        if cambio < tolerancia:
            break

    eta = [math.fsum(c * v for c, v in zip(coef, fila)) for fila in x]
    mu = [logistica(e) for e in eta]

    # La información se recalcula con los coeficientes finales, no con los de
    # la vuelta anterior: la inversa que sale del bucle corresponde a los
    # pesos de un paso antes.
    #
    # Con la tolerancia de acá —1e-10 sobre los coeficientes— las dos
    # coinciden hasta el duodécimo decimal, así que esta línea no cambia
    # ningún número. Está igual porque lo que la hace innecesaria es la
    # tolerancia, no la cuenta: con un criterio de corte más flojo la
    # diferencia aparece, y es exactamente la que separa a este proyecto de
    # `summary(glm)`, que corta por devianza y se queda con los pesos que
    # tenía guardados. Está contado en el README.
    w = [max(m * (1 - m), 1e-10) for m in mu]
    _, inversa = resolver_ponderado(x, [0.0] * n, w)

    # Devianza: −2 por la log-verosimilitud. Es el residuo de la logística.
    devianza = -2 * math.fsum(
        (y[i] * math.log(max(mu[i], 1e-300)) + (1 - y[i]) * math.log(max(1 - mu[i], 1e-300)))
        for i in range(n))
    positivos = math.fsum(y)
    base = positivos / n
    devianza_nula = -2 * (positivos * math.log(base) + (n - positivos) * math.log(1 - base)) \
        if 0 < base < 1 else 0.0
    return {"coeficientes": coef, "inversa": inversa, "vueltas": vueltas, "mu": mu,
            "devianza": devianza, "devianza_nula": devianza_nula, "n": n, "k": k}


def clasificacion(y, mu, corte=0.5):
    """La matriz de confusión al corte elegido, y el AUC.

    El AUC se calcula por el estadístico de Mann-Whitney sobre las
    probabilidades: es la proporción de pares —un positivo y un negativo— en
    los que el modelo le da más probabilidad al positivo. Los empates cuentan
    medio.
    """
    vp = fp = vn = fn = 0
    for real, p in zip(y, mu):
        pred = 1 if p >= corte else 0
        if real == 1 and pred == 1:
            vp += 1
        elif real == 0 and pred == 1:
            fp += 1
        elif real == 0 and pred == 0:
            vn += 1
        else:
            fn += 1

    positivos = [p for real, p in zip(y, mu) if real == 1]
    negativos = [p for real, p in zip(y, mu) if real == 0]
    if positivos and negativos:
        mejores = math.fsum(sum(1 for q in negativos if p > q) + 0.5 * sum(1 for q in negativos if p == q)
                            for p in positivos)
        auc = mejores / (len(positivos) * len(negativos))
    else:
        auc = None

    total = vp + fp + vn + fn
    return {
        "verdaderos_positivos": vp, "falsos_positivos": fp,
        "verdaderos_negativos": vn, "falsos_negativos": fn,
        "sensibilidad": vp / (vp + fn) if vp + fn else None,
        "especificidad": vn / (vn + fp) if vn + fp else None,
        "exactitud": (vp + vn) / total if total else None,
        # La exactitud del modelo trivial que siempre dice la clase mayoritaria.
        "exactitud_trivial": max(vp + fn, vn + fp) / total if total else None,
        "auc": auc, "corte": corte,
    }


def calcular(datos, parametros):
    respuesta = parametros["respuesta_binaria"]
    predictores = parametros["predictores_binaria"]
    if not respuesta or not predictores:
        return None

    x, y, _ = matriz(datos, respuesta, predictores, parametros["exito"])
    if len(x) <= len(predictores) + 1 or len(set(y)) < 2:
        return None

    modelo = ajustar(x, y)
    if modelo is None:
        return None

    # Si el ajuste no convergió, no hay coeficientes que informar.
    #
    # Pasa cuando los predictores **separan** las dos clases: si existe una
    # combinación de ellos que las parte sin ningún caso del lado equivocado,
    # el máximo de la verosimilitud no está en ningún punto finito. Cada
    # vuelta del IRLS agranda los coeficientes y mejora un poquito el ajuste,
    # para siempre. Lo que queda en la vuelta cincuenta no es una estimación:
    # es dónde estaba el algoritmo cuando se le acabaron las vueltas, y con
    # otra tolerancia o en otra computadora daría otra cosa.
    #
    # Escribirlo igual sería el error que este proyecto denuncia en todos los
    # otros pasos: un número plausible que no significa nada. Así que la tabla
    # de coeficientes queda vacía, y lo que se escribe es el aviso y la
    # clasificación, que es justamente la que deja ver la separación.
    convergio = modelo["vueltas"] < MAXIMO_VUELTAS
    probables = [m for m, real in zip(modelo["mu"], y) if real == 1]
    improbables = [m for m, real in zip(modelo["mu"], y) if real == 0]
    separadas = bool(probables and improbables and min(probables) > max(improbables))

    critico = float(stats.norm.ppf(1 - (1 - parametros["confianza"]) / 2))
    terminos = ["(ordenada)"] + predictores
    filas = []
    for j, nombre in enumerate(terminos if convergio else []):
        b = modelo["coeficientes"][j]
        ee = math.sqrt(modelo["inversa"][j][j])
        z = b / ee if ee > 0 else float("nan")
        filas.append({
            "termino": nombre, "estimacion": b, "error_estandar": ee, "z": z,
            "p": float(2 * stats.norm.sf(abs(z))) if ee > 0 else float("nan"),
            "odds_ratio": exponencial(b),
            "or_inferior": exponencial(b - critico * ee),
            "or_superior": exponencial(b + critico * ee),
            "significativo": (float(2 * stats.norm.sf(abs(z))) < 1 - parametros["confianza"]
                              if ee > 0 else False),
        })

    avisos = []
    if not convergio:
        avisos.append({"donde": "logística",
                       "aviso": f"El ajuste no convergió en {MAXIMO_VUELTAS} vueltas, así que "
                                f"la tabla de coeficientes queda vacía a propósito. Lo que "
                                f"había en la última vuelta no es una estimación: es dónde "
                                f"estaba el algoritmo cuando se le acabaron las vueltas."})
    if separadas:
        avisos.append({"donde": "logística",
                       "aviso": "Los predictores separan perfectamente las dos clases: no hay "
                                "un solo caso del lado equivocado. Con separación el máximo de "
                                "la verosimilitud no existe y los coeficientes se van al "
                                "infinito. La salida no es insistir con el ajuste: es juntar "
                                "más datos, sacar el predictor que separa —muchas veces es uno "
                                "que se construyó a partir de la respuesta— o usar una "
                                "logística penalizada."})
    for fila in filas:
        if fila["termino"] != "(ordenada)" and fila["odds_ratio"] > 50:
            avisos.append({"donde": "logística",
                           "aviso": f"El odds ratio de «{fila['termino']}» es enorme. Con pocos "
                                    f"casos en una de las celdas, eso es casi siempre "
                                    f"separación y no un efecto real."})

    positivos = int(math.fsum(y))
    por_variable = positivos / len(predictores) if predictores else 0
    if por_variable < 10:
        avisos.append({"donde": "logística",
                       "aviso": f"Hay {positivos} casos con el resultado de interés y "
                                f"{len(predictores)} predictores: "
                                + f"{por_variable:.1f}".replace(".", ",") +
                                " por predictor. La regla práctica pide al menos diez; con "
                                "menos, los coeficientes están sesgados y los intervalos son "
                                "demasiado angostos."})

    return {"coeficientes": filas, "modelo": modelo,
            "clasificacion": clasificacion(y, modelo["mu"]),
            "positivos": positivos, "avisos": avisos,
            "convergio": convergio, "separadas": separadas,
            "respuesta": respuesta, "exito": parametros["exito"]}

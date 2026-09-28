"""Paso 1: la regresión lineal múltiple.

Los coeficientes, sus errores estándar, sus intervalos de confianza y el
ajuste del modelo. Nada de esto es difícil; lo que suele faltar es el paso 2.

El VIF va acá y no en el diagnóstico a propósito: no es un supuesto que se
verifica después, es una propiedad de los predictores que uno eligió. Si dos
miden casi lo mismo, el modelo no está mal ajustado —está mal planteado—, y
eso se decide antes de mirar un residuo.
"""

import math

from scipy import stats

from algebra import resolver
from comun import media, numero


def matriz(datos, respuesta, predictores):
    """Las filas completas, con la columna de unos adelante para la ordenada.

    Se descarta la fila a la que le falte cualquiera de las variables del
    modelo. Es lo que hacen R y statsmodels por omisión, y conviene saber
    cuántas se fueron: el número va al resumen.
    """
    x, y, indices = [], [], []
    for i, fila in enumerate(datos):
        valores = [numero(fila.get(v, "")) for v in [respuesta] + predictores]
        if any(v is None for v in valores):
            continue
        y.append(valores[0])
        x.append([1.0] + valores[1:])
        indices.append(i)
    return x, y, indices


def vif(x, predictores):
    """Factor de inflación de la varianza: cuánto se infla el error estándar de
    cada coeficiente por culpa de la correlación con los otros predictores.

    Se calcula regresando cada predictor contra todos los demás. Un VIF de 10
    quiere decir que el error estándar es √10 ≈ 3,2 veces más grande de lo que
    sería si ese predictor fuera independiente del resto.
    """
    k = len(predictores)
    if k < 2:
        return {p: None for p in predictores}
    salida = {}
    for j in range(k):
        objetivo = [fila[j + 1] for fila in x]
        otros = [[1.0] + [fila[i + 1] for i in range(k) if i != j] for fila in x]
        coef, _ = resolver(otros, objetivo)
        if coef is None:
            salida[predictores[j]] = None
            continue
        m = media(objetivo)
        sc_total = math.fsum((v - m) ** 2 for v in objetivo)
        ajustados = [math.fsum(c * v for c, v in zip(coef, fila)) for fila in otros]
        sc_residual = math.fsum((v - a) ** 2 for v, a in zip(objetivo, ajustados))
        r2 = 1 - sc_residual / sc_total if sc_total > 0 else 0.0
        salida[predictores[j]] = float("inf") if r2 >= 1 else 1 / (1 - r2)
    return salida


def ajustar(x, y, confianza, predictores):
    """El ajuste completo. Devuelve todo lo que los pasos siguientes necesitan."""
    n, k = len(x), len(x[0])
    if n <= k:
        return None
    coef, inversa = resolver(x, y)
    if coef is None:
        return None

    ajustados = [math.fsum(c * v for c, v in zip(coef, fila)) for fila in x]
    residuos = [v - a for v, a in zip(y, ajustados)]
    gl = n - k
    sc_residual = math.fsum(r * r for r in residuos)
    varianza = sc_residual / gl
    m = media(y)
    sc_total = math.fsum((v - m) ** 2 for v in y)
    sc_modelo = sc_total - sc_residual

    r2 = 1 - sc_residual / sc_total if sc_total > 0 else 0.0
    # El R² ajustado penaliza por cada predictor agregado. El R² común nunca
    # baja al sumar variables, así que solo no sirve para elegir modelo.
    r2_ajustado = 1 - (1 - r2) * (n - 1) / gl if gl > 0 else 0.0

    critico = float(stats.t.ppf(1 - (1 - confianza) / 2, gl))
    terminos = ["(ordenada)"] + predictores
    factores = vif(x, predictores)

    filas = []
    for j, nombre in enumerate(terminos):
        ee = math.sqrt(varianza * inversa[j][j])
        t = coef[j] / ee if ee > 0 else float("nan")
        p = float(2 * stats.t.sf(abs(t), gl)) if ee > 0 else float("nan")
        filas.append({
            "termino": nombre, "estimacion": coef[j], "error_estandar": ee,
            "t": t, "gl": gl, "p": p,
            "inferior": coef[j] - critico * ee, "superior": coef[j] + critico * ee,
            "significativo": p < 1 - confianza,
            "vif": factores.get(nombre),
        })

    gl_modelo = k - 1
    f = ((sc_modelo / gl_modelo) / varianza) if gl_modelo > 0 and varianza > 0 else None
    return {
        "coeficientes": filas, "ajustados": ajustados, "residuos": residuos,
        "inversa": inversa, "n": n, "k": k, "gl": gl, "varianza": varianza,
        "sc_total": sc_total, "sc_modelo": sc_modelo, "sc_residual": sc_residual,
        "r2": r2, "r2_ajustado": r2_ajustado,
        "ee_residual": math.sqrt(varianza),
        "f": f, "gl_modelo": gl_modelo,
        "p_f": float(stats.f.sf(f, gl_modelo, gl)) if f is not None else None,
    }


def calcular(datos, parametros):
    x, y, indices = matriz(datos, parametros["respuesta"], parametros["predictores"])
    modelo = ajustar(x, y, parametros["confianza"], parametros["predictores"])
    if modelo is None:
        raise SystemExit("No hay casos completos suficientes para ajustar el modelo.")
    modelo["x"] = x
    modelo["y"] = y
    modelo["indices"] = indices
    modelo["descartados"] = len(datos) - len(indices)
    return modelo

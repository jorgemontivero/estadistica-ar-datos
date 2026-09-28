#!/usr/bin/env python
"""
Recalcula cada respuesta del banco de ejercicios por un camino independiente.

El generador usa NumPy y SciPy. Comprobar sus resultados con NumPy y SciPy no
comprueba nada: un error de la biblioteca —o del uso que se le da— pasaría por
los dos lados igual. Así que acá **no se importa ninguna de las dos**. La
normal y la t se calculan con lo que trae Python de fábrica: `math.erfc` y una
beta incompleta escrita a mano, que es el mismo criterio de
`src/lib/distribuciones.ts`.

La `autoprueba` contrasta esas implementaciones contra valores de tabla que
cualquiera puede mirar en el apéndice de un libro, no contra SciPy.

    npm run ejercicios
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BANCO = RAIZ / "datos" / "ejercicios" / "ejercicios.json"
CONCEPTOS = RAIZ / "src" / "content" / "conceptos"

comprobaciones = 0
problemas: list[str] = []

c = {
    "rojo": lambda s: f"\x1b[31m{s}\x1b[0m",
    "verde": lambda s: f"\x1b[32m{s}\x1b[0m",
    "gris": lambda s: f"\x1b[90m{s}\x1b[0m",
}


def cierto(que: str, condicion: bool) -> None:
    global comprobaciones
    comprobaciones += 1
    if not condicion:
        problemas.append(que)


def parecido(que: str, a: float, b: float, tol: float) -> None:
    global comprobaciones
    comprobaciones += 1
    if not (abs(float(a) - float(b)) <= tol):
        problemas.append(f"{que}: {a} contra {b} (tolerancia {tol})")


# ------------------------------------------------- distribuciones a mano

def norm_cdf(z: float) -> float:
    return 0.5 * math.erfc(-z / math.sqrt(2.0))


def bisecar(f, objetivo: float, lo: float, hi: float) -> float:
    for _ in range(200):
        m = (lo + hi) / 2
        if f(m) < objetivo:
            lo = m
        else:
            hi = m
    return (lo + hi) / 2


def norm_ppf(p: float) -> float:
    return bisecar(norm_cdf, p, -40.0, 40.0)


def beta_inc(x: float, a: float, b: float) -> float:
    """Beta incompleta regularizada, por fracción continua de Lentz."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    lbeta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    frente = math.exp(a * math.log(x) + b * math.log(1 - x) - lbeta)
    if x < (a + 1) / (a + b + 2):
        return frente * _fc(x, a, b) / a
    return 1.0 - frente * _fc(1 - x, b, a) / b


def _fc(x: float, a: float, b: float) -> float:
    diminuto = 1e-300
    c_, d = 1.0, 1.0 - (a + b) * x / (a + 1)
    if abs(d) < diminuto:
        d = diminuto
    d = 1 / d
    h = d
    for m in range(1, 300):
        m2 = 2 * m
        num = m * (b - m) * x / ((a + m2 - 1) * (a + m2))
        d = 1 + num * d
        c_ = 1 + num / c_
        if abs(d) < diminuto:
            d = diminuto
        if abs(c_) < diminuto:
            c_ = diminuto
        d = 1 / d
        h *= d * c_
        num = -(a + m) * (a + b + m) * x / ((a + m2) * (a + m2 + 1))
        d = 1 + num * d
        c_ = 1 + num / c_
        if abs(d) < diminuto:
            d = diminuto
        if abs(c_) < diminuto:
            c_ = diminuto
        d = 1 / d
        delta = d * c_
        h *= delta
        if abs(delta - 1) < 1e-15:
            break
    return h


def t_cdf(t: float, gl: int) -> float:
    x = gl / (gl + t * t)
    mitad = 0.5 * beta_inc(x, gl / 2, 0.5)
    return 1 - mitad if t > 0 else mitad


def t_ppf(p: float, gl: int) -> float:
    return bisecar(lambda t: t_cdf(t, gl), p, -200.0, 200.0)


def autoprueba() -> None:
    """Contra valores de tabla, no contra SciPy."""
    assert abs(norm_cdf(1.96) - 0.9750) < 1e-4, "la normal no da 0,9750 en 1,96"
    assert abs(norm_cdf(0.0) - 0.5) < 1e-12
    assert abs(norm_ppf(0.975) - 1.9600) < 1e-4
    # t de Student, tabla clásica
    assert abs(t_ppf(0.975, 10) - 2.228) < 1e-3, "t(0,975; 10) no da 2,228"
    assert abs(t_ppf(0.995, 20) - 2.845) < 1e-3, "t(0,995; 20) no da 2,845"
    assert abs(t_ppf(0.95, 1) - 6.314) < 1e-3, "t(0,95; 1) no da 6,314"
    assert abs(t_cdf(0.0, 7) - 0.5) < 1e-12


# ------------------------------------------------------- recalcular cada tema

def media(v):
    return sum(v) / len(v)


def desvio(v):
    m = media(v)
    return math.sqrt(sum((x - m) ** 2 for x in v) / (len(v) - 1))


def mediana(v):
    s = sorted(v)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def revisar_descriptivos(e, r):
    x = [float(v) for v in e["datos"]]
    cierto(f"{e['id']}: la cantidad de datos coincide con n",
           len(x) == e["parametros"]["n"])
    # El orden importa: «media» es subcadena de «mediana», así que la más
    # larga se prueba primero o la mediana se compara contra la media.
    esperado = [
        ("mediana", mediana(x)),
        ("media", media(x)),
        ("desvío", desvio(x)),
        ("rango", max(x) - min(x)),
    ]
    for p in e["preguntas"]:
        for clave, valor in esperado:
            if clave in p["texto"].lower():
                parecido(f"{e['id']} · {clave}", p["respuesta"], valor,
                         max(p["tolerancia"], 1e-4))
                break
        else:
            problemas.append(f"{e['id']}: no sé recalcular «{p['texto']}»")


def revisar_normal(e, r):
    q = e["parametros"]
    z = (q["corte"] - q["mu"]) / q["sd"]
    for p in e["preguntas"]:
        if "por debajo" in p["texto"]:
            parecido(f"{e['id']} · P(X < corte)", p["respuesta"],
                     norm_cdf(z), max(p["tolerancia"], 1e-4))
        else:
            esperado = q["mu"] + q["sd"] * norm_ppf(q["pct"] / 100)
            parecido(f"{e['id']} · percentil {q['pct']}", p["respuesta"],
                     esperado, max(p["tolerancia"], 1e-3))


def revisar_ic(e, r):
    q = e["parametros"]
    n, m, s, conf = q["n"], q["media"], q["s"], q["confianza"]
    ee = s / math.sqrt(n)
    t = t_ppf(0.5 + conf / 2, n - 1)
    margen = t * ee
    for p in e["preguntas"]:
        if "error estándar" in p["texto"]:
            parecido(f"{e['id']} · EE", p["respuesta"], ee,
                     max(p["tolerancia"], 1e-4))
        elif "inferior" in p["texto"]:
            parecido(f"{e['id']} · límite inferior", p["respuesta"],
                     m - margen, max(p["tolerancia"], 1e-3))
        else:
            parecido(f"{e['id']} · límite superior", p["respuesta"],
                     m + margen, max(p["tolerancia"], 1e-3))
    cierto(f"{e['id']}: el intervalo contiene a la media muestral",
           (m - margen) < m < (m + margen))


def revisar_t(e, r):
    q = e["parametros"]
    n, m, s, mu0 = q["n"], q["media"], q["s"], q["mu0"]
    t = (m - mu0) / (s / math.sqrt(n))
    p_val = 2 * (1 - t_cdf(abs(t), n - 1))
    for p in e["preguntas"]:
        if "estadístico t" in p["texto"]:
            parecido(f"{e['id']} · t", p["respuesta"], t,
                     max(p["tolerancia"], 1e-4))
        elif "valor p" in p["texto"]:
            parecido(f"{e['id']} · valor p", p["respuesta"], p_val,
                     max(p["tolerancia"], 1e-4))
        else:
            cierto(f"{e['id']}: la decisión coincide con el valor p",
                   p["respuesta"] == (1.0 if p_val < q["alfa"] else 0.0))


def revisar_sumatoria(e, r):
    x = [float(v) for v in e["datos"]]
    n, c = e["parametros"]["n"], e["parametros"]["c"]
    cierto(f"{e['id']}: la cantidad de datos coincide con n", len(x) == n)
    m = media(x)
    esperado = [
        ("suma de los cuadrados", sum(v * v for v in x)),
        ("cuadrado de la suma", sum(x) ** 2),
        ("constante", n * c),
        ("desvíos respecto de la media", sum(v - m for v in x)),
        ("suma de los valores", sum(x)),
    ]
    for p in e["preguntas"]:
        texto = p["texto"].lower()
        for clave, valor in esperado:
            # «suma de los cuadrados» antes que «suma de los valores»: la
            # pregunta corta entraría en la larga.
            if clave.split(" respecto")[0] in texto or (
                clave == "constante" and "constante" in texto
            ):
                parecido(f"{e['id']} · {clave}", p["respuesta"], valor,
                         max(p["tolerancia"], 1e-9))
                break
        else:
            problemas.append(f"{e['id']}: no sé recalcular «{p['texto']}»")


def significativas(v: float, c: int) -> float:
    """Redondeo a c cifras significativas, con Decimal de la estándar."""
    from decimal import Decimal, ROUND_HALF_UP

    if v == 0:
        return 0.0
    d = math.floor(math.log10(abs(v))) + 1
    return float(
        Decimal(repr(v)).quantize(
            Decimal(1).scaleb(d - c), rounding=ROUND_HALF_UP
        )
    )


def revisar_redondeo(e, r):
    q = e["parametros"]
    esperado = [
        significativas(q["valor"], q["cifras"]),
        float(q["sig_a"]),
    ]
    cierto(f"{e['id']}: hay una respuesta por cada cuenta",
           len(e["preguntas"]) == len(esperado))
    for p, valor in zip(e["preguntas"], esperado):
        parecido(f"{e['id']} · {p['texto'][:32]}", p["respuesta"], valor,
                 max(p["tolerancia"], 1e-9))
    # Las cifras significativas declaradas tienen que salir de cómo se
    # escribe el número, no de cómo lo imprime Python.
    escrito = f"{q['a']:.{q['decimales_a']}f}"
    cierto(f"{e['id']}: las cifras significativas coinciden con lo escrito",
           len(escrito.replace(".", "").lstrip("0")) == q["sig_a"])
    cierto(f"{e['id']}: el valor escrito no es ambiguo",
           not escrito.rstrip(".").endswith("0"))


def q7(x, p):
    """El método 7, que es el que declara la entrada de cuantiles."""
    n = len(x)
    h = (n - 1) * p + 1
    i = int(math.floor(h))
    f = h - i
    if i >= n:
        return float(x[-1])
    return float(x[i - 1] + f * (x[i] - x[i - 1]))


def revisar_cuantiles(e, r):
    x = sorted(float(v) for v in e["datos"])
    cierto(f"{e['id']}: los datos vienen ordenados",
           [float(v) for v in e["datos"]] == x)
    q1, q3 = q7(x, 0.25), q7(x, 0.75)
    ric = q3 - q1
    cerco = q3 + 1.5 * ric
    fuera = [v for v in x if v > cerco or v < q1 - 1.5 * ric]
    esperado = [q1, q3, ric, cerco, float(len(fuera))]
    cierto(f"{e['id']}: hay una respuesta por cada cuenta",
           len(e["preguntas"]) == len(esperado))
    for p, valor in zip(e["preguntas"], esperado):
        parecido(f"{e['id']} · {p['texto'][:30]}", p["respuesta"], valor,
                 max(p["tolerancia"], 1e-6))
    cierto(f"{e['id']}: el tercer cuartil no es menor que el primero", q3 >= q1)


def revisar_tabla(e, r):
    x = [float(v) for v in e["datos"]]
    q = e["parametros"]
    n, amp, ini = q["n"], q["amplitud"], q["inicio"]
    lo = ini + amp * q["clase_elegida"]
    hi = lo + amp
    dentro = [v for v in x if lo <= v < hi]
    esperado = [
        float(round(1 + 3.322 * math.log10(n))),
        float(len(dentro)),
        len(dentro) / n,
        float(len([v for v in x if v < hi])),
        (lo + hi) / 2,
        float(len([v for v in x if v == q["limite"]])),
    ]
    cierto(f"{e['id']}: hay una respuesta por cada cuenta",
           len(e["preguntas"]) == len(esperado))
    for p, valor in zip(e["preguntas"], esperado):
        parecido(f"{e['id']} · {p['texto'][:30]}", p["respuesta"], valor,
                 max(p["tolerancia"], 1e-6))
    # Que la tabla cierre: ningún dato fuera del rango de las clases.
    tope = ini + amp * q["clases"]
    cierto(f"{e['id']}: ningún dato queda fuera de las clases",
           all(ini <= v < tope for v in x))
    cierto(f"{e['id']}: hay valores justo en un límite interno",
           any(v == q["limite"] for v in x))
    cierto(f"{e['id']}: la cantidad de datos coincide con n", len(x) == n)


def revisar_caja(e, r):
    x = sorted(float(v) for v in e["datos"])
    q1, me_, q3 = q7(x, 0.25), q7(x, 0.50), q7(x, 0.75)
    ric = q3 - q1
    alto, bajo = q3 + 1.5 * ric, q1 - 1.5 * ric
    dentro = [v for v in x if bajo <= v <= alto]
    esperado = [q1, me_, max(dentro), float(len(x) - len(dentro))]
    cierto(f"{e['id']}: hay una respuesta por cada cuenta",
           len(e["preguntas"]) == len(esperado))
    for p, valor in zip(e["preguntas"], esperado):
        parecido(f"{e['id']} · {p['texto'][:30]}", p["respuesta"], valor,
                 max(p["tolerancia"], 1e-6))
    cierto(f"{e['id']}: el bigote no supera al máximo", max(dentro) <= max(x))
    cierto(f"{e['id']}: la caja contiene a la mediana", q1 <= me_ <= q3)


def revisar_histograma(e, r):
    q = e["parametros"]
    anchos, frec = q["anchos"], q["frecuencias"]
    a = q["ancha"]
    dens = [f / w for f, w in zip(frec, anchos)]
    esperado = [
        dens[a],
        dens[0],
        float(max(range(4), key=lambda i: frec[i]) + 1),
        float(max(range(4), key=lambda i: dens[i]) + 1),
    ]
    cierto(f"{e['id']}: hay una respuesta por cada cuenta",
           len(e["preguntas"]) == len(esperado))
    for p, valor in zip(e["preguntas"], esperado):
        parecido(f"{e['id']} · {p['texto'][:30]}", p["respuesta"], valor,
                 max(p["tolerancia"], 1e-6))
    cierto(f"{e['id']}: las frecuencias suman n", sum(frec) == q["n"])
    # El ejercicio pierde sentido si las dos lecturas coinciden.
    cierto(f"{e['id']}: la clase más frecuente no es la más densa",
           esperado[2] != esperado[3])
    cierto(f"{e['id']}: hay una clase más ancha que las otras",
           anchos.count(max(anchos)) == 1)


def revisar_ojiva(e, r):
    q = e["parametros"]
    frec, amp = q["frecuencias"], q["amplitud"]
    n = sum(frec)
    acum, s = [], 0
    for f in frec:
        s += f
        acum.append(s)
    i = next(j for j, a in enumerate(acum) if a >= n / 2)
    antes = acum[i - 1] if i else 0
    mediana = amp * i + (n / 2 - antes) / frec[i] * amp
    esperado = [float(acum[q["clase"] - 1]), mediana, float(n)]
    cierto(f"{e['id']}: hay una respuesta por cada cuenta",
           len(e["preguntas"]) == len(esperado))
    for p, valor in zip(e["preguntas"], esperado):
        parecido(f"{e['id']} · {p['texto'][:30]}", p["respuesta"], valor,
                 max(p["tolerancia"], 1e-6))
    cierto(f"{e['id']}: la acumulada no decrece",
           all(b >= a for a, b in zip(acum, acum[1:])))
    cierto(f"{e['id']}: la acumulada termina en n", acum[-1] == q["n"])


def revisar_contingencia(e, r):
    q = e["parametros"]
    tabla, i, j = q["tabla"], q["fila"], q["columna"]
    n = sum(sum(f) for f in tabla)
    tot_fila = sum(tabla[i])
    tot_col = sum(f[j] for f in tabla)
    celda = tabla[i][j]
    esperado = [
        float(tot_fila),
        celda / n * 100,
        celda / tot_fila * 100,
        celda / tot_col * 100,
    ]
    cierto(f"{e['id']}: hay una respuesta por cada cuenta",
           len(e["preguntas"]) == len(esperado))
    for p, valor in zip(e["preguntas"], esperado):
        parecido(f"{e['id']} · {p['texto'][:30]}", p["respuesta"], valor,
                 max(p["tolerancia"], 1e-6))
    cierto(f"{e['id']}: el total declarado es la suma de la tabla", n == q["n"])
    cierto(f"{e['id']}: ninguna celda es cero",
           all(c > 0 for f in tabla for c in f))


def revisar_regresion_simple(e, r):
    q = e["parametros"]
    x, y, n = q["x"], q["y"], q["n"]
    mx, my = media(x), media(y)
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y)) / (n - 1)
    sx, sy = desvio(x), desvio(y)
    rr = sxy / (sx * sy)
    b = sxy / sx ** 2
    a = my - b * mx
    esperado = [rr, rr ** 2, b, a, a + b * q["x0"]]
    cierto(f"{e['id']}: hay una respuesta por cada cuenta",
           len(e["preguntas"]) == len(esperado))
    for p, valor in zip(e["preguntas"], esperado):
        parecido(f"{e['id']} · {p['texto'][:30]}", p["respuesta"], valor,
                 max(p["tolerancia"], 1e-6))
    cierto(f"{e['id']}: la correlación está entre −1 y 1", -1 <= rr <= 1)
    cierto(f"{e['id']}: el punto a predecir está dentro del rango",
           min(x) <= q["x0"] <= max(x))


def revisar_riesgo(e, r):
    q = e["parametros"]
    a, b, c, d = q["a"], q["b"], q["c"], q["d"]
    inc_e = a / (a + b)
    inc_ne = c / (c + d)
    rr = inc_e / inc_ne
    orr = (a / b) / (c / d)
    esperado = [inc_e, rr, orr]
    cierto(f"{e['id']}: hay una respuesta por cada cuenta",
           len(e["preguntas"]) == len(esperado))
    for p, valor in zip(e["preguntas"], esperado):
        parecido(f"{e['id']} · {p['texto'][:30]}", p["respuesta"], valor,
                 max(p["tolerancia"], 1e-6))
    # Sin esto el ejercicio no enseña nada: con un evento raro los dos
    # coinciden y la confusión entre RR y OR no se nota.
    cierto(f"{e['id']}: el odds ratio se separa del riesgo relativo",
           abs(orr / rr - 1) > 0.15)
    cierto(f"{e['id']}: las cuatro celdas son positivas",
           min(a, b, c, d) > 0)


def revisar_simpson(e, r):
    q = e["parametros"]
    ta1 = q["a1"] / q["n_a1"]
    ta2 = q["a2"] / q["n_a2"]
    tb1 = q["b1"] / q["n_b1"]
    tb2 = q["b2"] / q["n_b2"]
    tot_a = (q["a1"] + q["a2"]) / (q["n_a1"] + q["n_a2"])
    tot_b = (q["b1"] + q["b2"]) / (q["n_b1"] + q["n_b2"])
    esperado = [ta1, ta2, tot_a, tot_b, 1.0]
    cierto(f"{e['id']}: hay una respuesta por cada cuenta",
           len(e["preguntas"]) == len(esperado))
    for p, valor in zip(e["preguntas"], esperado):
        parecido(f"{e['id']} · {p['texto'][:30]}", p["respuesta"], valor,
                 max(p["tolerancia"], 1e-6))
    # La paradoja tiene que ocurrir de verdad, o el ejercicio no existe.
    cierto(f"{e['id']}: A gana en el primer grupo", ta1 > tb1)
    cierto(f"{e['id']}: A gana en el segundo grupo", ta2 > tb2)
    cierto(f"{e['id']}: y sin embargo pierde en el total", tot_a < tot_b)


def revisar_variaciones(e, r):
    q = e["parametros"]
    s, mes = q["serie"], q["mes"]
    p0, p1 = q["p0"], q["p1"]
    esperado = [
        (s[mes] / s[mes - 1] - 1) * 100,
        (s[mes] / s[0] - 1) * 100,
        p1 - p0,
        (p1 / p0 - 1) * 100,
    ]
    cierto(f"{e['id']}: hay una respuesta por cada cuenta",
           len(e["preguntas"]) == len(esperado))
    for p, valor in zip(e["preguntas"], esperado):
        parecido(f"{e['id']} · {p['texto'][:30]}", p["respuesta"], valor,
                 max(p["tolerancia"], 1e-6))
    # La acumulada es el producto de las mensuales, nunca su suma. Si las dos
    # cuentas dieran lo mismo, el diagnóstico no enseñaría nada.
    prod = 1.0
    for i in range(1, mes + 1):
        prod *= s[i] / s[i - 1]
    parecido(f"{e['id']}: la acumulada es el encadenamiento de las mensuales",
             (prod - 1) * 100, esperado[1], 1e-6)
    suma = sum(s[i] / s[i - 1] - 1 for i in range(1, mes + 1)) * 100
    cierto(f"{e['id']}: sumar las mensuales da distinto que encadenarlas",
           abs(suma - esperado[1]) > 0.1)
    cierto(f"{e['id']}: la serie crece", all(b > a for a, b in zip(s, s[1:])))


def revisar_deflactacion(e, r):
    q = e["parametros"]
    x0, x1, i0, i1 = q["x0"], q["x1"], q["i0"], q["i1"]
    const = x1 * i0 / i1
    esperado = [const, (x1 / x0 - 1) * 100, (const / x0 - 1) * 100]
    cierto(f"{e['id']}: hay una respuesta por cada cuenta",
           len(e["preguntas"]) == len(esperado))
    for p, valor in zip(e["preguntas"], esperado):
        parecido(f"{e['id']} · {p['texto'][:30]}", p["respuesta"], valor,
                 max(p["tolerancia"], 1e-6))
    cierto(f"{e['id']}: los precios subieron", i1 > i0)
    cierto(f"{e['id']}: deflactar baja el valor nominal", const < x1)
    # Restar las variaciones tiene que dar visiblemente distinto, o el
    # diagnóstico sobre esa aproximación no tendría sentido.
    resta = (x1 / x0 - 1) - (i1 / i0 - 1)
    cierto(f"{e['id']}: restar las variaciones no aproxima bien",
           abs(resta * 100 - esperado[2]) > 0.5)


def revisar_indices_base(e, r):
    q = e["parametros"]
    s, bv, bn = q["serie"], q["base_vieja"], q["base_nueva"]
    iv = [v / s[bv] * 100 for v in s]
    inu = [v / s[bn] * 100 for v in s]
    k = q["valor_nuevo_sistema"] / 100
    esperado = [iv[-1], inu[-1], k]
    cierto(f"{e['id']}: hay una respuesta por cada cuenta",
           len(e["preguntas"]) == len(esperado))
    for p, valor in zip(e["preguntas"], esperado):
        parecido(f"{e['id']} · {p['texto'][:30]}", p["respuesta"], valor,
                 max(p["tolerancia"], 1e-6))
    parecido(f"{e['id']}: el índice vale 100 en su año base", iv[bv], 100.0,
             1e-9)
    parecido(f"{e['id']}: y 100 en el nuevo año base", inu[bn], 100.0, 1e-9)
    # Cambiar de base no cambia las variaciones: es la propiedad que lo
    # justifica, y conviene comprobarla.
    for i in range(1, len(s)):
        parecido(f"{e['id']}: la variación no depende de la base",
                 iv[i] / iv[i - 1], inu[i] / inu[i - 1], 1e-9)


def revisar_laspeyres(e, r):
    q = e["parametros"]
    p0, q0, p1, q1 = q["p0"], q["q0"], q["p1"], q["q1"]
    sp = lambda a, b: sum(x * y for x, y in zip(a, b))  # noqa: E731
    L = sp(p1, q0) / sp(p0, q0) * 100
    Pa = sp(p1, q1) / sp(p0, q1) * 100
    F = math.sqrt(L * Pa)
    V = sp(p1, q1) / sp(p0, q0) * 100
    esperado = [L, Pa, F, V]
    cierto(f"{e['id']}: hay una respuesta por cada cuenta",
           len(e["preguntas"]) == len(esperado))
    for p, valor in zip(e["preguntas"], esperado):
        parecido(f"{e['id']} · {p['texto'][:30]}", p["respuesta"], valor,
                 max(p["tolerancia"], 1e-6))
    cierto(f"{e['id']}: Fisher queda entre Laspeyres y Paasche",
           min(L, Pa) <= F <= max(L, Pa))
    # Con el consumo moviéndose en contra del precio, Paasche tiene que
    # quedar por debajo: si no, el ejercicio no muestra el sesgo de sustitución.
    cierto(f"{e['id']}: Paasche queda por debajo de Laspeyres", Pa < L)
    cierto(f"{e['id']}: los dos se separan lo suficiente",
           abs(L - Pa) > 1.0)


def revisar_razon(e, r):
    q = e["parametros"]
    a, b, ev = q["a"], q["b"], q["eventos"]
    tot = a + b
    esperado = [a / b, a / tot, ev / tot * 1000, ev / tot * 100000]
    cierto(f"{e['id']}: hay una respuesta por cada cuenta",
           len(e["preguntas"]) == len(esperado))
    for p, valor in zip(e["preguntas"], esperado):
        parecido(f"{e['id']} · {p['texto'][:30]}", p["respuesta"], valor,
                 max(p["tolerancia"], 1e-6))
    cierto(f"{e['id']}: la proporción está entre 0 y 1", 0 < a / tot < 1)
    # Si la razón fuera menor que 1 se confundiría con una proporción y el
    # diagnóstico no distinguiría nada.
    cierto(f"{e['id']}: la razón se distingue de la proporción",
           abs(a / b - a / tot) > 0.05)


def revisar_laborales(e, r):
    q = e["parametros"]
    tot, pea, des, salen = q["total"], q["pea"], q["desocupados"], q["salen"]
    ocu = pea - des
    esperado = [
        pea / tot * 100,
        ocu / tot * 100,
        des / pea * 100,
        (des - salen) / (pea - salen) * 100,
    ]
    cierto(f"{e['id']}: hay una respuesta por cada cuenta",
           len(e["preguntas"]) == len(esperado))
    for p, valor in zip(e["preguntas"], esperado):
        parecido(f"{e['id']} · {p['texto'][:30]}", p["respuesta"], valor,
                 max(p["tolerancia"], 1e-6))
    cierto(f"{e['id']}: el empleo no supera a la actividad",
           esperado[1] <= esperado[0])
    # El punto del ejercicio: la desocupación baja sin que nadie trabaje más.
    cierto(f"{e['id']}: la desocupación baja al salir gente de la PEA",
           esperado[3] < esperado[2])
    cierto(f"{e['id']}: y la caída se nota", esperado[2] - esperado[3] > 0.3)


def revisar_estandarizacion(e, r):
    q = e["parametros"]
    ta, tb = q["tasas_a"], q["tasas_b"]
    pa, pb = q["na_pob"], q["nb_pob"]
    ref = [(x + y) / 2 for x, y in zip(pa, pb)]
    tot = sum(ref)
    pr = [x / tot for x in ref]
    cruda_a = sum(t * n for t, n in zip(ta, pa)) / sum(pa)
    cruda_b = sum(t * n for t, n in zip(tb, pb)) / sum(pb)
    est_a = sum(t * p for t, p in zip(ta, pr))
    est_b = sum(t * p for t, p in zip(tb, pr))
    esperado = [cruda_a, est_a, est_b, 2.0]
    cierto(f"{e['id']}: hay una respuesta por cada cuenta",
           len(e["preguntas"]) == len(esperado))
    for p, valor in zip(e["preguntas"], esperado):
        parecido(f"{e['id']} · {p['texto'][:30]}", p["respuesta"], valor,
                 max(p["tolerancia"], 1e-6))
    # Sin la inversión el ejercicio no muestra nada.
    cierto(f"{e['id']}: la cruda de A sale peor", cruda_a > cruda_b)
    cierto(f"{e['id']}: la estandarizada se da vuelta", est_a < est_b)
    cierto(f"{e['id']}: B es peor en los cuatro grupos de edad",
           all(y > x for x, y in zip(ta, tb)))
    cierto(f"{e['id']}: las tasas crecen con la edad",
           all(b_ > a_ for a_, b_ in zip(ta, ta[1:])))


def revisar_gini(e, r):
    partes = e["parametros"]["partes"]
    p = [0.0] + [0.2 * (i + 1) for i in range(5)]
    q_ = [0.0]
    for x in partes:
        q_.append(q_[-1] + x / 100)
    g = 1 - sum((q_[i + 1] + q_[i]) * (p[i + 1] - p[i]) for i in range(5))
    esperado = [partes[0] + partes[1], g, partes[-1] / partes[0]]
    cierto(f"{e['id']}: hay una respuesta por cada cuenta",
           len(e["preguntas"]) == len(esperado))
    for pr, valor in zip(e["preguntas"], esperado):
        parecido(f"{e['id']} · {pr['texto'][:30]}", pr["respuesta"], valor,
                 max(pr["tolerancia"], 1e-6))
    parecido(f"{e['id']}: las participaciones suman 100",
             sum(partes), 100.0, 0.05)
    cierto(f"{e['id']}: los quintiles vienen ordenados",
           all(b_ >= a_ for a_, b_ in zip(partes, partes[1:])))
    cierto(f"{e['id']}: el Gini está entre 0 y 1", 0 < g < 1)
    parecido(f"{e['id']}: la curva de Lorenz termina en 1", q_[-1], 1.0, 1e-9)


def pascal(n: int, k: int) -> int:
    """C(n,k) por el triángulo de Pascal.

    El generador la calcula con factoriales (`math.comb`). Repetir esa
    cuenta acá no comprobaría nada: la recurrencia
    C(n,k) = C(n−1,k−1) + C(n−1,k) no usa ningún factorial y es el segundo
    camino que hace falta.
    """
    fila = [1]
    for _ in range(n):
        fila = [1] + [fila[i] + fila[i + 1] for i in range(len(fila) - 1)] + [1]
    return fila[k]


def producto(desde: int, cuantos: int) -> int:
    """desde × (desde−1) × … con `cuantos` factores."""
    total = 1
    for i in range(cuantos):
        total *= desde - i
    return total


def revisar_combinatoria(e, r):
    n = e["parametros"]["n"]
    k = e["parametros"]["r"]

    comb = pascal(n, k)
    fact_k = producto(k, k)
    var = comb * fact_k          # V = C × k!, sin pasar por n!
    perm = producto(n, n)
    rep = n ** k

    esperado = [var, comb, perm, rep]
    cierto(f"{e['id']}: hay una respuesta por cada conteo",
           len(e["preguntas"]) == len(esperado))
    for pr, valor in zip(e["preguntas"], esperado):
        parecido(f"{e['id']} · {pr['texto'][:30]}", pr["respuesta"],
                 float(valor), 0.5)

    # Identidades que tienen que cumplirse pase lo que pase.
    cierto(f"{e['id']}: C(n,k) = C(n,n−k)", pascal(n, k) == pascal(n, n - k))
    cierto(f"{e['id']}: las combinaciones de todos los tamaños suman 2^n",
           sum(pascal(n, i) for i in range(n + 1)) == 2 ** n)
    cierto(f"{e['id']}: sin orden hay menos casos que con orden", comb < var)
    cierto(f"{e['id']}: con repetición hay más casos que sin repetición",
           rep > var)
    cierto(f"{e['id']}: se piden menos puestos que personas", k < n)


def revisar_reglas(e, r):
    pa_ = e["parametros"]
    n = pa_["n"]
    ambos, solo_a, solo_b = pa_["ambos"], pa_["solo_a"], pa_["solo_b"]
    ninguno = n - ambos - solo_a - solo_b

    p_a = (ambos + solo_a) / n
    p_b = (ambos + solo_b) / n
    p_ab = ambos / n
    # La unión, contada directamente sobre las personas: no es la fórmula
    # de la suma, así que sirve para comprobarla.
    p_union = (ambos + solo_a + solo_b) / n

    esperado = [p_a, p_union, p_a * p_b, p_ab / p_b]
    cierto(f"{e['id']}: hay una respuesta por cada regla",
           len(e["preguntas"]) == len(esperado))
    for pr, valor in zip(e["preguntas"], esperado):
        parecido(f"{e['id']} · {pr['texto'][:30]}", pr["respuesta"], valor,
                 max(pr["tolerancia"], 1e-6))

    parecido(f"{e['id']}: la fórmula de la suma coincide con el conteo "
             f"directo", p_a + p_b - p_ab, p_union, 1e-9)
    parecido(f"{e['id']}: las cuatro celdas suman el total",
             ambos + solo_a + solo_b + ninguno, float(n), 1e-9)
    cierto(f"{e['id']}: nadie queda fuera de la tabla", ninguno > 0)
    cierto(f"{e['id']}: los eventos no son excluyentes, que es el punto",
           ambos > 0)
    cierto(f"{e['id']}: la condicional no coincide con la marginal, "
           f"así que hay algo que aprender",
           abs(p_ab / p_b - p_a) > 0.01)


def revisar_bayes(e, r):
    pr_ = e["parametros"]
    pa, pb = pr_["pa"], pr_["pb"]
    da, db = pr_["da"], pr_["db"]

    total = pa * da + pb * db
    # Las posteriores por la forma de momios: momio posterior = momio
    # previo × razón de verosimilitudes. No pasa por la probabilidad total,
    # así que es un camino distinto al del generador.
    momio = (pb / pa) * (db / da)
    post_b = momio / (1 + momio)
    post_a = 1 / (1 + momio)

    esperado = [total, post_b, post_a]
    cierto(f"{e['id']}: hay una respuesta por cada paso",
           len(e["preguntas"]) == len(esperado))
    for prg, valor in zip(e["preguntas"], esperado):
        parecido(f"{e['id']} · {prg['texto'][:30]}", prg["respuesta"], valor,
                 max(prg["tolerancia"], 1e-6))

    parecido(f"{e['id']}: las previas suman 1", pa + pb, 1.0, 1e-9)
    parecido(f"{e['id']}: las posteriores suman 1", post_a + post_b, 1.0, 1e-9)
    cierto(f"{e['id']}: la probabilidad total queda entre las dos tasas",
           min(da, db) < total < max(da, db))
    cierto(f"{e['id']}: la máquina peor sube su participación al conocerse "
           f"la falla", post_b > pb)
    # Si el promedio sin pesar diera lo mismo, el diagnóstico no enseñaría
    # nada. Se impone al generar; acá solo se confirma.
    cierto(f"{e['id']}: promediar sin pesar da distinto",
           abs((da + db) / 2 - total) > 0.005)


def revisar_intuicion(e, r):
    pr_ = e["parametros"]
    n = pr_["n_pers"]
    p_una, p_otra = pr_["p_una"], pr_["p_otra"]

    # El generador multiplica los 365−i/365 uno a uno. Acá se suman
    # logaritmos y se exponencia: mismo número, distinta aritmética.
    log_distintos = sum(math.log((365 - i) / 365) for i in range(n))
    coincide = 1 - math.exp(log_distintos)

    esperado = [coincide, 0.5, p_una * p_otra]
    cierto(f"{e['id']}: hay una respuesta por cada pregunta",
           len(e["preguntas"]) == len(esperado))
    for prg, valor in zip(e["preguntas"], esperado):
        parecido(f"{e['id']} · {prg['texto'][:30]}", prg["respuesta"], valor,
                 max(prg["tolerancia"], 1e-6))

    cierto(f"{e['id']}: la conjunción no supera a ninguna de sus partes",
           p_una * p_otra < min(p_una, p_otra))
    cierto(f"{e['id']}: la coincidencia de cumpleaños sorprende, que es el "
           f"motivo del ejercicio", coincide > 0.3)
    cierto(f"{e['id']}: la moneda no tiene memoria: la respuesta está "
           f"declarada constante", e["preguntas"][1].get("constante") is True)


REVISORES = {
    "sumatoria": revisar_sumatoria,
    "redondeo": revisar_redondeo,
    "descriptivos": revisar_descriptivos,
    "cuantiles": revisar_cuantiles,
    "tabla-frecuencias": revisar_tabla,
    "diagrama-de-caja": revisar_caja,
    "histograma": revisar_histograma,
    "ojiva": revisar_ojiva,
    "tabla-de-contingencia": revisar_contingencia,
    "correlacion-y-recta": revisar_regresion_simple,
    "riesgo-y-odds": revisar_riesgo,
    "paradoja-de-simpson": revisar_simpson,
    "variaciones": revisar_variaciones,
    "deflactacion": revisar_deflactacion,
    "indices-y-base": revisar_indices_base,
    "laspeyres-paasche": revisar_laspeyres,
    "razon-proporcion-tasa": revisar_razon,
    "tasas-laborales": revisar_laborales,
    "estandarizacion": revisar_estandarizacion,
    "gini": revisar_gini,
    "combinatoria": revisar_combinatoria,
    "reglas-de-probabilidad": revisar_reglas,
    "bayes": revisar_bayes,
    "probabilidad-contraintuitiva": revisar_intuicion,
    "normal": revisar_normal,
    "ic-media": revisar_ic,
    "prueba-t": revisar_t,
}


def revisar_ejercicio_eph() -> None:
    """Recalcula desde el CSV **publicado**, no desde los microdatos.

    Es la comprobación que importa: que las respuestas que se publican
    correspondan al archivo que la gente se baja, y no a otro que quedó en la
    máquina de quien lo generó.
    """
    import csv
    import hashlib

    ficha_p = RAIZ / "datos" / "ejercicios" / "ejercicio-eph.json"
    if not ficha_p.exists():
        return
    ficha = json.loads(ficha_p.read_text(encoding="utf-8"))
    csv_p = RAIZ / "public" / ficha["archivo"].lstrip("/")

    cierto("eph: el archivo que se ofrece existe", csv_p.exists())
    if not csv_p.exists():
        return

    sha = hashlib.sha256(csv_p.read_bytes()).hexdigest()
    cierto("eph: el sha256 publicado es el del archivo", sha == ficha["sha256"])

    with csv_p.open(encoding="utf-8", newline="") as f:
        filas = list(csv.DictReader(f, delimiter=ficha["separador"]))

    cierto("eph: la cantidad de filas coincide con la publicada",
           len(filas) == ficha["filas"])
    cierto("eph: están todas las columnas declaradas",
           set(ficha["columnas"]) <= set(filas[0].keys()))

    def col(nombre):
        return [float(r[nombre]) for r in filas]

    edad = col("CH06")
    estado = col("ESTADO")
    p21 = col("P21")
    pondera = col("PONDERA")
    pondiio = col("PONDIIO")

    ocup = [i for i, e in enumerate(estado) if e == 1]
    coning = [i for i in ocup if p21[i] > 0]

    esperado = {
        "filas": float(len(filas)),
        "edad": sum(max(e, 0) for e in edad) / len(edad),
        "ingreso": sum(p21[i] for i in coning) / len(coning),
        "mediana": mediana([p21[i] for i in coning]),
        "ponderado": (sum(p21[i] * pondiio[i] for i in coning)
                      / sum(pondiio[i] for i in coning)),
        "poblacion": sum(pondera),
    }

    # Un bloque de cuentas esperadas por ejercicio, en el orden de sus
    # preguntas. Si el generador agrega una y acá no, la cantidad no coincide
    # y salta.
    edad_cruda = col("CH06")
    edad = [max(v, 0) for v in edad_cruda]
    ing = sorted(p21[i] for i in coning)
    q1, me_, q3 = (q7(ing, 0.25), q7(ing, 0.50), q7(ing, 0.75))
    ric = q3 - q1
    cerco = q3 + 1.5 * ric
    pesos = [pondiio[i] for i in coning]
    orden = sorted(range(len(coning)), key=lambda j: p21[coning[j]])
    total = sum(pesos)
    acu = 0.0
    me_pond = None
    for j in orden:
        acu += pesos[j]
        if acu / total >= 0.5:
            me_pond = p21[coning[j]]
            break
    n = len(filas)
    dentro20 = sum(1 for v in edad if 20 <= v < 30)

    esperado = {
        "eph-descriptivos-01": [
            float(n),
            sum(edad) / n,
            sum(p21[i] for i in coning) / len(coning),
            mediana([p21[i] for i in coning]),
            (sum(p21[i] * pondiio[i] for i in coning)
             / sum(pondiio[i] for i in coning)),
            sum(pondera),
        ],
        "eph-cuantiles": [
            q1, q3, q3, float(sum(1 for v in ing if v > cerco)), me_pond,
        ],
        "eph-tabla": [
            float(round(1 + 3.322 * math.log10(n))),
            float(dentro20),
            dentro20 / n,
            float(sum(1 for v in edad if v < 30)),
            float(sum(1 for v in edad_cruda if v == -1)),
        ],
    }

    cierto("eph: están los tres ejercicios",
           {e["id"] for e in ficha["ejercicios"]} == set(esperado))

    for ej in ficha["ejercicios"]:
        vals = esperado[ej["id"]]
        cierto(f"{ej['id']}: hay una respuesta por cada cuenta esperada",
               len(ej["preguntas"]) == len(vals))
        cierto(f"{ej['id']}: el concepto que declara existe",
               ej["concepto"] in {p.stem for p in CONCEPTOS.glob("*.mdx")
                                  if not p.name.startswith("_")})
        for p, valor in zip(ej["preguntas"], vals):
            parecido(f"{ej['id']} · {p['texto'][:34]}", p["respuesta"], valor,
                     max(p["tolerancia"], 1e-6))
            cierto(f"{ej['id']} · {p['texto'][:24]}: trae solución",
                   len(p["solucion"]) > 30)
            dg = p["diagnosticos"]
            cierto(f"{ej['id']}: no hay dos diagnósticos con el mismo valor",
                   len({d["valor"] for d in dg}) == len(dg))
            for d in dg:
                cierto(
                    f"{ej['id']}: el diagnóstico {d['valor']} se distingue "
                    f"de la respuesta",
                    abs(d["valor"] - p["respuesta"])
                    > max(p["tolerancia"], 1e-9),
                )
                cierto(f"{ej['id']}: el diagnóstico explica el motivo",
                       len(d["motivo"]) > 30)


def revisar_fundamentos() -> None:
    """Los de opción: no se recalculan, pero hay bastante que exigirles."""
    import csv
    from collections import Counter

    ficha_p = RAIZ / "datos" / "ejercicios" / "fundamentos.json"
    if not ficha_p.exists():
        return
    f = json.loads(ficha_p.read_text(encoding="utf-8"))
    conceptos = {p.stem for p in CONCEPTOS.glob("*.mdx")
                 if not p.name.startswith("_")}

    csv_p = RAIZ / "public" / f["archivo"].lstrip("/")
    with csv_p.open(encoding="utf-8", newline="") as fh:
        filas = list(csv.DictReader(fh, delimiter=";"))
    cierto("fundamentos: la cantidad de filas coincide", len(filas) == f["filas"])

    # --- clasificar las columnas -------------------------------------------
    for q in f["ejercicio"]["preguntas"]:
        col = q["columna"]
        cierto(f"fundamentos/{col}: la columna existe en el archivo",
               col in filas[0])
        if col not in filas[0]:
            continue
        valores = [r[col] for r in filas]

        cierto(f"fundamentos/{col}: la respuesta está entre las opciones",
               q["respuesta"] in q["opciones"])
        cierto(f"fundamentos/{col}: no hay opciones repetidas",
               len(set(q["opciones"])) == len(q["opciones"]))
        cierto(f"fundamentos/{col}: la cantidad de valores distintos coincide",
               len(set(valores)) == q["distintos"])
        cierto(f"fundamentos/{col}: la condición de enteros coincide",
               all(v.lstrip("-").isdigit() for v in valores) == q["enteros"])

        if q["codigos_declarados"]:
            cierto(f"fundamentos/{col}: los códigos declarados son los del "
                   f"archivo",
                   q["codigos_declarados"] == sorted(set(valores)))

        # Lo que el archivo sí puede contradecir.
        if q["respuesta"].startswith("Cuantitativa"):
            cierto(f"fundamentos/{col}: una cuantitativa es numérica",
                   all(_numerico(v) for v in valores))
        if q["respuesta"].startswith("Cualitativa"):
            cierto(f"fundamentos/{col}: una cualitativa no tiene cientos de "
                   f"categorías", len(set(valores)) <= 30)
        cierto(f"fundamentos/{col}: la justificación es sustantiva",
               len(q["solucion"]) > 60)

    # --- las preguntas de teoría -------------------------------------------
    posiciones = []
    for q in f["teoria"]["preguntas"]:
        i = q["id"]
        cierto(f"{i}: el concepto que declara existe", q["concepto"] in conceptos)
        cierto(f"{i}: la respuesta está entre las opciones",
               q["respuesta"] in q["opciones"])
        cierto(f"{i}: hay al menos tres opciones", len(q["opciones"]) >= 3)
        cierto(f"{i}: no hay opciones repetidas",
               len(set(q["opciones"])) == len(q["opciones"]))
        cierto(f"{i}: la justificación es sustantiva", len(q["solucion"]) > 60)
        cierto(f"{i}: hay al menos un distractor explicado",
               len(q["por_que_no"]) >= 1)
        for d in q["por_que_no"]:
            cierto(f"{i}: el distractor está entre las opciones",
                   d["opcion"] in q["opciones"])
            cierto(f"{i}: el distractor no es la respuesta correcta",
                   d["opcion"] != q["respuesta"])
            cierto(f"{i}: el distractor explica por qué no",
                   len(d["motivo"]) > 30)
        posiciones.append(q["opciones"].index(q["respuesta"]))

    # Si la correcta cayera siempre en el mismo lugar, se contestaría sin leer.
    cierto("teoría: la respuesta correcta no está siempre en la misma posición",
           len(set(posiciones)) > 1)
    mas_comun = Counter(posiciones).most_common(1)[0][1]
    cierto("teoría: ninguna posición concentra más de la mitad de las "
           "respuestas", mas_comun <= len(posiciones) / 2 + 1)


def _numerico(v: str) -> bool:
    try:
        float(v)
        return True
    except ValueError:
        return False


def revisar_graficos() -> None:
    """Los de opción sobre gráficos.

    La respuesta es una categoría, pero los **datos** de cada gráfico sí se
    pueden contradecir: una ojiva que baje, una caja con el primer cuartil
    por encima del tercero o un histograma con un límite de más no son
    gráficos de ese tipo, por más que lo digan.
    """
    from collections import Counter

    ficha_p = RAIZ / "datos" / "ejercicios" / "graficos.json"
    if not ficha_p.exists():
        return
    f = json.loads(ficha_p.read_text(encoding="utf-8"))
    conceptos = {p.stem for p in CONCEPTOS.glob("*.mdx")
                 if not p.name.startswith("_")}
    cierto("gráficos: el concepto que declara existe",
           f["concepto"] in conceptos)

    posiciones = []
    for q in f["identificar"]["preguntas"] + f["elegir"]["preguntas"]:
        i = q["id"]
        cierto(f"{i}: la respuesta está entre las opciones",
               q["respuesta"] in q["opciones"])
        cierto(f"{i}: no hay opciones repetidas",
               len(set(q["opciones"])) == len(q["opciones"]))
        cierto(f"{i}: hay al menos cuatro opciones", len(q["opciones"]) >= 4)
        cierto(f"{i}: la justificación es sustantiva", len(q["solucion"]) > 60)
        cierto(f"{i}: hay al menos un distractor explicado",
               len(q["por_que_no"]) >= 1)
        for d in q["por_que_no"]:
            cierto(f"{i}: el distractor está entre las opciones",
                   d["opcion"] in q["opciones"])
            cierto(f"{i}: el distractor no es la respuesta",
                   d["opcion"] != q["respuesta"])
            cierto(f"{i}: el distractor explica por qué no",
                   len(d["motivo"]) > 30)
        posiciones.append(q["opciones"].index(q["respuesta"]))

    # Los datos, contra el tipo que declaran.
    for q in f["identificar"]["preguntas"]:
        g = q["grafico"]
        i, tipo = q["id"], g["tipo"]
        if tipo in ("barras",):
            cierto(f"{i}: hay una etiqueta por valor",
                   len(g["etiquetas"]) == len(g["valores"]))
        if tipo == "histograma":
            cierto(f"{i}: hay un límite más que clases",
                   len(g["limites"]) == len(g["valores"]) + 1)
            cierto(f"{i}: los límites crecen",
                   all(b > a for a, b in zip(g["limites"], g["limites"][1:])))
        if tipo == "sectores":
            cierto(f"{i}: hay una etiqueta por sector",
                   len(g["etiquetas"]) == len(g["valores"]))
            cierto(f"{i}: los sectores son pocos", len(g["valores"]) <= 6)
            cierto(f"{i}: todos los sectores son positivos",
                   all(v > 0 for v in g["valores"]))
        if tipo == "ojiva":
            cierto(f"{i}: la acumulada no decrece",
                   all(b >= a for a, b in zip(g["acumuladas"],
                                              g["acumuladas"][1:])))
            cierto(f"{i}: hay un límite más que acumuladas",
                   len(g["limites"]) == len(g["acumuladas"]) + 1)
        if tipo == "dispersion":
            cierto(f"{i}: cada punto tiene dos coordenadas",
                   all(len(p) == 2 for p in g["puntos"]))
            cierto(f"{i}: hay suficientes puntos", len(g["puntos"]) >= 10)
        if tipo == "lineas":
            cierto(f"{i}: hay una etiqueta por punto",
                   len(g["etiquetas"]) == len(g["valores"]))
        if tipo == "caja":
            for gr in g["grupos"]:
                cierto(f"{i}/{gr['nombre']}: los cinco números están en orden",
                       gr["min"] <= gr["q1"] <= gr["me"] <= gr["q3"]
                       <= gr["max"])
                cierto(f"{i}/{gr['nombre']}: los atípicos quedan fuera de la "
                       f"caja",
                       all(a > gr["max"] or a < gr["min"]
                           for a in gr["atipicos"]))

    cierto("gráficos: la respuesta correcta no está siempre en el mismo lugar",
           len(set(posiciones)) > 1)
    mas = Counter(posiciones).most_common(1)[0][1]
    cierto("gráficos: ninguna posición concentra más de la mitad",
           mas <= len(posiciones) / 2 + 1)


def autoprueba_probabilidad() -> None:
    """Contra valores que están en cualquier manual, no contra el generador."""
    assert pascal(5, 2) == 10, "Pascal no da C(5,2) = 10"
    assert pascal(52, 5) == 2598960, "manos de póker: C(52,5) = 2.598.960"
    assert producto(5, 5) == 120, "5! = 120"
    assert producto(10, 3) == 720, "V(10,3) = 720"
    # El caso de manual: con 23 personas la probabilidad pasa de 0,5.
    lg = sum(math.log((365 - i) / 365) for i in range(23))
    assert abs((1 - math.exp(lg)) - 0.507297) < 1e-6, "cumpleaños con n = 23"
    # Bayes por momios contra el ejemplo clásico de la prueba diagnóstica:
    # prevalencia 1 %, sensibilidad 99 %, especificidad 95 % → VPP ≈ 0,1667.
    momio = (0.01 / 0.99) * (0.99 / 0.05)
    assert abs(momio / (1 + momio) - 0.166666) < 1e-5, "VPP del caso clásico"


def main() -> None:
    autoprueba()
    autoprueba_probabilidad()

    if not BANCO.exists():
        print(c["rojo"]("No hay banco. Corré primero el generador."))
        sys.exit(1)

    banco = json.loads(BANCO.read_text(encoding="utf-8"))
    ejercicios = banco["ejercicios"]
    conceptos = {p.stem for p in CONCEPTOS.glob("*.mdx")
                 if not p.name.startswith("_")}

    vistos = set()
    for e in ejercicios:
        cierto(f"{e['id']}: el id no se repite", e["id"] not in vistos)
        vistos.add(e["id"])
        cierto(f"{e['id']}: enlaza a un concepto que existe",
               e["concepto"] in conceptos)
        cierto(f"{e['id']}: tiene enunciado", len(e["enunciado"]) > 20)
        cierto(f"{e['id']}: tiene preguntas", len(e["preguntas"]) >= 1)
        for i, p in enumerate(e["preguntas"], 1):
            cierto(f"{e['id']} · pregunta {i}: la respuesta es finita",
                   math.isfinite(float(p["respuesta"])))
            cierto(f"{e['id']} · pregunta {i}: trae solución",
                   len(p["solucion"]) > 20)
            cierto(f"{e['id']} · pregunta {i}: la solución usa coma decimal",
                   not decimal_ingles(p["solucion"] + " " + p["texto"]))
            cierto(f"{e['id']} · pregunta {i}: declara tolerancia",
                   "tolerancia" in p)
            dg = p.get("diagnosticos", [])
            cierto(f"{e['id']} · pregunta {i}: no hay dos diagnósticos con "
                   f"el mismo valor",
                   len({d["valor"] for d in dg}) == len(dg))
            for d in dg:
                cierto(f"{e['id']} · pregunta {i}: el diagnóstico "
                       f"{d['valor']} se distingue de la respuesta",
                       abs(d["valor"] - p["respuesta"])
                       > max(p["tolerancia"], 1e-9))
        REVISORES[e["tema"]](e, None)

    revisar_ejercicio_eph()
    revisar_fundamentos()
    revisar_graficos()

    # Una pregunta cuya respuesta es la misma en los doce ejercicios de su
    # familia se contesta sin entender nada. Pasó con el histograma: la
    # clase que «parece» más alta era siempre la cuarta.
    from collections import defaultdict
    por_familia = defaultdict(list)
    for e in ejercicios:
        por_familia[e["tema"]].append(e)
    for tema, lista in por_familia.items():
        if len(lista) < 4:
            continue
        cuantas = len(lista[0]["preguntas"])
        for j in range(cuantas):
            if any(e["preguntas"][j].get("constante")
                   for e in lista if len(e["preguntas"]) > j):
                continue  # da lo mismo siempre, y está declarado
            valores = {e["preguntas"][j]["respuesta"] for e in lista
                       if len(e["preguntas"]) > j}
            cierto(
                f"{tema}: la pregunta {j + 1} no tiene siempre la misma "
                f"respuesta",
                len(valores) > 1,
            )

    # Que la mitad de las pruebas t no rechace: si todas rechazaran, se
    # podría contestar sin mirar los datos.
    decisiones = [
        p["respuesta"]
        for e in ejercicios if e["tema"] == "prueba-t"
        for p in e["preguntas"] if "rechaza" in p["texto"]
    ]
    cierto("prueba-t: hay ejercicios que rechazan y otros que no",
           0 < sum(decisiones) < len(decisiones))

    print(f"\n  {len(ejercicios)} ejercicios · "
          f"{sum(len(e['preguntas']) for e in ejercicios)} preguntas · "
          f"{comprobaciones} comprobaciones\n")

    if problemas:
        print(c["rojo"](f"  ✗  {len(problemas)} fallan\n"))
        for p in problemas[:25]:
            print(f"     {p}")
        sys.exit(1)

    print(c["verde"]("  ●") + "  todas las respuestas se recalculan igual "
          "sin NumPy ni SciPy\n")


def decimal_ingles(texto: str) -> list[str]:
    """Punto usado como coma decimal.

    En castellano el punto solo separa miles, así que siempre lo siguen
    exactamente tres cifras: «1.442,5455» está bien y «25.0» no.
    """
    import re
    return re.findall(r"\d\.\d{1,2}(?!\d)|\d\.\d{4,}", texto)


if __name__ == "__main__":
    main()

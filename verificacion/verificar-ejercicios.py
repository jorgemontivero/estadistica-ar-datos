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


REVISORES = {
    "descriptivos": revisar_descriptivos,
    "normal": revisar_normal,
    "ic-media": revisar_ic,
    "prueba-t": revisar_t,
}


def main() -> None:
    autoprueba()

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
        REVISORES[e["tema"]](e, None)

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

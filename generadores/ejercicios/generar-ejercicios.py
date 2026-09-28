#!/usr/bin/env python
"""
Banco de ejercicios con respuesta calculada y verificable.

La regla del sitio —ningún número sin recalcular— vale también para las
respuestas. Un ejercicio escrito a mano tiene una solución que nadie comprueba
y que envejece; uno generado acá tiene:

  · **semilla fija**, así que el enunciado y los datos son siempre los mismos;
  · **respuesta calculada** de los datos, no tipeada;
  · **solución paso a paso** armada con los valores intermedios reales;
  · y una **tolerancia** declarada, para que corregir no sea una discusión.

`scripts/verificar-ejercicios.py` recalcula cada respuesta por un camino
distinto —sólo con la biblioteca estándar— y falla si no coincide. Si el
número lo produjo scipy, no tiene sentido comprobarlo con scipy.

Salida: datos/ejercicios/<tema>.json

    python datos/ejercicios/generar-ejercicios.py
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from scipy import stats

SALIDA = Path(__file__).resolve().parent
SEMILLA = 6000
POR_FAMILIA = 12


def num(x: float, d: int = 4) -> str:
    """Formatea como escribe el sitio: coma decimal y punto de miles."""
    s = f"{float(x):,.{d}f}"
    return s.replace(",", "@").replace(".", ",").replace("@", ".")


def redondear(x: float, d: int = 4) -> float:
    """Los JSON guardan el valor con precisión suficiente y sin ruido binario."""
    return float(round(float(x), d))


# --------------------------------------------------------------- contextos
# Los enunciados tienen que sonar a un problema argentino y no a un manual
# traducido: es el mismo criterio que el resto del sitio.

CONTEXTOS_DESC = [
    ("los minutos que tardó el colectivo en llegar a la parada, en {n} días",
     "minutos", 8, 26, 0),
    ("las consultas atendidas por guardia en un centro de salud, en {n} turnos",
     "consultas", 12, 48, 0),
    ("los gastos en transporte de {n} hogares, en miles de pesos",
     "miles de pesos", 20, 90, 0),
    ("las superficies sembradas de {n} lotes, en hectáreas",
     "hectáreas", 30, 140, 0),
]

CONTEXTOS_NORMAL = [
    ("el peso al nacer en una maternidad", "gramos", 3200, 480),
    ("el rendimiento de un lote de trigo", "quintales por hectárea", 38, 6),
    ("el tiempo de atención en una ventanilla", "minutos", 9.5, 2.4),
    ("la temperatura máxima diaria de enero en Catamarca", "°C", 34.0, 3.1),
]

CONTEXTOS_IC = [
    ("el gasto mensual en servicios de los hogares de un barrio",
     "pesos", 42000, 9000),
    ("la cantidad de días de internación tras una cirugía", "días", 5.4, 1.8),
    ("el peso de bolsas que salen de una envasadora", "kilos", 25.0, 0.6),
]

CONTEXTOS_T = [
    ("una envasadora que dice llenar bolsas de {mu0} kilos", "kilos", 25.0, 0.55),
    ("un proveedor que promete entregas en {mu0} días", "días", 7.0, 1.4),
    ("un proceso calibrado en {mu0} milímetros", "milímetros", 120.0, 0.9),
]


# --------------------------------------------------------------- familias

def familia_descriptivos(rng) -> list[dict]:
    """Media, mediana y desvío sobre datos chicos: todo exacto."""
    ejercicios = []
    for k in range(POR_FAMILIA):
        plantilla, unidad, lo, hi, dec = CONTEXTOS_DESC[k % len(CONTEXTOS_DESC)]
        n = int(rng.integers(7, 12))
        x = np.sort(rng.integers(lo, hi + 1, n)).astype(float)

        media = x.mean()
        mediana = float(np.median(x))
        s = float(x.std(ddof=1))
        rango = float(x.max() - x.min())

        ordenados = ", ".join(f"{int(v)}" for v in x)
        ejercicios.append({
            "id": f"descriptivos-{k + 1:02d}",
            "tema": "descriptivos",
            "concepto": "media-aritmetica",
            "nivel": 1,
            "titulo": "Resumir una variable",
            "enunciado": (
                f"Se registraron {plantilla.format(n=n)}. Los valores, ya "
                f"ordenados, son:"
            ),
            "datos": [int(v) for v in x],
            "unidad": unidad,
            "parametros": {"n": n},
            "preguntas": [
                {
                    "texto": "¿Cuál es la media?",
                    "respuesta": redondear(media, 4),
                    "tolerancia": 0.01,
                    "solucion": (
                        f"La suma de los {n} valores es {int(x.sum())}. "
                        f"Dividida por {n} da {num(media, 4)}."
                    ),
                },
                {
                    "texto": "¿Cuál es la mediana?",
                    "respuesta": redondear(mediana, 4),
                    "tolerancia": 0.01,
                    "solucion": (
                        f"Con {n} valores ordenados, la mediana es "
                        + (
                            f"el del medio, el que ocupa la posición "
                            f"{(n + 1) // 2}: {num(mediana, 4)}."
                            if n % 2
                            else f"el promedio de los dos del medio, "
                                 f"posiciones {n // 2} y {n // 2 + 1}: "
                                 f"{num(mediana, 4)}."
                        )
                    ),
                },
                {
                    "texto": "¿Cuál es el desvío estándar muestral?",
                    "respuesta": redondear(s, 4),
                    "tolerancia": 0.01,
                    "solucion": (
                        f"La suma de los cuadrados de los desvíos respecto de "
                        f"{num(media, 4)} es {num(float(((x - media) ** 2).sum()), 4)}. "
                        f"Dividida por n − 1 = {n - 1} da una varianza de "
                        f"{num(s ** 2, 4)}, y su raíz es {num(s, 4)}."
                    ),
                },
                {
                    "texto": "¿Cuál es el rango?",
                    "respuesta": redondear(rango, 4),
                    "tolerancia": 0.001,
                    "solucion": (
                        f"El máximo es {int(x.max())} y el mínimo "
                        f"{int(x.min())}: su diferencia es {num(rango, 0)}."
                    ),
                },
            ],
        })
    return ejercicios


def familia_normal(rng) -> list[dict]:
    """Probabilidades y percentiles con la normal."""
    ejercicios = []
    for k in range(POR_FAMILIA):
        desc, unidad, mu, sd = CONTEXTOS_NORMAL[k % len(CONTEXTOS_NORMAL)]
        mu = float(mu * (1 + rng.uniform(-0.04, 0.04)))
        sd = float(sd * (1 + rng.uniform(-0.10, 0.10)))
        mu, sd = round(mu, 1), round(sd, 2)

        corte = round(mu + sd * float(rng.uniform(-1.6, 1.6)), 1)
        z = (corte - mu) / sd
        p_menor = float(stats.norm.cdf(z))
        pct = int(rng.choice([5, 10, 25, 75, 90, 95]))
        valor_pct = mu + sd * float(stats.norm.ppf(pct / 100))

        ejercicios.append({
            "id": f"normal-{k + 1:02d}",
            "tema": "normal",
            "concepto": "distribucion-normal",
            "nivel": 2,
            "titulo": "Probabilidades con la normal",
            "enunciado": (
                f"Se acepta que {desc} sigue una distribución normal con media "
                f"{num(mu, 1)} y desvío estándar {num(sd, 2)} {unidad}."
            ),
            "datos": [],
            "unidad": unidad,
            "parametros": {"mu": mu, "sd": sd, "corte": corte, "pct": pct},
            "preguntas": [
                {
                    "texto": (
                        f"¿Qué proporción de los casos está por debajo de "
                        f"{num(corte, 1)} {unidad}?"
                    ),
                    "respuesta": redondear(p_menor, 6),
                    "tolerancia": 0.002,
                    "solucion": (
                        f"Se tipifica: z = ({num(corte, 1)} − {num(mu, 1)}) / {num(sd, 2)} = "
                        f"{num(z, 4)}. La tabla de la normal da "
                        f"Φ({num(z, 2)}) = {num(p_menor, 4)}."
                    ),
                },
                {
                    "texto": (
                        f"¿Por encima de qué valor está el "
                        f"{100 - pct} % de los casos?"
                    ),
                    "respuesta": redondear(valor_pct, 4),
                    "tolerancia": 0.05,
                    "solucion": (
                        f"Es el percentil {pct}. El z que deja {num(pct / 100, 2)} "
                        f"a la izquierda es {num(stats.norm.ppf(pct / 100), 4)}, y "
                        f"el valor es {num(mu, 1)} + {num(stats.norm.ppf(pct / 100), 4)} × "
                        f"{num(sd, 2)} = {num(valor_pct, 4)}."
                    ),
                },
            ],
        })
    return ejercicios


def familia_ic(rng) -> list[dict]:
    """Intervalo de confianza para la media, con sigma desconocido."""
    ejercicios = []
    for k in range(POR_FAMILIA):
        desc, unidad, mu, sd = CONTEXTOS_IC[k % len(CONTEXTOS_IC)]
        n = int(rng.integers(12, 41))
        x = rng.normal(mu, sd, n)
        dec = 0 if unidad == "pesos" else 2
        # Se redondea a lo que va a ver quien resuelve, y recién después se
        # calcula: si no, la respuesta no se puede alcanzar con el enunciado.
        media = round(float(x.mean()), dec)
        s = round(float(x.std(ddof=1)), dec)
        conf = float(rng.choice([0.90, 0.95, 0.99]))
        gl = n - 1
        t = float(stats.t.ppf(0.5 + conf / 2, gl))
        ee = s / math.sqrt(n)
        margen = t * ee

        ejercicios.append({
            "id": f"ic-media-{k + 1:02d}",
            "tema": "ic-media",
            "concepto": "ic-para-la-media",
            "nivel": 2,
            "titulo": "Intervalo de confianza para la media",
            "enunciado": (
                f"Para estimar {desc} se tomó una muestra de {n} casos: la media "
                f"fue de {num(media, dec)} y el desvío estándar muestral "
                f"{num(s, dec)} {unidad}. El desvío poblacional es desconocido."
            ),
            "datos": [],
            "unidad": unidad,
            "parametros": {
                "n": n, "media": redondear(media, 4),
                "s": redondear(s, 4), "confianza": conf,
            },
            "preguntas": [
                {
                    "texto": "¿Cuál es el error estándar de la media?",
                    "respuesta": redondear(ee, 6),
                    "tolerancia": 0.01,
                    "solucion": (
                        f"EE = s / √n = {num(s, 4)} / √{n} = {num(ee, 4)}."
                    ),
                },
                {
                    "texto": (
                        f"¿Cuál es el límite inferior del intervalo al "
                        f"{num(conf * 100, 0)} %?"
                    ),
                    "respuesta": redondear(media - margen, 4),
                    "tolerancia": 0.05,
                    "solucion": (
                        f"Con {gl} grados de libertad, el t crítico es "
                        f"{num(t, 4)}. El margen es {num(t, 4)} × {num(ee, 4)} = "
                        f"{num(margen, 4)}, y el límite inferior "
                        f"{num(media, 4)} − {num(margen, 4)} = {num(media - margen, 4)}."
                    ),
                },
                {
                    "texto": "¿Y el límite superior?",
                    "respuesta": redondear(media + margen, 4),
                    "tolerancia": 0.05,
                    "solucion": (
                        f"{num(media, 4)} + {num(margen, 4)} = {num(media + margen, 4)}."
                    ),
                },
            ],
        })
    return ejercicios


def familia_prueba_t(rng) -> list[dict]:
    """Prueba t de una muestra, con la decisión explícita."""
    ejercicios = []
    for k in range(POR_FAMILIA):
        plantilla, unidad, mu0, sd = CONTEXTOS_T[k % len(CONTEXTOS_T)]
        n = int(rng.integers(10, 31))
        # La mitad de los ejercicios tienen efecto real y la mitad no: si
        # todos rechazaran, el ejercicio enseñaría a contestar sin mirar.
        corrimiento = float(rng.choice([0.0, 0.0, 0.5, -0.5, 0.8])) * sd
        x = rng.normal(mu0 + corrimiento, sd, n)
        # Igual que arriba: lo que se muestra es lo que se usa.
        media = round(float(x.mean()), 3)
        s = round(float(x.std(ddof=1)), 3)
        gl = n - 1
        ee = s / math.sqrt(n)
        t = (media - mu0) / ee
        p = float(2 * stats.t.sf(abs(t), gl))

        ejercicios.append({
            "id": f"prueba-t-{k + 1:02d}",
            "tema": "prueba-t",
            "concepto": "prueba-t-para-una-media",
            "nivel": 2,
            "titulo": "Prueba t para una muestra",
            "enunciado": (
                f"Se quiere comprobar lo que afirma "
                f"{plantilla.format(mu0=num(mu0, 1))}. En una muestra de {n} casos la "
                f"media fue de {num(media, 3)} y el desvío estándar muestral "
                f"{num(s, 3)} {unidad}. Se trabaja al 5 % con una prueba bilateral."
            ),
            "datos": [],
            "unidad": unidad,
            "parametros": {
                "n": n, "media": redondear(media, 4), "s": redondear(s, 4),
                "mu0": mu0, "alfa": 0.05,
            },
            "preguntas": [
                {
                    "texto": "¿Cuánto vale el estadístico t?",
                    "respuesta": redondear(t, 4),
                    "tolerancia": 0.01,
                    "solucion": (
                        f"t = (x̄ − μ₀) / (s/√n) = ({num(media, 4)} − {num(mu0, 1)}) / "
                        f"({num(s, 4)}/√{n}) = {num(media - mu0, 4)} / {num(ee, 4)} = "
                        f"{num(t, 4)}."
                    ),
                },
                {
                    "texto": "¿Cuál es el valor p bilateral?",
                    "respuesta": redondear(p, 6),
                    "tolerancia": 0.005,
                    "solucion": (
                        f"Con {gl} grados de libertad, el área de las dos colas "
                        f"más allá de |t| = {num(abs(t), 4)} es {num(p, 4)}."
                    ),
                },
                {
                    "texto": (
                        "¿Se rechaza la hipótesis nula? Respondé 1 por sí y "
                        "0 por no."
                    ),
                    "respuesta": 1.0 if p < 0.05 else 0.0,
                    "tolerancia": 0.0,
                    "solucion": (
                        f"El valor p es {num(p, 4)}, que "
                        + (
                            f"es menor que 0,05: se rechaza. Los datos son "
                            f"incompatibles con que la media valga {num(mu0, 1)}."
                            if p < 0.05
                            else f"no es menor que 0,05: no se rechaza. Eso no "
                                 f"prueba que la media sea {num(mu0, 1)}, solo que "
                                 f"estos datos no alcanzan para descartarlo."
                        )
                    ),
                },
            ],
        })
    return ejercicios


CONTEXTOS_SUMA = [
    ("las personas que viven en cada uno de los {n} hogares relevados",
     "personas"),
    ("los reclamos recibidos en {n} semanas", "reclamos"),
    ("los kilos vendidos en {n} jornadas", "kilos"),
]


def familia_sumatoria(rng) -> list[dict]:
    """La sumatoria, y el error de siempre: Σx² no es (Σx)²."""
    ejercicios = []
    for k in range(POR_FAMILIA):
        plantilla, unidad = CONTEXTOS_SUMA[k % len(CONTEXTOS_SUMA)]
        n = int(rng.integers(5, 9))
        x = rng.integers(2, 15, n).astype(int)

        suma = int(x.sum())
        suma_cuad = int((x ** 2).sum())
        cuad_suma = int(suma ** 2)
        c = int(rng.integers(3, 8))
        media = suma / n
        suma_desvios = float(sum(float(v) - media for v in x))

        ejercicios.append({
            "id": f"sumatoria-{k + 1:02d}",
            "tema": "sumatoria",
            "concepto": "notacion-y-simbolos",
            "nivel": 1,
            "titulo": "Trabajar con la sumatoria",
            "enunciado": (
                f"Se anotaron {plantilla.format(n=n)}. Llamando $$x_i$$ a cada "
                f"valor, con $$i$$ de 1 a {n}:"
            ),
            "datos": [int(v) for v in x],
            "unidad": unidad,
            "parametros": {"n": n, "c": c},
            "preguntas": [
                {
                    "texto": "¿Cuánto vale la suma de los valores?",
                    "respuesta": float(suma),
                    "tolerancia": 0.0,
                    "solucion": (
                        f"Se suman los {n} valores uno por uno: {num(suma, 0)}."
                    ),
                },
                {
                    "texto": (
                        "¿Cuánto vale la suma de los cuadrados, es decir "
                        "elevar cada valor al cuadrado y después sumar?"
                    ),
                    "respuesta": float(suma_cuad),
                    "tolerancia": 0.0,
                    "solucion": (
                        f"Primero se eleva cada uno al cuadrado y después se "
                        f"suman: {num(suma_cuad, 0)}. Nótese que no es lo "
                        f"mismo que elevar la suma al cuadrado, que da "
                        f"{num(cuad_suma, 0)}: la diferencia entre los dos es "
                        f"la razón de que la varianza no sea cero."
                    ),
                },
                {
                    "texto": (
                        "¿Y el cuadrado de la suma, o sea sumar primero y "
                        "elevar después?"
                    ),
                    "respuesta": float(cuad_suma),
                    "tolerancia": 0.0,
                    "solucion": (
                        f"La suma es {num(suma, 0)} y su cuadrado "
                        f"{num(cuad_suma, 0)}. Es {num(cuad_suma / suma_cuad, 2)} "
                        f"veces la suma de los cuadrados: son operaciones "
                        f"distintas y el orden importa."
                    ),
                },
                {
                    "texto": (
                        f"¿Cuánto vale la suma, desde 1 hasta {n}, de la "
                        f"constante {c}?"
                    ),
                    "respuesta": float(n * c),
                    "tolerancia": 0.0,
                    "solucion": (
                        f"Sumar {n} veces la constante {c} es multiplicarla "
                        f"por {n}: {num(n * c, 0)}. La sumatoria de una "
                        f"constante no la deja igual ni la anula."
                    ),
                },
                {
                    "texto": (
                        "¿Cuánto vale la suma de los desvíos respecto de la "
                        "media?"
                    ),
                    "respuesta": round(suma_desvios, 6),
                    "tolerancia": 1e-6,
                    # Da cero siempre, y esa es justamente la enseñanza: el
                    # control de respuestas constantes tiene que saltearla.
                    "constante": True,
                    "solucion": (
                        "Cero, y no por casualidad: la media es justamente el "
                        "valor que hace que los desvíos se cancelen. Por eso "
                        "para medir dispersión hay que elevarlos al cuadrado "
                        "o tomar su valor absoluto."
                    ),
                },
            ],
        })
    return ejercicios


def familia_redondeo(rng) -> list[dict]:
    """Cifras significativas y el redondeo en dos pasos."""
    ejercicios = []
    for k in range(POR_FAMILIA):
        bruto = float(rng.uniform(100, 99000))
        valor = round(bruto, 4)
        cifras = int(rng.choice([2, 3, 4]))

        from decimal import Decimal, ROUND_HALF_UP

        def sig(v: float, c: int) -> float:
            if v == 0:
                return 0.0
            d = math.floor(math.log10(abs(v))) + 1
            return float(
                Decimal(repr(v)).quantize(
                    Decimal(1).scaleb(d - c), rounding=ROUND_HALF_UP
                )
            )

        redondeado = sig(valor, cifras)
        # El clásico: redondear en dos pasos no da lo mismo que en uno.
        paso1 = sig(valor, cifras + 1)
        dos_pasos = sig(paso1, cifras)

        # La cantidad de decimales varía, y con ella la respuesta: si `a`
        # tuviera siempre un decimal, la pregunta se contestaría de memoria.
        da = int(rng.choice([0, 1, 2]))
        a = round(float(rng.uniform(10, 999)), da)
        b = round(float(rng.uniform(10, 99)), 4)
        producto = a * b
        # Con valores mayores que 1 y sin ceros a la izquierda, las cifras
        # significativas son las enteras más las decimales escritas.
        sig_a = len(str(int(abs(a)))) + da
        sig_b = len(str(int(abs(b)))) + 4

        ejercicios.append({
            "id": f"redondeo-{k + 1:02d}",
            "tema": "redondeo",
            "concepto": "redondeo-y-cifras-significativas",
            "nivel": 1,
            "titulo": "Redondeo y cifras significativas",
            "enunciado": (
                f"Una medición dio {num(valor, 4)} y otras dos, {num(a, da)} y "
                f"{num(b, 4)}."
            ),
            "datos": [],
            "unidad": "",
            "parametros": {
                "valor": valor, "cifras": cifras, "a": a, "b": b,
                "decimales_a": da, "sig_a": sig_a,
            },
            "preguntas": [
                {
                    "texto": (
                        f"Redondeá {num(valor, 4)} a {cifras} cifras "
                        f"significativas."
                    ),
                    "respuesta": redondeado,
                    "tolerancia": 0.0,
                    "solucion": (
                        f"Las cifras significativas se cuentan desde el primer "
                        f"dígito distinto de cero, no desde la coma: "
                        f"{num(redondeado, 4)}."
                        + (
                            f" Ojo con hacerlo en dos pasos: redondeando "
                            f"primero a {cifras + 1} cifras "
                            f"({num(paso1, 4)}) y después a {cifras} daría "
                            f"{num(dos_pasos, 4)}, que no es lo mismo."
                            if dos_pasos != redondeado
                            else ""
                        )
                    ),
                },
                {
                    "texto": (
                        f"¿Cuántas cifras significativas puede tener como "
                        f"máximo el producto {num(a, da)} × {num(b, 4)}?"
                    ),
                    "respuesta": float(sig_a),
                    "tolerancia": 0.0,
                    "solucion": (
                        f"Las del factor menos preciso. {num(a, da)} tiene "
                        f"{sig_a} cifras significativas y {num(b, 4)} tiene "
                        f"{sig_b}: el producto no puede tener más que el "
                        f"primero. La calculadora devuelve {num(producto, 6)} "
                        f"y escribirlo entero sería inventar precisión que "
                        f"ninguna de las dos mediciones tiene."
                    ),
                },
            ],
        })
    return ejercicios


CONTEXTOS_CUANTILES = [
    ("los días que tardó en resolverse cada uno de {n} trámites", "días"),
    ("la edad de {n} pacientes atendidos en una guardia", "años"),
    ("los kilómetros recorridos por {n} vehículos en un día", "kilómetros"),
]


def cuantil_tipo7(x: list[float], p: float) -> float:
    """El método que declara la entrada de cuantiles: h = (n−1)p + 1."""
    n = len(x)
    h = (n - 1) * p + 1
    i = int(math.floor(h))
    f = h - i
    if i >= n:
        return float(x[-1])
    return float(x[i - 1] + f * (x[i] - x[i - 1]))


def cuantil_tipo6(x: list[float], p: float) -> float:
    """El de Excel con CUARTIL.EXC y el de SPSS: h = (n+1)p."""
    n = len(x)
    h = (n + 1) * p
    if h < 1:
        return float(x[0])
    if h >= n:
        return float(x[-1])
    i = int(math.floor(h))
    f = h - i
    return float(x[i - 1] + f * (x[i] - x[i - 1]))


def cuantil_tipo2(x: list[float], p: float) -> float:
    """El de Stata: inversa de la acumulada, promediando en los saltos."""
    n = len(x)
    g = n * p
    if abs(g - round(g)) < 1e-12:
        k = int(round(g))
        if k <= 0:
            return float(x[0])
        if k >= n:
            return float(x[-1])
        return float((x[k - 1] + x[k]) / 2)
    return float(x[int(math.ceil(g)) - 1])


def fusionar_diagnosticos(preguntas: list[dict]) -> list[dict]:
    """Un mismo número no se publica dos veces con dos motivos.

    Pasa cuando dos convenciones coinciden: el lector veía el mismo valor
    repetido y tenía que adivinar si era un error de la página.
    """
    for p in preguntas:
        por_valor: dict[float, list[str]] = {}
        for d in p.get("diagnosticos", []):
            por_valor.setdefault(d["valor"], []).append(d["motivo"])
        p["diagnosticos"] = [
            {"valor": v,
             "motivo": (motivos[0] if len(motivos) == 1
                        else _unir(motivos))}
            for v, motivos in por_valor.items()
        ]
    return preguntas


def _unir(motivos: list[str]) -> str:
    """Dos convenciones que dan lo mismo se cuentan en una sola frase."""
    programas = []
    for m in motivos:
        if "Excel" in m or "SPSS" in m:
            programas.append("CUARTIL.EXC de Excel y SPSS (método 6)")
        if "Stata" in m:
            programas.append("Stata (método 2)")
    if programas:
        return ("No está mal: es lo que devuelven "
                + " y ".join(programas)
                + ". Con muestras chicas los métodos difieren; con muchas, no.")
    return motivos[0]


def familia_cuantiles(rng) -> list[dict]:
    """Cuartiles, rango intercuartílico y la regla del 1,5."""
    ejercicios = []
    for k in range(POR_FAMILIA):
        plantilla, unidad = CONTEXTOS_CUANTILES[k % len(CONTEXTOS_CUANTILES)]
        n = int(rng.integers(9, 16))
        x = sorted(int(v) for v in rng.integers(4, 60, n))
        # Que haya un atípico la mitad de las veces: si siempre hubiera, la
        # última pregunta se contestaría sin mirar.
        if k % 2 == 0:
            x[-1] = int(x[-1] + rng.integers(45, 90))
            x = sorted(x)
        xf = [float(v) for v in x]

        q1 = cuantil_tipo7(xf, 0.25)
        q2 = cuantil_tipo7(xf, 0.50)
        q3 = cuantil_tipo7(xf, 0.75)
        ric = q3 - q1
        cerca_alto = q3 + 1.5 * ric
        cerca_bajo = q1 - 1.5 * ric
        atipicos = [v for v in xf if v > cerca_alto or v < cerca_bajo]

        q1_t6, q3_t6 = cuantil_tipo6(xf, 0.25), cuantil_tipo6(xf, 0.75)
        q1_t2, q3_t2 = cuantil_tipo2(xf, 0.25), cuantil_tipo2(xf, 0.75)

        otros_q1 = []
        for etiqueta, valor in (
            ("CUARTIL.EXC de Excel, o SPSS: es el método 6", q1_t6),
            ("Stata: es el método 2", q1_t2),
        ):
            if abs(valor - q1) > 0.01:
                otros_q1.append({"valor": redondear(valor, 4),
                                 "motivo": (
                                     f"No está mal: es lo que devuelve "
                                     f"{etiqueta}. Con muestras chicas los "
                                     f"métodos difieren; con muchas, no.")})

        ejercicios.append({
            "id": f"cuantiles-{k + 1:02d}",
            "tema": "cuantiles",
            "concepto": "cuantiles",
            "nivel": 1,
            "titulo": "Cuartiles, rango intercuartílico y atípicos",
            "enunciado": (
                f"Se registraron {plantilla.format(n=n)}. Los valores, ya "
                f"ordenados, son:"
            ),
            "datos": x,
            "unidad": unidad,
            "parametros": {"n": n},
            "nota": (
                "Usá el método que explica la entrada de cuantiles: "
                "h = (n − 1)·p + 1, interpolando. Es el que traen R, pandas, "
                "NumPy y CUARTIL.INC de Excel."
            ),
            "preguntas": [
                {
                    "texto": "¿Cuánto vale el primer cuartil?",
                    "respuesta": redondear(q1, 4),
                    "tolerancia": 0.02,
                    "solucion": (
                        f"La posición es h = ({n} − 1)·0,25 + 1 = "
                        f"{num((n - 1) * 0.25 + 1, 2)}, así que se interpola "
                        f"entre los datos de esa posición: Q₁ = {num(q1, 4)}."
                    ),
                    "diagnosticos": otros_q1,
                },
                {
                    "texto": "¿Y el tercer cuartil?",
                    "respuesta": redondear(q3, 4),
                    "tolerancia": 0.02,
                    "solucion": (
                        f"Con p = 0,75 la posición es "
                        f"{num((n - 1) * 0.75 + 1, 2)} y queda "
                        f"Q₃ = {num(q3, 4)}."
                    ),
                    "diagnosticos": [
                        d for d, v in (
                            ({"valor": redondear(q3_t6, 4),
                              "motivo": ("No está mal: es el método 6, el de "
                                         "CUARTIL.EXC de Excel y el de SPSS.")},
                             q3_t6),
                            ({"valor": redondear(q3_t2, 4),
                              "motivo": ("No está mal: es el método 2, el que "
                                         "usa Stata por defecto.")},
                             q3_t2),
                        ) if abs(v - q3) > 0.01
                    ],
                },
                {
                    "texto": "¿Cuánto vale el rango intercuartílico?",
                    "respuesta": redondear(ric, 4),
                    "tolerancia": 0.02,
                    "solucion": (
                        f"RIC = Q₃ − Q₁ = {num(q3, 4)} − {num(q1, 4)} = "
                        f"{num(ric, 4)}. Es la amplitud del 50 % central, y a "
                        f"diferencia del rango no se mueve si aparece un "
                        f"valor extremo."
                    ),
                    "diagnosticos": [],
                },
                {
                    "texto": (
                        "Según la regla del 1,5, ¿a partir de qué valor un "
                        "dato se considera atípico por arriba?"
                    ),
                    "respuesta": redondear(cerca_alto, 4),
                    "tolerancia": 0.02,
                    "solucion": (
                        f"El cerco superior es Q₃ + 1,5 × RIC = {num(q3, 4)} "
                        f"+ 1,5 × {num(ric, 4)} = {num(cerca_alto, 4)}."
                    ),
                    "diagnosticos": [],
                },
                {
                    "texto": (
                        "¿Cuántos valores del conjunto quedan fuera de los "
                        "cercos?"
                    ),
                    "respuesta": float(len(atipicos)),
                    "tolerancia": 0.0,
                    "solucion": (
                        (f"Queda{'n' if len(atipicos) != 1 else ''} "
                         f"{num(len(atipicos), 0)} fuera: "
                         f"{', '.join(num(v, 0) for v in atipicos)}. "
                         if atipicos
                         else "Ninguno: todos caen dentro de los cercos. ")
                        + "Que un valor sea atípico por esta regla no "
                          "significa que esté mal ni que haya que sacarlo: "
                          "significa que hay que mirarlo."
                    ),
                    "diagnosticos": [],
                },
            ],
        })
        ejercicios[-1]["preguntas"] = fusionar_diagnosticos(
            ejercicios[-1]["preguntas"]
        )
    return ejercicios


CONTEXTOS_TABLA = [
    ("el gasto semanal en transporte de {n} hogares", "pesos"),
    ("los minutos de espera de {n} personas en una ventanilla", "minutos"),
    ("el peso de {n} bolsas al salir de la envasadora", "kilos"),
]


def familia_tabla(rng) -> list[dict]:
    """Armar la tabla de frecuencias: clases, límites y acumuladas."""
    ejercicios = []
    for k in range(POR_FAMILIA):
        plantilla, unidad = CONTEXTOS_TABLA[k % len(CONTEXTOS_TABLA)]
        n = int(rng.integers(28, 61))
        amplitud = int(rng.choice([5, 10, 20]))
        inicio = int(rng.choice([0, 10, 20, 100]))
        clases = int(rng.integers(5, 8))
        tope = inicio + amplitud * clases

        # Los datos se sortean dentro del rango de las clases, así que
        # ninguno queda afuera: la tabla cierra por construcción.
        x = [int(v) for v in rng.integers(inicio, tope, n)]
        # Y se fuerza que alguno caiga justo en un límite interno, que es
        # donde se decide si el intervalo es abierto o cerrado.
        limite = inicio + amplitud * int(rng.integers(1, clases))
        x[0] = limite
        x[1] = limite
        x = sorted(x)

        sturges = 1 + 3.322 * math.log10(n)
        k_sturges = int(round(sturges))

        elegida = int(rng.integers(0, clases))
        lo = inicio + amplitud * elegida
        hi = lo + amplitud
        # Semiabierto: incluye el límite inferior y excluye el superior.
        dentro = [v for v in x if lo <= v < hi]
        acumulada = len([v for v in x if v < hi])
        marca = (lo + hi) / 2

        en_limite = len([v for v in x if v == limite])

        ejercicios.append({
            "id": f"tabla-frecuencias-{k + 1:02d}",
            "tema": "tabla-frecuencias",
            "concepto": "tabla-de-frecuencias",
            "nivel": 1,
            "titulo": "Armar una tabla de frecuencias",
            "enunciado": (
                f"Se relevó {plantilla.format(n=n)}, en {unidad}. Los "
                f"{num(n, 0)} valores, ordenados, son los de abajo. Se "
                f"decidió agruparlos en {num(clases, 0)} clases de amplitud "
                f"{num(amplitud, 0)}, empezando en {num(inicio, 0)}, con "
                f"intervalos semiabiertos del tipo [Lᵢ, Lᵢ₊₁)."
            ),
            "datos": x,
            "unidad": unidad,
            "parametros": {
                "n": n, "amplitud": amplitud, "inicio": inicio,
                "clases": clases, "clase_elegida": elegida,
                "limite": limite,
            },
            "preguntas": [
                {
                    "texto": (
                        "¿Cuántas clases sugiere la regla de Sturges? "
                        "Redondeá al entero más cercano."
                    ),
                    "respuesta": float(k_sturges),
                    "tolerancia": 0.0,
                    "solucion": (
                        f"k = 1 + 3,322 × log₁₀({num(n, 0)}) = "
                        f"{num(sturges, 4)}, que redondeado da "
                        f"{num(k_sturges, 0)}. Es una sugerencia, no una "
                        f"ley: acá se usaron {num(clases, 0)} clases, y "
                        f"está bien siempre que se justifique."
                    ),
                    "diagnosticos": [],
                },
                {
                    "texto": (
                        f"¿Cuál es la frecuencia absoluta de la clase "
                        f"[{num(lo, 0)}, {num(hi, 0)})?"
                    ),
                    "respuesta": float(len(dentro)),
                    "tolerancia": 0.0,
                    "solucion": (
                        f"Son {num(len(dentro), 0)} valores: los que van "
                        f"desde {num(lo, 0)} inclusive hasta {num(hi, 0)} "
                        f"sin incluirlo."
                    ),
                    "diagnosticos": [],
                },
                {
                    "texto": (
                        f"¿Y la frecuencia relativa de esa misma clase, en "
                        f"tanto por uno?"
                    ),
                    "respuesta": redondear(len(dentro) / n, 6),
                    "tolerancia": 0.002,
                    "solucion": (
                        f"Se divide la frecuencia absoluta por el total: "
                        f"{num(len(dentro), 0)} / {num(n, 0)} = "
                        f"{num(len(dentro) / n, 4)}, o sea el "
                        f"{num(len(dentro) / n * 100, 1)} % de los casos. La "
                        f"suma de todas las relativas tiene que dar 1: es la "
                        f"comprobación de que la tabla cierra."
                    ),
                    "diagnosticos": [],
                },
                {
                    "texto": (
                        f"¿Cuántos valores hay acumulados hasta el final de "
                        f"esa clase, es decir por debajo de {num(hi, 0)}?"
                    ),
                    "respuesta": float(acumulada),
                    "tolerancia": 0.0,
                    "solucion": (
                        f"La acumulada suma todas las clases anteriores más "
                        f"esta: {num(acumulada, 0)} de {num(n, 0)}."
                    ),
                    "diagnosticos": [],
                },
                {
                    "texto": "¿Cuál es la marca de esa clase?",
                    "respuesta": redondear(marca, 4),
                    "tolerancia": 0.001,
                    "solucion": (
                        f"El punto medio: ({num(lo, 0)} + {num(hi, 0)}) / 2 = "
                        f"{num(marca, 4)}. Es el valor que representa a toda "
                        f"la clase cuando se calcula con datos agrupados."
                    ),
                    "diagnosticos": [],
                },
                {
                    "texto": (
                        f"Hay valores exactamente iguales a {num(limite, 0)}, "
                        f"que es un límite entre dos clases. ¿Cuántos, y en "
                        f"cuál de las dos van? Respondé cuántos."
                    ),
                    "respuesta": float(en_limite),
                    "tolerancia": 0.0,
                    "solucion": (
                        f"Son {num(en_limite, 0)}, y van en la clase que "
                        f"empieza en {num(limite, 0)}: el intervalo "
                        f"semiabierto incluye su límite inferior y excluye el "
                        f"superior. Sin esa convención el valor entraría en "
                        f"dos clases o en ninguna, y la tabla no cerraría."
                    ),
                    "diagnosticos": [],
                },
            ],
        })
    return ejercicios


CONTEXTOS_CAJA = [
    ("los minutos que duró cada una de {n} llamadas al 147", "minutos"),
    ("los días de demora de {n} expedientes", "días"),
    ("la cantidad de consultas diarias de {n} jornadas", "consultas"),
]


def familia_caja(rng) -> list[dict]:
    """Los cinco números del diagrama de caja, y dónde terminan los bigotes."""
    ejercicios = []
    for k in range(POR_FAMILIA):
        plantilla, unidad = CONTEXTOS_CAJA[k % len(CONTEXTOS_CAJA)]
        n = int(rng.integers(11, 18))
        x = sorted(int(v) for v in rng.integers(5, 45, n))
        # Dos tercios de los ejercicios con atípico, un tercio sin: si
        # siempre hubiera, la última pregunta se contestaría sin mirar.
        if k % 3 != 2:
            x[-1] = int(x[-1] + rng.integers(40, 80))
            x = sorted(x)
        xf = [float(v) for v in x]

        q1 = cuantil_tipo7(xf, 0.25)
        me = cuantil_tipo7(xf, 0.50)
        q3 = cuantil_tipo7(xf, 0.75)
        ric = q3 - q1
        cerco_alto, cerco_bajo = q3 + 1.5 * ric, q1 - 1.5 * ric
        dentro = [v for v in xf if cerco_bajo <= v <= cerco_alto]
        bigote_alto, bigote_bajo = max(dentro), min(dentro)
        atipicos = [v for v in xf if v not in dentro]

        ejercicios.append({
            "id": f"caja-{k + 1:02d}",
            "tema": "diagrama-de-caja",
            "concepto": "diagrama-de-caja",
            "nivel": 1,
            "titulo": "Los números de un diagrama de caja",
            "enunciado": (
                f"Se midieron {plantilla.format(n=n)}. Para dibujar el "
                f"diagrama de caja hacen falta cinco números y los cercos. "
                f"Los valores ordenados son:"
            ),
            "datos": x,
            "unidad": unidad,
            "parametros": {"n": n},
            "nota": (
                "Para los cuartiles, el método de la entrada de cuantiles: "
                "h = (n − 1)·p + 1."
            ),
            "preguntas": [
                {
                    "texto": "¿Dónde está el borde inferior de la caja?",
                    "respuesta": redondear(q1, 4),
                    "tolerancia": 0.02,
                    "solucion": (
                        f"Es el primer cuartil: {num(q1, 4)}. La caja va de "
                        f"Q₁ a Q₃ y contiene el 50 % central."
                    ),
                    "diagnosticos": [],
                },
                {
                    "texto": "¿Y la línea de adentro de la caja?",
                    "respuesta": redondear(me, 4),
                    "tolerancia": 0.02,
                    "solucion": (
                        f"La mediana: {num(me, 4)}. No es el promedio, y por "
                        f"eso la línea no suele quedar en el medio de la caja "
                        f"cuando la variable es asimétrica."
                    ),
                    "diagnosticos": [
                        {
                            "valor": redondear(sum(xf) / n, 4),
                            "motivo": (
                                "Es la media. La línea de la caja es la "
                                "mediana; poner la media es un error "
                                "frecuente y cambia el dibujo."
                            ),
                        },
                    ],
                },
                {
                    "texto": (
                        "¿Hasta qué valor llega el bigote superior?"
                    ),
                    "respuesta": redondear(bigote_alto, 4),
                    "tolerancia": 0.02,
                    "solucion": (
                        f"Hasta {num(bigote_alto, 4)}, que es el valor más "
                        f"grande **que todavía cae dentro del cerco** "
                        f"({num(cerco_alto, 4)}). El bigote no llega al "
                        f"máximo salvo que no haya atípicos."
                        + (f" Acá el máximo es {num(max(xf), 0)} y queda "
                           f"afuera, dibujado como punto."
                           if atipicos else
                           " Acá no hay atípicos, así que coincide con el "
                           "máximo.")
                    ),
                    "diagnosticos": (
                        [{
                            "valor": redondear(max(xf), 4),
                            "motivo": (
                                "Es el máximo. El bigote no llega al máximo "
                                "cuando hay valores fuera del cerco: esos se "
                                "dibujan como puntos sueltos."
                            ),
                        }] if atipicos else []
                    ),
                },
                {
                    "texto": (
                        "¿Cuántos puntos sueltos hay que dibujar fuera de "
                        "los bigotes?"
                    ),
                    "respuesta": float(len(atipicos)),
                    "tolerancia": 0.0,
                    "solucion": (
                        (f"Hay {num(len(atipicos), 0)} fuera de los cercos: "
                         f"{', '.join(num(v, 0) for v in atipicos)}. Se "
                         f"dibujan como puntos sueltos, no como parte del "
                         f"bigote, y que aparezcan no significa que estén "
                         f"mal: significa que conviene mirarlos."
                         if atipicos
                         else "Ninguno: todos los valores caen dentro de los "
                              "cercos, así que los bigotes llegan al mínimo y "
                              "al máximo. Un diagrama sin puntos sueltos es "
                              "tan informativo como uno con ellos.")
                    ),
                    "diagnosticos": [],
                },
            ],
        })
    return ejercicios


def familia_histograma(rng) -> list[dict]:
    """Clases desiguales: la altura es la densidad, no la frecuencia."""
    ejercicios = []
    for k in range(POR_FAMILIA):
        # Tres clases angostas y una ancha: el caso donde el histograma
        # miente si se dibuja la frecuencia.
        # La clase ancha cambia de lugar: si fuera siempre la última, la
        # pregunta de cuál parece más alta se contestaría sin mirar.
        ancha = int(rng.integers(0, 4))
        anchos = [10, 10, 10, 10]
        anchos[ancha] = int(rng.choice([30, 40, 50]))
        limites = [0]
        for a in anchos:
            limites.append(limites[-1] + a)
        frec = [int(rng.integers(18, 40)) for _ in range(4)]
        # Junta bastantes casos: en frecuencia parece la más alta y en
        # densidad es la más baja.
        frec[ancha] = int(rng.integers(42, 70))
        n = sum(frec)

        densidad = [f / a for f, a in zip(frec, anchos)]
        mas_alta_frec = int(max(range(4), key=lambda i: frec[i]))
        mas_alta_dens = int(max(range(4), key=lambda i: densidad[i]))

        tabla = " · ".join(
            f"[{limites[i]}, {limites[i + 1]}): {frec[i]}" for i in range(4)
        )

        ejercicios.append({
            "id": f"histograma-{k + 1:02d}",
            "tema": "histograma",
            "concepto": "histograma",
            "nivel": 2,
            "titulo": "Un histograma con clases de distinto ancho",
            "enunciado": (
                f"Una tabla de frecuencias agrupa {num(n, 0)} casos en cuatro "
                f"clases, y una de ellas es más ancha que el resto: {tabla}."
            ),
            "datos": [],
            "unidad": "",
            "parametros": {
                "n": n, "anchos": anchos, "frecuencias": frec, "ancha": ancha,
                "lim0": limites[0], "lim4": limites[4],
            },
            "nota": (
                "En un histograma el área de cada barra representa la "
                "frecuencia, no su altura. Con clases de distinto ancho, la "
                "altura es la densidad: frecuencia dividida por amplitud."
            ),
            "preguntas": [
                {
                    "texto": (
                        f"¿Qué altura tiene que tener la barra de la clase "
                        f"[{limites[ancha]}, {limites[ancha + 1]}), la más "
                        f"ancha?"
                    ),
                    "respuesta": redondear(densidad[ancha], 6),
                    "tolerancia": 0.005,
                    "solucion": (
                        f"La densidad: {num(frec[ancha], 0)} / "
                        f"{num(anchos[ancha], 0)} = "
                        f"{num(densidad[ancha], 4)}. Si se dibujara "
                        f"{num(frec[ancha], 0)} de alto, esa barra tendría un "
                        f"área {num(anchos[ancha] / 10, 0)} veces mayor de la "
                        f"que le corresponde."
                    ),
                    "diagnosticos": [
                        {
                            "valor": float(frec[ancha]),
                            "motivo": (
                                "Es la frecuencia. Dibujarla como altura con "
                                "clases desiguales exagera la clase ancha, "
                                "porque el área queda multiplicada por su "
                                "amplitud."
                            ),
                        },
                    ],
                },
                {
                    "texto": (
                        f"¿Y la de la primera clase, [{limites[0]}, "
                        f"{limites[1]})?"
                    ),
                    "respuesta": redondear(densidad[0], 6),
                    "tolerancia": 0.005,
                    "solucion": (
                        f"{num(frec[0], 0)} / {num(anchos[0], 0)} = "
                        f"{num(densidad[0], 4)}. Con clases de igual ancho "
                        f"dividir por la amplitud no cambia la forma del "
                        f"dibujo, solo la escala del eje; el problema aparece "
                        f"cuando los anchos difieren."
                    ),
                    "diagnosticos": [],
                },
                {
                    "texto": (
                        "Si alguien dibuja las frecuencias como alturas, ¿qué "
                        "clase parece la más alta? Respondé con su número, "
                        "de 1 a 4."
                    ),
                    "respuesta": float(mas_alta_frec + 1),
                    "tolerancia": 0.0,
                    "solucion": (
                        f"La clase {num(mas_alta_frec + 1, 0)}, con "
                        f"{num(frec[mas_alta_frec], 0)} casos."
                    ),
                    "diagnosticos": [],
                },
                {
                    "texto": (
                        "¿Y cuál es realmente la más alta, dibujando la "
                        "densidad?"
                    ),
                    "respuesta": float(mas_alta_dens + 1),
                    "tolerancia": 0.0,
                    "solucion": (
                        f"La clase {num(mas_alta_dens + 1, 0)}, con una "
                        f"densidad de {num(densidad[mas_alta_dens], 4)}. "
                        + (
                            f"O sea que el histograma mal dibujado señala la "
                            f"clase {num(mas_alta_frec + 1, 0)} y el bien "
                            f"dibujado la {num(mas_alta_dens + 1, 0)}: no es "
                            f"una diferencia de escala, es una conclusión "
                            f"distinta."
                            if mas_alta_dens != mas_alta_frec
                            else "Acá coinciden, pero no tiene por qué pasar."
                        )
                    ),
                    "diagnosticos": [],
                },
            ],
        })
    return ejercicios


CONTEXTOS_OJIVA = [
    ("el puntaje obtenido por {n} postulantes en una prueba", "puntos"),
    ("los minutos de demora de {n} colectivos", "minutos"),
]


def familia_ojiva(rng) -> list[dict]:
    """La acumulada, y leer la mediana interpolando sobre la ojiva."""
    ejercicios = []
    for k in range(POR_FAMILIA):
        plantilla, unidad = CONTEXTOS_OJIVA[k % len(CONTEXTOS_OJIVA)]
        amp = 10
        clases = 5
        frec = [int(rng.integers(6, 30)) for _ in range(clases)]
        n = sum(frec)
        limites = [amp * i for i in range(clases + 1)]
        acum = []
        s = 0
        for f in frec:
            s += f
            acum.append(s)

        # La clase donde la acumulada cruza la mitad.
        i_med = next(i for i, a in enumerate(acum) if a >= n / 2)
        antes = acum[i_med - 1] if i_med else 0
        # Interpolación lineal dentro de la clase, que es lo que hace la ojiva.
        mediana = limites[i_med] + (n / 2 - antes) / frec[i_med] * amp

        elegida = int(rng.integers(1, clases))
        tabla = " · ".join(
            f"[{limites[i]}, {limites[i + 1]}): {frec[i]}"
            for i in range(clases)
        )

        ejercicios.append({
            "id": f"ojiva-{k + 1:02d}",
            "tema": "ojiva",
            "concepto": "ojiva",
            "nivel": 2,
            "titulo": "Leer una ojiva",
            "enunciado": (
                f"Se agrupó {plantilla.format(n=n)} en cinco clases de "
                f"amplitud {num(amp, 0)}: {tabla}."
            ),
            "datos": [],
            "unidad": unidad,
            "parametros": {
                "n": n, "amplitud": amp, "frecuencias": frec,
                "clase": elegida,
            },
            "nota": (
                "La ojiva se dibuja acumulando y marcando el punto en el "
                "límite **superior** de cada clase, no en la marca de clase: "
                "recién ahí está completa la acumulación."
            ),
            "preguntas": [
                {
                    "texto": (
                        f"¿Qué valor le corresponde a la ojiva en el punto "
                        f"{num(limites[elegida], 0)}?"
                    ),
                    "respuesta": float(acum[elegida - 1]),
                    "tolerancia": 0.0,
                    "solucion": (
                        f"La acumulada hasta el final de la clase "
                        f"{num(elegida, 0)}: {num(acum[elegida - 1], 0)} de "
                        f"{num(n, 0)} casos."
                    ),
                    "diagnosticos": [
                        {
                            "valor": float(frec[elegida - 1]),
                            "motivo": (
                                "Es la frecuencia de esa clase sola. La ojiva "
                                "dibuja la acumulada, no la simple: ese sería "
                                "el polígono de frecuencias."
                            ),
                        },
                    ],
                },
                {
                    "texto": (
                        "Leyendo la ojiva, ¿en qué valor cruza la mitad de "
                        "los casos? Interpolá dentro de la clase."
                    ),
                    "respuesta": redondear(mediana, 4),
                    "tolerancia": 0.05,
                    "solucion": (
                        f"La mitad son {num(n / 2, 1)} casos, que se alcanzan "
                        f"dentro de la clase [{num(limites[i_med], 0)}, "
                        f"{num(limites[i_med + 1], 0)}). Interpolando: "
                        f"{num(limites[i_med], 0)} + ({num(n / 2, 1)} − "
                        f"{num(antes, 0)}) / {num(frec[i_med], 0)} × "
                        f"{num(amp, 0)} = {num(mediana, 4)}."
                    ),
                    "diagnosticos": [
                        {
                            "valor": float(limites[i_med] + amp / 2),
                            "motivo": (
                                "Es la marca de la clase donde cae la "
                                "mediana. Sirve como aproximación grosera, "
                                "pero la ojiva permite interpolar y dar un "
                                "valor mejor."
                            ),
                        },
                    ],
                },
                {
                    "texto": (
                        "¿Qué valor toma la ojiva en el último límite?"
                    ),
                    "respuesta": float(n),
                    "tolerancia": 0.0,
                    "solucion": (
                        f"{num(n, 0)}, el total de casos. La ojiva siempre "
                        f"termina en n —o en 1, si se dibuja con "
                        f"frecuencias relativas—, y que no llegue es la "
                        f"señal de que la tabla no cierra."
                    ),
                    "diagnosticos": [],
                },
            ],
        })
    return ejercicios


CONTEXTOS_CONTINGENCIA = [
    ("Sexo", ["Varones", "Mujeres"],
     "Condición de actividad", ["Ocupado", "Desocupado", "Inactivo"]),
    ("Zona", ["Urbana", "Rural"],
     "Cobertura de salud", ["Obra social", "Prepaga", "Solo pública"]),
    ("Turno", ["Mañana", "Tarde"],
     "Resultado", ["Aprobado", "Recursa", "Abandonó"]),
]


def familia_contingencia(rng) -> list[dict]:
    """La tabla de doble entrada, y cuál de los tres porcentajes contesta."""
    ejercicios = []
    for k in range(POR_FAMILIA):
        vf, filas, vc, cols = CONTEXTOS_CONTINGENCIA[
            k % len(CONTEXTOS_CONTINGENCIA)
        ]
        tabla = [[int(rng.integers(18, 140)) for _ in cols] for _ in filas]
        n = sum(sum(f) for f in tabla)
        tot_fila = [sum(f) for f in tabla]
        tot_col = [sum(f[j] for f in tabla) for j in range(len(cols))]

        i, j = 0, int(rng.integers(0, len(cols)))
        celda = tabla[i][j]
        p_conjunta = celda / n
        p_fila = celda / tot_fila[i]
        p_columna = celda / tot_col[j]

        texto_tabla = " | ".join(
            f"{filas[a]}: "
            + ", ".join(f"{cols[b]} {tabla[a][b]}" for b in range(len(cols)))
            for a in range(len(filas))
        )

        ejercicios.append({
            "id": f"contingencia-{k + 1:02d}",
            "tema": "tabla-de-contingencia",
            "concepto": "porcentajes-fila-columna-total",
            "nivel": 1,
            "titulo": "Leer una tabla de doble entrada",
            "enunciado": (
                f"Se cruzaron {vf.lower()} y {vc.lower()} en {num(n, 0)} "
                f"casos. La tabla es: {texto_tabla}."
            ),
            "datos": [],
            "unidad": "",
            "parametros": {
                "tabla": tabla, "n": n, "fila": i, "columna": j,
            },
            "nota": (
                "Los tres porcentajes de una celda son distintos y cada uno "
                "contesta una pregunta diferente. Conviene decidir la "
                "pregunta antes de dividir."
            ),
            "preguntas": [
                {
                    "texto": f"¿Cuántos casos hay en total en «{filas[i]}»?",
                    "respuesta": float(tot_fila[i]),
                    "tolerancia": 0.0,
                    "solucion": (
                        f"Es el total marginal de esa fila: la suma de sus "
                        f"{num(len(cols), 0)} celdas, {num(tot_fila[i], 0)}."
                    ),
                    "diagnosticos": [],
                },
                {
                    "texto": (
                        f"¿Qué porcentaje del **total** de casos son "
                        f"«{filas[i]}» y además «{cols[j]}»?"
                    ),
                    "respuesta": redondear(p_conjunta * 100, 4),
                    "tolerancia": 0.05,
                    "solucion": (
                        f"Es el porcentaje conjunto: la celda sobre el total "
                        f"general, {num(celda, 0)} / {num(n, 0)} = "
                        f"{num(p_conjunta * 100, 2)} %."
                    ),
                    "diagnosticos": [
                        {
                            "valor": redondear(p_fila * 100, 4),
                            "motivo": (
                                "Se dividió por el total de la fila. Ese es "
                                "el porcentaje fila y contesta otra pregunta: "
                                "qué parte de ese grupo tiene la "
                                "característica."
                            ),
                        },
                        {
                            "valor": redondear(p_columna * 100, 4),
                            "motivo": (
                                "Se dividió por el total de la columna: es el "
                                "porcentaje columna."
                            ),
                        },
                    ],
                },
                {
                    "texto": (
                        f"De los «{filas[i]}», ¿qué porcentaje son "
                        f"«{cols[j]}»?"
                    ),
                    "respuesta": redondear(p_fila * 100, 4),
                    "tolerancia": 0.05,
                    "solucion": (
                        f"La pregunta empieza por «de los {filas[i].lower()}», "
                        f"así que el denominador es esa fila: "
                        f"{num(celda, 0)} / {num(tot_fila[i], 0)} = "
                        f"{num(p_fila * 100, 2)} %."
                    ),
                    "diagnosticos": [
                        {
                            "valor": redondear(p_columna * 100, 4),
                            "motivo": (
                                "Está invertida: eso contesta «de los "
                                + cols[j].lower()
                                + ", qué porcentaje son " + filas[i].lower()
                                + "», que es otra cosa."
                            ),
                        },
                    ],
                },
                {
                    "texto": (
                        f"Y al revés: de los «{cols[j]}», ¿qué porcentaje son "
                        f"«{filas[i]}»?"
                    ),
                    "respuesta": redondear(p_columna * 100, 4),
                    "tolerancia": 0.05,
                    "solucion": (
                        f"Ahora el denominador es la columna: "
                        f"{num(celda, 0)} / {num(tot_col[j], 0)} = "
                        f"{num(p_columna * 100, 2)} %. Comparando con la "
                        f"pregunta anterior se ve que invertir la condición "
                        f"cambia el número: es el mismo error que confundir "
                        f"P(A|B) con P(B|A)."
                    ),
                    "diagnosticos": [],
                },
            ],
        })
    return ejercicios


CONTEXTOS_REGRESION = [
    ("los años de antigüedad", "el salario en miles", "años", "miles"),
    ("la superficie en hectáreas", "el rendimiento en quintales",
     "hectáreas", "quintales"),
    ("las horas de estudio", "el puntaje obtenido", "horas", "puntos"),
]


def familia_regresion(rng) -> list[dict]:
    """Covarianza, r, r² y la recta, sobre pocos pares."""
    ejercicios = []
    for k in range(POR_FAMILIA):
        nx, ny, ux, uy = CONTEXTOS_REGRESION[k % len(CONTEXTOS_REGRESION)]
        n = int(rng.integers(8, 12))
        x = np.sort(rng.integers(2, 30, n)).astype(float)
        b_real = float(rng.uniform(0.8, 3.2))
        y = np.round(b_real * x + rng.uniform(5, 30)
                     + rng.normal(0, 4.5, n))

        mx, my = float(x.mean()), float(y.mean())
        sxy = float(((x - mx) * (y - my)).sum() / (n - 1))
        sx = float(x.std(ddof=1))
        sy = float(y.std(ddof=1))
        r = sxy / (sx * sy)
        b = sxy / sx ** 2
        a = my - b * mx
        # Un valor dentro del rango: extrapolar es otro ejercicio.
        x0 = float(int((x.min() + x.max()) / 2))
        pred = a + b * x0

        ejercicios.append({
            "id": f"regresion-simple-{k + 1:02d}",
            "tema": "correlacion-y-recta",
            "concepto": "recta-de-minimos-cuadrados",
            "nivel": 1,
            "titulo": "Correlación y recta de mínimos cuadrados",
            "enunciado": (
                f"Se midieron {nx} ($$x$$) y {ny} ($$y$$) en {num(n, 0)} "
                f"casos. Los pares, ordenados por $$x$$, son: "
                + " · ".join(f"({int(a_)}, {int(b_)})"
                             for a_, b_ in zip(x, y))
                + "."
            ),
            "datos": [],
            "unidad": "",
            "parametros": {
                "x": [float(v) for v in x], "y": [float(v) for v in y],
                "x0": x0, "n": n,
            },
            "preguntas": [
                {
                    "texto": "¿Cuánto vale el coeficiente de correlación?",
                    "respuesta": redondear(r, 4),
                    "tolerancia": 0.005,
                    "solucion": (
                        f"r = s(x,y) / (s(x)·s(y)) = {num(sxy, 4)} / "
                        f"({num(sx, 4)} × {num(sy, 4)}) = {num(r, 4)}. No "
                        f"tiene unidades: es el mismo número si se mide en "
                        f"{ux} o en cualquier otra escala lineal."
                    ),
                    "diagnosticos": [
                        {
                            "valor": redondear(r ** 2, 4),
                            "motivo": (
                                "Es r al cuadrado, el coeficiente de "
                                "determinación. Siempre es menor que r en "
                                "valor absoluto y no lleva signo."
                            ),
                        },
                    ],
                },
                {
                    "texto": (
                        "¿Qué proporción de la variabilidad de $$y$$ queda "
                        "explicada por el modelo?"
                    ),
                    "respuesta": redondear(r ** 2, 4),
                    "tolerancia": 0.005,
                    "solucion": (
                        f"r² = {num(r ** 2, 4)}, o sea el "
                        f"{num(r ** 2 * 100, 1)} %. Ojo con leerlo como "
                        f"«explicar» en sentido causal: es la parte de la "
                        f"variabilidad que la recta reproduce, nada más."
                    ),
                    "diagnosticos": [
                        {
                            "valor": redondear(abs(r), 4),
                            "motivo": (
                                "Es r, no r². La proporción explicada es el "
                                "cuadrado, y siempre es menor."
                            ),
                        },
                    ],
                },
                {
                    "texto": "¿Cuál es la pendiente de la recta?",
                    "respuesta": redondear(b, 4),
                    "tolerancia": 0.01,
                    "solucion": (
                        f"b = s(x,y) / s²(x) = {num(sxy, 4)} / "
                        f"{num(sx ** 2, 4)} = {num(b, 4)}. Se lee: por cada "
                        f"{ux[:-1] if ux.endswith('s') else ux} más, "
                        f"{num(b, 2)} {uy} más en promedio."
                    ),
                    "diagnosticos": [
                        {
                            "valor": redondear(r, 4),
                            "motivo": (
                                "Es la correlación. La pendiente sí tiene "
                                "unidades y depende de las escalas; r no."
                            ),
                        },
                    ],
                },
                {
                    "texto": "¿Y la ordenada al origen?",
                    "respuesta": redondear(a, 4),
                    "tolerancia": 0.05,
                    "solucion": (
                        f"a = ȳ − b·x̄ = {num(my, 4)} − {num(b, 4)} × "
                        f"{num(mx, 4)} = {num(a, 4)}. Es el valor predicho "
                        f"para x = 0, que acá está fuera del rango observado: "
                        f"interpretarlo como algo real sería extrapolar."
                    ),
                    "diagnosticos": [],
                },
                {
                    "texto": (
                        f"¿Qué valor de $$y$$ predice la recta para "
                        f"$$x = {num(x0, 0)}$$?"
                    ),
                    "respuesta": redondear(pred, 4),
                    "tolerancia": 0.05,
                    "solucion": (
                        f"ŷ = {num(a, 4)} + {num(b, 4)} × {num(x0, 0)} = "
                        f"{num(pred, 4)}. Está dentro del rango de los datos, "
                        f"que es la única zona donde la recta tiene respaldo."
                    ),
                    "diagnosticos": [],
                },
            ],
        })
    return ejercicios


CONTEXTOS_RIESGO = [
    ("fumar", "tener tos crónica"),
    ("trabajar en el turno noche", "reportar insomnio"),
    ("no tener cobertura", "demorar una consulta"),
]


def familia_riesgo(rng) -> list[dict]:
    """Riesgo relativo y odds ratio, y por qué no son lo mismo."""
    ejercicios = []
    for k in range(POR_FAMILIA):
        exp, evento = CONTEXTOS_RIESGO[k % len(CONTEXTOS_RIESGO)]
        # Con eventos frecuentes el odds ratio se aleja del riesgo relativo,
        # y esa separación es la enseñanza del ejercicio: si los dos números
        # dieran casi lo mismo, confundirlos no tendría consecuencia y no
        # habría nada que diagnosticar. Se sortea hasta que se separen.
        while True:
            n_e = int(rng.integers(120, 400))
            n_ne = int(rng.integers(120, 400))
            p_e = float(rng.uniform(0.25, 0.55))
            p_ne = float(rng.uniform(0.08, 0.22))
            a_ = int(round(n_e * p_e))
            b_ = n_e - a_
            c_ = int(round(n_ne * p_ne))
            d_ = n_ne - c_
            if min(a_, b_, c_, d_) <= 0:
                continue
            rr_ = (a_ / n_e) / (c_ / n_ne)
            or_ = (a_ / b_) / (c_ / d_)
            if abs(or_ / rr_ - 1) > 0.25:
                break

        inc_e = a_ / n_e
        inc_ne = c_ / n_ne
        rr = inc_e / inc_ne
        odds_e = a_ / b_
        odds_ne = c_ / d_
        orr = odds_e / odds_ne

        ejercicios.append({
            "id": f"riesgo-{k + 1:02d}",
            "tema": "riesgo-y-odds",
            "concepto": "riesgo-relativo-y-odds-ratio",
            "nivel": 2,
            "titulo": "Riesgo relativo y odds ratio",
            "enunciado": (
                f"Se siguió a dos grupos según {exp}. Entre los "
                f"{num(n_e, 0)} expuestos, {num(a_, 0)} pasaron a "
                f"{evento}; entre los {num(n_ne, 0)} no expuestos, "
                f"{num(c_, 0)}."
            ),
            "datos": [],
            "unidad": "",
            "parametros": {"a": a_, "b": b_, "c": c_, "d": d_},
            "preguntas": [
                {
                    "texto": "¿Cuál es la incidencia entre los expuestos?",
                    "respuesta": redondear(inc_e, 6),
                    "tolerancia": 0.002,
                    "solucion": (
                        f"{num(a_, 0)} / {num(n_e, 0)} = {num(inc_e, 4)}, o "
                        f"sea el {num(inc_e * 100, 1)} %."
                    ),
                    "diagnosticos": [
                        {
                            "valor": redondear(odds_e, 6),
                            "motivo": (
                                "Eso es la **chance**: casos sobre no casos. "
                                "La incidencia es casos sobre el total del "
                                "grupo."
                            ),
                        },
                    ],
                },
                {
                    "texto": "¿Cuánto vale el riesgo relativo?",
                    "respuesta": redondear(rr, 4),
                    "tolerancia": 0.01,
                    "solucion": (
                        f"RR = {num(inc_e, 4)} / {num(inc_ne, 4)} = "
                        f"{num(rr, 4)}. Se lee: los expuestos tienen "
                        f"{num(rr, 2)} veces el riesgo de los no expuestos."
                    ),
                    "diagnosticos": [
                        {
                            "valor": redondear(orr, 4),
                            "motivo": (
                                "Es el odds ratio, no el riesgo relativo. Los "
                                "dos se parecen solo cuando el evento es "
                                "raro, y acá no lo es."
                            ),
                        },
                    ],
                },
                {
                    "texto": "¿Y el odds ratio?",
                    "respuesta": redondear(orr, 4),
                    "tolerancia": 0.01,
                    "solucion": (
                        f"OR = ({num(a_, 0)}/{num(b_, 0)}) / "
                        f"({num(c_, 0)}/{num(d_, 0)}) = {num(orr, 4)}. "
                        f"Es {num(orr / rr, 2)} veces el riesgo relativo: con "
                        f"una incidencia del {num(inc_e * 100, 0)} % entre "
                        f"los expuestos el evento no es raro, y ahí el OR "
                        f"exagera la asociación si se lo lee como un RR."
                    ),
                    "diagnosticos": [
                        {
                            "valor": redondear(rr, 4),
                            "motivo": (
                                "Es el riesgo relativo. El odds ratio usa "
                                "casos sobre no casos, no sobre el total."
                            ),
                        },
                    ],
                },
            ],
        })
    return ejercicios


CONTEXTOS_SIMPSON = [
    ("dos hospitales", "Hospital A", "Hospital B", "casos graves",
     "casos leves", "la tasa de recuperación"),
    ("dos tratamientos", "Tratamiento A", "Tratamiento B", "cálculos grandes",
     "cálculos chicos", "la tasa de éxito"),
]


def familia_simpson(rng) -> list[dict]:
    """El total dice lo contrario que cada grupo."""
    ejercicios = []
    for k in range(POR_FAMILIA):
        ctx, ga, gb, e1, e2, medida = CONTEXTOS_SIMPSON[
            k % len(CONTEXTOS_SIMPSON)
        ]
        # A es mejor en los dos estratos, pero atiende sobre todo los
        # difíciles; B se lleva los fáciles y gana en el total.
        n_a1 = int(rng.integers(220, 320))   # A, estrato difícil
        n_a2 = int(rng.integers(30, 70))     # A, estrato fácil
        n_b1 = int(rng.integers(30, 70))     # B, estrato difícil
        n_b2 = int(rng.integers(220, 320))   # B, estrato fácil
        p_a1 = float(rng.uniform(0.70, 0.76))
        p_b1 = p_a1 - float(rng.uniform(0.04, 0.08))
        p_a2 = float(rng.uniform(0.92, 0.96))
        p_b2 = p_a2 - float(rng.uniform(0.02, 0.05))

        a1, a2 = int(round(n_a1 * p_a1)), int(round(n_a2 * p_a2))
        b1, b2 = int(round(n_b1 * p_b1)), int(round(n_b2 * p_b2))

        ta1, ta2 = a1 / n_a1, a2 / n_a2
        tb1, tb2 = b1 / n_b1, b2 / n_b2
        tot_a = (a1 + a2) / (n_a1 + n_a2)
        tot_b = (b1 + b2) / (n_b1 + n_b2)

        ejercicios.append({
            "id": f"simpson-{k + 1:02d}",
            "tema": "paradoja-de-simpson",
            "concepto": "paradoja-de-simpson",
            "nivel": 2,
            "titulo": "Cuando el total dice lo contrario",
            "enunciado": (
                f"Se comparan {ctx} según {medida}. Entre los {e1}: "
                f"{ga} resolvió {num(a1, 0)} de {num(n_a1, 0)} y {gb}, "
                f"{num(b1, 0)} de {num(n_b1, 0)}. Entre los {e2}: {ga} "
                f"resolvió {num(a2, 0)} de {num(n_a2, 0)} y {gb}, "
                f"{num(b2, 0)} de {num(n_b2, 0)}."
            ),
            "datos": [],
            "unidad": "",
            "parametros": {
                "a1": a1, "n_a1": n_a1, "a2": a2, "n_a2": n_a2,
                "b1": b1, "n_b1": n_b1, "b2": b2, "n_b2": n_b2,
            },
            "preguntas": [
                {
                    "texto": (
                        f"Entre los {e1}, ¿cuál es {medida} de {ga}, en tanto "
                        f"por uno?"
                    ),
                    "respuesta": redondear(ta1, 6),
                    "tolerancia": 0.002,
                    "solucion": (
                        f"{num(a1, 0)} / {num(n_a1, 0)} = {num(ta1, 4)}, "
                        f"contra {num(tb1, 4)} de {gb}: {ga} va mejor."
                    ),
                    "diagnosticos": [],
                },
                {
                    "texto": (
                        f"Entre los {e2}, ¿cuál es {medida} de {ga}?"
                    ),
                    "respuesta": redondear(ta2, 6),
                    "tolerancia": 0.002,
                    "solucion": (
                        f"{num(a2, 0)} / {num(n_a2, 0)} = {num(ta2, 4)}, "
                        f"contra {num(tb2, 4)} de {gb}: {ga} también va "
                        f"mejor acá."
                    ),
                    "diagnosticos": [],
                },
                {
                    "texto": (
                        f"Juntando los dos grupos, ¿cuál es {medida} total de "
                        f"{ga}?"
                    ),
                    "respuesta": redondear(tot_a, 6),
                    "tolerancia": 0.002,
                    "solucion": (
                        f"({num(a1, 0)} + {num(a2, 0)}) / ({num(n_a1, 0)} + "
                        f"{num(n_a2, 0)}) = {num(tot_a, 4)}."
                    ),
                    "diagnosticos": [
                        {
                            "valor": redondear((ta1 + ta2) / 2, 6),
                            "motivo": (
                                "Se promediaron las dos tasas. No se puede: "
                                "los grupos tienen tamaños muy distintos y "
                                "hay que volver a los conteos."
                            ),
                        },
                    ],
                },
                {
                    "texto": (
                        f"¿Y {medida} total de {gb}?"
                    ),
                    "respuesta": redondear(tot_b, 6),
                    "tolerancia": 0.002,
                    "solucion": (
                        f"({num(b1, 0)} + {num(b2, 0)}) / ({num(n_b1, 0)} + "
                        f"{num(n_b2, 0)}) = {num(tot_b, 4)}. **Es mayor que "
                        f"la de {ga}**, aunque {ga} ganaba en los dos grupos "
                        f"por separado."
                    ),
                    "diagnosticos": [],
                },
                {
                    "texto": (
                        f"¿Cuál conviene elegir? Respondé 1 por {ga} y 2 por "
                        f"{gb}."
                    ),
                    "respuesta": 1.0,
                    "tolerancia": 0.0,
                    "constante": True,
                    "solucion": (
                        f"{ga}, que es mejor en los dos grupos. El total "
                        f"engaña porque {ga} atendió sobre todo {e1}, que son "
                        f"los difíciles, y {gb} sobre todo {e2}. La variable "
                        f"que define el grupo es una **variable de "
                        f"confusión**: hay que comparar dentro de ella y no "
                        f"por encima."
                    ),
                    "diagnosticos": [],
                },
            ],
        })
    return ejercicios


MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def familia_variaciones(rng) -> list[dict]:
    """Mensual, interanual y acumulada, y los puntos porcentuales."""
    ejercicios = []
    for k in range(POR_FAMILIA):
        # Una serie de índice desde diciembre, con inflación mensual variada.
        base = float(rng.integers(900, 2600))
        serie = [base]
        for _ in range(6):
            serie.append(serie[-1] * (1 + float(rng.uniform(0.012, 0.055))))
        serie = [round(v, 1) for v in serie]
        mes = int(rng.integers(3, 7))          # el mes que se pregunta
        dic = serie[0]

        mensual = serie[mes] / serie[mes - 1] - 1
        acumulada = serie[mes] / dic - 1
        # Suma de las mensuales hasta ese mes: el error clásico.
        suma_mensuales = sum(
            serie[i] / serie[i - 1] - 1 for i in range(1, mes + 1)
        )

        # Y el par de porcentajes, para puntos porcentuales.
        p0 = round(float(rng.uniform(5.0, 9.0)), 1)
        p1 = round(p0 + float(rng.uniform(0.8, 2.4)), 1)
        pp = p1 - p0
        relativo = (p1 / p0 - 1) * 100

        texto = " · ".join(
            f"{MESES[i - 1] if i else 'diciembre'} {num(v, 1)}"
            for i, v in enumerate(serie)
        )

        ejercicios.append({
            "id": f"variaciones-{k + 1:02d}",
            "tema": "variaciones",
            "concepto": "variacion-interanual-mensual-acumulada",
            "nivel": 1,
            "titulo": "Variación mensual, acumulada y puntos porcentuales",
            "enunciado": (
                f"Un índice de precios vale: {texto}. Diciembre es el del año "
                f"anterior."
            ),
            "datos": [],
            "unidad": "",
            "parametros": {
                "serie": serie, "mes": mes, "p0": p0, "p1": p1,
            },
            "preguntas": [
                {
                    "texto": (
                        f"¿Cuál fue la variación mensual de "
                        f"{MESES[mes - 1]}, en porcentaje?"
                    ),
                    "respuesta": redondear(mensual * 100, 4),
                    "tolerancia": 0.02,
                    "solucion": (
                        f"{num(serie[mes], 1)} / {num(serie[mes - 1], 1)} − 1 "
                        f"= {num(mensual * 100, 2)} %."
                    ),
                    "diagnosticos": [],
                },
                {
                    "texto": (
                        f"¿Y la variación acumulada desde diciembre hasta "
                        f"{MESES[mes - 1]}?"
                    ),
                    "respuesta": redondear(acumulada * 100, 4),
                    "tolerancia": 0.02,
                    "solucion": (
                        f"Contra diciembre del año anterior: "
                        f"{num(serie[mes], 1)} / {num(dic, 1)} − 1 = "
                        f"{num(acumulada * 100, 2)} %. No es la suma de las "
                        f"mensuales, que daría {num(suma_mensuales * 100, 2)} "
                        f"%: las variaciones se **encadenan**, no se suman."
                    ),
                    "diagnosticos": [
                        {
                            "valor": redondear(suma_mensuales * 100, 4),
                            "motivo": (
                                "Se sumaron las variaciones mensuales. Hay "
                                "que multiplicar los factores: cada mes se "
                                "aplica sobre el nivel ya aumentado."
                            ),
                        },
                    ],
                },
                {
                    "texto": (
                        f"La desocupación pasó del {num(p0, 1)} % al "
                        f"{num(p1, 1)} %. ¿Cuántos **puntos porcentuales** "
                        f"subió?"
                    ),
                    "respuesta": redondear(pp, 4),
                    "tolerancia": 0.01,
                    "solucion": (
                        f"La resta: {num(p1, 1)} − {num(p0, 1)} = "
                        f"{num(pp, 1)} puntos porcentuales."
                    ),
                    "diagnosticos": [
                        {
                            "valor": redondear(relativo, 4),
                            "motivo": (
                                "Eso es la variación relativa, en porcentaje. "
                                "Los puntos porcentuales son la diferencia "
                                "entre dos porcentajes, no su cociente."
                            ),
                        },
                    ],
                },
                {
                    "texto": "¿Y en qué porcentaje aumentó?",
                    "respuesta": redondear(relativo, 4),
                    "tolerancia": 0.05,
                    "solucion": (
                        f"{num(p1, 1)} / {num(p0, 1)} − 1 = "
                        f"{num(relativo, 2)} %. Decir «subió "
                        f"{num(pp, 1)} %» cuando subió {num(pp, 1)} puntos "
                        f"es el error más repetido del periodismo económico: "
                        f"acá la diferencia entre las dos lecturas es de "
                        f"{num(abs(relativo - pp), 1)}."
                    ),
                    "diagnosticos": [
                        {
                            "valor": redondear(pp, 4),
                            "motivo": (
                                "Esos son los puntos porcentuales, la resta. "
                                "El porcentaje de aumento es el cociente."
                            ),
                        },
                    ],
                },
            ],
        })
    return ejercicios


CONTEXTOS_DEFLACTAR = [
    ("el salario promedio del sector", "pesos"),
    ("la recaudación mensual", "millones de pesos"),
    ("el gasto en transporte por hogar", "pesos"),
]


def familia_deflactacion(rng) -> list[dict]:
    """De pesos corrientes a constantes, y la variación real."""
    ejercicios = []
    for k in range(POR_FAMILIA):
        nombre, unidad = CONTEXTOS_DEFLACTAR[k % len(CONTEXTOS_DEFLACTAR)]
        i0 = 100.0
        i1 = round(i0 * (1 + float(rng.uniform(0.35, 1.20))), 1)
        x0 = float(int(rng.integers(180, 900)) * 1000)
        # El nominal sube, pero menos o más que los precios: las dos cosas
        # pasan y conviene que el ejercicio no siempre dé pérdida.
        x1 = round(x0 * (1 + float(rng.uniform(0.20, 1.40))), 0)

        x1_const = x1 * i0 / i1
        var_nominal = x1 / x0 - 1
        var_real = x1_const / x0 - 1
        # El error de restar las dos variaciones.
        var_precios = i1 / i0 - 1
        resta = var_nominal - var_precios

        ejercicios.append({
            "id": f"deflactacion-{k + 1:02d}",
            "tema": "deflactacion",
            "concepto": "deflactacion",
            "nivel": 1,
            "titulo": "Pasar a pesos constantes",
            "enunciado": (
                f"En el período base, {nombre} era de "
                f"${num(x0, 0)} y el índice de precios valía "
                f"{num(i0, 1)}. En el período actual es de ${num(x1, 0)} y el "
                f"índice, {num(i1, 1)}."
            ),
            "datos": [],
            "unidad": unidad,
            "parametros": {"x0": x0, "x1": x1, "i0": i0, "i1": i1},
            "nota": (
                "Para llevar a precios del período base: multiplicar por el "
                "índice de la base y dividir por el del dato."
            ),
            "preguntas": [
                {
                    "texto": (
                        "¿Cuánto vale el dato actual expresado en pesos del "
                        "período base?"
                    ),
                    "respuesta": redondear(x1_const, 2),
                    "tolerancia": 1.0,
                    "solucion": (
                        f"${num(x1, 0)} × {num(i0, 1)} / {num(i1, 1)} = "
                        f"${num(x1_const, 2)}."
                    ),
                    "diagnosticos": [
                        {
                            "valor": redondear(x1 * i1 / i0, 2),
                            "motivo": (
                                "Se multiplicó por el índice del dato y se "
                                "dividió por el de la base: está al revés, y "
                                "en vez de descontar la inflación la agrega "
                                "de nuevo."
                            ),
                        },
                    ],
                },
                {
                    "texto": "¿Cuál fue la variación nominal, en porcentaje?",
                    "respuesta": redondear(var_nominal * 100, 4),
                    "tolerancia": 0.05,
                    "solucion": (
                        f"${num(x1, 0)} / ${num(x0, 0)} − 1 = "
                        f"{num(var_nominal * 100, 2)} %. Es lo que muestra el "
                        f"bolsillo antes de descontar los precios."
                    ),
                    "diagnosticos": [],
                },
                {
                    "texto": "¿Y la variación real?",
                    "respuesta": redondear(var_real * 100, 4),
                    "tolerancia": 0.05,
                    "solucion": (
                        f"Con los dos valores en pesos del período base: "
                        f"${num(x1_const, 2)} / ${num(x0, 0)} − 1 = "
                        f"{num(var_real * 100, 2)} %. "
                        + ("Aunque el monto nominal subió, el poder de compra "
                           "cayó."
                           if var_real < 0
                           else "El aumento le ganó a los precios.")
                    ),
                    "diagnosticos": [
                        {
                            "valor": redondear(resta * 100, 4),
                            "motivo": (
                                "Se restaron las dos variaciones. Es una "
                                "aproximación que solo sirve con números "
                                "chicos: con inflación alta el error es "
                                "grande, porque hay que dividir los "
                                "factores, no restar los porcentajes."
                            ),
                        },
                    ],
                },
            ],
        })
    return ejercicios


def familia_indices_base(rng) -> list[dict]:
    """Construir un índice, cambiar la base y empalmar dos series."""
    ejercicios = []
    for k in range(POR_FAMILIA):
        n = 5
        serie = [float(int(rng.integers(40, 120)))]
        for _ in range(n - 1):
            serie.append(round(serie[-1] * (1 + float(rng.uniform(0.05, 0.3))), 1))
        anios = [2021 + i for i in range(n)]
        base_vieja = 0
        base_nueva = int(rng.integers(2, n))

        idx_vieja = [round(v / serie[base_vieja] * 100, 2) for v in serie]
        idx_nueva = [round(v / serie[base_nueva] * 100, 2) for v in serie]
        # Cambiar de base sin volver al dato original: dividir por el valor
        # que la vieja tiene en el nuevo período.
        factor = 100 / idx_vieja[base_nueva]

        # Empalme: una serie nueva arranca en el último año con otra base.
        solapado = idx_nueva[base_nueva]      # 100 por construcción
        valor_nuevo_sistema = round(float(rng.integers(80, 130)), 1)
        k_empalme = valor_nuevo_sistema / solapado

        ejercicios.append({
            "id": f"indices-base-{k + 1:02d}",
            "tema": "indices-y-base",
            "concepto": "cambio-de-base-y-empalme",
            "nivel": 1,
            "titulo": "Construir un índice y cambiarle la base",
            "enunciado": (
                "Una serie de valores anuales: "
                + " · ".join(f"{a} {num(v, 1)}"
                             for a, v in zip(anios, serie))
                + "."
            ),
            "datos": [],
            "unidad": "",
            "parametros": {
                "serie": serie, "anios": anios,
                "base_vieja": base_vieja, "base_nueva": base_nueva,
                "valor_nuevo_sistema": valor_nuevo_sistema,
            },
            "preguntas": [
                {
                    "texto": (
                        f"Con base {anios[base_vieja]} = 100, ¿cuánto vale el "
                        f"índice en {anios[-1]}?"
                    ),
                    "respuesta": redondear(idx_vieja[-1], 4),
                    "tolerancia": 0.05,
                    "solucion": (
                        f"{num(serie[-1], 1)} / {num(serie[base_vieja], 1)} × "
                        f"100 = {num(idx_vieja[-1], 2)}."
                    ),
                    "diagnosticos": [],
                },
                {
                    "texto": (
                        f"Cambiando la base a {anios[base_nueva]} = 100, "
                        f"¿cuánto vale ahora el índice en {anios[-1]}?"
                    ),
                    "respuesta": redondear(idx_nueva[-1], 4),
                    "tolerancia": 0.1,
                    "solucion": (
                        f"Se divide toda la serie por el valor del nuevo año "
                        f"base y se multiplica por 100: "
                        f"{num(idx_vieja[-1], 2)} / "
                        f"{num(idx_vieja[base_nueva], 2)} × 100 = "
                        f"{num(idx_nueva[-1], 2)}. El coeficiente es "
                        f"{num(factor, 4)} y vale para todos los años."
                    ),
                    "diagnosticos": [
                        {
                            "valor": redondear(
                                idx_vieja[-1] - idx_vieja[base_nueva] + 100, 4
                            ),
                            "motivo": (
                                "Se restó y se sumó 100. Cambiar de base es "
                                "dividir, no restar: un índice es un "
                                "cociente."
                            ),
                        },
                    ],
                },
                {
                    "texto": (
                        f"Un sistema nuevo arranca en {anios[base_nueva]} con "
                        f"el valor {num(valor_nuevo_sistema, 1)}. ¿Cuál es el "
                        f"coeficiente de empalme para llevar la serie vieja "
                        f"—la de base {anios[base_nueva]} = 100— a ese "
                        f"sistema?"
                    ),
                    "respuesta": redondear(k_empalme, 6),
                    "tolerancia": 0.005,
                    "solucion": (
                        f"Sale del período en que las dos se superponen: "
                        f"{num(valor_nuevo_sistema, 1)} / {num(solapado, 1)} "
                        f"= {num(k_empalme, 4)}. Se multiplica por él toda la "
                        f"serie vieja y las dos quedan en la misma escala."
                    ),
                    "diagnosticos": [],
                },
            ],
        })
    return ejercicios


BIENES = [
    ["pan", "carne", "leche"],
    ["nafta", "gas", "electricidad"],
    ["alquiler", "expensas", "internet"],
]


def familia_laspeyres(rng) -> list[dict]:
    """Laspeyres, Paasche, Fisher y el índice de valor."""
    ejercicios = []
    for k in range(POR_FAMILIA):
        bienes = BIENES[k % len(BIENES)]
        m = len(bienes)
        p0 = [float(int(rng.integers(8, 40))) for _ in range(m)]
        q0 = [float(int(rng.integers(20, 120))) for _ in range(m)]
        # La sustitución es el fenómeno que el ejercicio enseña, así que hay
        # que producirla: la cantidad cae MÁS en el bien que más subió. Con
        # precios y cantidades sorteados por separado, Paasche puede quedar
        # por encima de Laspeyres y no se ve nada.
        while True:
            subas = [float(rng.uniform(1.25, 2.7)) for _ in range(m)]
            media_suba = sum(subas) / m
            p1, q1 = [], []
            for a, b, s_ in zip(p0, q0, subas):
                p1.append(round(a * s_, 1))
                # Cuanto más se despega de la suba media, más cae el consumo.
                caida = 0.9 - 0.45 * (s_ - media_suba) / media_suba
                q1.append(float(max(5, int(b * caida))))
            sp_ = lambda u, v_: sum(x * y for x, y in zip(u, v_))
            L_ = sp_(p1, q0) / sp_(p0, q0)
            P_ = sp_(p1, q1) / sp_(p0, q1)
            if P_ < L_ and abs(L_ - P_) * 100 > 1.5:
                break

        L = sum(x * y for x, y in zip(p1, q0)) / sum(
            x * y for x, y in zip(p0, q0)) * 100
        Pa = sum(x * y for x, y in zip(p1, q1)) / sum(
            x * y for x, y in zip(p0, q1)) * 100
        F = math.sqrt(L * Pa)
        V = sum(x * y for x, y in zip(p1, q1)) / sum(
            x * y for x, y in zip(p0, q0)) * 100

        tabla = " · ".join(
            f"{bienes[i]}: p₀ {num(p0[i], 0)}, q₀ {num(q0[i], 0)}, "
            f"p₁ {num(p1[i], 1)}, q₁ {num(q1[i], 0)}"
            for i in range(m)
        )

        ejercicios.append({
            "id": f"laspeyres-{k + 1:02d}",
            "tema": "laspeyres-paasche",
            "concepto": "laspeyres-paasche-fisher",
            "nivel": 2,
            "titulo": "Laspeyres, Paasche y Fisher",
            "enunciado": (
                f"Precios y cantidades de tres bienes en el período base (0) "
                f"y en el actual (1): {tabla}."
            ),
            "datos": [],
            "unidad": "",
            "parametros": {"p0": p0, "q0": q0, "p1": p1, "q1": q1},
            "preguntas": [
                {
                    "texto": "¿Cuánto vale el índice de Laspeyres?",
                    "respuesta": redondear(L, 4),
                    "tolerancia": 0.05,
                    "solucion": (
                        f"Pesa con las cantidades **del período base**: "
                        f"Σp₁q₀ / Σp₀q₀ × 100 = {num(L, 2)}. Es el que usa "
                        f"el IPC, porque la canasta se fija de antemano."
                    ),
                    "diagnosticos": [
                        {
                            "valor": redondear(Pa, 4),
                            "motivo": (
                                "Se usaron las cantidades actuales: ese es "
                                "Paasche. Laspeyres fija la canasta en el "
                                "período base."
                            ),
                        },
                    ],
                },
                {
                    "texto": "¿Y el de Paasche?",
                    "respuesta": redondear(Pa, 4),
                    "tolerancia": 0.05,
                    "solucion": (
                        f"Σp₁q₁ / Σp₀q₁ × 100 = {num(Pa, 2)}. Da menos que "
                        f"Laspeyres —{num(L, 2)}— porque la gente se corre "
                        f"hacia lo que subió menos, y Paasche recoge ese "
                        f"cambio de consumo."
                    ),
                    "diagnosticos": [
                        {
                            "valor": redondear(L, 4),
                            "motivo": "Ese es Laspeyres, con la canasta vieja.",
                        },
                    ],
                },
                {
                    "texto": "¿Cuánto vale el índice de Fisher?",
                    "respuesta": redondear(F, 4),
                    "tolerancia": 0.05,
                    "solucion": (
                        f"Es la media **geométrica** de los dos: "
                        f"√({num(L, 2)} × {num(Pa, 2)}) = {num(F, 2)}, y "
                        f"queda entre ambos."
                    ),
                    "diagnosticos": [
                        {
                            "valor": redondear((L + Pa) / 2, 4),
                            "motivo": (
                                "Es la media aritmética. Fisher usa la "
                                "geométrica, que para índices es la que "
                                "conserva las propiedades que se le piden."
                            ),
                        },
                    ],
                },
                {
                    "texto": "¿Y el índice de valor?",
                    "respuesta": redondear(V, 4),
                    "tolerancia": 0.05,
                    "solucion": (
                        f"Σp₁q₁ / Σp₀q₀ × 100 = {num(V, 2)}. Mezcla el "
                        f"cambio de precios con el de cantidades: es lo que "
                        f"efectivamente se gastó, no cuánto subieron los "
                        f"precios."
                    ),
                    "diagnosticos": [],
                },
            ],
        })
    return ejercicios


CONTEXTOS_RAZON = [
    ("varones", "mujeres", "personas"),
    ("viviendas con conexión", "viviendas sin conexión", "viviendas"),
    ("matriculados en turno mañana", "matriculados en turno tarde",
     "estudiantes"),
]


def familia_razon(rng) -> list[dict]:
    """Razón, proporción y tasa: tres cocientes distintos."""
    ejercicios = []
    for k in range(POR_FAMILIA):
        a_nom, b_nom, unidad = CONTEXTOS_RAZON[k % len(CONTEXTOS_RAZON)]
        a = int(rng.integers(1800, 9000))
        b = int(rng.integers(1800, 9000))
        total = a + b
        eventos = int(rng.integers(12, 90))

        razon = a / b
        proporcion = a / total
        por_mil = eventos / total * 1000
        por_cien_mil = eventos / total * 100000

        ejercicios.append({
            "id": f"razon-{k + 1:02d}",
            "tema": "razon-proporcion-tasa",
            "concepto": "razon-proporcion-tasa",
            "nivel": 1,
            "titulo": "Razón, proporción y tasa",
            "enunciado": (
                f"En una localidad hay {num(a, 0)} {a_nom} y {num(b, 0)} "
                f"{b_nom}, o sea {num(total, 0)} {unidad} en total. Durante "
                f"el año se registraron {num(eventos, 0)} defunciones."
            ),
            "datos": [],
            "unidad": "",
            "parametros": {"a": a, "b": b, "eventos": eventos},
            "nota": (
                "Las tres se calculan con los mismos números y no son lo "
                "mismo: lo que cambia es qué va en el denominador."
            ),
            "preguntas": [
                {
                    "texto": f"¿Cuál es la razón de {a_nom} a {b_nom}?",
                    "respuesta": redondear(razon, 6),
                    "tolerancia": 0.002,
                    "solucion": (
                        f"Una parte sobre **la otra**, no sobre el total: "
                        f"{num(a, 0)} / {num(b, 0)} = {num(razon, 4)}. Se "
                        f"lee «{num(razon, 2)} {a_nom} por cada "
                        f"{b_nom[:-1] if b_nom.endswith('s') else b_nom}»."
                    ),
                    "diagnosticos": [
                        {
                            "valor": redondear(proporcion, 6),
                            "motivo": (
                                "Se dividió por el total: eso es la "
                                "proporción. En una razón el denominador es "
                                "la otra parte, y por eso puede pasar de 1."
                            ),
                        },
                    ],
                },
                {
                    "texto": f"¿Y la proporción de {a_nom} sobre el total?",
                    "respuesta": redondear(proporcion, 6),
                    "tolerancia": 0.002,
                    "solucion": (
                        f"{num(a, 0)} / {num(total, 0)} = "
                        f"{num(proporcion, 4)}, o sea el "
                        f"{num(proporcion * 100, 1)} %. Una proporción "
                        f"siempre está entre 0 y 1; una razón, no."
                    ),
                    "diagnosticos": [
                        {
                            "valor": redondear(razon, 6),
                            "motivo": "Esa es la razón, con la otra parte abajo.",
                        },
                    ],
                },
                {
                    "texto": (
                        "¿Cuál es la tasa bruta de mortalidad, por mil?"
                    ),
                    "respuesta": redondear(por_mil, 4),
                    "tolerancia": 0.02,
                    "solucion": (
                        f"{num(eventos, 0)} / {num(total, 0)} × 1.000 = "
                        f"{num(por_mil, 2)} por mil. La tasa relaciona los "
                        f"eventos con la población expuesta, no dos partes "
                        f"entre sí."
                    ),
                    "diagnosticos": [],
                },
                {
                    "texto": "¿Y la misma tasa expresada por cien mil?",
                    "respuesta": redondear(por_cien_mil, 4),
                    "tolerancia": 0.5,
                    "solucion": (
                        f"Es la misma tasa con otra escala: "
                        f"{num(por_mil, 2)} × 100 = {num(por_cien_mil, 1)} "
                        f"por cien mil. Cambiar la escala no cambia el "
                        f"fenómeno; se usa la que evita arrastrar ceros o "
                        f"decimales."
                    ),
                    "diagnosticos": [
                        {
                            "valor": redondear(por_mil * 10, 4),
                            "motivo": (
                                "Se multiplicó por 10 en vez de por 100: de "
                                "«por mil» a «por cien mil» hay dos órdenes "
                                "de magnitud."
                            ),
                        },
                    ],
                },
            ],
        })
    return ejercicios


def familia_laborales(rng) -> list[dict]:
    """Actividad, empleo y desocupación, y el denominador de cada una."""
    ejercicios = []
    for k in range(POR_FAMILIA):
        total = int(rng.integers(90, 320)) * 1000
        pea = int(total * float(rng.uniform(0.44, 0.52)))
        desocupados = int(pea * float(rng.uniform(0.05, 0.12)))
        ocupados = pea - desocupados

        t_act = pea / total
        t_emp = ocupados / total
        t_des = desocupados / pea
        # El error clásico: dividir los desocupados por la población total.
        t_des_mal = desocupados / total

        # Un segundo momento donde la desocupación baja porque gente sale
        # de la PEA, no porque consiga trabajo.
        salen = int(desocupados * float(rng.uniform(0.18, 0.35)))
        pea2 = pea - salen
        desoc2 = desocupados - salen
        t_des2 = desoc2 / pea2
        t_emp2 = ocupados / total

        ejercicios.append({
            "id": f"laborales-{k + 1:02d}",
            "tema": "tasas-laborales",
            "concepto": "indicadores-socioeconomicos",
            "nivel": 1,
            "titulo": "Las tres tasas del mercado de trabajo",
            "enunciado": (
                f"En un aglomerado hay {num(total, 0)} personas. La población "
                f"económicamente activa es de {num(pea, 0)}, de las cuales "
                f"{num(desocupados, 0)} están desocupadas."
            ),
            "datos": [],
            "unidad": "",
            "parametros": {
                "total": total, "pea": pea, "desocupados": desocupados,
                "salen": salen,
            },
            "nota": (
                "Dos de las tres tasas se calculan sobre la población total "
                "y la tercera no. Esa excepción es la fuente de casi todos "
                "los malentendidos."
            ),
            "preguntas": [
                {
                    "texto": "¿Cuál es la tasa de actividad?",
                    "respuesta": redondear(t_act * 100, 4),
                    "tolerancia": 0.05,
                    "solucion": (
                        f"PEA sobre población total: {num(pea, 0)} / "
                        f"{num(total, 0)} = {num(t_act * 100, 1)} %."
                    ),
                    "diagnosticos": [],
                },
                {
                    "texto": "¿Y la tasa de empleo?",
                    "respuesta": redondear(t_emp * 100, 4),
                    "tolerancia": 0.05,
                    "solucion": (
                        f"Ocupados sobre población total: "
                        f"{num(ocupados, 0)} / {num(total, 0)} = "
                        f"{num(t_emp * 100, 1)} %. El denominador es el mismo "
                        f"que en la actividad."
                    ),
                    "diagnosticos": [],
                },
                {
                    "texto": "¿Cuál es la tasa de desocupación?",
                    "respuesta": redondear(t_des * 100, 4),
                    "tolerancia": 0.05,
                    "solucion": (
                        f"Acá el denominador **cambia**: los desocupados se "
                        f"dividen por la PEA, no por la población total. "
                        f"{num(desocupados, 0)} / {num(pea, 0)} = "
                        f"{num(t_des * 100, 1)} %."
                    ),
                    "diagnosticos": [
                        {
                            "valor": redondear(t_des_mal * 100, 4),
                            "motivo": (
                                "Se dividió por la población total. Es el "
                                "error más frecuente del indicador: los "
                                "chicos y los jubilados no están buscando "
                                "trabajo, así que no pueden estar "
                                "desocupados."
                            ),
                        },
                    ],
                },
                {
                    "texto": (
                        f"Al trimestre siguiente, {num(salen, 0)} personas "
                        f"dejan de buscar trabajo y salen de la PEA. Nadie "
                        f"consigue empleo. ¿Cuál es la nueva tasa de "
                        f"desocupación?"
                    ),
                    "respuesta": redondear(t_des2 * 100, 4),
                    "tolerancia": 0.05,
                    "solucion": (
                        f"{num(desoc2, 0)} / {num(pea2, 0)} = "
                        f"{num(t_des2 * 100, 1)} %, contra "
                        f"{num(t_des * 100, 1)} % del trimestre anterior. "
                        f"**Bajó sin que nadie consiguiera trabajo**: la tasa "
                        f"de empleo quedó igual, en {num(t_emp2 * 100, 1)} %. "
                        f"Por eso las tres se leen juntas y nunca una sola."
                    ),
                    "diagnosticos": [],
                },
            ],
        })
    return ejercicios


CONTEXTOS_ESTANDARIZAR = [
    ("dos provincias", "Provincia A", "Provincia B", "mortalidad"),
    ("dos hospitales", "Hospital A", "Hospital B", "letalidad"),
]

GRUPOS_EDAD = ["0 a 14", "15 a 44", "45 a 64", "65 y más"]


def familia_estandarizacion(rng) -> list[dict]:
    """La tasa cruda dice una cosa y la estandarizada, la contraria."""
    ejercicios = []
    for k in range(POR_FAMILIA):
        ctx, na, nb, medida = CONTEXTOS_ESTANDARIZAR[
            k % len(CONTEXTOS_ESTANDARIZAR)
        ]
        # Tasas específicas que crecen con la edad, y A mejor en todas.
        while True:
            base = [float(rng.uniform(0.4, 1.2)), float(rng.uniform(1.2, 3.0)),
                    float(rng.uniform(5.0, 11.0)), float(rng.uniform(28.0, 55.0))]
            tasas_a = [round(t, 1) for t in base]
            tasas_b = [round(t * float(rng.uniform(1.10, 1.35)), 1)
                       for t in base]
            # A envejecida, B joven: ahí la cruda se da vuelta.
            pa = [0.12, 0.30, 0.25, 0.33]
            pb = [0.28, 0.45, 0.19, 0.08]
            na_pob = [int(round(p * 100000)) for p in pa]
            nb_pob = [int(round(p * 100000)) for p in pb]
            ref = [(x + y) / 2 for x, y in zip(na_pob, nb_pob)]
            tot_ref = sum(ref)
            p_ref = [r / tot_ref for r in ref]

            cruda_a = sum(t * n_ for t, n_ in zip(tasas_a, na_pob)) / sum(na_pob)
            cruda_b = sum(t * n_ for t, n_ in zip(tasas_b, nb_pob)) / sum(nb_pob)
            est_a = sum(t * p for t, p in zip(tasas_a, p_ref))
            est_b = sum(t * p for t, p in zip(tasas_b, p_ref))
            # La paradoja: cruda peor en A, estandarizada mejor en A.
            if cruda_a > cruda_b and est_a < est_b:
                break

        tabla = " · ".join(
            f"{GRUPOS_EDAD[i]}: {na} {num(tasas_a[i], 1)} en "
            f"{num(na_pob[i], 0)}, {nb} {num(tasas_b[i], 1)} en "
            f"{num(nb_pob[i], 0)}"
            for i in range(4)
        )

        ejercicios.append({
            "id": f"estandarizacion-{k + 1:02d}",
            "tema": "estandarizacion",
            "concepto": "estandarizacion-directa",
            "nivel": 2,
            "titulo": "Estandarizar para poder comparar",
            "enunciado": (
                f"Se comparan {ctx} según su {medida}, por mil. Las tasas "
                f"específicas por grupo de edad y la población de cada grupo "
                f"son: {tabla}. Como población de referencia se usa la suma "
                f"de las dos."
            ),
            "datos": [],
            "unidad": "por mil",
            "parametros": {
                "tasas_a": tasas_a, "tasas_b": tasas_b,
                "na_pob": na_pob, "nb_pob": nb_pob,
            },
            "preguntas": [
                {
                    "texto": f"¿Cuál es la tasa cruda de {na}?",
                    "respuesta": redondear(cruda_a, 4),
                    "tolerancia": 0.02,
                    "solucion": (
                        f"Es el promedio de las específicas pesado por la "
                        f"población **propia**: {num(cruda_a, 2)} por mil, "
                        f"contra {num(cruda_b, 2)} de {nb}. Así vista, "
                        f"{na} está peor."
                    ),
                    "diagnosticos": [
                        {
                            "valor": redondear(sum(tasas_a) / 4, 4),
                            "motivo": (
                                "Se promediaron las cuatro tasas sin pesar "
                                "por la población de cada grupo. Los grupos "
                                "tienen tamaños muy distintos."
                            ),
                        },
                    ],
                },
                {
                    "texto": (
                        f"Estandarizando por edad con la población de "
                        f"referencia, ¿cuál es la tasa de {na}?"
                    ),
                    "respuesta": redondear(est_a, 4),
                    "tolerancia": 0.02,
                    "solucion": (
                        f"Se aplican las tasas de {na} a la estructura de "
                        f"edad de la referencia: Σ tasa × proporción = "
                        f"{num(est_a, 2)} por mil."
                    ),
                    "diagnosticos": [
                        {
                            "valor": redondear(cruda_a, 4),
                            "motivo": (
                                "Es la tasa cruda, pesada con la población "
                                "propia. Estandarizar es usar la misma "
                                "estructura para las dos."
                            ),
                        },
                    ],
                },
                {
                    "texto": f"¿Y la de {nb} estandarizada?",
                    "respuesta": redondear(est_b, 4),
                    "tolerancia": 0.02,
                    "solucion": (
                        f"{num(est_b, 2)} por mil. **Mayor que la de {na}**, "
                        f"al revés de lo que decían las crudas."
                    ),
                    "diagnosticos": [],
                },
                {
                    "texto": (
                        f"¿Cuál tiene peor {medida} de verdad? Respondé 1 por "
                        f"{na} y 2 por {nb}."
                    ),
                    "respuesta": 2.0,
                    "tolerancia": 0.0,
                    "constante": True,
                    "solucion": (
                        f"{nb}: tiene peores tasas en **los cuatro grupos de "
                        f"edad**. La cruda de {na} salía más alta solo "
                        f"porque su población es más envejecida, y la "
                        f"{medida} sube con la edad. La edad es una variable "
                        f"de confusión y estandarizar es la forma de sacarla "
                        f"del medio."
                    ),
                    "diagnosticos": [],
                },
            ],
        })
    return ejercicios


def familia_gini(rng) -> list[dict]:
    """El Gini a partir de la participación de cada quintil."""
    ejercicios = []
    for k in range(POR_FAMILIA):
        # Participaciones crecientes que suman 100.
        crudo = sorted(float(rng.uniform(1, 10)) for _ in range(5))
        s = sum(crudo)
        partes = [round(c / s * 100, 1) for c in crudo]
        partes[-1] = round(100 - sum(partes[:-1]), 1)

        # Lorenz: p acumulada de población, q acumulada de ingreso.
        p = [0.0] + [0.2 * (i + 1) for i in range(5)]
        q = [0.0]
        for x in partes:
            q.append(q[-1] + x / 100)
        gini = 1 - sum((q[i + 1] + q[i]) * (p[i + 1] - p[i])
                       for i in range(5))
        palma = partes[-1] / (partes[0] + partes[1])
        razon_extremos = partes[-1] / partes[0]

        ejercicios.append({
            "id": f"gini-{k + 1:02d}",
            "tema": "gini",
            "concepto": "curva-de-lorenz-y-gini",
            "nivel": 2,
            "titulo": "Gini a partir de los quintiles",
            "enunciado": (
                "La participación de cada quintil en el ingreso total, del "
                "más pobre al más rico, es: "
                + " · ".join(f"Q{i + 1} {num(v, 1)} %"
                             for i, v in enumerate(partes))
                + "."
            ),
            "datos": [],
            "unidad": "",
            "parametros": {"partes": partes},
            "nota": (
                "Con datos agrupados el Gini se calcula por trapecios sobre "
                "la curva de Lorenz: G = 1 − Σ (qᵢ + qᵢ₋₁) · Δp."
            ),
            "preguntas": [
                {
                    "texto": (
                        "¿Qué porcentaje del ingreso acumula el 40 % más "
                        "pobre?"
                    ),
                    "respuesta": redondear(partes[0] + partes[1], 4),
                    "tolerancia": 0.05,
                    "solucion": (
                        f"Los dos primeros quintiles: {num(partes[0], 1)} + "
                        f"{num(partes[1], 1)} = "
                        f"{num(partes[0] + partes[1], 1)} %. Es un punto de "
                        f"la curva de Lorenz: el de abscisa 0,40."
                    ),
                    "diagnosticos": [],
                },
                {
                    "texto": "¿Cuánto vale el coeficiente de Gini?",
                    "respuesta": redondear(gini, 4),
                    "tolerancia": 0.005,
                    "solucion": (
                        f"Por trapecios sobre la curva: G = "
                        f"{num(gini, 4)}. Va de 0 —todos igual— a 1 —uno se "
                        f"queda con todo—."
                    ),
                    "diagnosticos": [
                        {
                            "valor": redondear(1 - gini, 4),
                            "motivo": (
                                "Es el complemento: el área **bajo** la "
                                "curva en lugar de la que queda entre la "
                                "curva y la diagonal."
                            ),
                        },
                    ],
                },
                {
                    "texto": (
                        "¿Cuántas veces el ingreso del quintil más rico es "
                        "el del más pobre?"
                    ),
                    "respuesta": redondear(razon_extremos, 4),
                    "tolerancia": 0.05,
                    "solucion": (
                        f"{num(partes[-1], 1)} / {num(partes[0], 1)} = "
                        f"{num(razon_extremos, 2)} veces. Es la brecha de "
                        f"ingresos entre extremos, y dice algo que el Gini "
                        f"no: **dónde** está la desigualdad."
                    ),
                    "diagnosticos": [
                        {
                            "valor": redondear(palma, 4),
                            "motivo": (
                                "Eso es el índice de Palma: el 10 % más rico "
                                "sobre el 40 % más pobre. Acá, con "
                                "quintiles, sería el quinto sobre los dos "
                                "primeros."
                            ),
                        },
                    ],
                },
            ],
        })
    return ejercicios


# Las cuatro formas van escritas, no derivadas: cortarle la «s» al plural
# daba «cada paradas del recorrido» y mezclar géneros daba «cada uno de las
# 3 zonas». Salió mal en 8 de los 12 antes de escribirlas una por una.
CONTEXTOS_COMBI = [
    ("postulantes", "cargos", "cargo", "una comisión"),
    ("encuestadores", "turnos de campo", "turno de campo", "un equipo"),
    ("voluntarios", "puestos de atención", "puesto de atención",
     "una cuadrilla"),
]


def familia_combinatoria(rng) -> list[dict]:
    """Contar: el orden importa o no, se repite o no."""
    ejercicios = []
    for k in range(POR_FAMILIA):
        gente, puestos, puesto, grupo = CONTEXTOS_COMBI[
            k % len(CONTEXTOS_COMBI)
        ]
        n = int(rng.integers(7, 12))
        r = int(rng.integers(3, 5))

        variaciones = math.perm(n, r)
        combinaciones = math.comb(n, r)
        permutaciones = math.factorial(n)
        con_repeticion = n ** r

        ejercicios.append({
            "id": f"combinatoria-{k + 1:02d}",
            "tema": "combinatoria",
            "concepto": "permutaciones-y-variaciones",
            "nivel": 1,
            "titulo": "Contar de cuántas maneras",
            "enunciado": (
                f"Hay {num(n, 0)} {gente} y {num(r, 0)} {puestos}."
            ),
            "datos": [],
            "unidad": "",
            "parametros": {"n": n, "r": r},
            "nota": (
                "La pregunta que decide la fórmula es si **el orden "
                "importa**, y después si un mismo elemento puede repetirse."
            ),
            "preguntas": [
                {
                    "texto": (
                        f"Si los {num(r, 0)} {puestos} son distintos y "
                        f"nadie puede ocupar dos, ¿de cuántas maneras se "
                        f"asignan?"
                    ),
                    "respuesta": float(variaciones),
                    "tolerancia": 0.0,
                    "solucion": (
                        f"El orden importa —los puestos son distintos— y no "
                        f"hay repetición: son variaciones. "
                        f"V({num(n, 0)},{num(r, 0)}) = "
                        + " × ".join(str(n - i) for i in range(r))
                        + f" = {num(variaciones, 0)}."
                    ),
                    "diagnosticos": [
                        {
                            "valor": float(combinaciones),
                            "motivo": (
                                "Eso cuenta los grupos sin orden. Acá los "
                                "puestos son distintos, así que asignar a "
                                "Ana al primero y a Bruno al segundo no es "
                                "lo mismo que al revés."
                            ),
                        },
                    ],
                },
                {
                    "texto": (
                        f"Si en cambio se arma {grupo} de {num(r, 0)} "
                        f"personas, sin cargos ni jerarquía, ¿cuántos grupos "
                        f"distintos hay?"
                    ),
                    "respuesta": float(combinaciones),
                    "tolerancia": 0.0,
                    "solucion": (
                        f"Ahora el orden no importa: son combinaciones. "
                        f"C({num(n, 0)},{num(r, 0)}) = "
                        f"{num(variaciones, 0)} / {num(r, 0)}! = "
                        f"{num(combinaciones, 0)}. Es la cuenta anterior "
                        f"dividida por las {num(math.factorial(r), 0)} "
                        f"maneras de ordenar cada grupo."
                    ),
                    "diagnosticos": [
                        {
                            "valor": float(variaciones),
                            "motivo": (
                                "Son las variaciones: cuentan cada grupo "
                                "tantas veces como maneras hay de ordenarlo."
                            ),
                        },
                    ],
                },
                {
                    "texto": (
                        f"¿De cuántas maneras se pueden ordenar en fila los "
                        f"{num(n, 0)} {gente}?"
                    ),
                    "respuesta": float(permutaciones),
                    "tolerancia": 0.0,
                    "solucion": (
                        f"Son todos los elementos ordenados: "
                        f"{num(n, 0)}! = {num(permutaciones, 0)}."
                    ),
                    "diagnosticos": [],
                },
                {
                    "texto": (
                        f"Y si cada {puesto} se sortea por separado, de modo "
                        f"que una misma persona puede salir más de una vez, "
                        f"¿cuántos resultados hay?"
                    ),
                    "respuesta": float(con_repeticion),
                    "tolerancia": 0.0,
                    "solucion": (
                        f"Con repetición: cada uno de los {num(r, 0)} "
                        f"sorteos tiene {num(n, 0)} resultados posibles, "
                        f"así que son "
                        + " × ".join([num(n, 0)] * r)
                        + f" = {num(con_repeticion, 0)}. Es el principio de "
                        f"multiplicación en su forma más directa."
                    ),
                    "diagnosticos": [
                        {
                            "valor": float(variaciones),
                            "motivo": (
                                "Esas son las variaciones sin repetición: "
                                "suponen que quien ya salió no puede volver "
                                "a salir."
                            ),
                        },
                    ],
                },
            ],
        })
    return ejercicios


CONTEXTOS_REGLAS = [
    ("tener obra social", "tener empleo registrado"),
    ("haber terminado el secundario", "usar transporte público"),
    ("tener conexión a internet", "tener computadora en el hogar"),
]


def familia_reglas(rng) -> list[dict]:
    """Suma, producto, excluyentes e independientes."""
    ejercicios = []
    for k in range(POR_FAMILIA):
        na, nb = CONTEXTOS_REGLAS[k % len(CONTEXTOS_REGLAS)]
        # Se arma con una tabla de conteos para que todo cierre.
        #
        # Y se repite hasta que P(A|B) difiera de P(A): si los dos eventos
        # salen casi independientes, la última pregunta devuelve el mismo
        # número que la primera y el alumno no ve que condicionar cambia
        # algo. Pasó en 3 de los 12 antes de imponerlo acá.
        while True:
            n = int(rng.integers(400, 1200))
            ambos = int(n * float(rng.uniform(0.15, 0.30)))
            solo_a = int(n * float(rng.uniform(0.15, 0.28)))
            solo_b = int(n * float(rng.uniform(0.15, 0.28)))
            ninguno = n - ambos - solo_a - solo_b
            if ninguno <= 0:
                continue
            if abs(ambos / (ambos + solo_b) - (ambos + solo_a) / n) > 0.04:
                break

        pa = (ambos + solo_a) / n
        pb = (ambos + solo_b) / n
        p_ambos = ambos / n
        p_union = pa + pb - p_ambos
        p_union_mal = pa + pb
        p_si_indep = pa * pb
        p_a_dado_b = p_ambos / pb

        ejercicios.append({
            "id": f"reglas-{k + 1:02d}",
            "tema": "reglas-de-probabilidad",
            "concepto": "regla-de-la-suma",
            "nivel": 1,
            "titulo": "Sumar, multiplicar y no confundirse",
            "enunciado": (
                f"En un grupo de {num(n, 0)} personas: {num(ambos, 0)} "
                f"cumplen A ({na}) y B ({nb}) a la vez, {num(solo_a, 0)} "
                f"solo A, {num(solo_b, 0)} solo B, y {num(ninguno, 0)} "
                f"ninguna de las dos."
            ),
            "datos": [],
            "unidad": "",
            "parametros": {
                "n": n, "ambos": ambos, "solo_a": solo_a, "solo_b": solo_b,
            },
            "preguntas": [
                {
                    "texto": "¿Cuál es la probabilidad de A?",
                    "respuesta": redondear(pa, 6),
                    "tolerancia": 0.002,
                    "solucion": (
                        f"Los que cumplen A son los de «solo A» más los de "
                        f"«ambos»: ({num(solo_a, 0)} + {num(ambos, 0)}) / "
                        f"{num(n, 0)} = {num(pa, 4)}."
                    ),
                    "diagnosticos": [
                        {
                            "valor": redondear(solo_a / n, 6),
                            "motivo": (
                                "Se contaron solo los que cumplen A **y no** "
                                "B. Los que cumplen las dos también cumplen "
                                "A."
                            ),
                        },
                    ],
                },
                {
                    "texto": "¿Y la probabilidad de A o B, al menos una?",
                    "respuesta": redondear(p_union, 6),
                    "tolerancia": 0.002,
                    "solucion": (
                        f"P(A) + P(B) − P(A∩B) = {num(pa, 4)} + "
                        f"{num(pb, 4)} − {num(p_ambos, 4)} = "
                        f"{num(p_union, 4)}. Hay que restar la intersección "
                        f"o se cuenta dos veces a quienes cumplen las dos."
                    ),
                    "diagnosticos": [
                        {
                            "valor": redondear(p_union_mal, 6),
                            "motivo": (
                                "Se sumaron las dos sin restar la "
                                "intersección. Eso vale solo si los eventos "
                                "son mutuamente excluyentes, y acá "
                                + num(ambos, 0) + " personas cumplen ambos."
                            ),
                        },
                    ],
                },
                {
                    "texto": (
                        "Si A y B fueran independientes, ¿cuánto valdría "
                        "P(A∩B)?"
                    ),
                    "respuesta": redondear(p_si_indep, 6),
                    "tolerancia": 0.002,
                    "solucion": (
                        f"Sería el producto: {num(pa, 4)} × {num(pb, 4)} = "
                        f"{num(p_si_indep, 4)}. El valor observado es "
                        f"{num(p_ambos, 4)}, así que "
                        + ("no son independientes."
                           if abs(p_si_indep - p_ambos) > 0.01
                           else "son casi independientes.")
                    ),
                    "diagnosticos": [],
                },
                {
                    "texto": "¿Cuál es la probabilidad de A dado B?",
                    "respuesta": redondear(p_a_dado_b, 6),
                    "tolerancia": 0.002,
                    "solucion": (
                        f"P(A∩B) / P(B) = {num(p_ambos, 4)} / "
                        f"{num(pb, 4)} = {num(p_a_dado_b, 4)}. El "
                        f"denominador deja de ser el grupo entero y pasa a "
                        f"ser el de los que cumplen B."
                    ),
                    "diagnosticos": [
                        {
                            "valor": redondear(p_ambos, 6),
                            "motivo": (
                                "Esa es la probabilidad conjunta, sobre el "
                                "total. La condicional divide por P(B)."
                            ),
                        },
                    ],
                },
            ],
        })
    return ejercicios


CONTEXTOS_BAYES = [
    ("dos máquinas", "Máquina A", "Máquina B", "piezas", "defectuosa"),
    ("dos proveedores", "Proveedor A", "Proveedor B", "lotes", "fuera de norma"),
]


def familia_bayes(rng) -> list[dict]:
    """Probabilidad total y Bayes sobre un árbol de dos ramas."""
    ejercicios = []
    for k in range(POR_FAMILIA):
        ctx, na, nb, cosa, malo = CONTEXTOS_BAYES[k % len(CONTEXTOS_BAYES)]
        # El error que el ejercicio quiere provocar es promediar las dos
        # tasas sin pesar. Si ese promedio cae casi encima de la respuesta
        # buena, el diagnóstico se descarta y la pregunta pierde el punto:
        # la diferencia vale (pa − 0,5)(da − db), así que se exige que sea
        # visible en lugar de confiar en que salga.
        while True:
            pa = round(float(rng.uniform(0.55, 0.80)), 2)
            pb = round(1 - pa, 2)
            da = round(float(rng.uniform(0.02, 0.06)), 3)
            db = round(float(rng.uniform(0.08, 0.18)), 3)
            if abs((pa - 0.5) * (db - da)) > 0.005:
                break

        total = pa * da + pb * db
        post_a = pa * da / total
        post_b = pb * db / total

        ejercicios.append({
            "id": f"bayes-{k + 1:02d}",
            "tema": "bayes",
            "concepto": "teorema-de-bayes",
            "nivel": 2,
            "titulo": "Probabilidad total y Bayes",
            "enunciado": (
                f"Las {cosa} vienen de {ctx}. {na} aporta el "
                f"{num(pa * 100, 0)} % de la producción y {nb} el "
                f"{num(pb * 100, 0)} %. De lo que produce {na}, el "
                f"{num(da * 100, 1)} % sale {malo}; de {nb}, el "
                f"{num(db * 100, 1)} %."
            ),
            "datos": [],
            "unidad": "",
            "parametros": {"pa": pa, "pb": pb, "da": da, "db": db},
            "preguntas": [
                {
                    "texto": (
                        f"Si se toma una pieza al azar, ¿cuál es la "
                        f"probabilidad de que salga {malo}?"
                    ),
                    "respuesta": redondear(total, 6),
                    "tolerancia": 0.001,
                    "solucion": (
                        f"Probabilidad total: {num(pa, 2)} × {num(da, 3)} + "
                        f"{num(pb, 2)} × {num(db, 3)} = {num(total, 4)}. Es "
                        f"el promedio de las dos tasas **pesado por cuánto "
                        f"aporta cada máquina**."
                    ),
                    "diagnosticos": [
                        {
                            "valor": redondear((da + db) / 2, 6),
                            "motivo": (
                                "Se promediaron las dos tasas sin pesar. "
                                "Las máquinas no producen lo mismo."
                            ),
                        },
                    ],
                },
                {
                    "texto": (
                        f"Sale una pieza {malo}. ¿Cuál es la probabilidad de "
                        f"que venga de {nb}?"
                    ),
                    "respuesta": redondear(post_b, 6),
                    "tolerancia": 0.002,
                    "solucion": (
                        f"Bayes: {num(pb, 2)} × {num(db, 3)} / "
                        f"{num(total, 4)} = {num(post_b, 4)}. {nb} produce "
                        f"solo el {num(pb * 100, 0)} % del total y aporta el "
                        f"{num(post_b * 100, 1)} % de las fallas."
                    ),
                    "diagnosticos": [
                        {
                            "valor": redondear(db, 6),
                            "motivo": (
                                "Esa es la probabilidad de que una pieza de "
                                "B salga mal, que es la condicional al "
                                "revés. Acá se pregunta por el origen dado "
                                "que ya se sabe que está mal."
                            ),
                        },
                        {
                            "valor": redondear(pb, 6),
                            "motivo": (
                                "Esa es la probabilidad previa, antes de "
                                "saber que la pieza salió mal. El dato "
                                "cambia la creencia."
                            ),
                        },
                    ],
                },
                {
                    "texto": f"¿Y de que venga de {na}?",
                    "respuesta": redondear(post_a, 6),
                    "tolerancia": 0.002,
                    "solucion": (
                        f"{num(post_a, 4)}, y las dos posteriores suman 1: "
                        f"la pieza vino de una de las dos."
                    ),
                    "diagnosticos": [],
                },
            ],
        })
    return ejercicios


def familia_intuicion(rng) -> list[dict]:
    """Tres cuentas cuyo resultado nadie adivina."""
    ejercicios = []
    for k in range(POR_FAMILIA):
        n_pers = int(rng.integers(18, 45))
        distintos = 1.0
        for i in range(n_pers):
            distintos *= (365 - i) / 365
        coincide = 1 - distintos

        rachas = int(rng.integers(4, 8))
        p_racha = 0.5 ** rachas

        # Falacia de la conjunción, con números que la hacen visible.
        p_una = round(float(rng.uniform(0.25, 0.45)), 2)
        p_otra = round(float(rng.uniform(0.15, 0.35)), 2)
        p_conj = p_una * p_otra

        ejercicios.append({
            "id": f"intuicion-{k + 1:02d}",
            "tema": "probabilidad-contraintuitiva",
            "concepto": "falacias-de-probabilidad",
            "nivel": 2,
            "titulo": "Cuentas que la intuición falla",
            "enunciado": (
                f"Tres preguntas donde la respuesta suele sorprender. En un "
                f"aula hay {num(n_pers, 0)} personas."
            ),
            "datos": [],
            "unidad": "",
            "parametros": {
                "n_pers": n_pers, "rachas": rachas,
                "p_una": p_una, "p_otra": p_otra,
            },
            "preguntas": [
                {
                    "texto": (
                        f"¿Cuál es la probabilidad de que al menos dos de "
                        f"las {num(n_pers, 0)} personas cumplan años el "
                        f"mismo día?"
                    ),
                    "respuesta": redondear(coincide, 6),
                    "tolerancia": 0.002,
                    "solucion": (
                        f"Se calcula por el complemento: que **todas** "
                        f"cumplan en días distintos es 365/365 × 364/365 × … "
                        f"= {num(distintos, 4)}, así que la respuesta es "
                        f"1 − {num(distintos, 4)} = {num(coincide, 4)}. "
                        f"Con {num(n_pers, 0)} personas hay "
                        f"{num(n_pers * (n_pers - 1) // 2, 0)} pares "
                        f"posibles, y eso es lo que la intuición no cuenta."
                    ),
                    "diagnosticos": [
                        {
                            "valor": redondear(n_pers / 365, 6),
                            "motivo": (
                                "Se calculó la probabilidad de que alguien "
                                "coincida con **una persona fija**. La "
                                "pregunta es si coinciden dos cualesquiera, "
                                "y ahí lo que cuenta son los pares."
                            ),
                        },
                    ],
                },
                {
                    "texto": (
                        f"Salieron {num(rachas, 0)} caras seguidas con una "
                        f"moneda equilibrada. ¿Cuál es la probabilidad de "
                        f"que la próxima sea cara?"
                    ),
                    "respuesta": 0.5,
                    "tolerancia": 0.0,
                    "constante": True,
                    "solucion": (
                        f"0,5. La moneda no se acuerda. Lo que sí es poco "
                        f"probable es sacar {num(rachas, 0)} caras seguidas "
                        f"**antes de empezar**: {num(p_racha, 6)}. Pero eso "
                        f"ya ocurrió, y la tirada siguiente es independiente "
                        f"de las anteriores."
                    ),
                    "diagnosticos": [],
                },
                {
                    "texto": (
                        f"La probabilidad de un evento A es {num(p_una, 2)} "
                        f"y la de otro B, independiente, es "
                        f"{num(p_otra, 2)}. ¿Cuál es la de que ocurran los "
                        f"dos?"
                    ),
                    "respuesta": redondear(p_conj, 6),
                    "tolerancia": 0.002,
                    "solucion": (
                        f"{num(p_una, 2)} × {num(p_otra, 2)} = "
                        f"{num(p_conj, 4)}. La conjunción **nunca** puede "
                        f"ser más probable que cualquiera de sus partes, por "
                        f"más que el relato de los dos juntos suene más "
                        f"verosímil que el de uno solo."
                    ),
                    "diagnosticos": [
                        {
                            "valor": redondear(p_una + p_otra, 6),
                            "motivo": (
                                "Se sumaron. Sumar es para «uno u otro»; "
                                "para «los dos a la vez» se multiplica, y "
                                "por eso el resultado baja."
                            ),
                        },
                    ],
                },
            ],
        })
    return ejercicios


FAMILIAS = {
    "sumatoria": familia_sumatoria,
    "redondeo": familia_redondeo,
    "descriptivos": familia_descriptivos,
    "cuantiles": familia_cuantiles,
    "tabla-frecuencias": familia_tabla,
    "diagrama-de-caja": familia_caja,
    "histograma": familia_histograma,
    "ojiva": familia_ojiva,
    "tabla-de-contingencia": familia_contingencia,
    "correlacion-y-recta": familia_regresion,
    "riesgo-y-odds": familia_riesgo,
    "paradoja-de-simpson": familia_simpson,
    "variaciones": familia_variaciones,
    "deflactacion": familia_deflactacion,
    "indices-y-base": familia_indices_base,
    "laspeyres-paasche": familia_laspeyres,
    "razon-proporcion-tasa": familia_razon,
    "tasas-laborales": familia_laborales,
    "estandarizacion": familia_estandarizacion,
    "gini": familia_gini,
    "combinatoria": familia_combinatoria,
    "reglas-de-probabilidad": familia_reglas,
    "bayes": familia_bayes,
    "probabilidad-contraintuitiva": familia_intuicion,
    "normal": familia_normal,
    "ic-media": familia_ic,
    "prueba-t": familia_prueba_t,
}


def main() -> None:
    todos = []
    for nombre, fn in FAMILIAS.items():
        rng = np.random.default_rng(SEMILLA + sum(map(ord, nombre)))
        ejercicios = fn(rng)
        # Un diagnóstico que no se distingue de la respuesta le diría a quien
        # se equivocó que acertó. Pasa cuando la cuenta mala da lo mismo.
        for e in ejercicios:
            for p in e["preguntas"]:
                antes = len(p.get("diagnosticos", []))
                p["diagnosticos"] = [
                    dg for dg in p.get("diagnosticos", [])
                    if abs(dg["valor"] - p["respuesta"])
                    > max(p["tolerancia"], 1e-9)
                ]
                if len(p["diagnosticos"]) < antes:
                    print(f"    descartado en {e['id']}: un diagnóstico no se "
                          f"distinguía de la respuesta")
        todos.extend(ejercicios)
        print(f"  {nombre:16} {len(ejercicios)} ejercicios, "
              f"{sum(len(e['preguntas']) for e in ejercicios)} preguntas")

    salida = {
        "semilla": SEMILLA,
        # A diferencia del resto de los JSON del sitio, acá la fuente no es un
        # organismo: los datos se simulan. Queda dicho para que nadie los cite.
        "fuente": ("Datos simulados con semilla fija. No provienen de ninguna "
                   "fuente pública y no deben citarse como tales."),
        "generado_por": "datos/ejercicios/generar-ejercicios.py",
        "nota": ("Respuestas calculadas de los datos, no tipeadas. "
                 "scripts/verificar-ejercicios.py las recalcula solo con la "
                 "biblioteca estándar."),
        "ejercicios": todos,
    }
    destino = SALIDA / "ejercicios.json"
    destino.write_text(
        json.dumps(salida, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\n{len(todos)} ejercicios, "
          f"{sum(len(e['preguntas']) for e in todos)} preguntas")
    print(f"→ {destino}")


if __name__ == "__main__":
    main()

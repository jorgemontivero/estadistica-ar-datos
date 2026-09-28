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


FAMILIAS = {
    "descriptivos": familia_descriptivos,
    "normal": familia_normal,
    "ic-media": familia_ic,
    "prueba-t": familia_prueba_t,
}


def main() -> None:
    todos = []
    for nombre, fn in FAMILIAS.items():
        rng = np.random.default_rng(SEMILLA + sum(map(ord, nombre)))
        ejercicios = fn(rng)
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

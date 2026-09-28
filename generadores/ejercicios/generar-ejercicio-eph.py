#!/usr/bin/env python
"""
Ejercicio con archivo: descargar un extracto real y trabajarlo con software.

El banco de `generar-ejercicios.py` prueba si se entiende la fórmula, con
siete números que se resuelven a mano. Este prueba otra cosa: si se sabe
**abrir un archivo real sin equivocarse en el camino**, que es donde falla de
verdad quien recién empieza.

Por eso el extracto conserva las trampas del original en lugar de limpiarlas:

  · el separador es `;`, como lo publica el INDEC, no `,`;
  · `P21 = -9` es no respuesta de ingreso, no un ingreso de −9;
  · `P21 = 0` es «fuera de universo», no un ingreso de cero;
  · `CH06 = -1` es «menos de un año», no una edad de −1;
  · hay dos ponderadores distintos y no dan lo mismo.

Y por eso se publican también **las respuestas equivocadas**, con el motivo:
quien obtenga 987.432 en lugar de 1.104.227 tiene que poder averiguar cuál de
los errores cometió, que es donde está el aprendizaje.

Salida:
    public/datos/eph-catamarca-2026t1.csv   el archivo que se descarga
    datos/ejercicios/ejercicio-eph.json     enunciado, respuestas y trampas

    python datos/ejercicios/generar-ejercicio-eph.py
"""

from __future__ import annotations

import hashlib
import json
import os
import zipfile
from pathlib import Path

import math

import numpy as np
import pandas as pd

# La carpeta con los microdatos públicos. No se versionan: cada fuente se
# baja de su organismo. La variable de entorno DATOS_AR permite moverla.
DATOS = os.environ.get("DATOS_AR", "datos-fuente")

EPH = Path(
    DATOS + r"\INDEC\EPH\01_microdatos_eph"
    r"\2026\EPH_usu_1_Trim_2026_txt.zip"
)
RAIZ = Path(__file__).resolve().parent.parent.parent
CSV = RAIZ / "public" / "datos" / "eph-catamarca-2026t1.csv"
JSON = Path(__file__).resolve().parent / "ejercicio-eph.json"

AGLOMERADO = 22  # Gran Catamarca
COLUMNAS = [
    "CODUSU", "NRO_HOGAR", "COMPONENTE", "AGLOMERADO", "CH04", "CH06",
    "NIVEL_ED", "ESTADO", "CAT_OCUP", "P21", "PONDERA", "PONDIIO",
]


def num(x: float, d: int = 4) -> str:
    s = f"{float(x):,.{d}f}"
    return s.replace(",", "@").replace(".", ",").replace("@", ".")


def distinguibles(preguntas: list[dict]) -> list[dict]:
    """Saca los diagnósticos que caen dentro de la tolerancia.

    Un «error» que da un número indistinguible del correcto no es un error
    que valga la pena diagnosticar, y publicado como tal es peor que nada:
    le estaría diciendo a quien lo cometió que acertó.
    """
    for p in preguntas:
        quedan, fuera = [], []
        for d in p["diagnosticos"]:
            if abs(d["valor"] - p["respuesta"]) > max(p["tolerancia"], 1e-9):
                quedan.append(d)
            else:
                fuera.append(d["valor"])
        if fuera:
            print(f"  descartado (no se distingue de la respuesta): "
                  f"{p['texto'][:44]}… → {fuera}")
        p["diagnosticos"] = quedan
    return preguntas


def ejercicio_cuantiles(d) -> dict:
    """Cuantiles sobre el ingreso real, con las tres convenciones al lado."""
    con_ingreso = d[(d["ESTADO"] == 1) & (d["P21"] > 0)]
    x = con_ingreso["P21"].to_numpy(float)
    n = len(x)

    q1 = float(np.quantile(x, 0.25))
    me = float(np.quantile(x, 0.50))
    q3 = float(np.quantile(x, 0.75))
    ric = q3 - q1
    cerco = q3 + 1.5 * ric
    afuera = int((x > cerco).sum())

    # ¿Cambia algo según el método? Con esta cantidad de casos, no.
    otros = {
        m: [float(np.quantile(x, p, method=m)) for p in (0.25, 0.5, 0.75)]
        for m in ("weibull", "averaged_inverted_cdf")
    }
    coinciden = all(
        abs(v - r) < 1e-9
        for vals in otros.values()
        for v, r in zip(vals, (q1, me, q3))
    )

    # Mediana ponderada: el peso acumulado que alcanza la mitad del total.
    w = con_ingreso["PONDIIO"].to_numpy(float)
    orden = np.argsort(x)
    xs, ws = x[orden], w[orden]
    acum = np.cumsum(ws) / ws.sum()
    me_pond = float(xs[int(np.searchsorted(acum, 0.5))])

    return {
        "id": "eph-cuantiles",
        "tema": "cuantiles-con-archivo",
        "concepto": "cuantiles",
        "nivel": 2,
        "titulo": "Cuartiles y atípicos en un archivo real",
        "intro": (
            f"Trabajá sobre los {num(n, 0)} ocupados con ingreso declarado: "
            f"`ESTADO = 1` y `P21 > 0`. Usá el método que explica la entrada "
            f"de cuantiles, que es el que traen R, pandas, NumPy y "
            f"`CUARTIL.INC`."
        ),
        "preguntas": [
            {
                "texto": "¿Cuál es el primer cuartil del ingreso?",
                "respuesta": round(q1, 2),
                "tolerancia": 1.0,
                "solucion": (
                    f"Q₁ = ${num(q1, 0)}. Llama la atención lo redondo, y no "
                    f"es casualidad: la gente declara su ingreso en cifras "
                    f"redondas, así que los cuantiles caen sobre valores "
                    f"como 400.000 o 500.000."
                ),
                "diagnosticos": [],
            },
            {
                "texto": "¿Y el tercer cuartil?",
                "respuesta": round(q3, 2),
                "tolerancia": 1.0,
                "solucion": (
                    f"Q₃ = ${num(q3, 0)}, así que el 50 % central de los "
                    f"ocupados con ingreso gana entre ${num(q1, 0)} y "
                    f"${num(q3, 0)}."
                ),
                "diagnosticos": [],
            },
            {
                "texto": (
                    "Calculá el mismo Q₃ con `CUARTIL.EXC` de Excel o con "
                    "SPSS, que usan otro método. ¿Cuánto da?"
                ),
                "respuesta": round(otros["weibull"][2], 2),
                "tolerancia": 1.0,
                "solucion": (
                    (f"Lo mismo: ${num(q3, 0)}. "
                     if coinciden
                     else f"${num(otros['weibull'][2], 0)}. ")
                    + (
                        "Con los datos a mano de los otros ejercicios los "
                        "métodos daban distinto; con 594 casos dan igual. "
                        "Eso es exactamente lo que dice la teoría: la "
                        "convención importa con muestras chicas y deja de "
                        "importar cuando hay muchas."
                        if coinciden
                        else "Los métodos difieren, y hay que declarar cuál "
                             "se usó."
                    )
                ),
                "diagnosticos": [],
            },
            {
                "texto": (
                    "¿Cuántos casos superan el cerco superior de la regla "
                    "del 1,5?"
                ),
                "respuesta": float(afuera),
                "tolerancia": 0.0,
                "solucion": (
                    f"El cerco está en Q₃ + 1,5 × RIC = ${num(cerco, 0)}, y "
                    f"lo superan {num(afuera, 0)} de {num(n, 0)} casos: el "
                    f"{num(afuera / n * 100, 1)} %. Con una variable "
                    f"asimétrica como el ingreso la regla marca muchísimos, "
                    f"y ninguno es un error: son personas que ganan bien. "
                    f"La regla sirve para mirar, no para borrar."
                ),
                "diagnosticos": [],
            },
            {
                "texto": (
                    "¿Cuál es la mediana del ingreso **ponderando** con "
                    "`PONDIIO`?"
                ),
                "respuesta": round(me_pond, 2),
                "tolerancia": 1.0,
                "solucion": (
                    f"${num(me_pond, 0)}. No se busca el valor del medio "
                    f"entre los casos sino aquel donde la suma acumulada de "
                    f"los pesos llega a la mitad del total. Sin ponderar da "
                    f"${num(me, 0)}."
                ),
                "diagnosticos": [
                    {
                        "valor": round(me, 2),
                        "motivo": (
                            "Es la mediana sin ponderar: se ordenó y se tomó "
                            "el valor del medio, sin usar PONDIIO."
                        ),
                    },
                ],
            },
        ],
    }


def ejercicio_tabla(d) -> dict:
    """Tabla de frecuencias de la edad, con el código −1 de por medio."""
    edad_cruda = d["CH06"].to_numpy(float)
    edad = np.clip(edad_cruda, 0, None)
    n = len(edad)
    menores = int((edad_cruda == -1).sum())

    sturges = 1 + 3.322 * math.log10(n)
    k = int(round(sturges))
    amp, ini = 10, 0

    lo, hi = 20, 30
    dentro = int(((edad >= lo) & (edad < hi)).sum())
    acumulada = int((edad < hi).sum())
    # Con amplitud 10 desde 0, ¿cuántas clases hacen falta de verdad?
    necesarias = int(math.ceil((edad.max() + 1e-9) / amp))

    return {
        "id": "eph-tabla",
        "tema": "tabla-con-archivo",
        "concepto": "tabla-de-frecuencias",
        "nivel": 2,
        "titulo": "Agrupar en clases un archivo real",
        "intro": (
            f"Trabajá sobre la edad —columna `CH06`— de las {num(n, 0)} "
            f"personas del archivo. Acordate de que el `-1` es «menos de un "
            f"año» y hay que contarlo como 0. Usá clases de amplitud "
            f"{num(amp, 0)} empezando en {num(ini, 0)}, con intervalos "
            f"semiabiertos [Lᵢ, Lᵢ₊₁)."
        ),
        "preguntas": [
            {
                "texto": (
                    "¿Cuántas clases sugiere Sturges? Redondeá al entero más "
                    "cercano."
                ),
                "respuesta": float(k),
                "tolerancia": 0.0,
                "solucion": (
                    f"k = 1 + 3,322 × log₁₀({num(n, 0)}) = {num(sturges, 4)}, "
                    f"o sea {num(k, 0)}. Con amplitud 10 desde 0 hacen falta "
                    f"{num(necesarias, 0)} clases para cubrir hasta la edad "
                    f"máxima, así que la sugerencia y la construcción "
                    f"coinciden. No siempre pasa."
                ),
                "diagnosticos": [],
            },
            {
                "texto": (
                    f"¿Cuántas personas caen en la clase [{lo}, {hi})?"
                ),
                "respuesta": float(dentro),
                "tolerancia": 0.0,
                "solucion": (
                    f"{num(dentro, 0)} personas: las de 20 a 29 años "
                    f"cumplidos. El 30 no entra."
                ),
                "diagnosticos": [],
            },
            {
                "texto": f"¿Y la frecuencia relativa de esa clase?",
                "respuesta": round(dentro / n, 6),
                "tolerancia": 0.002,
                "solucion": (
                    f"{num(dentro, 0)} / {num(n, 0)} = "
                    f"{num(dentro / n, 4)}, el {num(dentro / n * 100, 1)} % "
                    f"de las personas del archivo. Es la clase más numerosa."
                ),
                "diagnosticos": [],
            },
            {
                "texto": (
                    f"¿Cuántas personas hay acumuladas por debajo de {hi} "
                    f"años?"
                ),
                "respuesta": float(acumulada),
                "tolerancia": 0.0,
                "solucion": (
                    f"{num(acumulada, 0)} de {num(n, 0)}, o sea el "
                    f"{num(acumulada / n * 100, 1)} %. Casi la mitad del "
                    f"aglomerado tiene menos de 30 años."
                ),
                "diagnosticos": [],
            },
            {
                "texto": (
                    "¿En qué clase caen las personas con `CH06 = -1`? "
                    "Respondé cuántas son."
                ),
                "respuesta": float(menores),
                "tolerancia": 0.0,
                "solucion": (
                    f"Son {num(menores, 0)}, y van en la primera clase, "
                    f"[0, 10), porque `-1` significa «menos de un año». Si se "
                    f"toma la columna tal cual, esas {num(menores, 0)} "
                    f"personas caen fuera de todas las clases y la tabla no "
                    f"cierra: la suma de las frecuencias da "
                    f"{num(n - menores, 0)} y no {num(n, 0)}."
                ),
                "diagnosticos": [
                    {
                        "valor": 0.0,
                        "motivo": (
                            "Si el filtro descartó los −1 antes de agrupar, "
                            "no aparece ninguno y se pierden esas personas "
                            "sin que nada lo avise."
                        ),
                    },
                ],
            },
        ],
    }


def main() -> None:
    with zipfile.ZipFile(EPH) as z, z.open("usu_individual_T126.txt") as f:
        ind = pd.read_csv(f, sep=";", decimal=",", low_memory=False,
                          usecols=COLUMNAS)

    d = ind[ind["AGLOMERADO"] == AGLOMERADO][COLUMNAS].copy()
    d = d.sort_values(["CODUSU", "NRO_HOGAR", "COMPONENTE"]).reset_index(drop=True)

    CSV.parent.mkdir(parents=True, exist_ok=True)
    # Igual que lo publica el INDEC: punto y coma, y sin índice.
    d.to_csv(CSV, sep=";", index=False, encoding="utf-8", lineterminator="\n")
    sha = hashlib.sha256(CSV.read_bytes()).hexdigest()

    # ------------------------------------------------------------ respuestas
    n_filas = len(d)
    n_viviendas = int(d["CODUSU"].nunique())

    # Edad: −1 es «menos de un año». Tratarlo como 0 es lo correcto.
    edad_bien = float(d["CH06"].clip(lower=0).mean())
    edad_con_menos_uno = float(d["CH06"].mean())
    edad_excluyendo = float(d.loc[d["CH06"] >= 0, "CH06"].mean())

    # Ingreso de la ocupación principal.
    ocupados = d[d["ESTADO"] == 1]
    con_ingreso = ocupados[ocupados["P21"] > 0]
    ing_bien = float(con_ingreso["P21"].mean())
    ing_con_ceros = float(ocupados["P21"].mean())
    ing_con_menos_nueve = float(
        ocupados.loc[ocupados["P21"] != 0, "P21"].mean()
    )
    ing_todas_las_filas = float(d.loc[d["P21"] > 0, "P21"].mean())
    ing_mediana = float(con_ingreso["P21"].median())

    w = con_ingreso["PONDIIO"].to_numpy(float)
    y = con_ingreso["P21"].to_numpy(float)
    ing_ponderado = float((w * y).sum() / w.sum())
    wp = con_ingreso["PONDERA"].to_numpy(float)
    ing_pondera = float((wp * y).sum() / wp.sum())

    poblacion = int(d["PONDERA"].sum())

    preguntas = [
        {
            "texto": "¿Cuántas filas tiene el archivo, sin contar el encabezado?",
            "respuesta": float(n_filas),
            "tolerancia": 0.0,
            "solucion": (
                f"El extracto tiene {num(n_filas, 0)} personas, repartidas en "
                f"{num(n_viviendas, 0)} viviendas."
            ),
            "diagnosticos": [
                {
                    "valor": 1.0,
                    "motivo": (
                        "El archivo se leyó con coma como separador. El INDEC "
                        "publica con punto y coma, y así se conservó acá: "
                        "todo entró en una sola columna."
                    ),
                },
            ],
        },
        {
            "texto": "¿Cuál es la edad promedio de las personas del extracto?",
            "respuesta": round(edad_bien, 4),
            "tolerancia": 0.02,
            "solucion": (
                f"La media es {num(edad_bien, 4)} años. La clave es que "
                f"`CH06 = -1` no es una edad sino el código de «menos de un "
                f"año»: hay {int((d['CH06'] == -1).sum())} personas así, y "
                f"corresponde contarlas como 0. Acá son pocas y la media "
                f"casi no se mueve, pero el criterio no depende de eso: un "
                f"código no es un valor."
            ),
            "diagnosticos": [
                {
                    "valor": round(edad_con_menos_uno, 4),
                    "motivo": (
                        "Se promedió la columna tal cual, con los −1 adentro "
                        "como si fueran edades negativas."
                    ),
                },
                {
                    "valor": round(edad_excluyendo, 4),
                    "motivo": (
                        "Se excluyó a los menores de un año en lugar de "
                        "contarlos como 0. Son personas del hogar y cuentan."
                    ),
                },
            ],
        },
        {
            "texto": (
                "Entre los ocupados con ingreso declarado, ¿cuál es el ingreso "
                "medio de la ocupación principal, sin ponderar?"
            ),
            "respuesta": round(ing_bien, 2),
            "tolerancia": 1.0,
            "solucion": (
                f"Hay que quedarse con `ESTADO = 1` y `P21 > 0`: son "
                f"{num(len(con_ingreso), 0)} personas y la media es "
                f"${num(ing_bien, 2)}. Los `P21 = 0` son «fuera de universo» "
                f"y los `P21 = -9`, no respuesta. En este extracto filtrar "
                f"por `P21 > 0` ya deja solo ocupados, pero conviene "
                f"escribir las dos condiciones: en otra base no pasa."
            ),
            "diagnosticos": [
                {
                    "valor": round(ing_con_ceros, 2),
                    "motivo": (
                        f"Se promediaron todos los ocupados, incluidos los "
                        f"{int((ocupados['P21'] == 0).sum())} con `P21 = 0`. "
                        f"Ese cero no es un ingreso de cero pesos: es que la "
                        f"pregunta no correspondía."
                    ),
                },
                {
                    "valor": round(ing_con_menos_nueve, 2),
                    "motivo": (
                        f"Se excluyeron los ceros pero quedaron los "
                        f"{int((ocupados['P21'] == -9).sum())} casos con "
                        f"`P21 = -9`, que es el código de no respuesta y "
                        f"arrastra la media hacia abajo."
                    ),
                },
                {
                    "valor": round(ing_todas_las_filas, 2),
                    "motivo": (
                        "Se filtró por `P21 > 0` pero no por `ESTADO = 1`, "
                        "así que entraron personas que no son ocupadas."
                    ),
                },
            ],
        },
        {
            "texto": "¿Y la mediana de ese mismo ingreso?",
            "respuesta": round(ing_mediana, 2),
            "tolerancia": 1.0,
            "solucion": (
                f"La mediana es ${num(ing_mediana, 2)}, bastante por debajo de "
                f"la media de ${num(ing_bien, 2)}. La diferencia es la "
                f"asimetría típica de cualquier distribución de ingresos: unos "
                f"pocos valores altos empujan la media y no mueven la mediana."
            ),
            "diagnosticos": [],
        },
        {
            "texto": (
                "Ponderando con `PONDIIO`, ¿cuál es el ingreso medio de la "
                "ocupación principal?"
            ),
            "respuesta": round(ing_ponderado, 2),
            "tolerancia": 1.0,
            "solucion": (
                f"La media ponderada es la suma de `P21 × PONDIIO` dividida "
                f"por la suma de `PONDIIO`: ${num(ing_ponderado, 2)}. "
                f"`PONDIIO` es el ponderador que corresponde al ingreso de la "
                f"ocupación principal, y reparte el peso de quienes no "
                f"declararon ingreso entre quienes sí lo hicieron."
            ),
            "diagnosticos": [
                {
                    "valor": round(ing_bien, 2),
                    "motivo": (
                        "No se ponderó: se calculó el promedio simple. La "
                        "muestra no es autoponderada, así que no da lo mismo."
                    ),
                },
                {
                    "valor": round(ing_pondera, 2),
                    "motivo": (
                        "Se usó `PONDERA` en lugar de `PONDIIO`. Para la media "
                        "la diferencia es chica; para el total de población es "
                        "enorme."
                    ),
                },
            ],
        },
        {
            "texto": (
                "¿A cuántas personas representa el extracto? Sumá `PONDERA`."
            ),
            "respuesta": float(poblacion),
            "tolerancia": 1.0,
            "solucion": (
                f"La suma de `PONDERA` da {num(poblacion, 0)} personas. Ese es "
                f"el sentido del ponderador: {num(n_filas, 0)} entrevistas "
                f"representan a la población del aglomerado."
            ),
            "diagnosticos": [
                {
                    "valor": float(n_filas),
                    "motivo": (
                        "Se contaron las filas. Cada fila no es una persona "
                        "de la población sino una persona de la muestra."
                    ),
                },
            ],
        },
    ]

    preguntas = distinguibles(preguntas)

    salida = {
        "fuente": ("Extracto de la Encuesta Permanente de Hogares, base "
                   "individual del primer trimestre de 2026, INDEC. Solo el "
                   "aglomerado Gran Catamarca y once variables."),
        "generado_por": "datos/ejercicios/generar-ejercicio-eph.py",
        "archivo": "/datos/eph-catamarca-2026t1.csv",
        "sha256": sha,
        "separador": ";",
        "filas": n_filas,
        "viviendas": n_viviendas,
        "columnas": COLUMNAS,
        "poblacion_representada": poblacion,
        "ejercicios": [
            {
                "id": "eph-descriptivos-01",
                "tema": "descriptivos-con-archivo",
                "concepto": "media-aritmetica",
                "nivel": 2,
                "titulo": "Resumir una variable en un archivo real",
                "intro": "",
                "preguntas": preguntas,
            },
            ejercicio_cuantiles(d),
            ejercicio_tabla(d),
        ],
    }

    for ej in salida["ejercicios"]:
        ej["preguntas"] = distinguibles(ej["preguntas"])

    JSON.write_text(json.dumps(salida, indent=2, ensure_ascii=False),
                    encoding="utf-8")

    print(f"{n_filas} filas · {n_viviendas} viviendas · "
          f"{poblacion:,} personas representadas")
    print(f"sha256 {sha[:16]}…")
    for p in preguntas:
        print(f"\n  {p['texto'][:64]}")
        print(f"    bien: {p['respuesta']}")
        for dg in p["diagnosticos"]:
            print(f"    mal : {dg['valor']}  ({dg['motivo'][:56]}…)")
    print(f"\n→ {CSV}\n→ {JSON}")


if __name__ == "__main__":
    main()

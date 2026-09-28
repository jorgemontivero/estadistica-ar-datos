#!/usr/bin/env python
"""
Dos ejercicios sobre gráficos: cuál corresponde, y cuál es este.

El primero es de criterio: dada una situación, qué gráfico usar. El segundo
muestra gráficos dibujados y pide identificarlos, que suena fácil hasta que
aparecen juntos un gráfico de barras y un histograma.

Acá solo se generan **los datos** de cada gráfico y la respuesta. El dibujo lo
hace el componente de Astro a partir de esos números: así el archivo de datos
no contiene etiquetas HTML y no hay nada que inyectar.

Las opciones se mezclan con semilla fija para que la correcta no caiga siempre
en el mismo lugar, que es lo que el verificador exige.

Salida: datos/ejercicios/graficos.json

    python datos/ejercicios/generar-graficos.py
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import numpy as np

SALIDA = Path(__file__).resolve().parent / "graficos.json"
SEMILLA = 7000

TIPOS = [
    "Gráfico de barras",
    "Histograma",
    "Gráfico de sectores",
    "Diagrama de caja",
    "Diagrama de dispersión",
    "Gráfico de líneas",
    "Ojiva",
]


# --------------------------------------------------------------- identificar

def graficos(rng) -> list[dict]:
    """Siete gráficos dibujables, con sus datos y su tipo."""
    g = []

    g.append({
        "clave": "barras",
        "tipo": "Gráfico de barras",
        "grafico": {
            "tipo": "barras",
            "etiquetas": ["Primaria", "Secundaria", "Terciaria",
                          "Universitaria"],
            "valores": [412, 508, 187, 232],
            "ejey": "Personas",
        },
        "solucion": (
            "Es un gráfico de barras: las categorías del eje horizontal no "
            "tienen un orden numérico ni una escala continua, y por eso las "
            "barras van **separadas**. Cualquier orden entre ellas es una "
            "decisión de quien dibuja."
        ),
        "por_que_no": [
            ("Histograma",
             "En un histograma el eje horizontal es una escala continua y "
             "las barras se tocan. Acá hay categorías y hay espacio entre "
             "las barras: esas dos cosas van juntas siempre."),
        ],
    })

    valores = [8, 21, 34, 27, 15, 6]
    g.append({
        "clave": "histograma",
        "tipo": "Histograma",
        "grafico": {
            "tipo": "histograma",
            "limites": [0, 10, 20, 30, 40, 50, 60],
            "valores": valores,
            "ejex": "Minutos",
            "ejey": "Frecuencia",
        },
        "solucion": (
            "Es un histograma: el eje horizontal es una variable continua "
            "partida en clases, las barras **se tocan** y el área de cada "
            "una representa su frecuencia."
        ),
        "por_que_no": [
            ("Gráfico de barras",
             "Las barras de un gráfico de barras van separadas porque las "
             "categorías no son contiguas. Acá el eje es una escala y las "
             "clases se continúan una con otra."),
            ("Polígono de frecuencias",
             "El polígono une con una línea las marcas de clase en vez de "
             "dibujar barras. Acá hay barras."),
        ],
    })

    g.append({
        "clave": "sectores",
        "tipo": "Gráfico de sectores",
        "grafico": {
            "tipo": "sectores",
            "etiquetas": ["Ocupados", "Desocupados", "Inactivos"],
            "valores": [631, 26, 545],
        },
        "solucion": (
            "Es un gráfico de sectores. Sirve para mostrar la **composición "
            "de un total** y solo funciona con pocas categorías: con más de "
            "cinco o seis, comparar ángulos es más difícil que comparar "
            "alturas y conviene pasar a barras."
        ),
        "por_que_no": [
            ("Gráfico de barras",
             "Las barras comparan magnitudes; los sectores muestran partes "
             "de un todo que suma 100 %."),
        ],
    })

    g.append({
        "clave": "caja",
        "tipo": "Diagrama de caja",
        "grafico": {
            "tipo": "caja",
            "grupos": [
                {"nombre": "Varones", "min": 12, "q1": 28, "me": 41,
                 "q3": 58, "max": 79, "atipicos": [112]},
                {"nombre": "Mujeres", "min": 9, "q1": 24, "me": 35,
                 "q3": 49, "max": 71, "atipicos": []},
            ],
            "ejey": "Ingreso, en miles",
        },
        "solucion": (
            "Es un diagrama de caja. Muestra cinco números —mínimo, los tres "
            "cuartiles y máximo— y los puntos que quedan fuera de los "
            "cercos. Es el gráfico que conviene para **comparar la "
            "distribución entre grupos**."
        ),
        "por_que_no": [
            ("Gráfico de barras",
             "Una barra muestra un solo número por categoría; la caja "
             "muestra la distribución entera."),
        ],
    })

    x = np.linspace(1, 10, 22)
    y = 2.1 * x + rng.normal(0, 2.6, 22) + 5
    g.append({
        "clave": "dispersion",
        "tipo": "Diagrama de dispersión",
        "grafico": {
            "tipo": "dispersion",
            "puntos": [[round(float(a), 2), round(float(b), 2)]
                       for a, b in zip(x, y)],
            "ejex": "Años de estudio",
            "ejey": "Ingreso, en miles",
        },
        "solucion": (
            "Es un diagrama de dispersión: cada punto es **un caso con dos "
            "variables cuantitativas**. Es el gráfico de la correlación y el "
            "primero que hay que mirar antes de ajustar una recta."
        ),
        "por_que_no": [
            ("Gráfico de líneas",
             "La línea une puntos consecutivos porque el eje horizontal "
             "tiene un orden —el tiempo, casi siempre—. Acá los puntos son "
             "casos independientes y unirlos no significaría nada."),
        ],
    })

    g.append({
        "clave": "lineas",
        "tipo": "Gráfico de líneas",
        "grafico": {
            "tipo": "lineas",
            "etiquetas": ["2019", "2020", "2021", "2022", "2023", "2024",
                          "2025", "2026"],
            "valores": [100.0, 92.4, 101.8, 110.2, 114.9, 108.3, 117.6,
                        124.1],
            "ejey": "Índice, base 2019 = 100",
        },
        "solucion": (
            "Es un gráfico de líneas. Se usa cuando el eje horizontal tiene "
            "un **orden natural**, casi siempre el tiempo: la línea sugiere "
            "continuidad entre un punto y el siguiente, y eso solo tiene "
            "sentido si esa continuidad existe."
        ),
        "por_que_no": [
            ("Diagrama de dispersión",
             "La dispersión no une los puntos porque no hay un orden que "
             "recorrer entre ellos."),
        ],
    })

    frec = [8, 21, 34, 27, 15, 6]
    acum, s = [], 0
    for f in frec:
        s += f
        acum.append(s)
    g.append({
        "clave": "ojiva",
        "tipo": "Ojiva",
        "grafico": {
            "tipo": "ojiva",
            "limites": [0, 10, 20, 30, 40, 50, 60],
            "acumuladas": acum,
            "ejex": "Minutos",
            "ejey": "Frecuencia acumulada",
        },
        "solucion": (
            "Es una ojiva: la curva de **frecuencias acumuladas**. Nunca "
            "baja, arranca en cero y termina en el total, y se dibuja sobre "
            "los límites superiores de cada clase. Sirve para leer "
            "percentiles."
        ),
        "por_que_no": [
            ("Gráfico de líneas",
             "Una serie de tiempo puede subir y bajar; la ojiva nunca baja, "
             "porque acumula."),
            ("Polígono de frecuencias",
             "El polígono dibuja las frecuencias simples y sube y baja "
             "siguiendo la forma de la distribución."),
        ],
    })
    return g


# ------------------------------------------------------------------- elegir

ELEGIR = [
    {
        "texto": (
            "Se quiere mostrar cómo se reparten los 1.339 casos de un "
            "relevamiento entre los 24 aglomerados urbanos del país."
        ),
        "respuesta": "Gráfico de barras",
        "solucion": (
            "Barras, y ordenadas por frecuencia. Son 24 categorías sin orden "
            "natural: comparar 24 ángulos de una torta es imposible, y "
            "comparar 24 alturas alineadas es inmediato."
        ),
        "por_que_no": [
            ("Gráfico de sectores",
             "Con 24 categorías los sectores se vuelven ilegibles y la "
             "leyenda ocupa más que el gráfico."),
            ("Histograma",
             "El histograma es para variables continuas agrupadas en "
             "clases; el aglomerado es una categoría."),
        ],
    },
    {
        "texto": (
            "Se quiere mostrar la forma de la distribución del ingreso de "
            "594 personas: si es simétrica, dónde se concentra, si tiene "
            "una cola larga."
        ),
        "respuesta": "Histograma",
        "solucion": (
            "Histograma. Es una variable continua y lo que interesa es la "
            "forma: dónde se amontonan los casos y hacia qué lado se estira."
        ),
        "por_que_no": [
            ("Gráfico de barras",
             "Las barras separadas sugieren categorías; acá el eje es una "
             "escala continua y las clases son contiguas."),
            ("Diagrama de caja",
             "La caja resume la distribución en cinco números y es excelente "
             "para comparar grupos, pero esconde la forma: no se ve si hay "
             "dos modas."),
        ],
    },
    {
        "texto": (
            "Se quiere comparar la distribución del ingreso entre cinco "
            "niveles educativos, en un solo gráfico."
        ),
        "respuesta": "Diagrama de caja",
        "solucion": (
            "Cajas, una por nivel. Muestran la mediana, la dispersión y los "
            "atípicos de cada grupo lado a lado, que es exactamente lo que "
            "se quiere comparar."
        ),
        "por_que_no": [
            ("Histograma",
             "Cinco histogramas superpuestos no se leen, y cinco separados "
             "obligan a ir y venir para comparar."),
            ("Gráfico de barras",
             "Una barra por nivel mostraría solo el promedio, y perdería "
             "toda la dispersión: dos grupos con la misma media pueden ser "
             "completamente distintos."),
        ],
    },
    {
        "texto": (
            "Se quiere mostrar la evolución del índice de precios mes a mes "
            "durante los últimos cuatro años."
        ),
        "respuesta": "Gráfico de líneas",
        "solucion": (
            "Líneas. El eje horizontal tiene un orden natural y la "
            "continuidad entre un mes y el siguiente es real, así que unir "
            "los puntos informa en lugar de engañar."
        ),
        "por_que_no": [
            ("Gráfico de barras",
             "Con 48 barras el gráfico se vuelve una empalizada y la "
             "tendencia, que es lo que importa, se pierde."),
            ("Diagrama de dispersión",
             "Los puntos sueltos no muestran la trayectoria, que es "
             "justamente lo que se quiere ver."),
        ],
    },
    {
        "texto": (
            "Se quiere ver si hay relación entre los años de estudio y el "
            "ingreso de cada persona."
        ),
        "respuesta": "Diagrama de dispersión",
        "solucion": (
            "Dispersión. Son dos variables cuantitativas medidas sobre los "
            "mismos casos, y lo que se busca es la forma de la relación: si "
            "es lineal, si hay curvatura, si hay puntos que se despegan."
        ),
        "por_que_no": [
            ("Gráfico de líneas",
             "Unir los puntos supondría que hay un orden entre las personas, "
             "y no lo hay."),
            ("Histograma",
             "El histograma describe una variable por vez y no puede mostrar "
             "la relación entre dos."),
        ],
    },
    {
        "texto": (
            "Se quiere responder «¿qué porcentaje de los casos está por "
            "debajo de 30 minutos?» directamente sobre el gráfico."
        ),
        "respuesta": "Ojiva",
        "solucion": (
            "Ojiva. La curva acumulada permite entrar por el eje horizontal "
            "en 30, subir hasta la curva y leer el porcentaje, o hacer el "
            "camino inverso para encontrar un percentil."
        ),
        "por_que_no": [
            ("Histograma",
             "El histograma muestra cuántos casos hay en cada clase, pero "
             "para acumular hay que ir sumando barras a ojo."),
        ],
    },
    {
        "texto": (
            "Una variable tiene solo tres categorías —ocupado, desocupado e "
            "inactivo— y se quiere mostrar qué parte del total representa "
            "cada una."
        ),
        "respuesta": "Gráfico de sectores",
        "solucion": (
            "Acá sí funciona: son tres categorías, suman el total y lo que "
            "interesa es la proporción de cada parte. Es el único caso en "
            "que la torta compite con las barras, y aun así muchos "
            "preferirían barras."
        ),
        "por_que_no": [
            ("Histograma",
             "La variable es cualitativa: no hay clases ni escala continua "
             "que agrupar."),
        ],
    },
    {
        "texto": (
            "Se quiere mostrar la cantidad de nacimientos de cada uno de los "
            "16 departamentos de una provincia, sobre el mapa."
        ),
        "respuesta": "Mapa de coropletas",
        "solucion": (
            "Un mapa de coropletas, coloreando cada departamento según su "
            "valor. Con una variable que tiene una ubicación, el mapa "
            "muestra algo que ningún otro gráfico puede: si los valores "
            "altos están cerca unos de otros."
        ),
        "por_que_no": [
            ("Gráfico de barras",
             "Las barras ordenan bien pero pierden la ubicación, que es lo "
             "que agrega el mapa."),
            ("Gráfico de sectores",
             "Con 16 categorías la torta es ilegible, y además el total de "
             "nacimientos repartido en departamentos no es lo que se quiere "
             "mostrar."),
        ],
    },
]

OPCIONES_ELEGIR = [
    "Gráfico de barras",
    "Histograma",
    "Gráfico de sectores",
    "Diagrama de caja",
    "Diagrama de dispersión",
    "Gráfico de líneas",
    "Ojiva",
    "Mapa de coropletas",
]


def main() -> None:
    rng = np.random.default_rng(SEMILLA)

    identificar = []
    for i, g in enumerate(graficos(rng), 1):
        # Las opciones incluyen los distractores explicados más el resto.
        distractores = [d for d, _ in g["por_que_no"]]
        opciones = list(dict.fromkeys([g["tipo"], *distractores]))
        for t in TIPOS:
            if len(opciones) >= 4:
                break
            if t not in opciones:
                opciones.append(t)
        random.Random(SEMILLA + i).shuffle(opciones)
        identificar.append({
            "id": f"identificar-{i:02d}",
            "grafico": g["grafico"],
            "opciones": opciones,
            "respuesta": g["tipo"],
            "solucion": g["solucion"],
            "por_que_no": [
                {"opcion": o, "motivo": m} for o, m in g["por_que_no"]
            ],
        })

    elegir = []
    for i, q in enumerate(ELEGIR, 1):
        opciones = list(OPCIONES_ELEGIR)
        random.Random(SEMILLA + 100 + i).shuffle(opciones)
        elegir.append({
            "id": f"elegir-{i:02d}",
            "texto": q["texto"],
            "opciones": opciones,
            "respuesta": q["respuesta"],
            "solucion": q["solucion"],
            "por_que_no": [
                {"opcion": o, "motivo": m} for o, m in q["por_que_no"]
            ],
        })

    salida = {
        "fuente": ("Gráficos dibujados a partir de datos inventados con "
                   "semilla fija, o tomados del extracto de la EPH. No son "
                   "una fuente de datos y no deben citarse."),
        "generado_por": "datos/ejercicios/generar-graficos.py",
        "advertencia": (
            "La respuesta es una categoría y no se recalcula. Lo que se "
            "comprueba es que esté entre las opciones, que cada distractor "
            "tenga su motivo, que los datos de cada gráfico sean coherentes "
            "con el tipo que declaran y que la correcta no caiga siempre en "
            "el mismo lugar."
        ),
        # El eje del ejercicio son los gráficos de la descriptiva, así que
        # se agrupa con ellos. El criterio de cuál usar tiene su propia
        # entrada en el módulo de cómputo y queda enlazado desde la página.
        "concepto": "histograma",
        "concepto_criterio": "eleccion-del-grafico",
        "identificar": {
            "titulo": "¿Qué gráfico es este?",
            "preguntas": identificar,
        },
        "elegir": {
            "titulo": "¿Qué gráfico corresponde?",
            "preguntas": elegir,
        },
    }
    SALIDA.write_text(json.dumps(salida, indent=2, ensure_ascii=False),
                      encoding="utf-8")

    print(f"{len(identificar)} gráficos para identificar, "
          f"{len(elegir)} situaciones para elegir\n")
    for q in identificar:
        pos = q["opciones"].index(q["respuesta"])
        print(f"  {q['grafico']['tipo']:<14} {q['respuesta']:<26} "
              f"correcta en la posición {pos + 1} de {len(q['opciones'])}")
    print(f"\n→ {SALIDA}")


if __name__ == "__main__":
    main()

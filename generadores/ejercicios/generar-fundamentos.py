#!/usr/bin/env python
"""
Ejercicios del módulo 1, con respuesta de opción.

El resto del banco tiene respuestas numéricas que se recalculan. Acá la
respuesta es una categoría, y una categoría no se recalcula: se declara. Eso
debilita la verificación y conviene decirlo en vez de disimularlo.

Lo que sí se puede hacer, y se hace:

  · la clave sale de **un diccionario declarado una sola vez** y no se tipea
    ejercicio por ejercicio, así que no puede contradecirse a sí misma;
  · todo lo que el archivo permite comprobar, se comprueba contra el archivo:
    cuántos valores distintos tiene cada columna, si son enteros, si los
    códigos declarados son los que aparecen;
  · lo que el archivo **no** puede decidir —que una escala sea ordinal y no
    nominal— queda marcado como criterio y no como dato.

Salida: datos/ejercicios/fundamentos.json

    python datos/ejercicios/generar-fundamentos.py
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
CSV = RAIZ / "public" / "datos" / "eph-catamarca-2026t1.csv"
SALIDA = Path(__file__).resolve().parent / "fundamentos.json"

NOMINAL = "Cualitativa nominal"
ORDINAL = "Cualitativa ordinal"
DISCRETA = "Cuantitativa discreta"
CONTINUA = "Cuantitativa continua"
NO_VARIABLE = "No es una variable de la persona"

OPCIONES = [NOMINAL, ORDINAL, DISCRETA, CONTINUA, NO_VARIABLE]

# El diccionario: una sola fuente para todas las respuestas de clasificación.
DICCIONARIO = [
    {
        "columna": "CODUSU",
        "que_es": "Identificador de la vivienda.",
        "clase": NO_VARIABLE,
        "por_que": (
            "Es una clave para unir registros, no una característica que se "
            "mida. No tiene sentido contar cuántas veces aparece cada valor "
            "como si fuera una categoría de análisis."
        ),
        "trampa": None,
    },
    {
        "columna": "AGLOMERADO",
        "codigos": {"22"},
        "que_es": "El aglomerado urbano. Acá vale 22 en todas las filas.",
        "clase": NOMINAL,
        "por_que": (
            "Está codificado con un número, pero el 22 no es una cantidad: "
            "es una etiqueta. Sumar aglomerados o sacarles el promedio no "
            "significa nada."
        ),
        "trampa": (
            "Es el error más común del módulo: confundir una variable "
            "cualitativa codificada con números con una cuantitativa."
        ),
    },
    {
        "columna": "CH04",
        "codigos": {"1", "2"},
        "que_es": "Sexo. 1 es varón y 2 es mujer.",
        "clase": NOMINAL,
        "por_que": (
            "Dos categorías sin orden entre ellas. Que estén numeradas 1 y 2 "
            "no las vuelve cuantitativas ni pone a una por encima de la otra."
        ),
        "trampa": (
            "Un promedio de CH04 da un número —alrededor de 1,5— y no "
            "significa absolutamente nada."
        ),
    },
    {
        "columna": "CH06",
        "que_es": "Edad en años cumplidos. El −1 es «menos de un año».",
        "clase": DISCRETA,
        "por_que": (
            "La edad en años cumplidos toma valores enteros y separados. La "
            "edad como magnitud es continua, pero **así medida** es discreta: "
            "lo que se clasifica es la variable tal como está en la matriz."
        ),
        "trampa": (
            "El −1 no es una edad negativa sino un código. Un código dentro "
            "de una columna numérica no la vuelve cualitativa, pero hay que "
            "sacarlo antes de cualquier cuenta."
        ),
    },
    {
        "columna": "NIVEL_ED",
        "codigos": {"1", "2", "3", "4", "5", "6", "7"},
        "que_es": (
            "Nivel educativo alcanzado, del 1 al 7. El 7 es «sin instrucción»."
        ),
        "clase": ORDINAL,
        "por_que": (
            "Las categorías tienen un orden natural —primaria incompleta está "
            "por debajo de secundaria completa— pero las distancias entre "
            "ellas no son comparables: no se puede decir que de 2 a 3 haya lo "
            "mismo que de 5 a 6."
        ),
        "trampa": (
            "El código no respeta el orden: el 7 es «sin instrucción», que "
            "es el nivel más bajo y está numerado último. Ordenar por el "
            "código pone al nivel más bajo arriba de todo."
        ),
    },
    {
        "columna": "ESTADO",
        "que_es": (
            "Condición de actividad: 0 entrevista no realizada, 1 ocupado, "
            "2 desocupado, 3 inactivo, 4 menor de 10 años."
        ),
        "codigos": {"0", "1", "2", "3", "4"},
        "clase": NOMINAL,
        "por_que": (
            "Son categorías sin un orden que las recorra: no hay un sentido "
            "en el que inactivo esté «por encima» de desocupado."
        ),
        "trampa": (
            "El 4 no es «más» que el 1: es una categoría aparte, la de "
            "quienes no entran en la pregunta por edad. Y hay un 0 con "
            "cuatro casos —entrevista individual no realizada— que no "
            "aparece en ningún resumen y arruina cualquier conteo que "
            "suponga que todos son 1, 2, 3 o 4."
        ),
    },
    {
        "columna": "P21",
        "que_es": (
            "Ingreso de la ocupación principal, en pesos. El 0 es «fuera de "
            "universo» y el −9, no respuesta."
        ),
        "clase": CONTINUA,
        "por_que": (
            "El dinero admite cualquier valor dentro de un intervalo y las "
            "diferencias son comparables. Que venga redondeado a pesos no lo "
            "vuelve discreto: lo discreto sería que solo pudiera tomar unos "
            "pocos valores posibles."
        ),
        "trampa": (
            "Tiene dos códigos escondidos entre los valores reales, y los dos "
            "son números que una máquina promedia sin quejarse."
        ),
    },
    {
        "columna": "PONDERA",
        "que_es": "Ponderador: a cuántas personas representa cada fila.",
        "clase": NO_VARIABLE,
        "por_que": (
            "No es una característica de la persona entrevistada sino una "
            "propiedad del diseño de la muestra. Describir su distribución "
            "no dice nada sobre la población."
        ),
        "trampa": (
            "Aparece como una columna numérica más y se cuela en cualquier "
            "«resumen de todas las variables» que uno pida al programa."
        ),
    },
]


# ---------------------------------------------------------------- teoría
# Escritas a mano: acá no hay nada que recalcular. Lo que el verificador sí
# puede exigir es que la respuesta esté entre las opciones, que cada
# distractor tenga su motivo y que el concepto que declaran exista.

TEORIA = [
    {
        "concepto": "estadistica-descriptiva-e-inferencial",
        "texto": (
            "Un informe publica que en el aglomerado Gran Catamarca el "
            "ingreso medio de la ocupación principal fue de $887.612, "
            "calculado con los ponderadores de la EPH. ¿Qué tipo de "
            "afirmación es?"
        ),
        "opciones": [
            "Inferencial: estima un valor de la población a partir de una muestra",
            "Descriptiva: resume los datos de las 1.339 personas relevadas",
            "Inferencial, porque el número tiene decimales",
            "Ninguna de las dos: es un dato administrativo",
        ],
        "respuesta":
            "Inferencial: estima un valor de la población a partir de una muestra",
        "solucion": (
            "El ponderador es lo que delata la intención: no se está "
            "describiendo a las 1.339 personas entrevistadas sino estimando "
            "el ingreso de toda la población del aglomerado a partir de "
            "ellas. Si el interés fuera solo la muestra, ponderar no tendría "
            "sentido."
        ),
        "por_que_no": [
            {
                "opcion":
                    "Descriptiva: resume los datos de las 1.339 personas relevadas",
                "motivo": (
                    "Sería descriptiva si el promedio fuera sin ponderar y la "
                    "conclusión se limitara a las personas entrevistadas."
                ),
            },
            {
                "opcion": "Inferencial, porque el número tiene decimales",
                "motivo": (
                    "La precisión del número no tiene nada que ver: un "
                    "promedio descriptivo también puede tener decimales."
                ),
            },
        ],
    },
    {
        "concepto": "poblacion-y-muestra",
        "texto": (
            "En ese mismo relevamiento, ¿cuál es la población?"
        ),
        "opciones": [
            "Las personas que viven en el aglomerado Gran Catamarca",
            "Las 1.339 personas entrevistadas",
            "Las 426 viviendas visitadas",
            "Todos los habitantes de la provincia de Catamarca",
        ],
        "respuesta": "Las personas que viven en el aglomerado Gran Catamarca",
        "solucion": (
            "La población es el conjunto sobre el que se quiere concluir. La "
            "EPH cubre aglomerados urbanos, así que acá es la población del "
            "aglomerado, no la muestra ni la provincia entera."
        ),
        "por_que_no": [
            {
                "opcion": "Las 1.339 personas entrevistadas",
                "motivo": "Esa es la muestra: el subconjunto que se observó.",
            },
            {
                "opcion": "Todos los habitantes de la provincia de Catamarca",
                "motivo": (
                    "La EPH no releva zonas rurales ni localidades chicas, "
                    "así que no permite concluir sobre toda la provincia."
                ),
            },
        ],
    },
    {
        "concepto": "unidad-de-analisis",
        "texto": (
            "En el archivo hay 1.339 filas y 426 valores distintos de CODUSU. "
            "Si el interés es el ingreso de las personas, ¿cuál es la unidad "
            "de análisis?"
        ),
        "opciones": [
            "La persona",
            "La vivienda",
            "El hogar",
            "El aglomerado",
        ],
        "respuesta": "La persona",
        "solucion": (
            "La unidad de análisis es aquello de lo que se predica la "
            "variable. El ingreso de la ocupación principal es de cada "
            "persona, y por eso hay una fila por persona: 1.339."
        ),
        "por_que_no": [
            {
                "opcion": "La vivienda",
                "motivo": (
                    "La vivienda es la unidad de **selección** de la muestra "
                    "—se eligen viviendas y se entrevista a todos sus "
                    "integrantes—, que es otra cosa que la unidad de análisis."
                ),
            },
            {
                "opcion": "El hogar",
                "motivo": (
                    "Sería el hogar si la variable fuera del hogar, como el "
                    "ingreso total familiar o la cantidad de ambientes."
                ),
            },
        ],
    },
    {
        "concepto": "parametro-y-estadistico",
        "texto": (
            "El ingreso medio calculado sobre las 1.339 personas del archivo "
            "es un…"
        ),
        "opciones": [
            "Estadístico, porque se calcula sobre la muestra",
            "Parámetro, porque describe a la población",
            "Parámetro, porque se usó el ponderador",
            "Ninguno: es un dato observado",
        ],
        "respuesta": "Estadístico, porque se calcula sobre la muestra",
        "solucion": (
            "El parámetro es el valor de la población, que no se conoce. Lo "
            "que se calcula con los datos observados es un estadístico, y "
            "sirve para estimar aquel. Ponderar no cambia eso: sigue "
            "calculándose con la muestra."
        ),
        "por_que_no": [
            {
                "opcion": "Parámetro, porque describe a la población",
                "motivo": (
                    "El parámetro existe pero no se observa. Si se conociera, "
                    "no haría falta la encuesta."
                ),
            },
            {
                "opcion": "Parámetro, porque se usó el ponderador",
                "motivo": (
                    "El ponderador sirve para estimar mejor el parámetro, no "
                    "para convertir el estadístico en uno."
                ),
            },
        ],
    },
    {
        "concepto": "censo-encuesta-registro",
        "texto": (
            "Las actas de nacimiento que carga el Registro Civil, con las que "
            "después se arman las estadísticas vitales, son un ejemplo de…"
        ),
        "opciones": [
            "Registro administrativo",
            "Censo",
            "Encuesta por muestreo",
            "Fuente secundaria",
        ],
        "respuesta": "Registro administrativo",
        "solucion": (
            "El dato se genera porque hay un trámite —inscribir un "
            "nacimiento—, no porque alguien haya salido a medir. Esa es la "
            "definición de registro administrativo, y explica sus virtudes "
            "—cobertura total y continuidad— y sus defectos: las variables "
            "son las que el trámite necesita y no las que el análisis querría."
        ),
        "por_que_no": [
            {
                "opcion": "Censo",
                "motivo": (
                    "Un censo es un operativo que releva a toda la población "
                    "en un momento dado. El registro es continuo y pasivo."
                ),
            },
            {
                "opcion": "Fuente secundaria",
                "motivo": (
                    "Primaria o secundaria depende de quién usa el dato, no "
                    "de cómo se generó: para el Registro Civil es primaria."
                ),
            },
        ],
    },
    {
        "concepto": "fuentes-primarias-y-secundarias",
        "texto": (
            "Alguien escribe una tesis usando el archivo de la EPH que bajó "
            "del sitio del INDEC. Para esa tesis, la EPH es una fuente…"
        ),
        "opciones": [
            "Secundaria: los datos los produjo otro con otro objetivo",
            "Primaria: son microdatos y no un resumen",
            "Primaria: los bajó directamente del organismo que los produce",
            "Depende de si los cita o no",
        ],
        "respuesta": "Secundaria: los datos los produjo otro con otro objetivo",
        "solucion": (
            "La distinción es sobre **quién generó el dato para qué**. Quien "
            "no participó del relevamiento usa una fuente secundaria, por más "
            "que la baje del organismo original y por más que sean microdatos."
        ),
        "por_que_no": [
            {
                "opcion": "Primaria: son microdatos y no un resumen",
                "motivo": (
                    "El nivel de desagregación no define la distinción. Un "
                    "microdato ajeno sigue siendo fuente secundaria."
                ),
            },
            {
                "opcion":
                    "Primaria: los bajó directamente del organismo que los produce",
                "motivo": (
                    "De dónde se baja el archivo tampoco cambia quién lo "
                    "produjo ni con qué objetivo."
                ),
            },
        ],
    },
    {
        "concepto": "error-y-sesgo",
        "texto": (
            "Una balanza marca siempre 200 gramos de más. Las mediciones que "
            "produce tienen…"
        ),
        "opciones": [
            "Sesgo, pero no necesariamente más error aleatorio",
            "Error aleatorio, pero no sesgo",
            "Ni sesgo ni error: es un problema de calibración",
            "Sesgo, que se corrige tomando más mediciones",
        ],
        "respuesta": "Sesgo, pero no necesariamente más error aleatorio",
        "solucion": (
            "El sesgo es un error que va siempre en la misma dirección. La "
            "balanza puede ser muy precisa —repetir la misma medición da "
            "siempre lo mismo— y estar corrida: precisión y exactitud son "
            "cosas distintas."
        ),
        "por_que_no": [
            {
                "opcion": "Sesgo, que se corrige tomando más mediciones",
                "motivo": (
                    "Esa es la confusión importante: promediar más "
                    "mediciones reduce el error aleatorio y **no toca el "
                    "sesgo**. Mil pesadas dan 200 gramos de más igual."
                ),
            },
            {
                "opcion": "Error aleatorio, pero no sesgo",
                "motivo": (
                    "El error aleatorio cambia de signo entre mediciones; "
                    "acá el corrimiento es constante."
                ),
            },
        ],
    },
    {
        "concepto": "matriz-de-datos",
        "texto": (
            "En una matriz de datos bien armada, ¿qué va en las filas?"
        ),
        "opciones": [
            "Las unidades de análisis, una por fila",
            "Las variables, una por fila",
            "Los valores, uno por fila",
            "Depende del programa que se use",
        ],
        "respuesta": "Las unidades de análisis, una por fila",
        "solucion": (
            "Una fila por caso y una columna por variable. Es la convención "
            "que esperan todos los programas estadísticos, y respetarla "
            "ahorra la mitad de los problemas de preparación."
        ),
        "por_que_no": [
            {
                "opcion": "Las variables, una por fila",
                "motivo": (
                    "Eso es la matriz transpuesta, que aparece seguido en "
                    "planillas armadas a mano y hay que dar vuelta antes de "
                    "analizar."
                ),
            },
            {
                "opcion": "Los valores, uno por fila",
                "motivo": (
                    "Ese es el formato largo, útil para algunas cosas, pero "
                    "no es la matriz de datos clásica."
                ),
            },
        ],
    },
]


def preguntas_de_teoria() -> list[dict]:
    """Las opciones se mezclan con semilla fija.

    Escritas de corrido, la correcta quedó primera en las ocho: se podían
    contestar sin leer. La semilla mantiene el orden estable entre
    compilaciones, que es lo que hace falta para que la respuesta publicada
    siga correspondiendo.
    """
    import random

    salida = []
    for i, q in enumerate(TEORIA, 1):
        opciones = list(q["opciones"])
        random.Random(9000 + i).shuffle(opciones)
        salida.append({
            "tipo": "opcion",
            "id": f"teoria-{i:02d}",
            "concepto": q["concepto"],
            "texto": q["texto"],
            "opciones": opciones,
            "respuesta": q["respuesta"],
            "solucion": q["solucion"],
            "por_que_no": q["por_que_no"],
        })
    return salida


def leer_columna(filas, nombre):
    return [f[nombre] for f in filas]


def main() -> None:
    with CSV.open(encoding="utf-8", newline="") as f:
        filas = list(csv.DictReader(f, delimiter=";"))

    preguntas = []
    for d in DICCIONARIO:
        valores = leer_columna(filas, d["columna"])
        distintos = len(set(valores))
        enteros = all(
            v.lstrip("-").isdigit() for v in valores if v not in ("", "NA")
        )
        top = Counter(valores).most_common(4)

        detalle = (
            f"En el archivo toma {distintos} "
            f"{'valor distinto' if distintos == 1 else 'valores distintos'}"
        )
        if distintos <= 8:
            detalle += (
                ": " + ", ".join(f"{v} ({n})" for v, n in
                                 sorted(Counter(valores).items(),
                                        key=lambda x: -x[1]))
            )
        detalle += "."

        preguntas.append({
            "tipo": "opcion",
            "columna": d["columna"],
            "texto": f"{d['columna']} — {d['que_es']}",
            "opciones": OPCIONES,
            "respuesta": d["clase"],
            "solucion": d["por_que"],
            "trampa": d["trampa"],
            "del_archivo": detalle,
            "distintos": distintos,
            "enteros": enteros,
            "codigos_declarados": sorted(d.get("codigos") or []),
            "codigos_del_archivo": sorted(set(valores))[:12],
        })

    salida = {
        "fuente": (
            "Clasificación de las columnas del extracto de la EPH publicado "
            "en /datos/eph-catamarca-2026t1.csv. Las clases salen de un "
            "diccionario declarado una sola vez en el generador."
        ),
        "generado_por": "datos/ejercicios/generar-fundamentos.py",
        "archivo": "/datos/eph-catamarca-2026t1.csv",
        "filas": len(filas),
        "advertencia": (
            "La respuesta es una categoría, así que no se recalcula como un "
            "número: se declara. Lo que el archivo permite comprobar —cuántos "
            "valores distintos hay, si son enteros— se comprueba; que una "
            "escala sea ordinal y no nominal es un criterio y no un dato."
        ),
        "opciones": OPCIONES,
        "teoria": {
            "id": "fundamentos-teoria",
            "tema": "conceptos-fundamentales",
            "concepto": "que-es-la-estadistica",
            "nivel": 1,
            "titulo": "¿Se entendieron los conceptos?",
            "preguntas": preguntas_de_teoria(),
        },
        "ejercicio": {
            "id": "fundamentos-clasificar",
            "tema": "clasificar-variables",
            "concepto": "tipos-de-variables",
            "nivel": 1,
            "titulo": "Clasificar las variables de un archivo real",
            "preguntas": preguntas,
        },
    }
    SALIDA.write_text(json.dumps(salida, indent=2, ensure_ascii=False),
                      encoding="utf-8")

    print(f"{len(preguntas)} columnas clasificadas sobre {len(filas)} filas\n")
    for p in preguntas:
        print(f"  {p['columna']:<12} {p['respuesta']:<34} "
              f"{p['distintos']:>5} distintos"
              + ("  [trampa]" if p["trampa"] else ""))
    print(f"\n{len(TEORIA)} preguntas teóricas")
    print(f"\n→ {SALIDA}")


if __name__ == "__main__":
    main()

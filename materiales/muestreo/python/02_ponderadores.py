"""Paso 2: los ponderadores.

El ponderador de diseño de una unidad es **la inversa de su probabilidad de
inclusión**. Nada más que eso, y nada menos: no es un ajuste ni una
corrección, es cuántas unidades de la población representa la que se
seleccionó.

De ahí sale la única comprobación que siempre hay que hacer y que casi nunca
se hace: **la suma de los ponderadores tiene que dar el tamaño de la
población.** Si da otra cosa, hay un error en el diseño o en el cálculo, y
todo lo que venga después está mal sin que se note.

Este paso también hace dos cosas que en cualquier encuesta real hay que
hacer y que el ejemplo muestra en chico:

    no respuesta        los hogares que no contestan se descuentan dentro de
                        su propio conglomerado, y el peso de los que sí
                        contestaron se agranda para cubrirlos. Supone que el
                        que no contestó se parece a sus vecinos, que es un
                        supuesto fuerte y hay que decirlo.
    post-estratificación se ajustan los pesos para que los totales por región
                        den exactamente los del marco. Baja la varianza y
                        corrige parte del sesgo de no respuesta.

Y avisa cuando los pesos quedan muy desparejos, que es lo que hace que una
muestra de trescientos casos tenga la precisión de ochenta.
"""

import math

from comun import indices_por, limpiar_texto, ordenar


def de_diseno(seleccion):
    """El peso de diseño: uno sobre la probabilidad de inclusión."""
    return [{"fila": f["fila"], "conglomerado": f["conglomerado"],
             "probabilidad": f["probabilidad"], "peso": 1 / f["probabilidad"]}
            for f in seleccion]


def ajustar_por_no_respuesta(pesos, respondieron):
    """Reparte el peso de los que no contestaron entre los que sí, dentro del
    mismo conglomerado.

    Es el ajuste por celdas más simple que existe y el que se usa por omisión
    cuando no hay nada mejor. Cuando un conglomerado entero no contesta no hay
    a quién repartirle, y ahí el ajuste no puede hacer nada: eso queda
    escrito.
    """
    por_celda: dict = {}
    for i, p in enumerate(pesos):
        clave = p["conglomerado"] if p["conglomerado"] is not None else "—"
        por_celda.setdefault(clave, []).append(i)

    salida = []
    celdas_perdidas = 0
    for clave in ordenar(list(por_celda)):
        indices = por_celda[clave]
        total = math.fsum(pesos[i]["peso"] for i in indices)
        con_dato = [i for i in indices if respondieron[i]]
        if not con_dato:
            celdas_perdidas += 1
            continue
        logrado = math.fsum(pesos[i]["peso"] for i in con_dato)
        factor = total / logrado
        for i in con_dato:
            salida.append({**pesos[i], "factor_no_respuesta": factor,
                           "peso": pesos[i]["peso"] * factor})
    salida.sort(key=lambda f: f["fila"])
    return salida, celdas_perdidas


def post_estratificar(datos, pesos, columna):
    """Ajusta los pesos para que los totales por celda den los del marco.

    El factor de cada celda es el total verdadero sobre el total estimado. Con
    una sola variable de calibración es una cuenta de una línea; con varias a
    la vez hay que iterar (el «raking»), que este proyecto no trae.
    """
    if not columna:
        return pesos, []
    verdaderos = {k: len(v) for k, v in indices_por(datos, columna).items()}
    estimados: dict = {}
    for p in pesos:
        clave = limpiar_texto(datos[p["fila"]].get(columna, ""))
        estimados[clave] = estimados.get(clave, 0.0) + p["peso"]

    detalle = []
    factores = {}
    for clave in ordenar(list(verdaderos)):
        estimado = estimados.get(clave, 0.0)
        factor = verdaderos[clave] / estimado if estimado > 0 else 1.0
        factores[clave] = factor
        detalle.append({"celda": clave, "en_el_marco": verdaderos[clave],
                        "estimado_antes": estimado, "factor": factor})

    salida = []
    for p in pesos:
        clave = limpiar_texto(datos[p["fila"]].get(columna, ""))
        salida.append({**p, "factor_post": factores.get(clave, 1.0),
                       "peso": p["peso"] * factores.get(clave, 1.0)})
    return salida, detalle


def resumir(pesos, poblacion):
    """Lo que hay que mirar de un vector de pesos antes de usarlo."""
    valores = [p["peso"] for p in pesos]
    n = len(valores)
    suma = math.fsum(valores)
    media = suma / n
    varianza = math.fsum((v - media) ** 2 for v in valores) / (n - 1) if n > 1 else 0.0
    cv = math.sqrt(varianza) / media if media > 0 else 0.0
    return {
        "n": n, "suma": suma, "poblacion": poblacion,
        "diferencia_con_la_poblacion": suma - poblacion,
        "minimo": min(valores), "maximo": max(valores), "media": media,
        "coeficiente_de_variacion": cv,
        "razon_maximo_minimo": max(valores) / min(valores) if min(valores) > 0 else float("inf"),
        # El efecto de los pesos desiguales sobre la varianza, de Kish. Es
        # cuánto se paga por ponderar, aparte de lo que se paga por
        # conglomerar.
        "deff_de_kish": 1 + cv ** 2,
        "n_efectivo_de_kish": n / (1 + cv ** 2),
    }


def calcular(datos, parametros, seleccion, respondieron=None):
    """Los tres momentos del ponderador: de diseño, ajustado y calibrado.

    Se escriben los tres porque cada uno responde una pregunta distinta. El de
    diseño tiene que sumar exactamente la población: si no, hay un error. El
    ajustado tiene que volver a sumarla después de la no respuesta. Y el
    calibrado tiene que dar los totales conocidos por celda.
    """
    poblacion = len(datos)
    pesos = de_diseno(seleccion)
    avisos = []
    antes = resumir(pesos, poblacion)

    celdas_perdidas = 0
    if respondieron is not None:
        logrados = sum(1 for r in respondieron if r)
        sin_ajustar = resumir([p for p, r in zip(pesos, respondieron) if r], poblacion)
        pesos, celdas_perdidas = ajustar_por_no_respuesta(pesos, respondieron)
        if celdas_perdidas:
            avisos.append({"donde": "no respuesta",
                           "aviso": f"Hay {celdas_perdidas} conglomerados donde no contestó "
                                    f"nadie. Ahí el ajuste no tiene a quién repartirle el "
                                    f"peso, así que esos casos quedan afuera y la muestra "
                                    f"representa menos población de la que debería."})
        avisos.append({"donde": "no respuesta",
                       "aviso": f"Contestaron {logrados} de {len(respondieron)} hogares. Sin "
                                f"ajustar, los pesos sumarían "
                                + f"{sin_ajustar['suma']:.0f}".replace(".", ",")
                                + f" y no {poblacion}: la encuesta estaría representando "
                                  f"menos población de la que hay. El ajuste reparte el peso "
                                  f"de los que faltan entre sus vecinos del mismo "
                                  f"conglomerado, y eso supone que se parecen. Es un "
                                  f"supuesto, no un dato."})
    tras_no_respuesta = resumir(pesos, poblacion)

    columna = parametros.get("calibrar_por") or parametros["estrato"]
    pesos, calibracion = post_estratificar(datos, pesos, columna)
    despues = resumir(pesos, poblacion)

    if abs(antes["diferencia_con_la_poblacion"]) > 1e-6:
        avisos.append({"donde": "ponderadores",
                       "aviso": "La suma de los pesos de diseño no da el tamaño de la "
                                "población. Con una selección sin no respuesta tiene que dar "
                                "exacto: si no da, hay un error en las probabilidades de "
                                "inclusión y todo lo que venga después está mal."})
    if despues["razon_maximo_minimo"] > 5:
        avisos.append({"donde": "ponderadores",
                       "aviso": "El peso más grande es más de cinco veces el más chico. Con "
                                "pesos así de desparejos unos pocos casos mandan sobre la "
                                "estimación: conviene mirar si vale la pena recortarlos, "
                                "aunque recortar introduce sesgo."})
    if despues["deff_de_kish"] > 1.2:
        avisos.append({"donde": "ponderadores",
                       "aviso": "Los pesos desiguales por sí solos ya inflan la varianza un "
                                + f"{(despues['deff_de_kish'] - 1) * 100:.0f}".replace(".", ",")
                                + " % (efecto de Kish). Eso es aparte de lo que cueste el "
                                  "conglomerado, y se suma."})

    if calibracion and all(abs(c["factor"] - 1) < 1e-9 for c in calibracion):
        avisos.append({"donde": "calibración",
                       "aviso": "La post-estratificación no cambió ningún peso: todos los "
                                "factores dieron uno. Es lo que tiene que pasar cuando se "
                                "calibra sobre la misma variable que ya estratificó el "
                                "diseño, y conviene saberlo, porque calibrar sobre algo que "
                                "el diseño ya controla da la sensación de haber corregido "
                                "algo sin haber corregido nada."})
    elif calibracion:
        mayor = max(abs(c["factor"] - 1) for c in calibracion)
        avisos.append({"donde": "calibración",
                       "aviso": f"La post-estratificación movió los pesos hasta un "
                                + f"{mayor * 100:.1f}".replace(".", ",")
                                + " %. Eso es lo que la muestra se había desviado de los "
                                  "totales conocidos, y es la parte del sesgo de no "
                                  "respuesta que la calibración sí puede corregir."})

    return {"pesos": pesos, "antes": antes, "tras_no_respuesta": tras_no_respuesta,
            "despues": despues, "calibracion": calibracion,
            "celdas_perdidas": celdas_perdidas, "avisos": avisos}

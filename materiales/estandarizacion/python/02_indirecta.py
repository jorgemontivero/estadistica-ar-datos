"""Paso 2: estandarización indirecta.

La directa aplica **las tasas propias** sobre una estructura ajena. La
indirecta hace lo contrario: aplica **las tasas de una referencia** sobre la
estructura propia, y pregunta cuántos casos habría si esta población se
muriera como la referencia.

    esperados = Σ nᵢ · mᵢ(referencia)
    razón     = observados / esperados

La razón se llama RME cuando son muertes (SMR en inglés) y RIE cuando son casos
nuevos. Un 1,20 quiere decir veinte por ciento más de lo que la estructura de
edad hacía esperar.

**Para qué sirve si ya está la directa.** Para lo que la directa no puede: la
indirecta solo necesita el **total** de casos observados, no el detalle por
edad. Sirve donde la directa se rompe —poblaciones chicas, causas poco
frecuentes, casos por edad no publicados— porque no hay que estimar una tasa
por grupo, que es justamente lo que se vuelve inestable con pocos casos.

**Lo que se paga.** Dos razones indirectas no son estrictamente comparables
entre sí, porque cada una está ajustada a su propia estructura. Se comparan
contra la referencia, no entre ellas. En la práctica se las compara igual, y
este paso deja al lado la tasa directa para que se vea cuánto se parecen.
"""

import math

from comun import ic_poisson


def tasas_de_referencia(poblaciones, grupos, cuales):
    """Las tasas específicas de la referencia, grupo por grupo.

    Si no se nombra ninguna población, la referencia es la suma de todas: es lo
    que hace la DEIS para comparar provincias contra el total del país.
    """
    if cuales:
        faltan = [c for c in cuales if c not in poblaciones]
        if faltan:
            raise SystemExit(f"La referencia «{', '.join(faltan)}» no está en los datos.")
        elegidas = cuales
    else:
        elegidas = sorted(poblaciones)

    tasas = {}
    casos_totales = 0.0
    expuestos_totales = 0.0
    for g in grupos:
        casos = math.fsum(poblaciones[p][g]["casos"] for p in elegidas)
        expuestos = math.fsum(poblaciones[p][g]["expuestos"] for p in elegidas)
        tasas[g] = casos / expuestos if expuestos > 0 else 0.0
        casos_totales += casos
        expuestos_totales += expuestos
    return {
        "nombre": " + ".join(elegidas) if cuales else "el total de las poblaciones",
        "tasas": tasas,
        "casos": casos_totales,
        "expuestos": expuestos_totales,
        "cruda": casos_totales / expuestos_totales if expuestos_totales > 0 else 0.0,
        "es_el_total": not cuales,
    }


def calcular(poblaciones, grupos, referencia, directas, parametros):
    """Una fila por población: observados, esperados, la razón y su intervalo."""
    multiplicador = parametros["multiplicador"]
    confianza = parametros["confianza"]
    por_nombre = {f["poblacion"]: f for f in directas}

    filas = []
    for nombre in sorted(poblaciones):
        celdas = poblaciones[nombre]
        observados = math.fsum(celdas[g]["casos"] for g in grupos)
        expuestos = math.fsum(celdas[g]["expuestos"] for g in grupos)
        esperados = math.fsum(celdas[g]["expuestos"] * referencia["tasas"][g]
                              for g in grupos)
        if not esperados > 0:
            continue

        # El intervalo de la razón sale del intervalo exacto del CONTEO
        # observado, dividido por los esperados. Los esperados se tratan como
        # conocidos, que es la convención: vienen de una población grande.
        ic = ic_poisson(observados, confianza)
        razon = observados / esperados
        directa = por_nombre.get(nombre)
        indirecta = razon * referencia["cruda"] * multiplicador

        filas.append({
            "poblacion": nombre,
            "observados": int(observados),
            "esperados": esperados,
            "razon": razon,
            "razon_inferior": ic["inferior"] / esperados,
            "razon_superior": ic["superior"] / esperados,
            "distinta_de_uno": not (ic["inferior"] / esperados <= 1
                                    <= ic["superior"] / esperados),
            "estandarizada_indirecta": indirecta,
            "estandarizada_directa": directa["estandarizada"] if directa else None,
            "diferencia_con_la_directa": (
                indirecta - directa["estandarizada"] if directa else None),
            "cruda": observados / expuestos * multiplicador if expuestos > 0 else None,
            # Se inicializan acá para que la clave exista siempre: más abajo se
            # rellenan solo las que tienen con qué.
            "rango_indirecto": None, "rango_directo": None,
        })

    # Los dos ordenamientos, para poder decir si coinciden.
    for clave, destino in (("razon", "rango_indirecto"),
                           ("estandarizada_directa", "rango_directo")):
        utiles = [f for f in filas if f[clave] is not None]
        orden = sorted(utiles, key=lambda f: (-f[clave], f["poblacion"]))
        for i, fila in enumerate(orden, start=1):
            fila[destino] = i
    filas.sort(key=lambda f: (-f["razon"], f["poblacion"]))
    return filas


def avisos_de(filas, referencia, parametros):
    salida = []
    if referencia["es_el_total"]:
        # Con la referencia igual al total, los esperados tienen que sumar los
        # observados: es una identidad, no una coincidencia.
        observados = math.fsum(f["observados"] for f in filas)
        esperados = math.fsum(f["esperados"] for f in filas)
        if abs(observados - esperados) > 1e-6 * max(1.0, observados):
            salida.append({
                "donde": "indirecta",
                "aviso": "Los casos esperados no suman los observados. Con la referencia "
                         "igual al total de las poblaciones eso es una identidad, así que "
                         "si no cierra hay un error en los datos o en la cuenta."})

    pocos = [f for f in filas if f["observados"] < 10]
    if pocos:
        salida.append({
            "donde": "indirecta",
            "aviso": f"Hay {len(pocos)} población(es) con menos de diez casos observados. "
                     f"El intervalo de la razón es exacto —no falla— pero sale tan ancho "
                     f"que no alcanza para concluir gran cosa."})

    flacos = [f for f in filas if f["esperados"] < 5]
    if flacos:
        salida.append({
            "donde": "indirecta",
            "aviso": f"Hay {len(flacos)} población(es) con menos de cinco casos esperados. "
                     f"La razón se vuelve muy sensible: un caso más o menos la mueve "
                     f"muchísimo."})

    iguales = [f for f in filas if not f["distinta_de_uno"]]
    if iguales:
        salida.append({
            "donde": "indirecta",
            "aviso": f"En {len(iguales)} de las {len(filas)} poblaciones el intervalo de "
                     f"la razón contiene al uno: su mortalidad no se distingue de la que "
                     f"la estructura de edad hacía esperar."})

    con_las_dos = [f for f in filas if f["rango_directo"] is not None]
    if con_las_dos:
        peor = max(con_las_dos, key=lambda f: abs(f["rango_directo"] - f["rango_indirecto"]))
        distancia = abs(peor["rango_directo"] - peor["rango_indirecto"])
        if distancia > 0:
            salida.append({
                "donde": "indirecta",
                "aviso": f"El orden por razón indirecta y el orden por tasa directa no son "
                         f"el mismo: «{peor['poblacion']}» está {distancia} puesto(s) más "
                         f"arriba en uno que en el otro. Son dos preguntas distintas y no "
                         f"tienen por qué coincidir; cuando coinciden es porque las tasas "
                         f"específicas van casi todas para el mismo lado."})
    return salida

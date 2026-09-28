"""Paso 1: estandarización directa.

La pregunta que contesta es una sola: **¿cuánto sería la tasa de cada
población si todas tuvieran la misma estructura por edad?**

Sin eso, dos tasas crudas no se pueden comparar. Una población más vieja tiene
más muertes aunque se muera menos a cada edad, y eso no es un detalle: en los
datos de este proyecto, la jurisdicción con la tasa cruda **más alta** del país
es la que tiene la **segunda más baja** una vez ajustada.

La cuenta es un promedio ponderado de las tasas específicas por edad, con los
pesos de la población estándar en vez de los propios:

    tasa ajustada = Σ (wᵢ / W) · (dᵢ / nᵢ)

Toda la idea está en esa línea. Lo que tiene trabajo es el intervalo: una suma
ponderada de Poisson no es Poisson, y por eso va el método de Fay-Feuer, que
está en `comun.py`.
"""

import math

from comun import ic_fay_feuer, ic_poisson


def calcular(poblaciones, grupos, pesos, parametros):
    """Una fila por población: la cruda, la ajustada y el lugar en cada orden."""
    multiplicador = parametros["multiplicador"]
    confianza = parametros["confianza"]
    total_peso = math.fsum(pesos[g] for g in grupos)
    if not total_peso > 0:
        raise SystemExit("Los pesos de la población estándar suman cero.")

    filas = []
    for nombre in poblaciones:
        celdas = poblaciones[nombre]
        casos = math.fsum(celdas[g]["casos"] for g in grupos)
        expuestos = math.fsum(celdas[g]["expuestos"] for g in grupos)
        if not expuestos > 0:
            continue

        # El promedio de las tasas específicas, ponderado por la estructura
        # estándar. Y la varianza de esa suma, tratando cada conteo como
        # Poisson: Var(Σ wᵢ dᵢ/nᵢ) = Σ (wᵢ/nᵢ)² dᵢ.
        ajustada = 0.0
        varianza = 0.0
        mayor_peso = 0.0
        aportes = []
        for g in grupos:
            expuestos_g = celdas[g]["expuestos"]
            if not expuestos_g > 0:
                continue
            peso = pesos[g] / total_peso
            tasa = celdas[g]["casos"] / expuestos_g
            ajustada += peso * tasa
            coeficiente = peso / expuestos_g
            varianza += coeficiente * coeficiente * celdas[g]["casos"]
            mayor_peso = max(mayor_peso, coeficiente)
            aportes.append(peso * tasa)

        ic = ic_fay_feuer(ajustada, varianza, mayor_peso, confianza)
        cruda = casos / expuestos
        ic_cruda = ic_poisson(casos, confianza)
        ultimo = celdas[grupos[-1]]["expuestos"] / expuestos

        filas.append({
            "poblacion": nombre,
            "casos": int(casos),
            "expuestos": int(expuestos),
            "proporcion_en_el_grupo_mayor": ultimo,
            "cruda": cruda * multiplicador,
            "cruda_inferior": ic_cruda["inferior"] / expuestos * multiplicador,
            "cruda_superior": ic_cruda["superior"] / expuestos * multiplicador,
            "estandarizada": ajustada * multiplicador,
            "estandarizada_inferior": ic["inferior"] * multiplicador,
            "estandarizada_superior": ic["superior"] * multiplicador,
            "cambio_relativo": (ajustada / cruda - 1) if cruda > 0 else None,
            # Cuántos casos habría con la misma gente y la estructura estándar.
            "casos_con_la_estructura_estandar": ajustada * expuestos,
        })

    poner_rangos(filas)
    return filas


def poner_rangos(filas):
    """El lugar de cada población en los dos ordenamientos, y cuánto se movió.

    El orden se rompe por nombre cuando dos tasas dan exactamente igual, para
    que los dos motores escriban las mismas filas en el mismo lugar.
    """
    for clave, destino in (("cruda", "rango_crudo"),
                           ("estandarizada", "rango_estandarizado")):
        orden = sorted(filas, key=lambda f: (-f[clave], f["poblacion"]))
        for i, fila in enumerate(orden, start=1):
            fila[destino] = i
    for fila in filas:
        fila["cambio_de_rango"] = fila["rango_crudo"] - fila["rango_estandarizado"]
    filas.sort(key=lambda f: (-f["estandarizada"], f["poblacion"]))


def por_edad(poblaciones, grupos, pesos, parametros):
    """El detalle que hay detrás de cada tasa ajustada.

    Es la tabla que hay que mirar cuando el resultado sorprende: ahí se ve si
    la diferencia viene de una edad en particular o está repartida.
    """
    multiplicador = parametros["multiplicador"]
    total_peso = math.fsum(pesos[g] for g in grupos)
    filas = []
    for nombre in sorted(poblaciones):
        celdas = poblaciones[nombre]
        expuestos_totales = math.fsum(celdas[g]["expuestos"] for g in grupos)
        for g in grupos:
            expuestos = celdas[g]["expuestos"]
            casos = celdas[g]["casos"]
            peso = pesos[g] / total_peso
            tasa = casos / expuestos if expuestos > 0 else None
            filas.append({
                "poblacion": nombre,
                "grupo_edad": g,
                "casos": int(casos),
                "expuestos": int(expuestos),
                "proporcion_propia": (expuestos / expuestos_totales
                                      if expuestos_totales > 0 else None),
                "peso_estandar": peso,
                "tasa_especifica": tasa * multiplicador if tasa is not None else None,
                "aporte": peso * tasa * multiplicador if tasa is not None else None,
            })
    return filas


def avisos_de(filas, detalle, parametros):
    """Lo que hay que decir sobre las tasas, además de los números."""
    salida = []

    # El hallazgo, si está: una población que cambia de punta a punta.
    vuelcos = [f for f in filas if abs(f["cambio_de_rango"]) >= len(filas) // 2]
    if vuelcos:
        peor = max(vuelcos, key=lambda f: abs(f["cambio_de_rango"]))
        salida.append({
            "donde": "estandarización",
            "aviso": f"«{peor['poblacion']}» pasa del puesto {peor['rango_crudo']} al "
                     f"{peor['rango_estandarizado']} al ajustar por edad. La tasa cruda y "
                     f"la ajustada no dicen lo mismo: dicen cosas distintas, y comparar "
                     f"poblaciones con la cruda es comparar estructuras de edad."})

    # Grupos con pocos casos: ahí la directa se vuelve inestable.
    flacos: dict = {}
    for f in detalle:
        if f["expuestos"] > 0 and f["casos"] < 5:
            flacos[f["poblacion"]] = flacos.get(f["poblacion"], 0) + 1
    if flacos:
        cuantas = len(flacos)
        peor = max(flacos, key=lambda p: (flacos[p], p))
        salida.append({
            "donde": "estandarización",
            "aviso": f"Hay {cuantas} población(es) con algún grupo de edad de menos de "
                     f"cinco casos —«{peor}» tiene {flacos[peor]}—. Una tasa específica "
                     f"calculada con cuatro muertes es muy inestable y la ajustada la "
                     f"arrastra: ahí conviene mirar también la indirecta, que no necesita "
                     f"estimar una tasa por grupo."})

    vacios = [f for f in detalle if f["expuestos"] == 0]
    if vacios:
        salida.append({
            "donde": "datos",
            "aviso": f"Hay {len(vacios)} celda(s) sin nadie expuesto. Ese grupo no aporta "
                     f"nada a la tasa ajustada de esa población, y su peso estándar queda "
                     f"sin usar: la suma de los pesos efectivos no llega a uno y la tasa "
                     f"sale más baja de lo que debería."})

    # Intervalos que se pisan con el de arriba: el orden no está establecido.
    pisados = 0
    for i in range(len(filas) - 1):
        a, b = filas[i], filas[i + 1]
        if a["estandarizada_inferior"] <= b["estandarizada_superior"]:
            pisados += 1
    if pisados:
        salida.append({
            "donde": "estandarización",
            "aviso": f"En {pisados} de los {len(filas) - 1} escalones del ranking el "
                     f"intervalo de una población se pisa con el de la siguiente. Un "
                     f"ranking se lee como si cada puesto estuviera decidido, y la mayoría "
                     f"de estos no lo están."})
    return salida

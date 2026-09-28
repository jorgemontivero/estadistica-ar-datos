"""Paso 3: comparar, y saber cuánto de la comparación es real.

Tres cosas que la tasa ajustada sola no contesta:

1. **¿Cuánto depende del estándar elegido?** Una tasa ajustada no es un número
   de la población: es un número de la población *y del estándar*. Cambiar de
   estándar cambia el nivel muchísimo —en estos datos, hasta el doble— y a
   veces también el orden. Este paso recalcula todo con cada estándar
   disponible y deja escrito exactamente qué pares se dan vuelta.

2. **¿La diferencia entre dos poblaciones es de estructura o de riesgo?** La
   descomposición de Kitagawa parte la diferencia entre dos tasas crudas en
   dos sumandos que suman exactamente la diferencia:

       C_a − C_b = Σ (p_ai − p_bi)·(m_ai + m_bi)/2   ← estructura
                 + Σ (m_ai − m_bi)·(p_ai + p_bi)/2   ← tasas

   La primera suma es cuánto de la brecha viene de que las poblaciones tienen
   edades distintas; la segunda, de que a cada edad se muere distinto. La
   identidad es exacta y no aproximada, y por eso sirve de comprobación.

3. **¿La diferencia entre dos tasas ajustadas está establecida?** La razón
   entre dos tasas, con su intervalo en escala logarítmica.
"""

import itertools
import math

from comun import razon_de_tasas, se_pisan


def por_estandar(poblaciones, grupos, todos_los_pesos, parametros, calcular_directa):
    """La misma tasa ajustada, con cada estándar disponible."""
    filas = []
    por_estandar_: dict = {}
    for estandar in sorted(todos_los_pesos):
        resultado = calcular_directa(poblaciones, grupos, todos_los_pesos[estandar],
                                     parametros)
        por_estandar_[estandar] = {f["poblacion"]: f for f in resultado}
        for f in resultado:
            filas.append({
                "estandar": estandar,
                "poblacion": f["poblacion"],
                "tasa": f["estandarizada"],
                "inferior": f["estandarizada_inferior"],
                "superior": f["estandarizada_superior"],
                "rango": f["rango_estandarizado"],
            })
    filas.sort(key=lambda f: (f["estandar"], f["rango"], f["poblacion"]))
    return filas, por_estandar_


def sensibilidad(por_estandar_, parametros):
    """Los pares cuyo orden depende de con qué estándar se los mire.

    Es la comprobación de una frase que se dice mucho y es falsa: que el
    estándar cambia el nivel pero no el orden. Cambia el orden. Lo que hay que
    ver es **cuáles** pares se dan vuelta, y si son pares que alguien hubiera
    afirmado distintos.
    """
    estandares = sorted(por_estandar_)
    poblaciones = sorted(next(iter(por_estandar_.values())))
    filas = []
    for uno, otro in itertools.combinations(estandares, 2):
        for a, b in itertools.combinations(poblaciones, 2):
            ta, tb = por_estandar_[uno][a], por_estandar_[uno][b]
            oa, ob = por_estandar_[otro][a], por_estandar_[otro][b]
            primero = ta["estandarizada"] - tb["estandarizada"]
            segundo = oa["estandarizada"] - ob["estandarizada"]
            if primero == 0 or segundo == 0 or (primero > 0) == (segundo > 0):
                continue
            filas.append({
                "estandar_1": uno, "estandar_2": otro,
                "poblacion_a": a, "poblacion_b": b,
                "tasa_a_1": ta["estandarizada"], "tasa_b_1": tb["estandarizada"],
                "tasa_a_2": oa["estandarizada"], "tasa_b_2": ob["estandarizada"],
                "distancia_1": abs(primero), "distancia_2": abs(segundo),
                # El solapamiento se mira con CADA estándar por separado. Un par
                # que se da vuelta y cuyos intervalos se pisan con los dos no
                # estaba ordenado de entrada; uno que se da vuelta y NO se pisa
                # con alguno es el caso peligroso: con ese estándar la
                # diferencia parecía establecida.
                "se_pisan_con_1": se_pisan(
                    {"inferior": ta["estandarizada_inferior"],
                     "superior": ta["estandarizada_superior"]},
                    {"inferior": tb["estandarizada_inferior"],
                     "superior": tb["estandarizada_superior"]}),
                "se_pisan_con_2": se_pisan(
                    {"inferior": oa["estandarizada_inferior"],
                     "superior": oa["estandarizada_superior"]},
                    {"inferior": ob["estandarizada_inferior"],
                     "superior": ob["estandarizada_superior"]}),
            })
            filas[-1]["se_pisan_con_los_dos"] = (filas[-1]["se_pisan_con_1"]
                                                 and filas[-1]["se_pisan_con_2"])
    filas.sort(key=lambda f: (f["estandar_1"], f["estandar_2"], f["poblacion_a"],
                              f["poblacion_b"]))
    return filas


def niveles(por_estandar_):
    """Cuánto cambia el NIVEL de una misma tasa según el estándar."""
    estandares = sorted(por_estandar_)
    poblaciones = sorted(next(iter(por_estandar_.values())))
    filas = []
    for p in poblaciones:
        valores = [por_estandar_[e][p]["estandarizada"] for e in estandares]
        menor, mayor = min(valores), max(valores)
        filas.append({
            "poblacion": p, "menor": menor, "mayor": mayor,
            "razon_entre_niveles": mayor / menor if menor > 0 else None,
            "estandar_del_menor": estandares[valores.index(menor)],
            "estandar_del_mayor": estandares[valores.index(mayor)],
        })
    return filas


def _kitagawa(celdas_a, celdas_b, grupos):
    """Los dos efectos, grupo por grupo. Suman exactamente la diferencia."""
    na = math.fsum(celdas_a[g]["expuestos"] for g in grupos)
    nb = math.fsum(celdas_b[g]["expuestos"] for g in grupos)
    salida = []
    for g in grupos:
        pa = celdas_a[g]["expuestos"] / na if na > 0 else 0.0
        pb = celdas_b[g]["expuestos"] / nb if nb > 0 else 0.0
        ma = (celdas_a[g]["casos"] / celdas_a[g]["expuestos"]
              if celdas_a[g]["expuestos"] > 0 else 0.0)
        mb = (celdas_b[g]["casos"] / celdas_b[g]["expuestos"]
              if celdas_b[g]["expuestos"] > 0 else 0.0)
        salida.append({
            "grupo_edad": g,
            "proporcion_a": pa, "proporcion_b": pb,
            "tasa_a": ma, "tasa_b": mb,
            "efecto_estructura": (pa - pb) * (ma + mb) / 2,
            "efecto_tasas": (ma - mb) * (pa + pb) / 2,
        })
    return salida


def descomponer(poblaciones, grupos, pares, parametros):
    """La descomposición de Kitagawa para cada par pedido, grupo por grupo."""
    multiplicador = parametros["multiplicador"]
    filas = []
    for a, b in pares:
        if a not in poblaciones or b not in poblaciones:
            continue
        for fila in _kitagawa(poblaciones[a], poblaciones[b], grupos):
            filas.append({
                "poblacion_a": a, "poblacion_b": b,
                "grupo_edad": fila["grupo_edad"],
                "proporcion_a": fila["proporcion_a"],
                "proporcion_b": fila["proporcion_b"],
                "tasa_a": fila["tasa_a"] * multiplicador,
                "tasa_b": fila["tasa_b"] * multiplicador,
                "efecto_estructura": fila["efecto_estructura"] * multiplicador,
                "efecto_tasas": fila["efecto_tasas"] * multiplicador,
            })
    return filas


def comparar(poblaciones, grupos, directas, pares, parametros):
    """Por cada par: la brecha cruda partida en dos, y la razón entre ajustadas."""
    multiplicador = parametros["multiplicador"]
    confianza = parametros["confianza"]
    por_nombre = {f["poblacion"]: f for f in directas}
    filas = []
    for a, b in pares:
        if a not in poblaciones or b not in poblaciones:
            raise SystemExit(f"«{a}» o «{b}» no está en los datos. Revisá «pares» en "
                             f"datos/parametros.csv.")
        fa, fb = por_nombre[a], por_nombre[b]
        partes = _kitagawa(poblaciones[a], poblaciones[b], grupos)
        estructura = math.fsum(p["efecto_estructura"] for p in partes) * multiplicador
        tasas = math.fsum(p["efecto_tasas"] for p in partes) * multiplicador
        diferencia = fa["cruda"] - fb["cruda"]
        razon = razon_de_tasas(
            {"valor": fa["estandarizada"], "inferior": fa["estandarizada_inferior"],
             "superior": fa["estandarizada_superior"]},
            {"valor": fb["estandarizada"], "inferior": fb["estandarizada_inferior"],
             "superior": fb["estandarizada_superior"]}, confianza)
        filas.append({
            "poblacion_a": a, "poblacion_b": b,
            "cruda_a": fa["cruda"], "cruda_b": fb["cruda"],
            "diferencia_cruda": diferencia,
            "efecto_estructura": estructura,
            "efecto_tasas": tasas,
            "residuo_de_la_identidad": diferencia - (estructura + tasas),
            # Qué proporción de la brecha cruda explica cada efecto. Puede pasar
            # de uno, y pasa: cuando los dos efectos van para lados contrarios,
            # la estructura explica más del 100 % y las tasas restan.
            "parte_estructura": estructura / diferencia if diferencia != 0 else None,
            "estandarizada_a": fa["estandarizada"], "estandarizada_b": fb["estandarizada"],
            "diferencia_estandarizada": fa["estandarizada"] - fb["estandarizada"],
            "razon": razon["valor"] if razon else None,
            "razon_inferior": razon["inferior"] if razon else None,
            "razon_superior": razon["superior"] if razon else None,
            "la_razon_excluye_al_uno": (
                not (razon["inferior"] <= 1 <= razon["superior"]) if razon else None),
            "se_dan_vuelta": (diferencia > 0) != (fa["estandarizada"] > fb["estandarizada"]),
        })
    return filas


def avisos_de(sensibles, niveles_, comparaciones):
    salida = []
    if sensibles:
        pisados = sum(1 for f in sensibles if f["se_pisan_con_los_dos"])
        peligrosos = len(sensibles) - pisados
        aviso = (f"Hay {len(sensibles)} par(es) de poblaciones cuyo orden se da vuelta "
                 f"según con qué estándar se las mire, y en {pisados} de ellos los "
                 f"intervalos se pisan con los dos estándares. Es la respuesta a la frase "
                 f"de que el estándar cambia el nivel pero no el orden: cambia el orden, y "
                 f"casi siempre lo cambia donde no estaba establecido.")
        if peligrosos:
            aviso += (f" Casi siempre, pero no siempre: en {peligrosos} par(es) los "
                      f"intervalos NO se pisan con alguno de los dos estándares, así que "
                      f"con ese estándar la diferencia parecía establecida y con el otro se "
                      f"da vuelta. Están marcados en sensibilidad.csv.")
        salida.append({"donde": "estándar", "aviso": aviso})
    if niveles_:
        peor = max(niveles_, key=lambda f: f["razon_entre_niveles"] or 0)
        if peor["razon_entre_niveles"] and peor["razon_entre_niveles"] > 1.2:
            salida.append({
                "donde": "estándar",
                "aviso": f"La tasa de «{peor['poblacion']}» va de "
                         + f"{peor['menor']:.1f}".replace(".", ",") + " con el estándar «"
                         + f"{peor['estandar_del_menor']}» a "
                         + f"{peor['mayor']:.1f}".replace(".", ",") + " con «"
                         + f"{peor['estandar_del_mayor']}». Son los mismos datos y el mismo "
                         "método. Una tasa ajustada sin el nombre de su estándar al lado no "
                         "quiere decir nada, y dos tasas ajustadas con estándares distintos "
                         "no se comparan."})
    for f in comparaciones:
        if f["se_dan_vuelta"]:
            salida.append({
                "donde": "comparación",
                "aviso": f"Entre «{f['poblacion_a']}» y «{f['poblacion_b']}» la tasa cruda "
                         f"y la ajustada van para lados contrarios. La descomposición dice "
                         f"por qué: el efecto de la estructura es "
                         + f"{f['efecto_estructura']:.1f}".replace(".", ",")
                         + " y el de las tasas "
                         + f"{f['efecto_tasas']:.1f}".replace(".", ",")
                         + ", y el primero es más grande que la brecha entera."})
    return salida

"""Paso 2: las cuatro tasas del mercado de trabajo.

Las cuatro salen de la misma cuenta —un numerador ponderado sobre un
denominador ponderado— y **cada una tiene su propio denominador**. Ese es el
error más común con la EPH después del de los ingresos:

    actividad      PEA / población total
    empleo         ocupados / población total
    desocupación   desocupados / **PEA**
    subocupación   subocupados / **PEA**

La desocupación no se calcula sobre la población: se calcula sobre los que
están en el mercado de trabajo. Un 7 % de desocupación no quiere decir que
siete de cada cien personas no tengan trabajo; quiere decir que siete de cada
cien que lo buscan no lo consiguen. Dividir por la población total da algo así
como la mitad, y da un número que no es comparable con nada de lo que publica
el INDEC.

Las cuatro se calculan además **sin ponderar**, que es lo que sale de contar
casos. La diferencia entre las dos columnas es lo que hacen los ponderadores, y
no es chica.
"""

import math

from comun import deff_de_proporcion, estimar_razon, ordenar

# Cada tasa: cómo se llama, qué cuenta arriba y qué cuenta abajo.
TASAS = [
    ("actividad", "Población económicamente activa", "Población total"),
    ("empleo", "Ocupados", "Población total"),
    ("desocupación", "Desocupados", "Población económicamente activa"),
    ("subocupación", "Subocupados", "Población económicamente activa"),
]


def es_activo(r) -> bool:
    return r["estado"] in (1, 2)


def numerador_de(nombre, r) -> bool:
    if nombre == "actividad":
        return es_activo(r)
    if nombre == "empleo":
        return r["estado"] == 1
    if nombre == "desocupación":
        return r["estado"] == 2
    # Subocupado es el ocupado que trabaja menos horas de las que querría:
    # INTENSI = 1. No es un desocupado y no se suma con ellos.
    return r["estado"] == 1 and r["intensi"] == 1


def denominador_de(nombre, r) -> bool:
    if nombre in ("actividad", "empleo"):
        return True
    return es_activo(r)


def una_tasa(registros, conglomerados, nombre, confianza, dentro=None):
    """Una tasa sobre un subconjunto, estimada como dominio.

    `dentro` marca el grupo —las mujeres, el Noroeste— y **no** se aplica
    filtrando la muestra: se aplica poniendo en cero el numerador y el
    denominador de los que quedan afuera. Es lo mismo para la estimación y no
    es lo mismo para el error estándar: filtrar rompe los conglomerados y
    pierde los hogares que quedaron sin ningún caso del grupo.
    """
    if dentro is None:
        def dentro(_r):
            return True

    w, y, x = [], [], []
    for r in registros:
        en_el_grupo = dentro(r)
        abajo = en_el_grupo and denominador_de(nombre, r)
        arriba = abajo and numerador_de(nombre, r)
        w.append(r["pondera"])
        y.append(1.0 if arriba else 0.0)
        x.append(1.0 if abajo else 0.0)

    salida = estimar_razon(w, y, x, conglomerados, confianza)
    if salida is None:
        return None

    n_abajo = int(sum(x))
    n_arriba = int(sum(y))
    sin_ponderar = n_arriba / n_abajo if n_abajo else None
    salida.update({
        "tasa": nombre,
        "n_numerador": n_arriba,
        "n_denominador": n_abajo,
        "sin_ponderar": sin_ponderar,
        "deff": deff_de_proporcion(salida["estimacion"], salida["error_estandar"],
                                   n_abajo),
    })
    return salida


def calcular(registros, conglomerados, parametros):
    """Las cuatro tasas del total, con su error estándar y su efecto de diseño."""
    confianza = parametros["confianza"]
    filas = []
    for nombre, arriba, abajo in TASAS:
        t = una_tasa(registros, conglomerados, nombre, confianza)
        if t is None:
            continue
        deff = t["deff"]
        filas.append({
            "tasa": nombre,
            "numerador": arriba,
            "denominador": abajo,
            "poblacion_numerador": t["total_numerador"],
            "poblacion_denominador": t["total_denominador"],
            "n_denominador": t["n_denominador"],
            "valor": t["estimacion"],
            "error_estandar": t["error_estandar"],
            "inferior": t["inferior"],
            "superior": t["superior"],
            "gl": t["gl"],
            "deff": deff,
            "n_efectivo": (t["n_denominador"] / deff) if deff and deff > 0 else None,
            "sin_ponderar": t["sin_ponderar"],
            "diferencia_con_la_ponderada": (
                t["sin_ponderar"] - t["estimacion"] if t["sin_ponderar"] is not None
                else None),
        })
    return filas


def por_grupo(registros, conglomerados, parametros, cortes):
    """Las mismas cuatro tasas, abiertas por sexo, por edad y por región.

    `cortes` es una lista de (nombre del corte, etiquetas en orden, función que
    devuelve la etiqueta de un registro). El orden de las etiquetas lo fija el
    corte y no el alfabeto: «65 y más» va último porque es el último tramo, no
    porque empiece con seis.
    """
    confianza = parametros["confianza"]
    filas = []
    for corte, etiquetas, de_cual in cortes:
        for grupo in etiquetas:
            for nombre, _arriba, _abajo in TASAS:
                t = una_tasa(registros, conglomerados, nombre, confianza,
                             lambda r, g=grupo, f=de_cual: f(r) == g)
                if t is None or t["n_denominador"] == 0:
                    continue
                filas.append({
                    "corte": corte, "grupo": grupo, "tasa": nombre,
                    "n_denominador": t["n_denominador"],
                    "poblacion_denominador": t["total_denominador"],
                    "valor": t["estimacion"],
                    "error_estandar": t["error_estandar"],
                    "inferior": t["inferior"], "superior": t["superior"],
                    "sin_ponderar": t["sin_ponderar"],
                })
    return filas


def identidad(tasas):
    """La comprobación que no puede fallar: empleo = actividad × (1 − desocupación).

    No es una casualidad aritmética: sale de que los tres cocientes comparten
    numeradores y denominadores. Si no cierra, algún denominador está mal, y
    como los tres se calculan por separado, el residuo de esta resta es la
    única señal que hay de que están bien.
    """
    valores = {t["tasa"]: t["valor"] for t in tasas}
    if not {"actividad", "empleo", "desocupación"} <= set(valores):
        return None
    esperado = valores["actividad"] * (1 - valores["desocupación"])
    return {
        "actividad": valores["actividad"],
        "desocupacion": valores["desocupación"],
        "empleo_observado": valores["empleo"],
        "empleo_por_la_identidad": esperado,
        "residuo": valores["empleo"] - esperado,
    }


def avisos_de(tasas, identidad_, registros):
    """Lo que hay que decir sobre las tasas, además de los números."""
    salida = []
    peores = [t for t in tasas if t["deff"] and t["deff"] > 2]
    if peores:
        cuales = ", ".join(f"«{t['tasa']}»" for t in peores)
        salida.append({
            "donde": "tasas",
            "aviso": f"El efecto de diseño de {cuales} pasa de 2. El efecto de diseño es "
                     f"un cociente de varianzas, así que un 2 no duplica el intervalo: lo "
                     f"ensancha un 41 %, que es la raíz de 2. Un programa al que se le "
                     f"pasa la columna sin contarle del diseño informa el error de la raíz "
                     f"de abajo, y el intervalo le sale así de corto."})
    if identidad_ and abs(identidad_["residuo"]) > 1e-12:
        salida.append({
            "donde": "tasas",
            "aviso": "La identidad empleo = actividad × (1 − desocupación) no cierra. "
                     "Los tres denominadores tienen que salir de la misma población: si "
                     "no cierra, alguno no salió de ahí."})
    chicos = [t for t in tasas if t["n_denominador"] < 100]
    if chicos:
        salida.append({
            "donde": "tasas",
            "aviso": f"Hay {len(chicos)} tasas con menos de cien casos en el "
                     f"denominador. El intervalo que sale es tan ancho que la tasa no "
                     f"distingue casi nada."})
    # El aglomerado con un solo hogar en la muestra no aporta varianza. Con la
    # EPH entera no pasa; con un filtro por región o con un aglomerado chico, sí.
    por_aglo: dict = {}
    for r in registros:
        por_aglo.setdefault(r["aglomerado"], set()).add(r["hogar"])
    solitarios = [a for a in ordenar(list(por_aglo)) if len(por_aglo[a]) < 2]
    if solitarios:
        salida.append({
            "donde": "tasas",
            "aviso": f"Hay {len(solitarios)} aglomerados con un solo hogar en la "
                     f"muestra. Un estrato con una sola unidad no aporta varianza: su "
                     f"aporte al error estándar es cero, y eso hace que el error total "
                     f"salga más chico de lo que corresponde."})
    return salida

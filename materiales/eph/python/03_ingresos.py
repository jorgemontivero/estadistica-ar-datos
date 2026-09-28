"""Paso 3: los ingresos, que es donde la EPH se cobra los descuidos.

Con el ingreso de la ocupación principal hay dos decisiones que tomar, y las
dos parecen menores:

1. **Qué hacer con el −9.** En la EPH, `P21 = −9` no es un ingreso negativo: es
   «no responde». Un cero tampoco es lo mismo: el cero es un ocupado que no
   cobra por su ocupación principal, y existe de verdad.
2. **Con qué ponderador.** `PONDERA` reparte la población; `PONDIIO` reparte la
   población **de los que declararon ingreso de la ocupación principal**. No
   son el mismo número y no sirven para lo mismo.

Lo que hace difícil el asunto es que **cada error por separado casi no se nota,
y juntos hunden el promedio un cuarto**. La tabla `ponderador-e-ingreso.csv`
está armada para mostrar exactamente eso:

- Con PONDIIO, meter o sacar a los que no declaran **da igual**, hasta el
  último decimal. Es que el INDEC les pone el ponderador en cero: ya están
  sacados.
- Con PONDERA y sacando a los que no declaran, el promedio se corre poco.
- Con PONDERA y los que no declaran adentro, se derrumba.

De ahí la moraleja, que no es «acordate del −9» sino otra: los dos descuidos se
tapan entre sí. El que usa PONDIIO nunca se entera de que nunca filtró el −9, y
el día que corre el mismo script sobre un trimestre anterior a 2016T2 —donde
PONDIIO no existe— el filtro que nunca escribió deja de estar y nada avisa.
"""

import math

from comun import cuantil_ponderado, estimar_razon

# Cuántos grupos tiene la tabla de deciles.
GRUPOS = 10


def _ocupados(registros):
    return [r for r in registros if r["estado"] == 1 and r["p21"] is not None]


def _ordenados(casos, peso):
    """Los valores y sus pesos, ordenados por valor, que es lo que pide el cuantil."""
    pares = sorted(((r["p21"], r[peso]) for r in casos), key=lambda par: par[0])
    return [v for v, _w in pares], [w for _v, w in pares]


def _resumen(casos, peso):
    pesos = [r[peso] for r in casos]
    total = math.fsum(pesos)
    if total <= 0 or not casos:
        return None
    media = math.fsum(r["p21"] * r[peso] for r in casos) / total
    valores, ordenados = _ordenados(casos, peso)
    return {"n": len(casos), "poblacion": total, "media": media,
            "mediana": cuantil_ponderado(valores, ordenados, 0.5)}


# Las cinco maneras de calcular el mismo promedio. La primera es la correcta y
# las otras cuatro son las que salen de saltearse una decisión.
#
#   etiqueta, ponderador, deja entrar al −9, deja entrar al 0
CASOS = [
    ("Lo correcto", "ingreso", False, False),
    ("Con los que no declaran adentro", "ingreso", True, False),
    ("Con el ponderador general", "general", False, False),
    ("Con el ponderador general y los que no declaran adentro", "general", True, False),
    ("Con los ocupados sin ingreso adentro", "ingreso", False, True),
]


def contraste(registros, nombre_ponderador_ingreso, nombre_ponderador):
    """El mismo ingreso medio, calculado de las cinco maneras."""
    ocupados = _ocupados(registros)
    filas = []
    correcto = None
    for etiqueta, cual, con_menos_nueve, con_cero in CASOS:
        peso = "pondera_ingreso" if cual == "ingreso" else "pondera"
        casos = [r for r in ocupados
                 if (con_menos_nueve or r["p21"] >= 0)
                 and (con_cero or r["p21"] != 0)]
        res = _resumen(casos, peso)
        if res is None:
            continue
        if correcto is None:
            correcto = res["media"]
        filas.append({
            "caso": etiqueta,
            "ponderador": (nombre_ponderador_ingreso if cual == "ingreso"
                           else nombre_ponderador),
            "que_hace_con_el_menos_nueve": "lo deja" if con_menos_nueve else "lo saca",
            "que_hace_con_el_cero": "lo deja" if con_cero else "lo saca",
            "n": res["n"],
            "poblacion": res["poblacion"],
            "media": res["media"],
            "mediana": res["mediana"],
            "diferencia": res["media"] - correcto,
            "diferencia_relativa": (res["media"] - correcto) / correcto if correcto else None,
        })
    return filas


def distribucion(registros, conglomerados, parametros):
    """La media con su intervalo, la mediana y los diez grupos de la distribución."""
    casos = [r for r in _ocupados(registros) if r["p21"] > 0]
    if not casos:
        return [], []

    # La media es una razón: suma de ingresos sobre suma de pesos. Se estima
    # con el mismo procedimiento que las tasas, y por la misma razón.
    w = [r["pondera_ingreso"] for r in registros]
    en_el_grupo = [r["estado"] == 1 and r["p21"] is not None and r["p21"] > 0
                   for r in registros]
    y = [r["p21"] if dentro else 0.0 for r, dentro in zip(registros, en_el_grupo)]
    x = [1.0 if dentro else 0.0 for dentro in en_el_grupo]
    est = estimar_razon(w, y, x, conglomerados, parametros["confianza"])

    valores, pesos = _ordenados(casos, "pondera_ingreso")
    total_peso = math.fsum(pesos)
    total_ingreso = math.fsum(v * w for v, w in zip(valores, pesos))
    cortes = [cuantil_ponderado(valores, pesos, k / GRUPOS) for k in range(1, GRUPOS)]

    grupos = []
    for k in range(1, GRUPOS + 1):
        del_grupo = [r for r in casos
                     if 1 + sum(1 for c in cortes if c < r["p21"]) == k]
        peso = math.fsum(r["pondera_ingreso"] for r in del_grupo)
        ingreso = math.fsum(r["p21"] * r["pondera_ingreso"] for r in del_grupo)
        grupos.append({
            "decil": k,
            "corte_superior": cortes[k - 1] if k < GRUPOS else None,
            "n": len(del_grupo),
            "poblacion": peso,
            "ingreso_medio": ingreso / peso if peso > 0 else None,
            "participacion": ingreso / total_ingreso if total_ingreso > 0 else None,
        })

    media_simple = math.fsum(r["p21"] for r in casos) / len(casos)
    d1 = grupos[0]["ingreso_medio"]
    d10 = grupos[-1]["ingreso_medio"]
    resumen = [
        {"estadistico": "casos", "valor": len(casos)},
        {"estadistico": "población representada", "valor": total_peso},
        {"estadistico": "media", "valor": est["estimacion"] if est else None},
        {"estadistico": "error estándar", "valor": est["error_estandar"] if est else None},
        {"estadistico": "límite inferior", "valor": est["inferior"] if est else None},
        {"estadistico": "límite superior", "valor": est["superior"] if est else None},
        {"estadistico": "mediana", "valor": cuantil_ponderado(valores, pesos, 0.5)},
        {"estadistico": "primer decil", "valor": cortes[0]},
        {"estadistico": "noveno decil", "valor": cortes[-1]},
        {"estadistico": "razón entre el décimo y el primer decil",
         "valor": d10 / d1 if d1 else None},
        {"estadistico": "media sin ponderar", "valor": media_simple},
    ]
    return resumen, grupos


def por_grupo(registros, cortes):
    """El ingreso medio y la mediana dentro de cada grupo, con PONDIIO."""
    casos = [r for r in _ocupados(registros) if r["p21"] > 0]
    total = _resumen(casos, "pondera_ingreso")
    filas = []
    for corte, etiquetas, de_cual in cortes:
        for grupo in etiquetas:
            del_grupo = [r for r in casos if de_cual(r) == grupo]
            res = _resumen(del_grupo, "pondera_ingreso")
            if res is None:
                continue
            filas.append({
                "corte": corte, "grupo": grupo, "n": res["n"],
                "poblacion": res["poblacion"], "media": res["media"],
                "mediana": res["mediana"],
                "razon_con_el_total": (res["media"] / total["media"]
                                       if total and total["media"] else None),
            })
    return filas


def informalidad(registros, conglomerados, parametros, cortes):
    """Asalariados a los que no les hacen el descuento jubilatorio.

    Es la medida de informalidad que sale de la EPH sin pedirle nada más:
    `PP07H = 2` entre los `CAT_OCUP = 3`. No es «trabajo en negro» en sentido
    amplio —no dice nada de los cuentapropistas— pero es la que se puede
    calcular con esta base y la que el INDEC informa.

    El denominador son los asalariados, no los ocupados. Sobre los ocupados da
    bastante menos y no se compara con nada.
    """
    confianza = parametros["confianza"]
    filas = []
    todos = [("Total", ["Total"], lambda _r: "Total")] + list(cortes)
    for corte, etiquetas, de_cual in todos:
        for grupo in etiquetas:
            w, y, x = [], [], []
            for r in registros:
                asalariado = r["estado"] == 1 and r["cat_ocup"] == 3 and de_cual(r) == grupo
                w.append(r["pondera"])
                x.append(1.0 if asalariado else 0.0)
                y.append(1.0 if asalariado and r["pp07h"] == 2 else 0.0)
            n = int(sum(x))
            if n < 2:
                continue
            est = estimar_razon(w, y, x, conglomerados, confianza)
            if est is None:
                continue
            filas.append({
                "corte": corte, "grupo": grupo,
                "n_asalariados": n,
                "asalariados": est["total_denominador"],
                "sin_descuento": est["total_numerador"],
                "tasa": est["estimacion"],
                "error_estandar": est["error_estandar"],
                "inferior": est["inferior"], "superior": est["superior"],
            })
    return filas


def avisos_de(contraste_, grupos, registros):
    """Lo que hay que decir sobre los ingresos, además de los números."""
    salida = []
    if len(contraste_) >= 4:
        correcto = contraste_[0]
        igual = contraste_[1]
        solo_peso = contraste_[2]
        los_dos = contraste_[3]
        if abs(igual["diferencia"]) < 1e-9:
            salida.append({
                "donde": "ingresos",
                "aviso": f"Con «{correcto['ponderador']}», dejar adentro a los que no "
                         f"declaran ingreso **no cambia nada**: el promedio da igual "
                         f"hasta el último decimal, porque ese ponderador les vale cero. "
                         f"Por eso el filtro del −9 se puede no escribir nunca sin que "
                         f"nadie lo note."})
        salida.append({
            "donde": "ingresos",
            "aviso": "Cambiar de ponderador corre el promedio "
                     + f"{abs(100 * solo_peso['diferencia_relativa']):.1f}".replace(".", ",")
                     + " %; dejar adentro al −9 con el ponderador general lo corre "
                     + f"{abs(100 * los_dos['diferencia_relativa']):.1f}".replace(".", ",")
                     + " %. Los dos descuidos por separado se disimulan y juntos no. Y "
                       "van juntos justo cuando el script se reusa sobre un trimestre "
                       "anterior a 2016T2, que es donde el ponderador de ingreso no "
                       "existe."})
    desparejos = [g for g in grupos
                  if g["poblacion"] and g["participacion"] is not None
                  and not (0.05 <= g["n"] / max(1, sum(x["n"] for x in grupos)) <= 0.16)]
    if desparejos:
        salida.append({
            "donde": "ingresos",
            "aviso": f"Hay {len(desparejos)} deciles con bastante más o bastante menos "
                     f"casos que la décima parte. No es un error de cálculo: los "
                     f"ingresos declarados se amontonan en cifras redondas, y un corte "
                     f"que cae sobre un montón se lleva todo el montón para un lado."})
    return salida

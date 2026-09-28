"""Paso 3: estimar, con la varianza que le corresponde al diseño.

Acá está lo que este proyecto existe para mostrar.

La estimación puntual de una encuesta compleja no tiene misterio: se
promedian los valores con los ponderadores y listo. **El error estándar sí lo
tiene**, y es donde se equivoca casi todo el mundo: se calcula el promedio con
los pesos y después el error estándar con la fórmula del muestreo aleatorio
simple, que es s/√n. El resultado es un intervalo que se ve bien, que es
angosto, y que no cubre lo que dice cubrir.

**Un solo estimador para los cuatro diseños.** La varianza se calcula siempre
con el método de la *última etapa* (ultimate cluster): dentro de cada estrato,
la variabilidad entre los totales ponderados de cada unidad primaria.

    v = Σ_h (1 − f_h) · a_h/(a_h − 1) · Σ_i (z_hi − z̄_h)²

Con conglomerados, la unidad primaria es el conglomerado. Sin conglomerados,
cada unidad es su propia unidad primaria, y entonces la fórmula **se reduce
exactamente** a la del estratificado; y con un solo estrato, a la del
aleatorio simple con corrección por población finita. No hay cuatro fórmulas:
hay una, mirada desde cuatro diseños.

El **efecto de diseño** es el cociente entre esa varianza y la que habría
dado un aleatorio simple del mismo tamaño. Mayor que uno significa que el
diseño costó precisión —lo típico de los conglomerados—; menor que uno, que la
ganó —lo típico de la estratificación—. Y el **tamaño efectivo**, n/deff, dice
a cuántos casos de un aleatorio simple equivale la muestra que se pagó.
"""

import math

from scipy import stats

from comun import indices_por, limpiar_texto, ordenar


def _linealizar(valores, pesos, clase):
    """El residuo que hay que acumular por unidad primaria, según qué se estima.

    Para un total, el aporte de cada caso es su peso por su valor. Para una
    media o una proporción —que son razones— hay que restarle la estimación,
    porque el denominador también es aleatorio: eso es la linealización de
    Taylor, y saltearla infla la varianza de una media hasta el absurdo.
    """
    suma_w = math.fsum(pesos)
    if clase == "total":
        return [pesos[i] * valores[i] for i in range(len(valores))], suma_w, None
    estimacion = math.fsum(pesos[i] * valores[i] for i in range(len(valores))) / suma_w
    return ([pesos[i] * (valores[i] - estimacion) for i in range(len(valores))],
            suma_w, estimacion)


def estimar(valores, pesos, estratos, unidades, fracciones, clase, confianza):
    """La estimación y su error estándar por el método de la última etapa.

    `fracciones` es, por estrato, qué proporción de las unidades primarias
    entró en la muestra: es la corrección por población finita de la primera
    etapa. Con una fracción chica casi no cambia nada; con una muestra que se
    come media población, cambia mucho.
    """
    n = len(valores)
    if n < 2:
        return None
    aportes, suma_w, estimacion = _linealizar(valores, pesos, clase)
    if clase == "total":
        estimacion = math.fsum(aportes)

    # Los aportes, acumulados por unidad primaria dentro de cada estrato.
    por_estrato: dict = {}
    for i in range(n):
        por_estrato.setdefault(estratos[i], {}).setdefault(unidades[i], 0.0)
        por_estrato[estratos[i]][unidades[i]] += aportes[i]

    varianza = 0.0
    grados = 0
    upm_totales = 0
    for h in ordenar(list(por_estrato)):
        zs = [por_estrato[h][u] for u in ordenar(list(por_estrato[h]))]
        a = len(zs)
        upm_totales += a
        if a < 2:
            # Un estrato con una sola unidad primaria no aporta grados de
            # libertad y su varianza no se puede estimar. Se lo deja pasar y
            # se avisa, que es mejor que devolver un cero silencioso.
            continue
        media_z = math.fsum(zs) / a
        f = fracciones.get(h, 0.0)
        varianza += (1 - f) * a / (a - 1) * math.fsum((z - media_z) ** 2 for z in zs)
        grados += a - 1

    if clase != "total":
        varianza = varianza / (suma_w ** 2)
    error = math.sqrt(varianza) if varianza > 0 else 0.0

    # Los grados de libertad de una encuesta compleja son (unidades primarias
    # − estratos), no (n − 1). Con 32 conglomerados y 4 estratos son 28, no
    # 319: usar n − 1 angosta el intervalo de más.
    gl = max(1, grados)
    critico = float(stats.t.ppf(1 - (1 - confianza) / 2, gl))
    return {"estimacion": estimacion, "error_estandar": error, "gl": gl,
            "inferior": estimacion - critico * error,
            "superior": estimacion + critico * error,
            "unidades_primarias": upm_totales, "suma_de_pesos": suma_w}


def como_si_fuera_simple(valores, pesos, poblacion, clase, confianza):
    """El error estándar que saldría de ignorar el diseño.

    Es lo que devuelve cualquier programa al que se le pasa la columna sin
    decirle nada más, y lo que aparece en la mayoría de los informes. Se
    calcula acá para poder ponerlo al lado del otro.
    """
    n = len(valores)
    if n < 2:
        return None
    suma_w = math.fsum(pesos)
    if clase == "total":
        estimacion = math.fsum(pesos[i] * valores[i] for i in range(n))
        media = math.fsum(valores) / n
        s2 = math.fsum((v - media) ** 2 for v in valores) / (n - 1)
        # El total ingenuo: N por la media simple, con la varianza de la media
        # simple escalada.
        error = poblacion * math.sqrt((1 - n / poblacion) * s2 / n)
        estimacion = poblacion * media
    else:
        estimacion = math.fsum(pesos[i] * valores[i] for i in range(n)) / suma_w
        media = math.fsum(valores) / n
        s2 = math.fsum((v - media) ** 2 for v in valores) / (n - 1)
        error = math.sqrt((1 - n / poblacion) * s2 / n)
        estimacion = media
    critico = float(stats.t.ppf(1 - (1 - confianza) / 2, n - 1))
    return {"estimacion": estimacion, "error_estandar": error, "gl": n - 1,
            "inferior": estimacion - critico * error,
            "superior": estimacion + critico * error}


def verdadero(datos, columna, clase, exito=""):
    """El valor de la población. Solo se puede calcular porque el marco es la
    población entera: en la vida real esta columna no existe, y es justamente
    por eso que el intervalo importa."""
    if clase == "proporcion":
        cuantos = sum(1 for f in datos if limpiar_texto(f.get(columna, "")) == exito)
        return cuantos / len(datos)
    valores = [float(f[columna]) for f in datos if f.get(columna, "").strip()]
    return math.fsum(valores) if clase == "total" else math.fsum(valores) / len(valores)


def calcular(datos, parametros, pesos, fracciones, nombre_diseno, estratificado=True):
    """`estratificado` dice si el DISEÑO usó los estratos al seleccionar.

    No es un detalle: aplicarle la fórmula estratificada a una muestra que se
    sacó sin estratificar no es un error de cuenta, es estimar otra cosa —la
    varianza de un post-estratificado— y da un efecto de diseño menor que uno
    que no le corresponde a nadie. Un aleatorio simple tiene deff 1 por
    definición, y si la tabla dice otra cosa, la tabla está mal.
    """
    confianza = parametros["confianza"]
    poblacion = len(datos)
    estrato = parametros["estrato"]
    filas = [p["fila"] for p in pesos]
    w = [p["peso"] for p in pesos]
    estratos = [limpiar_texto(datos[i].get(estrato, "")) if estrato and estratificado
                else "—" for i in filas]
    # Sin conglomerados, cada unidad es su propia unidad primaria: ahí la
    # fórmula de la última etapa se vuelve la del estratificado.
    unidades = [p["conglomerado"] if p["conglomerado"] is not None else f"u{p['fila']}"
                for p in pesos]

    objetivos = []
    if parametros["variable"]:
        objetivos.append((parametros["variable"], "media"))
    if parametros["variable_total"]:
        objetivos.append((parametros["variable_total"], "total"))
    if parametros["variable_binaria"]:
        objetivos.append((parametros["variable_binaria"], "proporcion"))

    salida = []
    for columna, clase in objetivos:
        if clase == "proporcion":
            valores = [1.0 if limpiar_texto(datos[i].get(columna, "")) == parametros["exito"]
                       else 0.0 for i in filas]
        else:
            valores = [float(datos[i][columna]) for i in filas]

        diseno = estimar(valores, w, estratos, unidades, fracciones, clase, confianza)
        simple = como_si_fuera_simple(valores, w, poblacion, clase, confianza)
        if diseno is None or simple is None:
            continue
        real = verdadero(datos, columna, clase, parametros["exito"])
        deff = ((diseno["error_estandar"] / simple["error_estandar"]) ** 2
                if simple["error_estandar"] > 0 else float("inf"))
        salida.append({
            "diseno": nombre_diseno, "variable": columna, "que": clase,
            "verdadero": real,
            "estimacion": diseno["estimacion"],
            "error_estandar": diseno["error_estandar"],
            "inferior": diseno["inferior"], "superior": diseno["superior"],
            "gl": diseno["gl"],
            "contiene_al_verdadero": diseno["inferior"] <= real <= diseno["superior"],
            "ee_ingenuo": simple["error_estandar"],
            "inferior_ingenuo": simple["inferior"], "superior_ingenuo": simple["superior"],
            "contiene_ingenuo": simple["inferior"] <= real <= simple["superior"],
            "deff": deff,
            "n_efectivo": len(valores) / deff if deff > 0 else float("nan"),
            "error_relativo": (abs(diseno["estimacion"] - real) / abs(real)
                               if real != 0 else float("nan")),
        })
    return salida


def por_estrato(datos, parametros, pesos, fracciones):
    """La misma media, estimada dentro de cada estrato.

    Es lo que casi siempre se pide después de la cifra general, y es donde el
    tamaño de muestra se vuelve el problema: una muestra que alcanza para el
    total puede no alcanzar para ninguna de sus partes.
    """
    estrato = parametros["estrato"]
    columna = parametros["variable"]
    if not estrato or not columna:
        return []
    confianza = parametros["confianza"]
    por_clave: dict = {}
    for p in pesos:
        clave = limpiar_texto(datos[p["fila"]].get(estrato, ""))
        por_clave.setdefault(clave, []).append(p)

    salida = []
    for clave in ordenar(list(por_clave)):
        grupo = por_clave[clave]
        valores = [float(datos[p["fila"]][columna]) for p in grupo]
        w = [p["peso"] for p in grupo]
        unidades = [p["conglomerado"] if p["conglomerado"] is not None else f"u{p['fila']}"
                    for p in grupo]
        r = estimar(valores, w, [clave] * len(grupo), unidades,
                    {clave: fracciones.get(clave, 0.0)}, "media", confianza)
        if r is None:
            continue
        marco = [float(f[columna]) for f in datos
                 if limpiar_texto(f.get(estrato, "")) == clave]
        real = math.fsum(marco) / len(marco)
        salida.append({
            "estrato": clave, "n": len(grupo),
            "unidades_primarias": r["unidades_primarias"],
            "verdadero": real, "estimacion": r["estimacion"],
            "error_estandar": r["error_estandar"],
            "inferior": r["inferior"], "superior": r["superior"],
            "contiene_al_verdadero": r["inferior"] <= real <= r["superior"],
            "error_relativo_del_ee": (r["error_estandar"] / r["estimacion"]
                                      if r["estimacion"] != 0 else float("nan")),
        })
    return salida


def cobertura(datos, parametros, seleccionar, replicas):
    """Cuántas veces le acierta cada intervalo, sacando la muestra muchas veces.

    Es la única prueba concluyente y la única que en la vida real no se puede
    hacer, porque haría falta conocer la población. Acá se puede: el marco
    **es** la población.

    Se saca la muestra `replicas` veces, con una semilla distinta cada vez, y
    se cuenta qué proporción de los intervalos contiene al valor verdadero. Un
    intervalo del 95 % que cubra el 95 % está bien construido. Uno que cubra
    el 70 % está mintiendo, y la diferencia no se ve mirando un solo intervalo:
    el de una muestra puntual se ve igual de respetable.
    """
    if replicas < 1:
        return None
    confianza = parametros["confianza"]
    columna = parametros["variable"]
    estrato = parametros["estrato"]
    real = verdadero(datos, columna, "media")

    aciertos_diseno = 0
    aciertos_ingenuo = 0
    anchos_diseno = []
    anchos_ingenuos = []
    for r in range(replicas):
        seleccion, fracciones = seleccionar(parametros["semilla"] + r + 1)
        filas = [s["fila"] for s in seleccion]
        w = [1 / s["probabilidad"] for s in seleccion]
        valores = [float(datos[i][columna]) for i in filas]
        estratos = [limpiar_texto(datos[i].get(estrato, "")) if estrato else "—"
                    for i in filas]
        unidades = [s["conglomerado"] if s["conglomerado"] is not None else f"u{s['fila']}"
                    for s in seleccion]

        d = estimar(valores, w, estratos, unidades, fracciones, "media", confianza)
        s = como_si_fuera_simple(valores, w, len(datos), "media", confianza)
        if d is None or s is None:
            continue
        if d["inferior"] <= real <= d["superior"]:
            aciertos_diseno += 1
        if s["inferior"] <= real <= s["superior"]:
            aciertos_ingenuo += 1
        anchos_diseno.append(d["superior"] - d["inferior"])
        anchos_ingenuos.append(s["superior"] - s["inferior"])

    hechas = len(anchos_diseno)
    if hechas == 0:
        return None
    return {
        "replicas": hechas, "verdadero": real, "nominal": confianza,
        "cobertura_del_diseno": aciertos_diseno / hechas,
        "cobertura_ingenua": aciertos_ingenuo / hechas,
        "ancho_medio_del_diseno": math.fsum(anchos_diseno) / hechas,
        "ancho_medio_ingenuo": math.fsum(anchos_ingenuos) / hechas,
    }

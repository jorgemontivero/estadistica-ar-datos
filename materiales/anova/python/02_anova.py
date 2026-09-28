"""Paso 2: las tablas de ANOVA.

Tres cosas, en este orden:

    un factor      la tabla clásica sobre el primer factor, con el tamaño del
                   efecto y la versión de Welch al lado.

    dos factores   si hay un segundo factor, el modelo completo con la
                   interacción, por sumas de cuadrados de **tipo III** y
                   también de **tipo I en los dos órdenes posibles**.

    efectos simples cuando la interacción es significativa, el efecto del
                   segundo factor **dentro de cada nivel** del primero. Es lo
                   único que se puede interpretar en ese caso.

Sobre los tipos de suma de cuadrados, que es donde más gente se quema sin
enterarse. Con las celdas balanceadas los tres tipos dan lo mismo y la
discusión no existe. Con celdas de tamaños distintos —o sea, casi siempre—
dan distinto:

    tipo I     secuencial: cada término se mide por lo que agrega a los
               anteriores. Depende del ORDEN en que se escriben los factores.
               Es lo que devuelve `anova()` de R.
    tipo III   cada término se mide por lo que agrega al modelo que ya tiene a
               todos los demás. No depende del orden. Es lo que devuelve SPSS
               por omisión, y lo que informa `car::Anova(type = 3)`.

Dos personas con los mismos datos y distinto programa pueden publicar valores
p distintos para el mismo efecto sin haberse equivocado en nada. Por eso este
proyecto escribe los tres y marca si alguna conclusión cambia.
"""

import math

from scipy import stats

from algebra import resolver
from comun import desvio, media, ordenar


# --------------------------------------------------------------- un factor
def tabla(grupos, confianza):
    """El ANOVA de un factor, desde los datos de cada grupo."""
    usables = [(e, v) for e, _, v in grupos if len(v) > 1]
    k = len(usables)
    if k < 2:
        return None

    resumenes = [{"grupo": e, "n": len(v), "media": media(v), "desvio": desvio(v)}
                 for e, v in usables]
    n = sum(r["n"] for r in resumenes)
    gl_entre = k - 1
    gl_dentro = n - k
    if gl_dentro < 1:
        return None

    media_general = math.fsum(r["n"] * r["media"] for r in resumenes) / n
    sc_entre = math.fsum(r["n"] * (r["media"] - media_general) ** 2 for r in resumenes)
    # La suma de cuadrados dentro se reconstruye desde los desvíos de cada grupo.
    sc_dentro = math.fsum((r["n"] - 1) * r["desvio"] ** 2 for r in resumenes)
    sc_total = sc_entre + sc_dentro

    cm_entre = sc_entre / gl_entre
    cm_dentro = sc_dentro / gl_dentro
    f = cm_entre / cm_dentro if cm_dentro > 0 else float("inf")

    eta = sc_entre / sc_total if sc_total > 0 else 0.0
    # Omega² descuenta el sesgo del eta², que siempre sobreestima porque el
    # factor explica algo de variabilidad aunque no haya ningún efecto real.
    omega = (max(0.0, (sc_entre - gl_entre * cm_dentro) / (sc_total + cm_dentro))
             if sc_total + cm_dentro > 0 else 0.0)

    return {
        "resumenes": resumenes, "n": n, "k": k,
        "sc_entre": sc_entre, "gl_entre": gl_entre, "cm_entre": cm_entre,
        "sc_dentro": sc_dentro, "gl_dentro": gl_dentro, "cm_dentro": cm_dentro,
        "sc_total": sc_total, "gl_total": n - 1,
        "f": f, "p": float(stats.f.sf(f, gl_entre, gl_dentro)),
        "critico": float(stats.f.ppf(confianza, gl_entre, gl_dentro)),
        "eta_cuadrado": eta, "omega_cuadrado": omega, "media_general": media_general,
    }


def welch(resumenes):
    """ANOVA de Welch: no supone varianzas iguales.

    Es al ANOVA clásico lo que la t de Welch es a la t clásica, y conviene por
    defecto cuando las varianzas difieren. Está escrito a mano porque
    `oneway.test` de R y `scipy.stats.alexandergovern` no son la misma prueba,
    y ninguna de las dos coincide con la otra hasta el último dígito.
    """
    k = len(resumenes)
    if k < 2 or any(r["n"] < 2 or not (r["desvio"] > 0) for r in resumenes):
        return None

    w = [r["n"] / r["desvio"] ** 2 for r in resumenes]
    suma_w = math.fsum(w)
    media_ponderada = math.fsum(w[i] * r["media"] for i, r in enumerate(resumenes)) / suma_w

    numerador = math.fsum(w[i] * (r["media"] - media_ponderada) ** 2
                          for i, r in enumerate(resumenes)) / (k - 1)
    # Este término aparece en el denominador del F y en los grados de libertad,
    # así que se calcula una sola vez.
    lambda_ = math.fsum((1 - w[i] / suma_w) ** 2 / (r["n"] - 1)
                        for i, r in enumerate(resumenes))

    denominador = 1 + ((2 * (k - 2)) / (k * k - 1)) * lambda_
    f = numerador / denominador
    gl2 = (k * k - 1) / (3 * lambda_)
    return {"f": f, "gl1": k - 1, "gl2": gl2, "p": float(stats.f.sf(f, k - 1, gl2))}


# ------------------------------------------------------------ dos factores
def columnas_de_efectos(valores, niveles):
    """Codificación por efectos: 1 en su nivel, −1 en el último, 0 en el resto.

    Se usa esta y no la de indicadoras 0/1 porque es la que hace que el término
    de interacción sea ortogonal a los efectos principales cuando el diseño
    está balanceado, que es la condición bajo la cual los tipos de suma de
    cuadrados coinciden. Con indicadoras, el tipo III daría otra cosa.
    """
    ultimo = niveles[-1]
    return [[1.0 if v == l else (-1.0 if v == ultimo else 0.0) for l in niveles[:-1]]
            for v in valores]


def _sc_residual(x, y):
    coeficientes, _ = resolver(x, y)
    if coeficientes is None:
        return None
    return math.fsum((y[i] - math.fsum(c * v for c, v in zip(coeficientes, fila))) ** 2
                     for i, fila in enumerate(x))


def _pegar(bloques):
    n = len(bloques[0])
    return [[v for bloque in bloques for v in bloque[i]] for i in range(n)]


def dos_factores(observaciones, niveles_a, niveles_b, nombre_a, nombre_b):
    """El modelo completo, por tipo III y por tipo I en los dos órdenes.

    `observaciones` es una lista de (nivel de A, nivel de B, valor), en un
    orden fijo.
    """
    if len(niveles_a) < 2 or len(niveles_b) < 2:
        return None

    y = [o[2] for o in observaciones]
    n = len(y)
    uno = [[1.0] for _ in range(n)]
    a = columnas_de_efectos([o[0] for o in observaciones], niveles_a)
    b = columnas_de_efectos([o[1] for o in observaciones], niveles_b)
    ab = [[x * z for x in a[i] for z in b[i]] for i in range(n)]

    bloques = {"a": a, "b": b, "ab": ab}
    anchos = {clave: len(v[0]) for clave, v in bloques.items()}
    completo = _pegar([uno, a, b, ab])
    gl_error = n - len(completo[0])
    if gl_error < 1:
        return None

    sc_residual = _sc_residual(completo, y)
    if sc_residual is None:
        # Pasa cuando falta alguna celda: sin datos en una combinación, la
        # columna de interacción que le corresponde no aporta nada nuevo y la
        # matriz queda sin inversa.
        return {"singular": True}
    cm_error = sc_residual / gl_error

    nombres = {"a": nombre_a, "b": nombre_b, "ab": f"{nombre_a} × {nombre_b}"}

    def fila(etiqueta, sc, gl):
        f = (sc / gl) / cm_error if cm_error > 0 and gl > 0 else float("inf")
        return {"termino": etiqueta, "sc": sc, "gl": gl, "cm": sc / gl if gl else None,
                "f": f, "p": float(stats.f.sf(f, gl, gl_error))}

    # Tipo III: cada término contra el modelo que ya tiene a todos los demás.
    tipo_iii = []
    for clave in ("a", "b", "ab"):
        otros = [uno] + [bloques[c] for c in ("a", "b", "ab") if c != clave]
        sc_sin = _sc_residual(_pegar(otros), y)
        if sc_sin is None:
            return {"singular": True}
        tipo_iii.append(fila(nombres[clave], sc_sin - sc_residual, anchos[clave]))

    # Tipo I: secuencial, en el orden en que se entra.
    def secuencial(orden):
        acumulado = [uno]
        previo = _sc_residual(uno, y)
        salida = []
        for clave in orden:
            acumulado.append(bloques[clave])
            ahora = _sc_residual(_pegar(acumulado), y)
            salida.append(fila(nombres[clave], previo - ahora, anchos[clave]))
            previo = ahora
        return salida

    return {
        "singular": False,
        "tipo_iii": tipo_iii,
        "tipo_i_a": secuencial(("a", "b", "ab")),
        "tipo_i_b": secuencial(("b", "a", "ab")),
        "sc_residual": sc_residual, "gl_error": gl_error, "cm_error": cm_error,
        "n": n, "nombres": nombres,
    }


def efectos_simples(celdas, niveles_a, niveles_b, cm_error, gl_error, confianza):
    """El efecto del segundo factor dentro de cada nivel del primero.

    Se prueba contra el cuadrado medio del error del modelo completo y no
    contra el de cada nivel por separado: usar todos los datos para estimar la
    varianza es lo que le da potencia a la prueba, y es lo que hace cualquier
    programa cuando informa efectos simples.
    """
    filas = []
    critico = float(stats.t.ppf(1 - (1 - confianza) / 2, gl_error))
    for nivel in niveles_a:
        presentes = [(b, celdas[(nivel, b)]) for b in niveles_b if (nivel, b) in celdas]
        if len(presentes) < 2:
            continue
        n = sum(len(v) for _, v in presentes)
        medias = [(b, len(v), media(v)) for b, v in presentes]
        media_nivel = math.fsum(c * m for _, c, m in medias) / n
        sc = math.fsum(c * (m - media_nivel) ** 2 for _, c, m in medias)
        gl = len(presentes) - 1
        f = (sc / gl) / cm_error if cm_error > 0 else float("inf")
        p = float(stats.f.sf(f, gl, gl_error))

        fila = {"nivel": nivel, "n": n, "gl": gl, "f": f, "p": p,
                "significativo": p < 1 - confianza,
                "diferencia": None, "inferior": None, "superior": None, "entre": ""}
        # Con exactamente dos niveles, el efecto simple es una diferencia y se
        # puede escribir con su intervalo, que es mucho más legible que un F.
        if len(presentes) == 2:
            (b1, n1, m1), (b2, n2, m2) = medias
            diferencia = m2 - m1
            ee = math.sqrt(cm_error * (1 / n1 + 1 / n2))
            fila.update({"diferencia": diferencia, "entre": f"{b2} − {b1}",
                         "inferior": diferencia - critico * ee,
                         "superior": diferencia + critico * ee})
        filas.append(fila)
    return filas


# ------------------------------------------------------------------ armado
def calcular(grupos_factor, grupos_celda, parametros):
    confianza = parametros["confianza"]
    alfa = 1 - confianza
    un_factor = tabla(grupos_factor, confianza)
    if un_factor is None:
        raise SystemExit("No hay al menos dos grupos con dos casos cada uno.")
    welch_ = welch(un_factor["resumenes"])

    avisos = []
    salida = {"un_factor": un_factor, "welch": welch_, "dos_factores": None,
              "efectos_simples": [], "interaccion_significativa": False,
              "tipos": [], "avisos": avisos}

    if not parametros["factor_2"]:
        return salida

    niveles_a = ordenar([n[0] for _, n, _ in grupos_celda])
    niveles_b = ordenar([n[1] for _, n, _ in grupos_celda])
    celdas = {n: v for _, n, v in grupos_celda}
    observaciones = [(n[0], n[1], x) for _, n, v in grupos_celda for x in v]

    modelo = dos_factores(observaciones, niveles_a, niveles_b,
                          parametros["factor"], parametros["factor_2"])
    if modelo is None or modelo.get("singular"):
        avisos.append({"donde": "diseño",
                       "aviso": "No se pudo ajustar el modelo de dos factores: alguna "
                                "combinación de niveles no tiene ningún caso. Con celdas "
                                "vacías la interacción no está definida y no hay tabla que "
                                "escribir."})
        return salida

    salida["dos_factores"] = modelo
    interaccion = modelo["tipo_iii"][2]
    salida["interaccion_significativa"] = interaccion["p"] < alfa

    # Los tres tipos, uno al lado del otro, con la marca de si difieren en la
    # conclusión y no solo en el número.
    tipos = []
    for i, clave in enumerate(("a", "b", "ab")):
        nombre = modelo["tipo_iii"][i]["termino"]
        p3 = modelo["tipo_iii"][i]["p"]
        pa = next(f["p"] for f in modelo["tipo_i_a"] if f["termino"] == nombre)
        pb = next(f["p"] for f in modelo["tipo_i_b"] if f["termino"] == nombre)
        veredictos = {p3 < alfa, pa < alfa, pb < alfa}
        tipos.append({
            "termino": nombre,
            "sc_tipo_iii": modelo["tipo_iii"][i]["sc"], "p_tipo_iii": p3,
            "sc_tipo_i_primero": next(f["sc"] for f in modelo["tipo_i_a"]
                                      if f["termino"] == nombre),
            "p_tipo_i_primero": pa,
            "sc_tipo_i_segundo": next(f["sc"] for f in modelo["tipo_i_b"]
                                      if f["termino"] == nombre),
            "p_tipo_i_segundo": pb,
            "cambia_la_conclusion": len(veredictos) > 1,
        })
    salida["tipos"] = tipos

    if any(t["cambia_la_conclusion"] for t in tipos):
        cuales = [t["termino"] for t in tipos if t["cambia_la_conclusion"]]
        avisos.append({"donde": "tipos de suma",
                       "aviso": f"El veredicto de {', '.join(cuales)} depende del tipo de "
                                f"suma de cuadrados. Con celdas desbalanceadas eso pasa, y "
                                f"significa que el efecto no está separado del otro factor: "
                                f"informar uno solo de los dos números sin decir cuál es "
                                f"elegir la conclusión."})

    if salida["interaccion_significativa"]:
        salida["efectos_simples"] = efectos_simples(
            celdas, niveles_a, niveles_b, modelo["cm_error"], modelo["gl_error"], confianza)
        principales = [t for t in tipos[:2] if t["p_tipo_iii"] >= alfa]
        aviso = (f"La interacción {interaccion['termino']} es significativa. Los efectos "
                 f"principales son promedios de efectos que no son iguales entre sí, así "
                 f"que no describen a nadie: lo que hay que interpretar son los efectos "
                 f"simples.")
        if principales:
            aviso += (f" Ojo con {' y '.join(t['termino'] for t in principales)}: el efecto "
                      f"principal no da significativo, y eso NO significa que no pase nada.")
        avisos.append({"donde": "interacción", "aviso": aviso})

    return salida

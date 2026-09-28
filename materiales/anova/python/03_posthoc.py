"""Paso 3: las comparaciones de a pares.

El F contesta «¿hay alguna diferencia?». No contesta «¿entre cuáles?», y esa
es la pregunta que casi siempre importa. Para eso están las comparaciones de a
pares, y para eso hay que corregir: con k grupos son k(k−1)/2 comparaciones, y
si cada una se mira a 0,05 la probabilidad de encontrar al menos un falso
positivo se dispara. Con seis grupos son quince comparaciones y esa
probabilidad pasa de 0,05 a más de 0,50.

**Se corren los cuatro métodos siempre, y también la prueba sin corregir.** No
es indecisión: elegir el método después de ver cuál da significativo es
exactamente la maniobra que las correcciones existen para impedir. Que estén
los cinco en la misma tabla vuelve visible el costo de la multiplicidad y
obliga a declarar cuál se usó.

    sin corregir  la t de a pares, sin ningún ajuste. Está para que se vea
                  cuánto cambia, no para informarla.
    Tukey         el estándar para comparar TODOS los pares. Usa el rango
                  studentizado, que es la distribución del mayor menos el
                  menor, y por eso es más potente que Bonferroni sin perder el
                  control del error.
    Bonferroni    el más simple: multiplica cada p por la cantidad de
                  comparaciones. Siempre válido, siempre conservador.
    Holm          uniformemente más potente que Bonferroni, sin costo alguno.
                  No hay ninguna razón para preferir Bonferroni sobre Holm
                  salvo que el lector espere ver Bonferroni.
    Scheffé       el más conservador de todos, pero vale para CUALQUIER
                  contraste y no solo los de a pares. Si solo se van a mirar
                  pares, es tirar potencia a la basura.

La columna `cambia_entre_correcciones` marca los pares donde los cuatro
métodos corregidos no coinciden en el veredicto. Ahí la conclusión no la
deciden los datos: la decide el método.
"""

import math

from scipy import stats

from comun import ordenar
from rango import rango_cola, rango_inv

METODOS = ["sin corregir", "tukey", "bonferroni", "holm", "scheffe"]


def comparaciones(resumenes, cm_dentro, gl_dentro, gl_entre, confianza):
    """Todos los pares, por los cinco caminos.

    Devuelve una fila por par y por método. El valor crítico de cada método
    depende solo de k, de los grados de libertad y de la confianza, así que se
    calcula una vez y no una por par: el de Tukey son dos cuadraturas anidadas
    por cada paso de una bisección, y dentro del doble bucle costaría cientos
    de veces más.
    """
    k = len(resumenes)
    if k < 2 or not (cm_dentro > 0):
        return []
    alfa = 1 - confianza
    m = k * (k - 1) // 2

    criticos = {
        "sin corregir": float(stats.t.ppf(1 - alfa / 2, gl_dentro)),
        "tukey": rango_inv(confianza, k, gl_dentro) / math.sqrt(2),
        "bonferroni": float(stats.t.ppf(1 - alfa / (2 * m), gl_dentro)),
        # Holm no tiene un intervalo de forma cerrada, así que se deja el de
        # Bonferroni: es el más conservador y contiene al de Holm.
        "holm": float(stats.t.ppf(1 - alfa / (2 * m), gl_dentro)),
        "scheffe": math.sqrt(gl_entre * float(stats.f.ppf(confianza, gl_entre, gl_dentro))),
    }

    pares = []
    for i in range(k):
        for j in range(i + 1, k):
            a, b = resumenes[i], resumenes[j]
            diferencia = a["media"] - b["media"]
            # Error estándar de la diferencia, con la varianza combinada del ANOVA.
            ee = math.sqrt(cm_dentro * (1 / a["n"] + 1 / b["n"]))
            t = diferencia / ee
            p_crudo = float(2 * stats.t.sf(abs(t), gl_dentro))

            for metodo in METODOS:
                if metodo == "tukey":
                    # Tukey trabaja con la diferencia sobre el error estándar de
                    # UNA media, que es el de la diferencia dividido por raíz de dos.
                    estadistico = abs(diferencia) / (ee / math.sqrt(2))
                    p = rango_cola(estadistico, k, gl_dentro)
                elif metodo == "scheffe":
                    estadistico = diferencia ** 2 / (ee ** 2 * gl_entre)
                    p = float(stats.f.sf(estadistico, gl_entre, gl_dentro))
                elif metodo == "bonferroni":
                    estadistico = t
                    p = min(1.0, p_crudo * m)
                else:
                    # «sin corregir» y «holm» arrancan del mismo p; Holm se
                    # ajusta después, cuando están todos y se pueden ordenar.
                    estadistico = t
                    p = p_crudo

                margen = criticos[metodo] * ee
                pares.append({
                    "a": a["grupo"], "b": b["grupo"], "metodo": metodo,
                    "diferencia": diferencia, "error_estandar": ee,
                    "estadistico": estadistico, "p_sin_corregir": p_crudo, "p": p,
                    "inferior": diferencia - margen, "superior": diferencia + margen,
                    "significativa": p < alfa,
                })

    # Holm: se ordenan los p de menor a mayor y al i-ésimo se lo multiplica por
    # (m − i), no por m. Después se fuerza la monotonía, para que un p ajustado
    # nunca sea menor que el anterior.
    de_holm = [f for f in pares if f["metodo"] == "holm"]
    orden = sorted(range(len(de_holm)), key=lambda i: (de_holm[i]["p_sin_corregir"],
                                                       de_holm[i]["a"], de_holm[i]["b"]))
    maximo = 0.0
    for puesto, indice in enumerate(orden):
        ajustado = min(1.0, de_holm[indice]["p_sin_corregir"] * (m - puesto))
        maximo = max(maximo, ajustado)
        de_holm[indice]["p"] = maximo
        de_holm[indice]["significativa"] = maximo < alfa

    # Y la marca por par: dónde los cuatro métodos corregidos no coinciden.
    corregidos = [f for f in pares if f["metodo"] != "sin corregir"]
    veredictos: dict[tuple, set] = {}
    for f in corregidos:
        veredictos.setdefault((f["a"], f["b"]), set()).add(f["significativa"])
    for f in pares:
        f["cambia_entre_correcciones"] = len(veredictos[(f["a"], f["b"])]) > 1

    return pares


def calcular(tabla_para_post_hoc, parametros, sobre: str):
    """`sobre` dice qué se está comparando, y va escrito en la salida.

    Con dos factores se comparan las **celdas** y no los márgenes. Es lo que
    corresponde cuando la interacción manda: comparar el promedio de un factor
    a través de niveles donde el efecto es distinto mezcla cosas que no se
    pueden mezclar.
    """
    if tabla_para_post_hoc is None:
        return {"pares": [], "avisos": [], "sobre": sobre, "cuantas": 0}

    pares = comparaciones(tabla_para_post_hoc["resumenes"],
                          tabla_para_post_hoc["cm_dentro"],
                          tabla_para_post_hoc["gl_dentro"],
                          tabla_para_post_hoc["gl_entre"],
                          parametros["confianza"])

    k = tabla_para_post_hoc["k"]
    m = k * (k - 1) // 2
    avisos = []

    discrepan = ordenar([f"{f['a']} vs {f['b']}" for f in pares
                         if f["cambia_entre_correcciones"] and f["metodo"] == "tukey"])
    if discrepan:
        avisos.append({"donde": "post hoc",
                       "aviso": f"En {len(discrepan)} de las {m} comparaciones los cuatro "
                                f"métodos no coinciden ({'; '.join(discrepan)}). Ahí la "
                                f"conclusión la decide la corrección elegida y no los "
                                f"datos: hay que declarar cuál se usó y por qué, y la "
                                f"respuesta honesta es que está en el borde."})

    sin_corregir = sum(1 for f in pares if f["metodo"] == "sin corregir" and f["significativa"])
    con_tukey = sum(1 for f in pares if f["metodo"] == "tukey" and f["significativa"])
    if sin_corregir > con_tukey:
        avisos.append({"donde": "post hoc",
                       "aviso": f"Sin corregir darían {sin_corregir} pares significativos y "
                                f"con Tukey quedan {con_tukey}. Esa diferencia es el precio "
                                f"de haber hecho {m} comparaciones, y no es opcional: sin "
                                f"pagarlo, la probabilidad de encontrar al menos un falso "
                                f"positivo no es 5 % sino mucho más."})

    if tabla_para_post_hoc["p"] >= 1 - parametros["confianza"] and con_tukey > 0:
        avisos.append({"donde": "post hoc",
                       "aviso": "El ANOVA no rechaza y sin embargo hay pares significativos "
                                "en el post hoc. No es una contradicción —las dos pruebas "
                                "no miden lo mismo—, pero informar solo el par sin decir "
                                "que el F no dio sería contar media historia."})
    if tabla_para_post_hoc["p"] < 1 - parametros["confianza"] and con_tukey == 0:
        avisos.append({"donde": "post hoc",
                       "aviso": "El ANOVA rechaza y ningún par sobrevive a Tukey. Pasa, y no "
                                "es un error: el F junta la información de todos los grupos "
                                "y puede detectar un patrón que ninguna comparación de a "
                                "dos alcanza a mostrar por separado."})

    return {"pares": pares, "avisos": avisos, "sobre": sobre, "cuantas": m}

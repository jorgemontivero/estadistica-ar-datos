"""Paso 2: dos o más muestras independientes.

Mann-Whitney para dos grupos, Kruskal-Wallis para tres o más, y la t de Welch
al lado, siempre, para que se vea cuándo las dos miran lo mismo y cuándo no.

**Lo que Mann-Whitney contrasta no es la igualdad de medianas.** Es la
afirmación más repetida sobre esta prueba y es falsa. Lo que contrasta es
P(X > Y) = ½: la probabilidad de que un caso tomado al azar de un grupo supere
a uno tomado al azar del otro. Solo cuando las dos distribuciones tienen la
misma forma y difieren nada más que en un desplazamiento, esa hipótesis
equivale a la de medianas iguales.

No es una sutileza de manual. Se pueden construir dos grupos con **la misma
mediana exacta** donde Mann-Whitney rechaza con toda la fuerza, y dos grupos
con medianas muy distintas donde no rechaza. Por eso este paso escribe
P(X > Y) en la tabla, al lado del valor p: es lo que la prueba realmente
estimó, y quien lea el informe tiene derecho a verlo.

Lo que sí es un desplazamiento —bajo el supuesto de forma igual— lo estima el
**Hodges-Lehmann**: la mediana de todas las diferencias entre un caso de un
grupo y uno del otro. Ese es el número que corresponde informar como «de
cuánto es la diferencia».
"""

import math

from scipy import stats

from comun import cuantil, mediana

from importlib import import_module

_apareadas = import_module("01_apareadas")
rangos_con_empates = _apareadas.rangos_con_empates


def mann_whitney(a, b, confianza):
    """Mann-Whitney por la aproximación normal, con corrección por empates.

    La aproximación se usa siempre, por lo mismo que en Wilcoxon: el valor p
    exacto solo es viable con muestras chicas, y cambiar de régimen según el n
    hace que dos corridas parecidas den números que no se pueden comparar.
    """
    na, nb = len(a), len(b)
    if na < 1 or nb < 1:
        return None

    rangos, correccion = rangos_con_empates(list(a) + list(b))
    suma_a = math.fsum(rangos[:na])
    u_a = suma_a - na * (na + 1) / 2
    u_b = na * nb - u_a

    esperado = na * nb / 2
    n = na + nb
    varianza = (na * nb / 12) * ((n + 1) - correccion / (n * (n - 1)))
    if varianza <= 0:
        return None
    u = min(u_a, u_b)
    z = (u - esperado + 0.5) / math.sqrt(varianza)
    p = float(2 * stats.norm.sf(abs(z)))

    # Hodges-Lehmann: la mediana de todas las diferencias entre pares.
    diferencias = sorted(y - x for y in b for x in a)
    return {
        "n_a": na, "n_b": nb, "u": u, "u_a": u_a, "z": z, "p": p,
        "significativa": p < 1 - confianza,
        # P(X > Y) con los empates contando medio, que es exactamente U
        # dividido por el total de pares. La orientación es la del sitio: la
        # probabilidad de que gane el PRIMER grupo, el que sale primero al
        # ordenar las etiquetas.
        "probabilidad_de_superar": u_a / (na * nb),
        "hodges_lehmann": cuantil(diferencias, 0.5),
        "mediana_a": mediana(list(a)), "mediana_b": mediana(list(b)),
    }


def kruskal_wallis(grupos, confianza):
    """Kruskal-Wallis: la extensión de Mann-Whitney a más de dos grupos.

    Vale la misma advertencia: contrasta que ninguna de las distribuciones
    tienda a dar valores más altos que las otras, no que las medianas sean
    iguales.
    """
    usables = [(nombre, v) for nombre, v in grupos.items() if len(v) > 0]
    k = len(usables)
    if k < 2:
        return None
    todos = [x for _, v in usables for x in v]
    n = len(todos)
    if n < 3:
        return None

    rangos, correccion = rangos_con_empates(todos)
    h = 0.0
    inicio = 0
    por_grupo = []
    for nombre, v in usables:
        suma = math.fsum(rangos[inicio:inicio + len(v)])
        por_grupo.append({"grupo": nombre, "n": len(v), "suma_de_rangos": suma,
                          "rango_promedio": suma / len(v), "mediana": mediana(list(v))})
        h += suma ** 2 / len(v)
        inicio += len(v)
    h = 12 / (n * (n + 1)) * h - 3 * (n + 1)
    # La corrección por empates: sin ella el H sale chico y la prueba pierde
    # potencia sin que nada lo avise.
    divisor = 1 - correccion / (n ** 3 - n) if n > 1 else 1
    h_corregido = h / divisor if divisor > 0 else h
    p = float(stats.chi2.sf(h_corregido, k - 1))

    # Epsilon cuadrado: la proporción de la variabilidad de los rangos que
    # explica el factor. Es el tamaño del efecto que corresponde a una prueba
    # de rangos, y casi nunca se informa.
    #
    # Ojo: circulan dos fórmulas con el mismo nombre. La clásica de Kelley es
    # H(n+1)/(n²−1); la de acá, (H − k + 1)/(n − k), es la que usan
    # `rstatix` y la calculadora del sitio. Con n grande dan parecido, con n
    # chico no. Se eligió esta para que el descargable y `calc-no-parametricas`
    # informen el mismo número.
    epsilon = (h_corregido - k + 1) / (n - k) if n > k else 0.0
    return {"h": h_corregido, "h_sin_corregir": h, "gl": k - 1, "p": p,
            "significativa": p < 1 - confianza, "n": n, "k": k,
            "epsilon_cuadrado": min(1.0, max(0.0, epsilon)), "grupos": por_grupo}


def calcular(datos, parametros, grupos, por_factor):
    confianza = parametros["confianza"]
    alfa = 1 - confianza
    avisos = []
    salida = {"mann_whitney": None, "kruskal": None, "t_de_welch": None,
              "nombres": list(grupos), "avisos": avisos}

    if len(grupos) == 2:
        nombres = list(grupos)
        a, b = grupos[nombres[0]], grupos[nombres[1]]
        u = mann_whitney(a, b, confianza)
        salida["mann_whitney"] = u
        if len(a) > 1 and len(b) > 1:
            t = stats.ttest_ind(a, b, equal_var=False)
            salida["t_de_welch"] = {"t": float(t.statistic), "p": float(t.pvalue),
                                    "significativa": float(t.pvalue) < alfa}

        if u and salida["t_de_welch"]:
            if (u["p"] < alfa) != (salida["t_de_welch"]["p"] < alfa):
                cual = ("Mann-Whitney" if u["p"] < alfa else "la t de Welch")
                otra = ("la t de Welch" if u["p"] < alfa else "Mann-Whitney")
                avisos.append({"donde": "independientes",
                               "aviso": f"{cual} rechaza y {otra} no. No es que una esté "
                                        f"bien y la otra mal: miden cosas distintas. La t "
                                        f"compara promedios y le pesan los valores "
                                        f"extremos; Mann-Whitney compara posiciones en el "
                                        f"orden y no los ve. Con datos muy asimétricos, la "
                                        f"de rangos suele tener más potencia, al revés de "
                                        f"lo que se cree."})
        if u:
            lejos = abs(u["probabilidad_de_superar"] - 0.5)
            if u["significativa"]:
                avisos.append({"donde": "independientes",
                               "aviso": f"Mann-Whitney rechaza, y lo que rechaza es que "
                                        f"P(X > Y) valga un medio: acá vale "
                                        + f"{u['probabilidad_de_superar']:.3f}".replace(".", ",")
                                        + ". Eso NO es lo mismo que decir que las medianas "
                                          "difieren. Solo lo es si las dos distribuciones "
                                          "tienen la misma forma; si no, hay que informar "
                                          "P(X > Y) y no una diferencia de medianas."})
            if lejos < 0.02 and u["significativa"]:
                avisos.append({"donde": "independientes",
                               "aviso": "El valor p es chico pero P(X > Y) está pegado a un "
                                        "medio: la diferencia es real y minúscula. Con esta "
                                        "cantidad de casos, la prueba detecta cosas que no "
                                        "importan."})

    elif len(grupos) > 2:
        salida["kruskal"] = kruskal_wallis(grupos, confianza)
        if salida["kruskal"] and salida["kruskal"]["significativa"]:
            avisos.append({"donde": "independientes",
                           "aviso": "Kruskal-Wallis rechaza, y como el F de un ANOVA no dice "
                                    "entre cuáles grupos está la diferencia. Las "
                                    "comparaciones de a pares con corrección están en el "
                                    "descargable de ANOVA."})

    if por_factor and len(por_factor) > 2:
        salida["kruskal_factor"] = kruskal_wallis(por_factor, confianza)
    else:
        salida["kruskal_factor"] = None

    return salida

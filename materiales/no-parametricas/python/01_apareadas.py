"""Paso 1: dos mediciones sobre la misma unidad.

Cuando cada caso aporta dos valores —antes y después, mano izquierda y mano
derecha, dos evaluadores sobre la misma historia clínica— lo que se analiza
**no son dos muestras**: es una sola, la de las diferencias. Ignorar eso es el
error más caro y más común con datos apareados, y por eso este paso corre las
dos cosas y las pone una al lado de la otra.

El motivo es de aritmética, no de doctrina. En una comparación apareada, la
variabilidad que importa es la de los cambios; en una comparación entre
muestras independientes, la que importa es la que hay entre personas. Si la
gente difiere mucho entre sí y cambia poco, el segundo denominador es enorme y
el efecto se pierde adentro.

Se corren dos pruebas apareadas:

    Wilcoxon de rangos con signo   usa el tamaño de cada cambio, no solo su
                                   signo. Supone que la distribución de las
                                   diferencias es simétrica.
    la prueba de los signos        solo cuenta cuántos subieron y cuántos
                                   bajaron. No supone nada sobre la forma, y
                                   por eso tiene menos potencia.

La de los signos casi nunca se informa, y es la única que sigue valiendo
cuando las diferencias son marcadamente asimétricas.
"""

import math

from scipy import stats

from comun import cuantil, desvio, media


def rangos_con_empates(valores):
    """Los rangos promediados en los empates, y la corrección que necesitan.

    Devuelve los rangos y la suma de (t³ − t) sobre cada grupo de empatados,
    que es el término que corrige la varianza del estadístico.
    """
    orden = sorted(range(len(valores)), key=lambda i: valores[i])
    rangos = [0.0] * len(valores)
    correccion = 0.0
    i = 0
    while i < len(orden):
        j = i
        while j + 1 < len(orden) and valores[orden[j + 1]] == valores[orden[i]]:
            j += 1
        promedio = (i + j) / 2 + 1
        for k in range(i, j + 1):
            rangos[orden[k]] = promedio
        t = j - i + 1
        if t > 1:
            correccion += t ** 3 - t
        i = j + 1
    return rangos, correccion


def wilcoxon(a, b, confianza):
    """Wilcoxon de rangos con signo, por la aproximación normal.

    Los pares sin cambio se descartan, que es la convención de Wilcoxon y la
    que usa `wilcox.test` de R. No es inocente: descartarlos reduce el n y
    puede exagerar el efecto si los empates son muchos, así que el proyecto
    escribe cuántos hubo.

    La aproximación normal se usa siempre, también con n chico, para que los
    dos idiomas den lo mismo: el valor p exacto por enumeración es viable
    hasta unos veinte pares y después no, y tener dos regímenes distintos
    según el n es una fuente de sorpresas.
    """
    diferencias = [y - x for x, y in zip(a, b)]
    sin_cambio = sum(1 for d in diferencias if d == 0)
    usadas = [d for d in diferencias if d != 0]
    n = len(usadas)
    if n < 1:
        return None

    rangos, correccion = rangos_con_empates([abs(d) for d in usadas])
    w_mas = math.fsum(r for d, r in zip(usadas, rangos) if d > 0)
    w_menos = math.fsum(r for d, r in zip(usadas, rangos) if d < 0)
    w = min(w_mas, w_menos)

    esperado = n * (n + 1) / 4
    varianza = n * (n + 1) * (2 * n + 1) / 24 - correccion / 48
    if varianza <= 0:
        return None
    # Corrección por continuidad: el estadístico es discreto y la normal no.
    z = (w - esperado + 0.5) / math.sqrt(varianza) if w < esperado else \
        (w - esperado - 0.5) / math.sqrt(varianza)
    p = float(2 * stats.norm.sf(abs(z)))

    # Hodges-Lehmann: la mediana de los promedios de cada par de diferencias.
    # Es el desplazamiento que la prueba está estimando, y el que corresponde
    # informar al lado del valor p.
    promedios = sorted((usadas[i] + usadas[j]) / 2
                       for i in range(n) for j in range(i, n))
    return {
        "n": n, "sin_cambio": sin_cambio, "w_mas": w_mas, "w_menos": w_menos, "w": w,
        "z": z, "p": p, "significativa": p < 1 - confianza,
        "hodges_lehmann": cuantil(promedios, 0.5),
        "mediana_del_cambio": cuantil(sorted(diferencias), 0.5),
        "media_del_cambio": media(diferencias), "desvio_del_cambio": desvio(diferencias),
    }


MAXIMO_EXACTO = 1000


def cola_binomial(k: int, n: int) -> float:
    """P(X ≤ k) con n ensayos y probabilidad un medio.

    Se calcula por recurrencia y no con coeficientes binomiales: C(148, 51)
    tiene cuarenta y una cifras, y aunque Python lo representa exacto, R no
    tiene enteros de ese tamaño y su `choose` lo aproxima por logaritmos. Con
    la recurrencia —arrancar en 2⁻ⁿ y multiplicar por (n − i + 1)/i— los dos
    hacen exactamente las mismas operaciones sobre los mismos números.

    El límite es el de la doble precisión: 2⁻ⁿ deja de ser representable
    alrededor de n = 1070, y por eso arriba de mil pares se usa la
    aproximación normal.
    """
    termino = 2.0 ** (-n)
    acumulado = termino
    for i in range(1, k + 1):
        termino = termino * (n - i + 1) / i
        acumulado += termino
    return min(1.0, acumulado)


def signos(a, b, confianza):
    """La prueba de los signos: solo cuenta cuántos suben y cuántos bajan.

    Con hasta mil pares el valor p sale exacto de la binomial; con más, de la
    aproximación normal con corrección por continuidad. El corte está escrito
    en la salida, porque no es lo mismo y quien lea tiene que saber cuál le
    tocó.
    """
    diferencias = [y - x for x, y in zip(a, b)]
    subieron = sum(1 for d in diferencias if d > 0)
    bajaron = sum(1 for d in diferencias if d < 0)
    n = subieron + bajaron
    if n < 1:
        return None

    k = min(subieron, bajaron)
    if n <= MAXIMO_EXACTO:
        p = min(1.0, 2 * cola_binomial(k, n))
        como = "binomial exacta"
    else:
        z = (k + 0.5 - n / 2) / math.sqrt(n / 4)
        p = min(1.0, float(2 * stats.norm.cdf(z)))
        como = "aproximación normal"
    return {"n": n, "subieron": subieron, "bajaron": bajaron,
            "empates": len(diferencias) - n, "p": p, "como": como,
            "proporcion_que_sube": subieron / n,
            "significativa": p < 1 - confianza}


def como_si_fueran_independientes(a, b, confianza):
    """La misma comparación, tirando el apareamiento.

    Está para que se vea el precio, no para informarla. Se corre la de
    Mann-Whitney y también la t de Welch, porque el error se comete con las
    dos por igual.
    """
    from importlib import import_module
    independientes = import_module("02_independientes")
    u = independientes.mann_whitney(a, b, confianza)
    t = float(stats.ttest_ind(a, b, equal_var=False).pvalue)
    return {"mann_whitney_p": u["p"] if u else None, "t_de_welch_p": t}


def calcular(datos, parametros, pares):
    a, b, descartados = pares
    if len(a) < 2:
        return None

    confianza = parametros["confianza"]
    alfa = 1 - confianza
    w = wilcoxon(a, b, confianza)
    s = signos(a, b, confianza)
    mal = como_si_fueran_independientes(a, b, confianza)

    avisos = []
    if w and mal["mann_whitney_p"] is not None:
        # La columna que justifica el paso: si tirar el apareamiento cambia la
        # conclusión, hay que decirlo con todas las letras.
        cambia = (w["p"] < alfa) != (mal["mann_whitney_p"] < alfa)
        if cambia:
            avisos.append({"donde": "apareadas",
                           "aviso": "Tratar estos datos como dos muestras independientes "
                                    "cambia la conclusión. No es una diferencia de matiz: "
                                    "el apareamiento es información que está en los datos, "
                                    "y tirarla no es una decisión conservadora, es perder "
                                    "el resultado."})
    else:
        cambia = False

    if w and s and (w["p"] < alfa) != (s["p"] < alfa):
        avisos.append({"donde": "apareadas",
                       "aviso": "Wilcoxon y la prueba de los signos no coinciden. Wilcoxon "
                                "usa el tamaño de los cambios y supone que su distribución "
                                "es simétrica; la de los signos solo cuenta direcciones y no "
                                "supone nada. Si las diferencias son asimétricas, la que "
                                "vale es la segunda."})
    if w and w["sin_cambio"] > 0:
        avisos.append({"donde": "apareadas",
                       "aviso": f"Hay {w['sin_cambio']} pares sin ningún cambio, y Wilcoxon "
                                f"los descarta. Con muchos empates eso infla el efecto "
                                f"aparente: la prueba termina hablando solo de los que se "
                                f"movieron."})
    if w and len(a) < 10:
        avisos.append({"donde": "apareadas",
                       "aviso": f"Con {len(a)} pares, la aproximación normal de Wilcoxon es "
                                f"apenas orientativa. Conviene la prueba exacta, que este "
                                f"proyecto no trae."})

    return {"wilcoxon": w, "signos": s, "como_independientes": mal,
            "cambia_la_conclusion": cambia, "descartados": descartados,
            "n_pares": len(a), "avisos": avisos}

"""Paso 1: los supuestos, celda por celda.

Un ANOVA pide tres cosas: residuos normales dentro de cada celda, varianzas
parecidas entre celdas y observaciones independientes. La tercera no se prueba
—se garantiza con el diseño—; las otras dos sí, y este paso las mira antes de
que se calcule ningún valor p.

**La normalidad se mira por celda y no sobre todo junto.** Es un error
frecuente y silencioso: si los grupos tienen medias distintas, la respuesta
apilada sale bimodal o achatada y Shapiro-Wilk rechaza aunque cada celda sea
perfectamente normal. Lo que el ANOVA supone normal es el residuo, no la
respuesta.

**Levene va con la mediana**, que es la variante de Brown-Forsythe: la versión
con la media es sensible a la falta de normalidad, que es justo lo que suele
venir con la heterocedasticidad. Es la misma que corre `calc-anova` en el
sitio.
"""

from scipy import stats

from comun import mediana


def shapiro_por_celda(grupos, alfa):
    """Shapiro-Wilk dentro de cada celda.

    Con menos de tres casos no hay prueba que hacer, y con muchos casos la
    prueba rechaza por desviaciones que no le importan a nadie: las dos cosas
    salen escritas en la fila, no se esconden.
    """
    filas = []
    for etiqueta, _, valores in grupos:
        n = len(valores)
        if n < 3 or len(set(valores)) < 2:
            filas.append({"celda": etiqueta, "n": n, "w": None, "p": None,
                          "normal": None, "por_que": "Hacen falta 3 casos distintos"})
            continue
        w, p = stats.shapiro(valores)
        filas.append({"celda": etiqueta, "n": n, "w": float(w), "p": float(p),
                      "normal": bool(p >= alfa), "por_que": ""})
    return filas


def levene(grupos):
    """Levene con centro en la mediana, escrito a mano.

    Está escrito y no llamado porque `leveneTest` no viene con R base y
    `scipy.stats.levene` y la versión de R difieren en cómo tratan los grupos
    de un solo caso. La cuenta es un ANOVA de un factor sobre |x − mediana del
    grupo|, y no tiene ningún secreto.
    """
    usables = [(e, v) for e, _, v in grupos if len(v) > 0]
    k = len(usables)
    if k < 2:
        return None

    z = []
    for _, valores in usables:
        m = mediana(valores)
        z.append([abs(x - m) for x in valores])

    n = sum(len(g) for g in z)
    if n - k < 1:
        return None

    medias_z = [sum(g) / len(g) for g in z]
    media_z = sum(sum(g) for g in z) / n

    numerador = sum(len(g) * (medias_z[i] - media_z) ** 2 for i, g in enumerate(z))
    denominador = sum(sum((x - medias_z[i]) ** 2 for x in g) for i, g in enumerate(z))
    if denominador <= 0:
        return None

    w = ((n - k) / (k - 1)) * (numerador / denominador)
    return {"w": w, "gl1": k - 1, "gl2": n - k,
            "p": float(stats.f.sf(w, k - 1, n - k))}


def calcular(grupos, parametros):
    alfa = 1 - parametros["confianza"]
    normalidad = shapiro_por_celda(grupos, alfa)
    homogeneidad = levene(grupos)

    # El veredicto que decide el paso siguiente.
    hay_veredicto = [f for f in normalidad if f["normal"] is not None]
    todas_normales = all(f["normal"] for f in hay_veredicto) if hay_veredicto else None
    varianzas_iguales = None if homogeneidad is None else homogeneidad["p"] >= alfa

    avisos = []
    if hay_veredicto and not todas_normales:
        cuales = [f["celda"] for f in hay_veredicto if not f["normal"]]
        avisos.append({"donde": "normalidad",
                       "aviso": f"Shapiro-Wilk rechaza la normalidad en "
                                f"{len(cuales)} de {len(hay_veredicto)} celdas "
                                f"({', '.join(cuales)}). Con celdas de veinte casos o más "
                                f"el ANOVA aguanta bastante; con celdas chicas conviene "
                                f"Kruskal-Wallis, que este proyecto no trae."})
    if varianzas_iguales is False:
        avisos.append({"donde": "homogeneidad",
                       "aviso": "Levene rechaza la igualdad de varianzas. El F clásico deja "
                                "de ser confiable, sobre todo con celdas de tamaños "
                                "distintos: la versión de Welch es la que corresponde, y "
                                "está en la misma tabla."})

    chicas = [f["celda"] for f in normalidad if f["n"] < 10]
    if chicas:
        avisos.append({"donde": "diseño",
                       "aviso": f"Hay {len(chicas)} celdas con menos de diez casos "
                                f"({', '.join(chicas)}). Con celdas así de chicas las "
                                f"pruebas de supuestos casi no tienen potencia: que no "
                                f"rechacen no significa que el supuesto se cumpla."})

    return {"normalidad": normalidad, "homogeneidad": homogeneidad,
            "todas_normales": todas_normales, "varianzas_iguales": varianzas_iguales,
            "avisos": avisos}

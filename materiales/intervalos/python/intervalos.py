"""Los cinco intervalos, escritos como funciones puras.

Son los mismos que calcula la calculadora de estadistica.ar, con los mismos
avisos y palabra por palabra: el verificador del sitio compara las dos cosas.
Si alguna vez dejaran de coincidir, sería un error de una de las dos y no una
diferencia de criterio.

    ic_media                 una media, con t o con z
    ic_proporcion            una proporción, por Wilson, Wald o Clopper-Pearson
    ic_diferencia_medias     dos medias, por Welch o con varianzas iguales
    ic_diferencia_proporcion dos proporciones
    ic_varianza              la varianza y el desvío, por chi-cuadrado

Lo único que necesita SciPy son los cuantiles: qt, qnorm, qchisq y qbeta. En R
vienen de fábrica.
"""

import math

from scipy import stats


def coma(v: float, decimales: int = 2) -> str:
    """Los números que van DENTRO de un aviso llevan coma decimal: son texto
    para leer, no valores para volver a calcular."""
    return f"{v:.{decimales}f}".replace(".", ",")


def critico(confianza: float, gl=None) -> float:
    """El z o el t que deja (1 − confianza)/2 en cada cola."""
    p = 1 - (1 - confianza) / 2
    return float(stats.norm.ppf(p)) if gl is None else float(stats.t.ppf(p, gl))


def fpc(n: int, N=None) -> float:
    """Corrección por población finita.

    Cuando la muestra es una parte grande de la población, el muestreo sin
    reposición reduce la variabilidad: en el extremo, si se releva a todos, no
    hay error de muestreo.
    """
    if N is None or not math.isfinite(N) or N <= 0 or n >= N:
        return 0.0 if (N is not None and n >= N) else 1.0
    return math.sqrt((N - n) / (N - 1))


def ic_media(media, desvio, n, confianza, sigma_conocida=False, N=None):
    if not (n > 1) or not (desvio >= 0) or not (0 < confianza < 1):
        return None

    gl = None if sigma_conocida else n - 1
    c = critico(confianza, gl)
    correccion = fpc(n, N)
    ee = desvio / math.sqrt(n) * correccion
    margen = c * ee

    avisos = []
    if n < 30 and not sigma_conocida:
        avisos.append("Con menos de 30 casos, el intervalo depende de que la variable sea "
                      "aproximadamente normal. Mirá el histograma antes de confiar en él.")
    if sigma_conocida:
        avisos.append("Estás usando z, que supone σ conocida. Si el desvío lo calculaste con "
                      "estos mismos datos, σ no es conocida y corresponde la t.")
    if N and n / N > 0.05:
        avisos.append(f"La muestra es el {coma(100 * n / N, 1)} % de la población, así que la "
                      f"corrección por población finita está achicando el margen un "
                      f"{coma((1 - correccion) * 100, 1)} %.")

    return {"estimacion": media, "inferior": media - margen, "superior": media + margen,
            "margen": margen, "error_estandar": ee, "critico": c, "gl": gl,
            "distribucion": "z" if sigma_conocida else "t", "avisos": avisos}


def ic_proporcion(exitos, n, confianza, metodo="wilson", N=None):
    if not (n > 0) or exitos < 0 or exitos > n or not (0 < confianza < 1):
        return None

    p = exitos / n
    z = critico(confianza)
    correccion = fpc(n, N)

    avisos = []
    esperados = min(exitos, n - exitos)
    if esperados < 5:
        avisos.append(f"Hay solo {esperados} caso{'' if esperados == 1 else 's'} en la categoría "
                      f"menos frecuente. La aproximación normal no sirve acá: usá el intervalo "
                      f"exacto de Clopper-Pearson.")
    if N and n / N > 0.05:
        avisos.append(f"La muestra es el {coma(100 * n / N, 1)} % de la población: la corrección "
                      f"por población finita está achicando el margen.")

    if metodo == "clopper-pearson":
        # El intervalo exacto: invierte la binomial usando su relación con la beta.
        alfa = 1 - confianza
        inferior = 0.0 if exitos == 0 else float(stats.beta.ppf(alfa / 2, exitos, n - exitos + 1))
        superior = 1.0 if exitos == n else float(stats.beta.ppf(1 - alfa / 2, exitos + 1, n - exitos))
        return {"estimacion": p, "inferior": inferior, "superior": superior,
                "margen": (superior - inferior) / 2,
                "error_estandar": math.sqrt(p * (1 - p) / n) * correccion,
                "critico": z, "gl": None, "distribucion": "beta",
                "avisos": avisos + [
                    "El intervalo exacto no es simétrico alrededor de la proporción observada, "
                    "así que el «margen» de acá es la mitad del ancho y no un ± en el sentido "
                    "habitual."]}

    if metodo == "wald":
        ee = math.sqrt(p * (1 - p) / n) * correccion
        margen = z * ee
        extra = ["El método de Wald es el de la fórmula clásica p ± z·√(p(1−p)/n). Tiene mala "
                 "cobertura con n chico o proporciones cerca de 0 o 1, y ahí conviene Wilson."]
        if p == 0 or p == 1:
            extra.append("Con una proporción de 0 o de 1, Wald da un intervalo de ancho cero, "
                         "que es absurdo: no hay certeza total con una muestra.")
        return {"estimacion": p, "inferior": max(0.0, p - margen), "superior": min(1.0, p + margen),
                "margen": margen, "error_estandar": ee, "critico": z, "gl": None,
                "distribucion": "z", "avisos": avisos + extra}

    # Wilson: el recomendado por omisión. Invierte la prueba de puntaje en vez
    # de suponer que la proporción muestral tiene distribución normal.
    z2 = z * z
    denominador = 1 + z2 / n
    centro = (p + z2 / (2 * n)) / denominador
    semiancho = z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / denominador * correccion
    extra = []
    if abs(centro - p) > 0.01:
        extra.append("El intervalo de Wilson no está centrado en la proporción observada: se "
                     "corre hacia 0,5. Eso es correcto y es justamente lo que lo hace mejor que "
                     "Wald con muestras chicas.")

    return {"estimacion": p, "inferior": max(0.0, centro - semiancho),
            "superior": min(1.0, centro + semiancho), "margen": semiancho,
            "error_estandar": math.sqrt(p * (1 - p) / n) * correccion, "critico": z, "gl": None,
            "distribucion": "z", "avisos": avisos + extra}


def ic_diferencia_medias(m1, s1, n1, m2, s2, n2, confianza, varianzas_iguales=False):
    if not (n1 > 1) or not (n2 > 1) or not (0 < confianza < 1):
        return None

    diferencia = m1 - m2
    v1 = s1 * s1 / n1
    v2 = s2 * s2 / n2

    if varianzas_iguales:
        # Varianza combinada, ponderada por los grados de libertad de cada grupo.
        sp2 = ((n1 - 1) * s1 * s1 + (n2 - 1) * s2 * s2) / (n1 + n2 - 2)
        ee = math.sqrt(sp2 * (1 / n1 + 1 / n2))
        gl = float(n1 + n2 - 2)
    else:
        # Welch-Satterthwaite: los grados de libertad casi nunca son enteros.
        ee = math.sqrt(v1 + v2)
        gl = (v1 + v2) ** 2 / (v1 ** 2 / (n1 - 1) + v2 ** 2 / (n2 - 1))

    c = critico(confianza, gl)
    margen = c * ee

    avisos = []
    razon = max(s1, s2) / min(s1, s2) if min(s1, s2) > 0 else float("inf")
    if varianzas_iguales and razon > 2:
        avisos.append(f"Los desvíos difieren en un factor de {coma(razon, 1)}, y estás suponiendo "
                      f"varianzas iguales. Conviene Welch, que no lo supone.")
    if not varianzas_iguales:
        avisos.append(f"Welch da {coma(gl, 2)} grados de libertad, con decimales. No es un error: "
                      f"es lo que devuelve la fórmula de Welch-Satterthwaite, y es lo que corre R "
                      f"por defecto.")
    if min(n1, n2) < 30:
        avisos.append("Con algún grupo de menos de 30 casos, el intervalo depende de la "
                      "normalidad dentro de cada grupo.")

    return {"estimacion": diferencia, "inferior": diferencia - margen,
            "superior": diferencia + margen, "margen": margen, "error_estandar": ee,
            "critico": c, "gl": gl, "distribucion": "t", "avisos": avisos}


def ic_diferencia_proporciones(x1, n1, x2, n2, confianza):
    if not (n1 > 0) or not (n2 > 0) or x1 < 0 or x1 > n1 or x2 < 0 or x2 > n2:
        return None

    p1 = x1 / n1
    p2 = x2 / n2
    diferencia = p1 - p2
    z = critico(confianza)
    ee = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    margen = z * ee

    avisos = []
    minimo = min(x1, n1 - x1, x2, n2 - x2)
    if minimo < 5:
        avisos.append(f"Hay una celda con solo {minimo} caso{'' if minimo == 1 else 's'}. Con "
                      f"conteos tan chicos este intervalo no es confiable: corresponde un método "
                      f"exacto.")
    if diferencia != 0 and ((diferencia > 0 and diferencia - margen < 0)
                            or (diferencia < 0 and diferencia + margen > 0)):
        avisos.append("El intervalo incluye el cero: los datos son compatibles con que no haya "
                      "diferencia entre los dos grupos.")

    return {"estimacion": diferencia, "inferior": max(-1.0, diferencia - margen),
            "superior": min(1.0, diferencia + margen), "margen": margen, "error_estandar": ee,
            "critico": z, "gl": None, "distribucion": "z", "avisos": avisos}


def ic_varianza(desvio, n, confianza):
    if not (n > 1) or not (desvio > 0) or not (0 < confianza < 1):
        return None

    gl = n - 1
    alfa = 1 - confianza
    s2 = desvio * desvio
    # Ojo con el cruce: el cuantil GRANDE del chi² va en el límite INFERIOR.
    inferior = gl * s2 / float(stats.chi2.ppf(1 - alfa / 2, gl))
    superior = gl * s2 / float(stats.chi2.ppf(alfa / 2, gl))

    return {"estimacion": s2, "inferior": inferior, "superior": superior,
            "margen": (superior - inferior) / 2, "error_estandar": None, "critico": None,
            "gl": gl, "distribucion": "chi2",
            "avisos": [
                "Este intervalo es extremadamente sensible a la normalidad: si la variable no es "
                "normal, la cobertura real puede estar muy lejos del nivel nominal, incluso con "
                "muestras grandes. Es el intervalo menos robusto de todos.",
                "No es simétrico alrededor de la varianza observada, porque la distribución "
                "chi-cuadrado tampoco lo es."]}

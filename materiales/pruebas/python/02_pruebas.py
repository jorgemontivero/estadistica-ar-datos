"""Paso 2: la prueba que corresponde, la que no, y el tamaño del efecto.

El árbol de decisión de estadistica.ar da un par para cada situación: una
prueba y una alternativa. El árbol no mira los datos —no puede, son seis
preguntas—, así que quién de las dos corresponde lo deciden los supuestos del
paso 1:

    dos grupos, los dos normales        t de Welch
    dos grupos, alguno no normal        Mann-Whitney
    tres o más, todos normales          ANOVA; de Welch si Levene rechaza
    tres o más, alguno no normal        Kruskal-Wallis
    categórica, esperadas ≥ 5           chi-cuadrado
    categórica 2×2, alguna esperada < 5 Fisher exacta

Y las dos se corren igual. No para elegir después la que más guste —eso sería
hacer trampa—, sino para que quede escrito cuándo la decisión importó: la
columna `cambia_la_conclusion` dice «Sí» cuando las dos pruebas no coinciden
en rechazar. Es el único caso en que discutir el supuesto cambia la
conclusión del informe; en todos los demás, la discusión es académica.

Cada fila lleva el tamaño del efecto, siempre. Un valor p sin tamaño del
efecto dice que algo pasa y no dice cuánto.
"""

import math

from scipy import stats

from comun import desvio, media, numeros

# Los nombres son los que devuelve el árbol del sitio, no una traducción.
WELCH = "Prueba t de Welch para dos muestras"
MANN = "Mann-Whitney"
ANOVA = "ANOVA de un factor"
ANOVA_WELCH = "ANOVA de Welch"
KRUSKAL = "Kruskal-Wallis"
CHI2_DOS = "Prueba z para dos proporciones, o chi-cuadrado"
CHI2_TRES = "Chi-cuadrado de homogeneidad"
FISHER = "Prueba exacta de Fisher"

# Cómo se llama el estadístico de cada una cuando se lo escribe en el informe.
SIMBOLO = {WELCH: "t", MANN: "U", ANOVA: "F", ANOVA_WELCH: "F", KRUSKAL: "H",
           CHI2_DOS: "χ²", CHI2_TRES: "χ²", FISHER: ""}

# Los cortes de Cohen, los mismos que usa la calculadora de tamaño del efecto.
CORTES = {"d": (0.2, 0.5, 0.8), "r": (0.1, 0.3, 0.5), "eta2": (0.01, 0.06, 0.14)}


def calificar(medida: str, valor: float) -> str:
    """La etiqueta de Cohen, que conviene usar con pinzas: él mismo las publicó
    como provisorias. Una d de 0,2 es enorme si se trata de mortalidad."""
    chico, medio, grande = CORTES[medida]
    v = abs(valor)
    if v < chico:
        return "insignificante"
    if v < medio:
        return "chico"
    if v < grande:
        return "medio"
    return "grande"


# ------------------------------------------------------------ las pruebas
def welch(a, b):
    r = stats.ttest_ind(a, b, equal_var=False)
    return {"estadistico": float(r.statistic), "gl": float(r.df), "p": float(r.pvalue)}


def mann_whitney(a, b):
    """Sin corrección por continuidad y por la aproximación normal, que es lo
    único que R y SciPy calculan igual: con el método exacto cada uno decide
    por su cuenta cuándo usarlo."""
    r = stats.mannwhitneyu(a, b, alternative="two-sided", use_continuity=False,
                           method="asymptotic")
    return {"estadistico": float(r.statistic), "gl": None, "p": float(r.pvalue)}


def anova(grupos):
    r = stats.f_oneway(*grupos)
    k = len(grupos)
    n = sum(len(g) for g in grupos)
    return {"estadistico": float(r.statistic), "gl": float(k - 1), "gl2": float(n - k),
            "p": float(r.pvalue)}


def anova_welch(grupos):
    """La ANOVA de Welch, escrita a mano: R la trae en `oneway.test` y SciPy no.

    Es la misma idea que la t de Welch llevada a k grupos: cada grupo pesa por
    su propia precisión, y los grados de libertad del denominador salen con
    decimales.
    """
    k = len(grupos)
    w = [len(g) / (desvio(g) ** 2) for g in grupos]
    suma = math.fsum(w)
    mg = math.fsum(wi * media(g) for wi, g in zip(w, grupos)) / suma
    entre = math.fsum(wi * (media(g) - mg) ** 2 for wi, g in zip(w, grupos)) / (k - 1)
    lam = 3 / (k * k - 1) * math.fsum(
        (1 - wi / suma) ** 2 / (len(g) - 1) for wi, g in zip(w, grupos))
    f = entre / (1 + 2 * (k - 2) / (k + 1) * lam)
    gl2 = 1 / lam
    return {"estadistico": f, "gl": float(k - 1), "gl2": gl2,
            "p": float(stats.f.sf(f, k - 1, gl2))}


def kruskal(grupos):
    r = stats.kruskal(*grupos)
    return {"estadistico": float(r.statistic), "gl": float(len(grupos) - 1),
            "p": float(r.pvalue)}


def chi_cuadrado(tabla):
    r = stats.chi2_contingency(tabla, correction=False)
    return {"estadistico": float(r.statistic), "gl": float(r.dof), "p": float(r.pvalue)}


def fisher(tabla):
    """Solo para tablas de 2×2: es la única que SciPy y R resuelven igual."""
    if len(tabla) != 2 or len(tabla[0]) != 2:
        return None
    _, p = stats.fisher_exact(tabla)
    return {"estadistico": None, "gl": None, "p": float(p)}


# ------------------------------------------------------- tamaños del efecto
def hedges(a, b):
    """d de Cohen con la corrección de Hedges, que la insesga con n chico."""
    n1, n2 = len(a), len(b)
    sp = math.sqrt(((n1 - 1) * desvio(a) ** 2 + (n2 - 1) * desvio(b) ** 2) / (n1 + n2 - 2))
    if sp == 0:
        return None
    d = (media(a) - media(b)) / sp
    gl = n1 + n2 - 2
    return d * (1 - 3 / (4 * gl - 1))


def r_de_rangos(p, n):
    """El r de la no paramétrica: |Z| / √n, con el Z que devuelve el valor p.

    Con un p pegado al cero el Z se va a infinito; se corta en 1, que es el
    máximo que la medida puede valer.
    """
    if not (p > 0):
        return 1.0
    z = abs(float(stats.norm.isf(p / 2)))
    return min(1.0, z / math.sqrt(n))


def eta_cuadrado(grupos):
    todos = [v for g in grupos for v in g]
    total = media(todos)
    entre = math.fsum(len(g) * (media(g) - total) ** 2 for g in grupos)
    st = math.fsum((v - total) ** 2 for v in todos)
    return entre / st if st > 0 else None


def epsilon_cuadrado(h, n, k):
    """El de Kruskal-Wallis, que se lee en la misma escala que el eta².

    Cuando H queda por debajo de k − 1 la fórmula da negativo, que como
    proporción de varianza no significa nada: ahí es cero.
    """
    if n <= k:
        return None
    return max(0.0, (h - k + 1) / (n - k))


def v_de_cramer(chi2, n, filas, columnas):
    m = min(filas, columnas) - 1
    return math.sqrt(chi2 / (n * m)) if m > 0 and n > 0 else None


# --------------------------------------------------------------- el paso
def calcular(datos, variables, parametros, supuestos):
    alfa = parametros["alfa"]
    factores = [v for v in variables if v["tipo"] == "grupo"]
    numericas = [v for v in variables if v["tipo"] == "numerica"]
    categoricas = [v for v in variables if v["tipo"] == "categorica"]

    normal_de = {(f["variable"], f["factor"], f["grupo"]): f["veredicto"]
                 for f in supuestos["supuestos"]}
    homogeneas_de = {(f["variable"], f["factor"]): f["homogeneas"]
                     for f in supuestos["homogeneidad"]}
    esperada_de = {(f["variable"], f["factor"]): f["esperada_minima"]
                   for f in supuestos["esperadas"]}

    filas, avisos = [], []

    def agregar(base, elegida, otra, cortes, medida, efecto):
        significativa = elegida["p"] < alfa
        alternativa = otra["p"] < alfa if otra else None
        filas.append({**base,
                      "simbolo": SIMBOLO.get(base["prueba"], ""),
                      "estadistico": elegida["estadistico"], "gl": elegida.get("gl"),
                      "gl2": elegida.get("gl2"), "p": elegida["p"],
                      "significativa": significativa,
                      "medida": medida, "efecto": efecto,
                      "calificacion": calificar(cortes, efecto) if efecto is not None else "",
                      "p_alternativa": otra["p"] if otra else None,
                      "significativa_alternativa": alternativa,
                      "cambia_la_conclusion": (alternativa is not None
                                               and alternativa != significativa)})

    for factor in factores:
        niveles = sorted({f.get(factor["nombre"], "") for f in datos
                          if f.get(factor["nombre"], "") != ""})
        if len(niveles) < 2:
            continue
        for v in numericas:
            grupos = []
            for nivel in niveles:
                x = numeros([f for f in datos if f.get(factor["nombre"], "") == nivel],
                            v["nombre"])
                if len(x) >= 2:
                    grupos.append((nivel, x))
            if len(grupos) < 2:
                continue
            valores = [x for _, x in grupos]
            # Sin variación en ningún grupo no hay nada que comparar: SciPy
            # devuelve «nan» y R directamente falla. Mejor decirlo.
            if all(desvio(x) == 0 for x in valores):
                avisos.append({
                    "variable": v["nombre"], "factor": factor["nombre"],
                    "aviso": "Los valores no varían en ningún grupo: no hay prueba que "
                             "aplicar."})
                continue
            n = sum(len(x) for x in valores)
            k = len(grupos)
            todos_normales = all(normal_de.get((v["nombre"], factor["nombre"], nivel))
                                 == "normal" for nivel, _ in grupos)
            base = {"variable": v["nombre"], "etiqueta": v["etiqueta"],
                    "factor": factor["nombre"], "que": "numérica", "k": k, "n": n}

            if k == 2:
                a, b = valores
                par, alterna = WELCH, MANN
                if todos_normales:
                    elegida, otra = welch(a, b), mann_whitney(a, b)
                    prueba, motivo = WELCH, "hay dos grupos y los dos pasan Shapiro-Wilk"
                    cortes, medida, efecto = "d", "d de Hedges", hedges(a, b)
                else:
                    elegida, otra = mann_whitney(a, b), welch(a, b)
                    prueba, motivo = MANN, "hay dos grupos y alguno no pasa Shapiro-Wilk"
                    cortes, medida = "r", "r de rangos"
                    efecto = r_de_rangos(elegida["p"], n)
            else:
                par, alterna = ANOVA, KRUSKAL
                if todos_normales:
                    homogeneas = homogeneas_de.get((v["nombre"], factor["nombre"]), True)
                    if homogeneas:
                        elegida = anova(valores)
                        prueba = ANOVA
                        motivo = "hay tres o más grupos, todos normales y con varianzas homogéneas"
                    else:
                        elegida = anova_welch(valores)
                        prueba = ANOVA_WELCH
                        motivo = "hay tres o más grupos normales, pero Levene rechaza la homogeneidad"
                    otra = kruskal(valores)
                    cortes, medida, efecto = "eta2", "eta²", eta_cuadrado(valores)
                else:
                    elegida, otra = kruskal(valores), anova(valores)
                    prueba, motivo = KRUSKAL, "hay tres o más grupos y alguno no pasa Shapiro-Wilk"
                    cortes, medida = "eta2", "épsilon²"
                    efecto = epsilon_cuadrado(elegida["estadistico"], n, k)

            base.update({"prueba_del_arbol": par, "alternativa_del_arbol": alterna,
                         "prueba": prueba, "motivo": motivo})
            agregar(base, elegida, otra, cortes, medida, efecto)

        for v in categoricas:
            categorias = sorted({f.get(v["nombre"], "") for f in datos
                                 if f.get(v["nombre"], "") != ""})
            tabla = [[sum(1 for f in datos
                          if f.get(v["nombre"], "") == categoria
                          and f.get(factor["nombre"], "") == nivel)
                      for nivel in niveles] for categoria in categorias]
            tabla = [f for f in tabla if sum(f) > 0]
            n = sum(sum(f) for f in tabla)
            if len(tabla) < 2 or n == 0:
                continue
            minima = esperada_de.get((v["nombre"], factor["nombre"]), 5.0)
            par = CHI2_DOS if len(niveles) == 2 else CHI2_TRES
            alterna = FISHER if len(niveles) == 2 and len(tabla) == 2 else ""
            chi = chi_cuadrado(tabla)
            exacta = fisher(tabla)
            if minima < 5 and exacta is not None:
                elegida, otra = exacta, chi
                prueba = FISHER
                motivo = "alguna frecuencia esperada es menor que 5, y la tabla es de 2×2"
            else:
                elegida, otra = chi, exacta
                prueba = par
                motivo = ("todas las frecuencias esperadas llegan a 5" if minima >= 5
                          else "alguna esperada es menor que 5, pero la tabla no es de 2×2")
            if minima < 5 and exacta is None:
                avisos.append({
                    "variable": v["nombre"], "factor": factor["nombre"],
                    "aviso": "La prueba exacta de Fisher para tablas de más de 2×2 no está en "
                             "este proyecto: R y SciPy no la resuelven igual. Con esperadas tan "
                             "chicas conviene juntar categorías o usar una prueba de "
                             "permutaciones."})
            base = {"variable": v["nombre"], "etiqueta": v["etiqueta"],
                    "factor": factor["nombre"], "que": "categórica",
                    "k": len(niveles), "n": n,
                    "prueba_del_arbol": par, "alternativa_del_arbol": alterna,
                    "prueba": prueba, "motivo": motivo}
            agregar(base, elegida, otra, "r", "V de Cramér",
                    v_de_cramer(chi["estadistico"], n, len(tabla), len(niveles)))

    return {"pruebas": filas, "avisos": avisos}

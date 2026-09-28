"""Las pruebas de comparación de la tabla 1.

Cuál se usa no se elige a ojo: sale del tipo de variable, de cuántos grupos hay
y de la forma de la distribución, con la misma regla que el árbol de decisión
de estadistica.ar.

    numérica, 2 grupos, simétrica    prueba t de Welch
    numérica, 2 grupos, asimétrica   Mann-Whitney
    numérica, 3 o más, simétrica     ANOVA de un factor
    numérica, 3 o más, asimétrica    Kruskal-Wallis
    categórica                       chi-cuadrado

Es lo único que necesita SciPy: en R alcanza con lo que ya trae. Las opciones
están puestas a mano y no por omisión —Welch sí, corrección de continuidad no,
corrección de Yates no— porque los valores por omisión de R y de SciPy no son
los mismos, y sin fijarlas los dos idiomas darían números distintos.
"""

import statistics

from scipy import stats

SIN_VARIACION = "Los valores no varían: no hay prueba que aplicar"


def comparar_numerica(grupos: list[list[float]], forma: str) -> dict:
    """`grupos` ya viene sin faltantes y sin grupos vacíos."""
    if len(grupos) < 2 or any(len(g) < 2 for g in grupos):
        return {"p": None, "prueba": "", "nota": "Algún grupo tiene menos de dos casos"}
    # Sin variación no hay prueba: SciPy devuelve «nan» y R directamente falla.
    # Mejor decirlo que dejar que cada idioma haga lo suyo.
    if all(statistics.pstdev(g) == 0 for g in grupos):
        return {"p": None, "prueba": "", "nota": SIN_VARIACION}
    if len(grupos) == 2:
        if forma == "asimétrica":
            u = stats.mannwhitneyu(grupos[0], grupos[1], alternative="two-sided",
                                   use_continuity=False, method="asymptotic")
            return {"p": float(u.pvalue), "prueba": "Mann-Whitney", "nota": ""}
        t = stats.ttest_ind(grupos[0], grupos[1], equal_var=False)
        return {"p": float(t.pvalue), "prueba": "t de Welch", "nota": ""}
    if forma == "asimétrica":
        k = stats.kruskal(*grupos)
        return {"p": float(k.pvalue), "prueba": "Kruskal-Wallis", "nota": ""}
    f = stats.f_oneway(*grupos)
    return {"p": float(f.pvalue), "prueba": "ANOVA", "nota": ""}


def comparar_categorica(tabla: list[list[int]]) -> dict:
    """`tabla` es la de contingencia: una fila por categoría, una columna por grupo."""
    filas = [f for f in tabla if sum(f) > 0]
    if len(filas) < 2 or len(filas[0]) < 2:
        return {"p": None, "prueba": "", "nota": "No hay tabla que comparar"}
    chi = stats.chi2_contingency(filas, correction=False)
    esperadas = chi.expected_freq
    baja = any(e < 5 for fila in esperadas for e in fila)
    return {"p": float(chi.pvalue), "prueba": "Chi-cuadrado",
            "nota": "Alguna frecuencia esperada es menor que 5" if baja else ""}

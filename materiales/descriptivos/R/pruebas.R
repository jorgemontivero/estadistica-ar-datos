# Las pruebas de comparación de la tabla 1.
#
# Cuál se usa no se elige a ojo: sale del tipo de variable, de cuántos grupos
# hay y de la forma de la distribución, con la misma regla que el árbol de
# decisión de estadistica.ar.
#
#     numérica, 2 grupos, simétrica    prueba t de Welch
#     numérica, 2 grupos, asimétrica   Mann-Whitney
#     numérica, 3 o más, simétrica     ANOVA de un factor
#     numérica, 3 o más, asimétrica    Kruskal-Wallis
#     categórica                       chi-cuadrado
#
# Las opciones están puestas a mano y no por omisión —Welch sí, corrección de
# continuidad no, corrección de Yates no— porque los valores por omisión de R y
# de SciPy no son los mismos, y sin fijarlas los dos idiomas darían números
# distintos.

SIN_VARIACION <- "Los valores no varían: no hay prueba que aplicar"

comparar_numerica <- function(grupos, forma) {
  if (length(grupos) < 2 || any(vapply(grupos, length, integer(1)) < 2)) {
    return(list(p = NULL, prueba = "", nota = "Algún grupo tiene menos de dos casos"))
  }
  # Sin variación no hay prueba: R falla y SciPy devuelve NaN. Mejor decirlo
  # que dejar que cada idioma haga lo suyo.
  sin_variar <- all(vapply(grupos, function(g) sd(g) == 0, logical(1)))
  if (sin_variar) return(list(p = NULL, prueba = "", nota = SIN_VARIACION))
  if (length(grupos) == 2) {
    if (forma == "asimétrica") {
      prueba <- suppressWarnings(wilcox.test(grupos[[1]], grupos[[2]], exact = FALSE,
                                             correct = FALSE))
      return(list(p = prueba$p.value, prueba = "Mann-Whitney", nota = ""))
    }
    prueba <- t.test(grupos[[1]], grupos[[2]], var.equal = FALSE)
    return(list(p = prueba$p.value, prueba = "t de Welch", nota = ""))
  }
  valores <- unlist(grupos)
  factor_grupo <- factor(rep(seq_along(grupos), vapply(grupos, length, integer(1))))
  if (forma == "asimétrica") {
    prueba <- kruskal.test(valores, factor_grupo)
    return(list(p = prueba$p.value, prueba = "Kruskal-Wallis", nota = ""))
  }
  prueba <- oneway.test(valores ~ factor_grupo, var.equal = TRUE)
  list(p = prueba$p.value, prueba = "ANOVA", nota = "")
}

comparar_categorica <- function(tabla) {
  filas <- tabla[rowSums(tabla) > 0, , drop = FALSE]
  if (nrow(filas) < 2 || ncol(filas) < 2) {
    return(list(p = NULL, prueba = "", nota = "No hay tabla que comparar"))
  }
  prueba <- suppressWarnings(chisq.test(filas, correct = FALSE))
  baja <- any(prueba$expected < 5)
  list(p = prueba$p.value, prueba = "Chi-cuadrado",
       nota = if (baja) "Alguna frecuencia esperada es menor que 5" else "")
}

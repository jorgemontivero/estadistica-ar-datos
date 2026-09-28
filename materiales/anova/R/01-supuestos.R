# Paso 1: los supuestos, celda por celda.
#
# Un ANOVA pide tres cosas: residuos normales dentro de cada celda, varianzas
# parecidas entre celdas y observaciones independientes. La tercera no se
# prueba —se garantiza con el diseño—; las otras dos sí, y este paso las mira
# antes de que se calcule ningún valor p.
#
# **La normalidad se mira por celda y no sobre todo junto.** Es un error
# frecuente y silencioso: si los grupos tienen medias distintas, la respuesta
# apilada sale bimodal o achatada y Shapiro-Wilk rechaza aunque cada celda sea
# perfectamente normal. Lo que el ANOVA supone normal es el residuo, no la
# respuesta.
#
# **Levene va con la mediana**, que es la variante de Brown-Forsythe: la
# versión con la media es sensible a la falta de normalidad, que es justo lo
# que suele venir con la heterocedasticidad. Es la misma que corre `calc-anova`
# en el sitio.

# Shapiro-Wilk dentro de cada celda.
#
# Con menos de tres casos no hay prueba que hacer, y con muchos casos la prueba
# rechaza por desviaciones que no le importan a nadie: las dos cosas salen
# escritas en la fila, no se esconden.
shapiro_por_celda <- function(grupos, alfa) {
  lapply(grupos, function(g) {
    n <- length(g$valores)
    if (n < 3 || length(unique(g$valores)) < 2) {
      return(list(celda = g$etiqueta, n = as.integer(n), w = NULL, p = NULL,
                  normal = NULL, por_que = "Hacen falta 3 casos distintos"))
    }
    s <- shapiro.test(g$valores)
    list(celda = g$etiqueta, n = as.integer(n),
         w = as.numeric(s$statistic), p = as.numeric(s$p.value),
         normal = as.numeric(s$p.value) >= alfa, por_que = "")
  })
}

# Levene con centro en la mediana, escrito a mano.
#
# Está escrito y no llamado porque `leveneTest` no viene con R base y
# `scipy.stats.levene` y la versión de R difieren en cómo tratan los grupos de
# un solo caso. La cuenta es un ANOVA de un factor sobre |x − mediana del
# grupo|, y no tiene ningún secreto.
levene <- function(grupos) {
  usables <- Filter(function(g) length(g$valores) > 0, grupos)
  k <- length(usables)
  if (k < 2) return(NULL)

  z <- lapply(usables, function(g) abs(g$valores - median(g$valores)))
  n <- sum(vapply(z, length, integer(1)))
  if (n - k < 1) return(NULL)

  medias_z <- vapply(z, mean, numeric(1))
  media_z <- sum(vapply(z, sum, numeric(1))) / n

  numerador <- sum(vapply(seq_along(z), function(i) {
    length(z[[i]]) * (medias_z[i] - media_z)^2
  }, numeric(1)))
  denominador <- sum(vapply(seq_along(z), function(i) {
    sum((z[[i]] - medias_z[i])^2)
  }, numeric(1)))
  if (denominador <= 0) return(NULL)

  w <- ((n - k) / (k - 1)) * (numerador / denominador)
  list(w = w, gl1 = as.integer(k - 1), gl2 = as.integer(n - k),
       p = pf(w, k - 1, n - k, lower.tail = FALSE))
}

calcular_supuestos <- function(grupos, parametros) {
  alfa <- 1 - parametros$confianza
  normalidad <- shapiro_por_celda(grupos, alfa)
  homogeneidad <- levene(grupos)

  # El veredicto que decide el paso siguiente.
  con_veredicto <- Filter(function(f) !is.null(f$normal), normalidad)
  todas_normales <- if (length(con_veredicto) == 0) NULL else
    all(vapply(con_veredicto, function(f) isTRUE(f$normal), logical(1)))
  varianzas_iguales <- if (is.null(homogeneidad)) NULL else homogeneidad$p >= alfa

  avisos <- list()
  if (length(con_veredicto) > 0 && !todas_normales) {
    cuales <- vapply(Filter(function(f) !isTRUE(f$normal), con_veredicto),
                     function(f) f$celda, character(1))
    avisos[[length(avisos) + 1]] <- list(
      donde = "normalidad",
      aviso = paste0("Shapiro-Wilk rechaza la normalidad en ", length(cuales), " de ",
                     length(con_veredicto), " celdas (", paste(cuales, collapse = ", "),
                     "). Con celdas de veinte casos o más el ANOVA aguanta bastante; con ",
                     "celdas chicas conviene Kruskal-Wallis, que este proyecto no trae."))
  }
  if (!is.null(varianzas_iguales) && !varianzas_iguales) {
    avisos[[length(avisos) + 1]] <- list(
      donde = "homogeneidad",
      aviso = paste0("Levene rechaza la igualdad de varianzas. El F clásico deja de ser ",
                     "confiable, sobre todo con celdas de tamaños distintos: la versión ",
                     "de Welch es la que corresponde, y está en la misma tabla."))
  }

  chicas <- vapply(Filter(function(f) f$n < 10, normalidad), function(f) f$celda,
                   character(1))
  if (length(chicas) > 0) {
    avisos[[length(avisos) + 1]] <- list(
      donde = "diseño",
      aviso = paste0("Hay ", length(chicas), " celdas con menos de diez casos (",
                     paste(chicas, collapse = ", "), "). Con celdas así de chicas las ",
                     "pruebas de supuestos casi no tienen potencia: que no rechacen no ",
                     "significa que el supuesto se cumpla."))
  }

  list(normalidad = normalidad, homogeneidad = homogeneidad,
       todas_normales = todas_normales, varianzas_iguales = varianzas_iguales,
       avisos = avisos)
}

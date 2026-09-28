# Paso 1: los supuestos, antes de la prueba y no después.
#
# Para cada variable numérica y cada variable de agrupamiento:
#
#     normalidad     Shapiro-Wilk dentro de cada grupo, que es donde el
#                    supuesto vive. Probarla sobre la variable entera,
#                    mezclando grupos que tienen medias distintas, es probar
#                    otra cosa.
#
#     homogeneidad   Levene con centro en la mediana —la versión de
#                    Brown y Forsythe, la robusta— entre los grupos.
#
# Para las categóricas, la frecuencia esperada más chica de la tabla: el
# supuesto del chi-cuadrado no es sobre las frecuencias observadas sino sobre
# las esperadas.
#
# El veredicto de normalidad no sale solo del valor p. Con menos de quince
# datos ninguna prueba de normalidad tiene potencia, así que no rechazar no
# dice nada; con más de trescientos rechazan desvíos tan chicos que no afectan
# a ninguna prueba t. Las dos cosas se informan, con la misma regla que usa la
# calculadora de normalidad del sitio.

SIN_POTENCIA <- "sin-potencia"
SIN_VARIACION <- "sin-variación"
NORMAL <- "normal"
NO_NORMAL <- "no-normal"
MINIMO_CON_POTENCIA <- 15
DEMASIADOS <- 300

# Tres cosas distintas, y ninguna es «pasó la prueba». Sin variación no hay
# distribución que evaluar; con menos de quince datos la prueba no tiene
# potencia y no rechazar no significa nada.
veredicto_normalidad <- function(x, p, alfa) {
  if (desvio(x) == 0) return(SIN_VARIACION)
  if (length(x) < MINIMO_CON_POTENCIA) return(SIN_POTENCIA)
  if (is.null(p) || p >= alfa) NORMAL else NO_NORMAL
}

# Shapiro-Wilk. Hace falta n ≥ 3, y con todos los valores iguales no hay nada
# que probar.
shapiro <- function(x) {
  if (length(x) < 3 || desvio(x) == 0) return(list(w = NULL, p = NULL))
  s <- shapiro.test(x)
  list(w = as.numeric(s$statistic), p = as.numeric(s$p.value))
}

# Levene con centro en la mediana: la versión de Brown y Forsythe.
#
# Es una ANOVA sobre las distancias absolutas de cada dato a la mediana de su
# grupo. Está escrita a mano y no tomada de una biblioteca porque R no la trae
# de fábrica: así las dos versiones calculan exactamente lo mismo.
levene <- function(grupos) {
  grupos <- grupos[vapply(grupos, function(g) length(g) >= 2, logical(1))]
  k <- length(grupos)
  if (k < 2) return(NULL)
  z <- lapply(grupos, function(g) abs(g - median(g)))
  n <- sum(vapply(z, length, integer(1)))
  if (n <= k) return(NULL)
  total <- mean(unlist(z))
  entre <- sum(vapply(z, function(g) length(g) * (mean(g) - total)^2, numeric(1)))
  dentro <- sum(vapply(z, function(g) sum((g - mean(g))^2), numeric(1)))
  if (dentro == 0) return(NULL)
  f <- (entre / (k - 1)) / (dentro / (n - k))
  list(f = f, gl1 = k - 1, gl2 = n - k, p = pf(f, k - 1, n - k, lower.tail = FALSE))
}

calcular_supuestos <- function(datos, variables, parametros) {
  alfa <- parametros$alfa
  factores <- which(variables$tipo == "grupo")
  numericas <- which(variables$tipo == "numerica")
  categoricas <- which(variables$tipo == "categorica")

  supuestos <- list()
  homogeneidad <- list()
  esperadas <- list()
  avisos <- list()

  anotar <- function(variable, factor, aviso) {
    avisos[[length(avisos) + 1]] <<- list(variable = variable, factor = factor, aviso = aviso)
  }

  for (fi in factores) {
    factor_nombre <- variables$nombre[fi]
    valores_factor <- columna(datos, factor_nombre)
    niveles <- ordenar(valores_factor[valores_factor != ""])

    for (vi in numericas) {
      por_grupo <- list()
      for (nivel in niveles) {
        x <- numeros(datos[valores_factor == nivel], variables$nombre[vi])
        if (length(x) < 2) next
        s <- shapiro(x)
        supuestos[[length(supuestos) + 1]] <- list(
          variable = variables$nombre[vi], etiqueta = variables$etiqueta[vi],
          factor = factor_nombre, grupo = nivel, n = as.integer(length(x)),
          media = mean(x), desvio = desvio(x), asimetria = asimetria(x),
          shapiro_w = s$w, shapiro_p = s$p,
          veredicto = veredicto_normalidad(x, s$p, alfa))
        por_grupo[[length(por_grupo) + 1]] <- x
        if (desvio(x) == 0) {
          anotar(variables$nombre[vi], factor_nombre,
                 paste0("En el grupo «", nivel, "» todos los valores son iguales: no hay ",
                        "distribución que evaluar ni prueba que aplicar."))
        } else if (length(x) < MINIMO_CON_POTENCIA) {
          anotar(variables$nombre[vi], factor_nombre,
                 paste0("En el grupo «", nivel, "» hay ", length(x), " datos: con menos de ",
                        MINIMO_CON_POTENCIA, " ninguna prueba de normalidad tiene potencia ",
                        "real, así que no rechazar acá no es evidencia de nada. La decisión ",
                        "hay que tomarla por el origen de los datos, no por el valor p."))
        } else if (length(x) > DEMASIADOS) {
          anotar(variables$nombre[vi], factor_nombre,
                 paste0("En el grupo «", nivel, "» hay ", length(x), " datos: con tantos, las ",
                        "pruebas de normalidad detectan desvíos tan chicos que no afectan a ",
                        "ninguna prueba t. Si rechaza, mirá el tamaño de la asimetría antes ",
                        "que el valor p."))
        }
      }

      lev <- levene(por_grupo)
      if (is.null(lev)) next
      homogeneas <- lev$p >= alfa
      homogeneidad[[length(homogeneidad) + 1]] <- list(
        variable = variables$nombre[vi], etiqueta = variables$etiqueta[vi],
        factor = factor_nombre, k = as.integer(length(por_grupo)),
        levene_f = lev$f, gl1 = as.integer(lev$gl1), gl2 = as.integer(lev$gl2),
        levene_p = lev$p, homogeneas = homogeneas,
        # Con dos grupos la prueba que corresponde es la de Welch, que no
        # supone varianzas iguales: Levene se informa, pero no decide nada.
        decide = length(por_grupo) > 2)
      if (length(por_grupo) == 2 && !homogeneas) {
        anotar(variables$nombre[vi], factor_nombre,
               paste0("Las varianzas no son homogéneas, pero con dos grupos eso no cambia la ",
                      "prueba: la de Welch no las supone iguales. Levene se informa para ",
                      "describir, no para decidir."))
      }
    }

    for (vi in categoricas) {
      todos <- columna(datos, variables$nombre[vi])
      categorias <- ordenar(todos[todos != ""])
      tabla <- lapply(categorias, function(categoria) {
        vapply(niveles, function(nivel) {
          sum(todos == categoria & valores_factor == nivel)
        }, numeric(1))
      })
      total <- sum(unlist(tabla))
      if (total == 0 || length(tabla) < 2 || length(niveles) < 2) next
      filas_suma <- vapply(tabla, sum, numeric(1))
      columnas_suma <- vapply(seq_along(niveles),
                              function(j) sum(vapply(tabla, function(f) f[j], numeric(1))),
                              numeric(1))
      minima <- min(outer(filas_suma, columnas_suma) / total)
      esperadas[[length(esperadas) + 1]] <- list(
        variable = variables$nombre[vi], etiqueta = variables$etiqueta[vi],
        factor = factor_nombre, filas = as.integer(length(tabla)),
        columnas = as.integer(length(niveles)), n = as.integer(total),
        esperada_minima = minima, todas_mayores_que_5 = minima >= 5)
      if (minima < 5) {
        cuanto <- gsub(".", ",", sprintf("%.2f", minima), fixed = TRUE)
        anotar(variables$nombre[vi], factor_nombre,
               paste0("La frecuencia esperada más chica de la tabla es ", cuanto, ". El ",
                      "chi-cuadrado pide que todas las esperadas lleguen a 5; con menos, su ",
                      "valor p no es confiable."))
      }
    }
  }

  list(supuestos = supuestos, homogeneidad = homogeneidad, esperadas = esperadas,
       avisos = avisos)
}

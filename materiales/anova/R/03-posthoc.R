# Paso 3: las comparaciones de a pares.
#
# El F contesta «¿hay alguna diferencia?». No contesta «¿entre cuáles?», y esa
# es la pregunta que casi siempre importa. Para eso están las comparaciones de
# a pares, y para eso hay que corregir: con k grupos son k(k−1)/2
# comparaciones, y si cada una se mira a 0,05 la probabilidad de encontrar al
# menos un falso positivo se dispara. Con seis grupos son quince comparaciones
# y esa probabilidad pasa de 0,05 a más de 0,50.
#
# **Se corren los cuatro métodos siempre, y también la prueba sin corregir.**
# No es indecisión: elegir el método después de ver cuál da significativo es
# exactamente la maniobra que las correcciones existen para impedir. Que estén
# los cinco en la misma tabla vuelve visible el costo de la multiplicidad y
# obliga a declarar cuál se usó.
#
#     sin corregir  la t de a pares, sin ningún ajuste. Está para que se vea
#                   cuánto cambia, no para informarla.
#     Tukey         el estándar para comparar TODOS los pares. Usa el rango
#                   studentizado, que es la distribución del mayor menos el
#                   menor, y por eso es más potente que Bonferroni sin perder
#                   el control del error.
#     Bonferroni    el más simple: multiplica cada p por la cantidad de
#                   comparaciones. Siempre válido, siempre conservador.
#     Holm          uniformemente más potente que Bonferroni, sin costo alguno.
#                   No hay ninguna razón para preferir Bonferroni sobre Holm
#                   salvo que el lector espere ver Bonferroni.
#     Scheffé       el más conservador de todos, pero vale para CUALQUIER
#                   contraste y no solo los de a pares. Si solo se van a mirar
#                   pares, es tirar potencia a la basura.
#
# La columna `cambia_entre_correcciones` marca los pares donde los cuatro
# métodos corregidos no coinciden en el veredicto. Ahí la conclusión no la
# deciden los datos: la decide el método.

METODOS <- c("sin corregir", "tukey", "bonferroni", "holm", "scheffe")

# Todos los pares, por los cinco caminos.
#
# Devuelve una fila por par y por método. El valor crítico de cada método
# depende solo de k, de los grados de libertad y de la confianza, así que se
# calcula una vez y no una por par: el de Tukey son dos cuadraturas anidadas
# por cada paso de una bisección, y dentro del doble bucle costaría cientos de
# veces más.
comparaciones <- function(resumenes, cm_dentro, gl_dentro, gl_entre, confianza) {
  k <- length(resumenes)
  if (k < 2 || !(cm_dentro > 0)) return(list())
  alfa <- 1 - confianza
  m <- k * (k - 1) / 2

  criticos <- list(
    "sin corregir" = qt(1 - alfa / 2, gl_dentro),
    "tukey" = rango_inv(confianza, k, gl_dentro) / sqrt(2),
    "bonferroni" = qt(1 - alfa / (2 * m), gl_dentro),
    # Holm no tiene un intervalo de forma cerrada, así que se deja el de
    # Bonferroni: es el más conservador y contiene al de Holm.
    "holm" = qt(1 - alfa / (2 * m), gl_dentro),
    "scheffe" = sqrt(gl_entre * qf(confianza, gl_entre, gl_dentro)))

  pares <- list()
  for (i in seq_len(k - 1)) {
    for (j in (i + 1):k) {
      a <- resumenes[[i]]
      b <- resumenes[[j]]
      diferencia <- a$media - b$media
      # Error estándar de la diferencia, con la varianza combinada del ANOVA.
      ee <- sqrt(cm_dentro * (1 / a$n + 1 / b$n))
      t <- diferencia / ee
      p_crudo <- 2 * pt(abs(t), gl_dentro, lower.tail = FALSE)

      for (metodo in METODOS) {
        if (metodo == "tukey") {
          # Tukey trabaja con la diferencia sobre el error estándar de UNA
          # media, que es el de la diferencia dividido por raíz de dos.
          estadistico <- abs(diferencia) / (ee / sqrt(2))
          p <- rango_cola(estadistico, k, gl_dentro)
        } else if (metodo == "scheffe") {
          estadistico <- diferencia^2 / (ee^2 * gl_entre)
          p <- pf(estadistico, gl_entre, gl_dentro, lower.tail = FALSE)
        } else if (metodo == "bonferroni") {
          estadistico <- t
          p <- min(1, p_crudo * m)
        } else {
          # «sin corregir» y «holm» arrancan del mismo p; Holm se ajusta
          # después, cuando están todos y se pueden ordenar.
          estadistico <- t
          p <- p_crudo
        }

        margen <- criticos[[metodo]] * ee
        pares[[length(pares) + 1]] <- list(
          a = a$grupo, b = b$grupo, metodo = metodo,
          diferencia = diferencia, error_estandar = ee,
          estadistico = estadistico, p_sin_corregir = p_crudo, p = p,
          inferior = diferencia - margen, superior = diferencia + margen,
          significativa = p < alfa)
      }
    }
  }

  # Holm: se ordenan los p de menor a mayor y al i-ésimo se lo multiplica por
  # (m − i), no por m. Después se fuerza la monotonía, para que un p ajustado
  # nunca sea menor que el anterior.
  cuales <- which(vapply(pares, function(f) f$metodo == "holm", logical(1)))
  orden <- cuales[order(vapply(pares[cuales], function(f) f$p_sin_corregir, numeric(1)),
                        vapply(pares[cuales], function(f) f$a, character(1)),
                        vapply(pares[cuales], function(f) f$b, character(1)),
                        method = "radix")]
  maximo <- 0
  for (puesto in seq_along(orden)) {
    indice <- orden[puesto]
    ajustado <- min(1, pares[[indice]]$p_sin_corregir * (m - puesto + 1))
    maximo <- max(maximo, ajustado)
    pares[[indice]]$p <- maximo
    pares[[indice]]$significativa <- maximo < alfa
  }

  # Y la marca por par: dónde los cuatro métodos corregidos no coinciden.
  claves <- vapply(pares, function(f) paste(f$a, f$b, sep = "\u0001"), character(1))
  corregidos <- vapply(pares, function(f) f$metodo != "sin corregir", logical(1))
  for (i in seq_along(pares)) {
    mismos <- claves == claves[i] & corregidos
    veredictos <- unique(vapply(pares[mismos], function(f) f$significativa, logical(1)))
    pares[[i]]$cambia_entre_correcciones <- length(veredictos) > 1
  }

  pares
}

# `sobre` dice qué se está comparando, y va escrito en la salida.
#
# Con dos factores se comparan las **celdas** y no los márgenes. Es lo que
# corresponde cuando la interacción manda: comparar el promedio de un factor a
# través de niveles donde el efecto es distinto mezcla cosas que no se pueden
# mezclar.
calcular_posthoc <- function(tabla_para_post_hoc, parametros, sobre) {
  if (is.null(tabla_para_post_hoc)) {
    return(list(pares = list(), avisos = list(), sobre = sobre, cuantas = 0L))
  }

  pares <- comparaciones(tabla_para_post_hoc$resumenes, tabla_para_post_hoc$cm_dentro,
                         tabla_para_post_hoc$gl_dentro, tabla_para_post_hoc$gl_entre,
                         parametros$confianza)

  k <- tabla_para_post_hoc$k
  m <- as.integer(k * (k - 1) / 2)
  avisos <- list()

  discrepan <- ordenar(vapply(Filter(function(f) isTRUE(f$cambia_entre_correcciones) &&
                                       f$metodo == "tukey", pares),
                              function(f) paste(f$a, f$b, sep = " vs "), character(1)))
  if (length(discrepan) > 0) {
    avisos[[length(avisos) + 1]] <- list(
      donde = "post hoc",
      aviso = paste0("En ", length(discrepan), " de las ", m, " comparaciones los ",
                     "cuatro métodos no coinciden (", paste(discrepan, collapse = "; "),
                     "). Ahí la conclusión la decide la corrección elegida y no los ",
                     "datos: hay que declarar cuál se usó y por qué, y la respuesta ",
                     "honesta es que está en el borde."))
  }

  cuantos <- function(metodo) {
    sum(vapply(pares, function(f) f$metodo == metodo && isTRUE(f$significativa), logical(1)))
  }
  sin_corregir <- cuantos("sin corregir")
  con_tukey <- cuantos("tukey")
  if (sin_corregir > con_tukey) {
    avisos[[length(avisos) + 1]] <- list(
      donde = "post hoc",
      aviso = paste0("Sin corregir darían ", sin_corregir, " pares significativos y con ",
                     "Tukey quedan ", con_tukey, ". Esa diferencia es el precio de haber ",
                     "hecho ", m, " comparaciones, y no es opcional: sin pagarlo, la ",
                     "probabilidad de encontrar al menos un falso positivo no es 5 % sino ",
                     "mucho más."))
  }

  alfa <- 1 - parametros$confianza
  if (tabla_para_post_hoc$p >= alfa && con_tukey > 0) {
    avisos[[length(avisos) + 1]] <- list(
      donde = "post hoc",
      aviso = paste0("El ANOVA no rechaza y sin embargo hay pares significativos en el ",
                     "post hoc. No es una contradicción —las dos pruebas no miden lo ",
                     "mismo—, pero informar solo el par sin decir que el F no dio sería ",
                     "contar media historia."))
  }
  if (tabla_para_post_hoc$p < alfa && con_tukey == 0) {
    avisos[[length(avisos) + 1]] <- list(
      donde = "post hoc",
      aviso = paste0("El ANOVA rechaza y ningún par sobrevive a Tukey. Pasa, y no es un ",
                     "error: el F junta la información de todos los grupos y puede ",
                     "detectar un patrón que ninguna comparación de a dos alcanza a ",
                     "mostrar por separado."))
  }

  list(pares = pares, avisos = avisos, sobre = sobre, cuantas = m)
}

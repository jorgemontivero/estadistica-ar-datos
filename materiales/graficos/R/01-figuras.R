# Las cuatro figuras, cada una con su tabla.
#
#     barras-<var>        una categórica, ordenada de mayor a menor
#     histograma-<var>    una numérica, con las clases de la regla del sitio
#     caja-<var>          una numérica por grupo, con los atípicos a la vista
#     dispersion-<x>-<y>  dos numéricas, con la recta de mínimos cuadrados
#
# No hay tortas. Con más de dos o tres categorías, comparar ángulos es más
# difícil que comparar largos, y la torta obliga a leer las etiquetas para
# entender lo que unas barras dicen de un vistazo.

barras <- function(datos, variable, etiqueta) {
  valores <- columna(datos, variable)
  valores <- valores[valores != ""]
  conteo <- table(valores)
  # De mayor a menor; a igual cantidad, alfabético.
  orden <- order(-as.integer(conteo), names(conteo))
  categorias <- names(conteo)[orden]
  cuantos <- as.integer(conteo)[orden]
  tabla <- lapply(seq_along(categorias), function(i) {
    list(categoria = categorias[i], n = cuantos[i], pct = cuantos[i] / length(valores) * 100)
  })
  nombre <- paste0("barras-", variable)
  escribir_csv(tabla, nombre, c("categoria", "n", "pct"))

  marco <- data.frame(categoria = factor(categorias, levels = categorias), n = cuantos,
                      pct = cuantos / length(valores) * 100)
  figura <- ggplot(marco, aes(x = categoria, y = n)) +
    geom_col(fill = PALETA[["acento"]], width = 0.62) +
    geom_text(aes(label = sub(".", ",", sprintf("%.1f %%", pct), fixed = TRUE)),
              vjust = -0.4, size = 3.2, colour = PALETA[["gris"]]) +
    scale_y_continuous(labels = eje_castellano) +
    labs(title = etiqueta, x = NULL, y = "Casos") +
    tema_sitio()
  guardar(figura, nombre)
  nombre
}

histograma <- function(datos, variable, etiqueta) {
  x <- numeros(columna(datos, variable))
  k <- clases_sugeridas(x)
  clases <- agrupar(x, k)
  nombre <- paste0("histograma-", variable)
  escribir_csv(clases, nombre, c("clase", "desde", "hasta", "marca", "n", "pct"))

  marco <- data.frame(
    marca = vapply(clases, function(c) c$marca, numeric(1)),
    n = vapply(clases, function(c) c$n, integer(1)),
    ancho = vapply(clases, function(c) c$hasta - c$desde, numeric(1))
  )
  figura <- ggplot(marco, aes(x = marca, y = n, width = ancho)) +
    geom_col(fill = PALETA[["acento"]], colour = PALETA[["papel"]], linewidth = 0.3) +
    scale_y_continuous(labels = eje_castellano) +
    scale_x_continuous(labels = eje_castellano) +
    labs(title = etiqueta, x = etiqueta, y = "Casos") +
    tema_sitio()
  guardar(figura, nombre)
  nombre
}

cajas <- function(datos, variable, etiqueta, grupo, etiqueta_grupo) {
  valores_grupo <- columna(datos, grupo)
  niveles <- sort(unique(valores_grupo[valores_grupo != ""]))
  tabla <- list()
  marco <- data.frame(grupo = character(), valor = numeric(), stringsAsFactors = FALSE)
  for (nivel in niveles) {
    valores <- numeros(columna(datos[valores_grupo == nivel], variable))
    if (length(valores) == 0) next
    c <- caja(valores)
    tabla[[length(tabla) + 1]] <- list(grupo = nivel, n = as.integer(c$n), minimo = c$minimo,
                                       q1 = c$q1, mediana = c$mediana, q3 = c$q3,
                                       maximo = c$maximo,
                                       atipicos = as.integer(length(c$atipicos)))
    marco <- rbind(marco, data.frame(grupo = nivel, valor = valores, stringsAsFactors = FALSE))
  }
  nombre <- paste0("caja-", variable)
  escribir_csv(tabla, nombre, c("grupo", "n", "minimo", "q1", "mediana", "q3", "maximo",
                                "atipicos"))

  figura <- ggplot(marco, aes(x = grupo, y = valor)) +
    geom_boxplot(fill = PALETA[["acento"]], colour = PALETA[["acento_fuerte"]],
                 outlier.colour = PALETA[["alerta"]], outlier.size = 1,
                 width = ANCHO_CAJA) +
    # La mediana en blanco, como en la versión de Python: dentro de una caja
    # llena, una línea oscura casi no se ve.
    stat_summary(fun = median, geom = "crossbar", width = ANCHO_CAJA, linewidth = 0.3,
                 colour = PALETA[["papel"]]) +
    scale_y_continuous(labels = eje_castellano) +
    labs(title = paste0(etiqueta, " según ", tolower(etiqueta_grupo)), x = NULL, y = etiqueta) +
    tema_sitio()
  guardar(figura, nombre)
  nombre
}

dispersion <- function(datos, x_var, y_var, x_etiqueta, y_etiqueta) {
  x_txt <- columna(datos, x_var)
  y_txt <- columna(datos, y_var)
  completos <- x_txt != "" & y_txt != ""
  x <- suppressWarnings(as.numeric(x_txt[completos]))
  y <- suppressWarnings(as.numeric(y_txt[completos]))
  validos <- !is.na(x) & !is.na(y)
  x <- x[validos]
  y <- y[validos]
  ajuste <- recta(x, y)
  nombre <- paste0("dispersion-", x_var, "-", y_var)
  escribir_csv(list(list(n = as.integer(ajuste$n), pendiente = ajuste$pendiente,
                         ordenada = ajuste$ordenada, r = ajuste$r)),
               nombre, c("n", "pendiente", "ordenada", "r"))

  marco <- data.frame(x = x, y = y)
  figura <- ggplot(marco, aes(x = x, y = y)) +
    # Sin transparencia: con alpha el color deja de ser el de la paleta, y una
    # figura que no se puede comprobar es una figura que no se puede confiar.
    geom_point(colour = PALETA[["acento"]], size = 1.1) +
    geom_abline(slope = ajuste$pendiente, intercept = ajuste$ordenada,
                colour = PALETA[["alerta"]], linewidth = 0.6) +
    scale_y_continuous(labels = eje_castellano) +
    scale_x_continuous(labels = eje_castellano) +
    labs(title = paste0(y_etiqueta, " según ", tolower(x_etiqueta)),
         x = x_etiqueta, y = y_etiqueta) +
    tema_sitio()
  guardar(figura, nombre)
  nombre
}

dibujar <- function(datos, variables) {
  es_grupo <- variables$tipo == "grupo"
  grupo <- if (any(es_grupo)) which(es_grupo)[1] else NULL
  numericas <- which(variables$tipo == "numerica")
  hechas <- character(0)
  for (k in which(variables$tipo == "categorica")) {
    etiqueta <- if (variables$etiqueta[k] != "") variables$etiqueta[k] else variables$nombre[k]
    hechas <- c(hechas, barras(datos, variables$nombre[k], etiqueta))
  }
  for (k in numericas) {
    etiqueta <- if (variables$etiqueta[k] != "") variables$etiqueta[k] else variables$nombre[k]
    hechas <- c(hechas, histograma(datos, variables$nombre[k], etiqueta))
    if (!is.null(grupo)) {
      etiqueta_grupo <- if (variables$etiqueta[grupo] != "") variables$etiqueta[grupo] else
        variables$nombre[grupo]
      hechas <- c(hechas, cajas(datos, variables$nombre[k], etiqueta,
                                variables$nombre[grupo], etiqueta_grupo))
    }
  }
  if (length(numericas) >= 2) {
    primeras <- numericas[1:2]
    etiquetas <- vapply(primeras, function(k) {
      if (variables$etiqueta[k] != "") variables$etiqueta[k] else variables$nombre[k]
    }, character(1))
    hechas <- c(hechas, dispersion(datos, variables$nombre[primeras[1]],
                                   variables$nombre[primeras[2]], etiquetas[1], etiquetas[2]))
  }
  hechas
}

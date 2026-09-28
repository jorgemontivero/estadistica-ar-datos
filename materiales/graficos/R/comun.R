# Los colores, el estilo y las cuentas que hay detrás de cada figura.
#
# Dos decisiones que valen para todo el proyecto:
#
#   · Cada figura se guarda con su tabla. El PNG es para pegar; el CSV de al
#     lado es para que cualquiera pueda revisar el número que la figura dibuja.
#     Una figura sin su tabla es una afirmación sin fuente.
#
#   · Las clases del histograma salen de la regla de Freedman y Diaconis,
#     acotada entre 4 y 25, que es la misma que usa la calculadora de
#     frecuencias del sitio. Así la figura y la tabla del informe no se
#     contradicen.

library(ggplot2)

# Los colores del sitio. El acento es el que lleva el dato; el resto es
# andamiaje y va en grises, para que el ojo no compita con la información.
PALETA <- c(acento = "#0e6b60", acento_fuerte = "#0a4f47", aviso = "#8a5a06",
            alerta = "#9e382b", gris = "#5b626a", papel = "#fbfaf7",
            tinta = "#191c1f", borde = "#cbc5b9")
SERIES <- unname(PALETA[c("acento", "aviso", "alerta", "gris", "acento_fuerte")])
ANCHO <- 7.2
ALTO <- 4.0
DPI <- 300  # 2160 × 1200 píxeles
ANCHO_CAJA <- 0.4  # de lo que le toca a cada grupo, igual en los dos idiomas

tema_sitio <- function() {
  theme_minimal(base_size = 10) +
    theme(
      plot.background = element_rect(fill = PALETA[["papel"]], colour = NA),
      panel.background = element_rect(fill = PALETA[["papel"]], colour = NA),
      panel.grid.major.x = element_blank(),
      panel.grid.minor = element_blank(),
      panel.grid.major.y = element_line(colour = PALETA[["borde"]], linewidth = 0.3),
      axis.line.x = element_line(colour = PALETA[["borde"]], linewidth = 0.4),
      axis.ticks = element_blank(),
      axis.text = element_text(colour = PALETA[["gris"]], size = 9),
      axis.title = element_text(colour = PALETA[["tinta"]], size = 10),
      plot.title = element_text(colour = PALETA[["tinta"]], size = 12, hjust = 0),
      plot.title.position = "plot"
    )
}

# Los números del eje como se escriben acá: 1.500.000 y no 1.5e6. matplotlib
# abrevia los ejes grandes con notación científica y R los escribe enteros: sin
# esto, la misma figura sale distinta en cada idioma.
eje_castellano <- function(valores) {
  vapply(valores, function(v) {
    if (is.na(v)) return("")
    entero <- format(floor(abs(v)), scientific = FALSE, trim = TRUE)
    decimales <- abs(v) - floor(abs(v))
    grupos <- character(0)
    while (nchar(entero) > 3) {
      grupos <- c(substring(entero, nchar(entero) - 2), grupos)
      entero <- substring(entero, 1, nchar(entero) - 3)
    }
    texto <- paste(c(entero, grupos), collapse = ".")
    if (decimales > 0) {
      resto <- sub("^0[.]", "", sub("0+$", "", sprintf("%.2f", decimales)))
      texto <- paste0(texto, ",", resto)
    }
    paste0(if (v < 0) "-" else "", texto)
  }, character(1))
}

guardar <- function(figura, nombre) {
  dir.create("salidas/figuras", showWarnings = FALSE, recursive = TRUE)
  ggsave(file.path("salidas/figuras", paste0(nombre, ".png")), figura,
         width = ANCHO, height = ALTO, dpi = DPI, bg = PALETA[["papel"]])
}

# ------------------------------------------------------------------ lectura
limpiar_texto <- function(x) {
  x[is.na(x)] <- ""
  trimws(gsub("[[:space:]]+", " ", x))
}

leer_csv <- function(ruta) {
  con <- file(ruta, open = "r", encoding = "UTF-8")
  lineas <- readLines(con, warn = FALSE)
  close(con)
  lineas[1] <- sub(paste0("^", intToUtf8(65279)), "", lineas[1])
  lineas <- lineas[trimws(lineas) != ""]
  columnas <- limpiar_texto(strsplit(lineas[1], ",", fixed = TRUE)[[1]])
  datos <- lapply(lineas[-1], function(linea) {
    partes <- strsplit(linea, ",", fixed = TRUE)[[1]]
    partes <- c(partes, rep("", length(columnas)))[seq_along(columnas)]
    fila <- as.list(limpiar_texto(partes))
    names(fila) <- columnas
    fila
  })
  datos
}

columna <- function(filas, nombre) {
  vapply(filas, function(f) if (is.null(f[[nombre]])) "" else f[[nombre]], character(1))
}

numeros <- function(textos) {
  v <- suppressWarnings(as.numeric(limpiar_texto(textos)))
  v[!is.na(v)]
}

# --------------------------------------------------------------- las cuentas
cuantil <- function(x, p) as.numeric(quantile(x, probs = p, type = 7, names = FALSE))

# La regla de Freedman y Diaconis, entre 4 y 25, como en el sitio.
clases_sugeridas <- function(x) {
  n <- length(x)
  rango <- max(x) - min(x)
  ric <- cuantil(x, 0.75) - cuantil(x, 0.25)
  if (ric > 0 && rango > 0) {
    h <- 2 * ric / n^(1 / 3)
    if (h > 0) return(min(25, max(4, ceiling(rango / h))))
  }
  min(25, max(4, ceiling(sqrt(n))))
}

# Las clases, como las arma la calculadora del sitio: todas del mismo ancho,
# cada una incluye su límite inferior y no el superior, salvo la última, que
# incluye el máximo.
agrupar <- function(x, k) {
  minimo <- min(x)
  maximo <- max(x)
  ancho <- if (maximo > minimo) (maximo - minimo) / k else 1
  filas <- list()
  for (i in seq_len(k)) {
    desde <- minimo + (i - 1) * ancho
    hasta <- if (i == k) maximo else desde + ancho
    ni <- if (i == k) sum(x >= desde & x <= hasta) else sum(x >= desde & x < hasta)
    filas[[i]] <- list(clase = i, desde = desde, hasta = hasta,
                       marca = (desde + hasta) / 2, n = as.integer(ni),
                       pct = ni / length(x) * 100)
  }
  filas
}

# Los cinco números de Tukey y los atípicos, con el criterio de 1,5 RIC.
caja <- function(x) {
  q1 <- cuantil(x, 0.25)
  mediana <- cuantil(x, 0.5)
  q3 <- cuantil(x, 0.75)
  ric <- q3 - q1
  dentro <- x[x >= q1 - 1.5 * ric & x <= q3 + 1.5 * ric]
  atipicos <- sort(x[x < q1 - 1.5 * ric | x > q3 + 1.5 * ric])
  list(n = length(x), minimo = if (length(dentro)) min(dentro) else min(x), q1 = q1,
       mediana = mediana, q3 = q3, maximo = if (length(dentro)) max(dentro) else max(x),
       atipicos = atipicos)
}

# La recta de mínimos cuadrados y el coeficiente de correlación.
recta <- function(x, y) {
  mx <- mean(x)
  my <- mean(y)
  sxy <- sum((x - mx) * (y - my))
  sxx <- sum((x - mx)^2)
  syy <- sum((y - my)^2)
  pendiente <- if (sxx > 0) sxy / sxx else 0
  list(n = length(x), pendiente = pendiente, ordenada = my - pendiente * mx,
       r = if (sxx > 0 && syy > 0) sxy / sqrt(sxx * syy) else NA_real_)
}

# ------------------------------------------------------------------ escribir
formatear <- function(x) {
  if (is.null(x)) return("")
  if (is.integer(x)) return(if (is.na(x)) "" else sprintf("%d", x))
  if (is.numeric(x)) return(if (is.na(x)) "" else sprintf("%.6f", x))
  if (is.na(x)) "" else as.character(x)
}

escribir_csv <- function(filas, nombre, columnas) {
  dir.create("salidas/figuras", showWarnings = FALSE, recursive = TRUE)
  lineas <- paste(columnas, collapse = ",")
  for (fila in filas) {
    celdas <- vapply(columnas, function(c) formatear(fila[[c]]), character(1))
    lineas <- c(lineas, paste(celdas, collapse = ","))
  }
  con <- file(file.path("salidas/figuras", paste0(nombre, ".csv")), open = "w",
              encoding = "UTF-8")
  on.exit(close(con))
  writeLines(lineas, con, sep = "\n")
}

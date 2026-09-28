# Lo que comparten los dos pasos: leer, calcular y escribir.
#
# Las estadísticas están escritas acá, con la misma definición que usa el
# sitio: los cuartiles por interpolación lineal (el tipo 7, el que trae R por
# omisión y el que usa Excel), y la asimetría con la corrección por tamaño de
# muestra que usan SKEW de Excel y `e1071::skewness` con `type = 2`.
#
# Los números se escriben con seis decimales y los conteos como enteros, así
# los archivos de R y los de Python salen idénticos byte a byte.

limpiar_texto <- function(x) {
  x[is.na(x)] <- ""
  trimws(gsub("[[:space:]]+", " ", x))
}

leer_csv <- function(ruta) {
  con <- file(ruta, open = "r", encoding = "UTF-8")
  lineas <- readLines(con, warn = FALSE)
  close(con)
  bom <- intToUtf8(65279)
  lineas[1] <- sub(paste0("^", bom), "", lineas[1])
  lineas <- lineas[trimws(lineas) != ""]
  columnas <- limpiar_texto(strsplit(lineas[1], ",", fixed = TRUE)[[1]])
  filas <- lapply(lineas[-1], function(linea) {
    partes <- strsplit(linea, ",", fixed = TRUE)[[1]]
    partes <- c(partes, rep("", length(columnas)))[seq_along(columnas)]
    fila <- as.list(limpiar_texto(partes))
    names(fila) <- columnas
    fila
  })
  filas
}

columna <- function(filas, nombre) {
  vapply(filas, function(f) if (is.null(f[[nombre]])) "" else f[[nombre]], character(1))
}

numero <- function(x) {
  x <- limpiar_texto(x)
  if (x == "") return(NULL)
  v <- suppressWarnings(as.numeric(x))
  if (is.na(v)) NULL else v
}

numeros <- function(textos) {
  v <- suppressWarnings(as.numeric(limpiar_texto(textos)))
  v[!is.na(v)]
}

# ---------------------------------------------------------- estadísticas
cuantil <- function(x, p) as.numeric(quantile(x, probs = p, type = 7, names = FALSE))

# La asimetría corregida por tamaño de muestra, como SKEW de Excel.
asimetria <- function(x) {
  n <- length(x)
  if (n < 3) return(NULL)
  s <- sd(x)
  if (!(s > 0)) return(NULL)
  n / ((n - 1) * (n - 2)) * sum(((x - mean(x)) / s)^3)
}

descriptivos <- function(x) {
  n <- length(x)
  if (n == 0) return(list(n = 0L))
  asim <- asimetria(x)
  list(
    n = as.integer(n),
    media = mean(x),
    desvio = if (n >= 2) sd(x) else NULL,
    minimo = min(x),
    q1 = cuantil(x, 0.25),
    mediana = cuantil(x, 0.5),
    q3 = cuantil(x, 0.75),
    maximo = max(x),
    asimetria = asim,
    # La regla del sitio: con |asimetría| > 1 se informa la mediana.
    forma = if (!is.null(asim) && abs(asim) > 1) "asimétrica" else "simétrica"
  )
}

# ------------------------------------------------------------------ escribir
formatear <- function(x) {
  if (is.null(x)) return("")
  if (is.logical(x)) return(if (is.na(x)) "" else if (x) "Sí" else "No")
  if (is.integer(x)) return(if (is.na(x)) "" else sprintf("%d", x))
  if (is.numeric(x)) return(if (is.na(x)) "" else sprintf("%.6f", x))
  if (is.na(x)) "" else as.character(x)
}

entrecomillar <- function(x) {
  necesita <- grepl('[,"\n]', x)
  ifelse(necesita, paste0('"', gsub('"', '""', x, fixed = TRUE), '"'), x)
}

escribir_csv <- function(filas, ruta, columnas) {
  dir.create(dirname(ruta), showWarnings = FALSE, recursive = TRUE)
  lineas <- paste(entrecomillar(columnas), collapse = ",")
  for (fila in filas) {
    celdas <- vapply(columnas, function(c) entrecomillar(formatear(fila[[c]])), character(1))
    lineas <- c(lineas, paste(celdas, collapse = ","))
  }
  con <- file(ruta, open = "w", encoding = "UTF-8")
  on.exit(close(con))
  writeLines(lineas, con, sep = "\n")
}

escribir_texto <- function(lineas, ruta) {
  dir.create(dirname(ruta), showWarnings = FALSE, recursive = TRUE)
  con <- file(ruta, open = "w", encoding = "UTF-8")
  on.exit(close(con))
  writeLines(lineas, con, sep = "\n")
}

# ------------------------------------------- cómo se escriben los números
# Uno o dos decimales según la escala. Una media de 41,3 con dos decimales
# finge una precisión que no hay; una de 0,42 con uno se queda corta.
decimales_de <- function(valor) if (abs(valor) >= 10) 1 else 2

coma <- function(texto) gsub(".", ",", texto, fixed = TRUE)

# El número como se escribe en un informe en castellano: miles con punto y
# decimales con coma. Un ingreso de 425282,9 se lee mal; 425.282,9 no.
numero_texto <- function(valor, decimales) {
  partes <- strsplit(sprintf(paste0("%.", decimales, "f"), abs(valor)), ".", fixed = TRUE)[[1]]
  entero <- partes[1]
  grupos <- character(0)
  while (nchar(entero) > 3) {
    grupos <- c(substring(entero, nchar(entero) - 2), grupos)
    entero <- substring(entero, 1, nchar(entero) - 3)
  }
  texto <- paste(c(entero, grupos), collapse = ".")
  if (decimales > 0) texto <- paste0(texto, ",", partes[2])
  paste0(if (valor < 0) "-" else "", texto)
}

p_texto <- function(p) {
  if (is.null(p) || is.na(p)) return("")
  if (p < 0.001) "< 0,001" else coma(sprintf("%.3f", p))
}

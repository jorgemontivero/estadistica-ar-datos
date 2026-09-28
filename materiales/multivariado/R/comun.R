# Lo que comparten los cuatro pasos: leer, tipificar, escribir.
#
# Los números se escriben con seis decimales, redondeados a diez dígitos
# significativos, así los archivos de R y los de Python salen idénticos byte a
# byte.
#
# Una advertencia sobre las sumas. Todo el núcleo numérico de este proyecto suma
# con `suma`, que es un bucle en orden fijo, y no con `sum`. No es por precisión
# —con veinticuatro filas cualquiera de las dos alcanza y sobra— sino por
# igualdad: `sum` de R acumula en long double y Python no tiene nada
# equivalente, y de ese último bit dependen los signos que devuelve la
# descomposición. Con sumas comunes en el mismo orden, los dos idiomas hacen
# exactamente las mismas operaciones de punto flotante y el proyecto entero sale
# **idéntico bit a bit**, no solo redondeado a diez dígitos.

limpiar_texto <- function(x) {
  x[is.na(x)] <- ""
  trimws(gsub("[[:space:]]+", " ", x))
}

# ------------------------------------------------------------------ leer
leer_csv <- function(ruta) {
  con <- file(ruta, open = "r", encoding = "UTF-8")
  lineas <- readLines(con, warn = FALSE)
  close(con)
  # Declarar la codificación no es un detalle: sin esto las cadenas quedan
  # marcadas como «unknown» y `sort(method = "radix")` se niega a ordenarlas en
  # cuanto aparece una tilde, que en una lista de provincias pasa enseguida.
  Encoding(lineas) <- "UTF-8"
  lineas[1] <- sub(paste0("^", intToUtf8(65279)), "", lineas[1])
  lineas <- lineas[trimws(lineas) != ""]
  columnas <- limpiar_texto(strsplit(lineas[1], ",", fixed = TRUE)[[1]])
  lapply(lineas[-1], function(linea) {
    partes <- strsplit(linea, ",", fixed = TRUE)[[1]]
    partes <- c(partes, rep("", length(columnas)))[seq_along(columnas)]
    fila <- as.list(limpiar_texto(partes))
    names(fila) <- columnas
    fila
  })
}

numero <- function(x) {
  x <- limpiar_texto(x)
  if (length(x) == 0 || x == "") return(NULL)
  v <- suppressWarnings(as.numeric(x))
  if (is.na(v)) NULL else v
}

# Qué archivo, cuántos componentes y cuántos grupos, declarado en un archivo.
leer_parametros <- function(ruta) {
  filas <- leer_csv(ruta)
  claves <- vapply(filas, function(f) f$clave, character(1))
  valores <- vapply(filas, function(f) f$valor, character(1))
  texto <- function(clave, por_omision = "") {
    i <- which(claves == clave)
    v <- if (length(i) == 0) "" else limpiar_texto(valores[i[1]])
    if (v == "") por_omision else v
  }
  entero <- function(clave, por_omision) {
    v <- numero(texto(clave, ""))
    if (is.null(v)) por_omision else as.integer(v)
  }
  confianza <- numero(texto("confianza", "0.95"))
  if (is.null(confianza)) confianza <- 0.95

  parametros <- list(
    datos = texto("datos", "datos/indicadores.csv"),
    tabla = texto("tabla", "datos/educacion.csv"),
    unidad = texto("unidad", "jurisdiccion"),
    componentes = entero("componentes", 3L),
    conglomerados = entero("conglomerados", 4L),
    enlace = texto("enlace", "ward"),
    ejes = entero("ejes", 2L),
    confianza = confianza
  )
  if (parametros$componentes < 1) {
    stop("«componentes» tiene que ser al menos 1.", call. = FALSE)
  }
  if (parametros$conglomerados < 2) {
    stop("«conglomerados» tiene que ser al menos 2.", call. = FALSE)
  }
  if (parametros$ejes < 1) stop("«ejes» tiene que ser al menos 1.", call. = FALSE)
  parametros
}

# Una tabla de «etiqueta + números» en una matriz, con sus nombres.
#
# Devuelve las filas en el orden del archivo. **El orden del archivo es el orden
# del proyecto**: no se reordena por nombre, porque las distancias y las
# fusiones se identifican por posición y reordenar cambiaría los empates.
leer_matriz <- function(ruta, clave_unidad) {
  filas <- leer_csv(ruta)
  if (length(filas) == 0) {
    stop(paste0(ruta, " no tiene ninguna fila."), call. = FALSE)
  }
  if (!(clave_unidad %in% names(filas[[1]]))) {
    stop(paste0("A ", ruta, " le falta la columna «", clave_unidad, "»."),
         call. = FALSE)
  }
  columnas <- setdiff(names(filas[[1]]), clave_unidad)
  if (length(columnas) == 0) {
    stop(paste0(ruta, " no tiene ninguna columna de números."), call. = FALSE)
  }
  unidades <- character(0)
  datos <- matrix(0, nrow = length(filas), ncol = length(columnas))
  for (i in seq_along(filas)) {
    nombre <- filas[[i]][[clave_unidad]]
    if (nombre %in% unidades) {
      stop(paste0("«", nombre, "» aparece dos veces en ", ruta, "."), call. = FALSE)
    }
    unidades <- c(unidades, nombre)
    for (j in seq_along(columnas)) {
      v <- numero(filas[[i]][[columnas[j]]])
      if (is.null(v)) {
        stop(paste0("«", nombre, "», columna «", columnas[j], "»: «",
                    filas[[i]][[columnas[j]]], "» no es un número. Este proyecto no ",
                    "imputa faltantes: una fila incompleta no se puede proyectar ni ",
                    "agrupar."), call. = FALSE)
      }
      datos[i, j] <- v
    }
  }
  list(unidades = unidades, columnas = columnas, datos = datos)
}

ordenar <- function(x) sort(unique(enc2utf8(x)), method = "radix")

# ------------------------------------------------------------ estadística
# La suma en el orden en que viene, sin compensar.
#
# No es `sum` a propósito. `sum` de R acumula en long double y Python no tiene
# nada equivalente. Cualquiera de las dos alcanza y sobra para veinticuatro
# filas, pero **no dan el mismo último bit**, y de ese bit dependen los signos
# que devuelve Jacobi. Con una suma común en un orden fijo, los dos idiomas
# hacen exactamente las mismas operaciones de punto flotante.
suma <- function(x) {
  total <- 0
  for (v in x) total <- total + v
  total
}

media <- function(x) suma(x) / length(x)

# Desvío estándar muestral, con n − 1.
desvio <- function(x) {
  if (length(x) < 2) return(NA_real_)
  m <- media(x)
  sqrt(suma((x - m)^2) / (length(x) - 1))
}

# La matriz centrada y escalada, más las medias y los desvíos que se usaron.
#
# Es **la** decisión del análisis multivariado y casi nunca se declara. Sin
# tipificar, cada variable pesa según el cuadrado de su unidad de medida: una
# población en personas y un porcentaje en la misma matriz dan un primer
# componente que es la población y nada más. El proyecto calcula las dos
# versiones y las pone al lado.
tipificar <- function(datos) {
  n <- nrow(datos)
  p <- ncol(datos)
  medias <- vapply(seq_len(p), function(j) media(datos[, j]), numeric(1))
  desvios <- vapply(seq_len(p), function(j) desvio(datos[, j]), numeric(1))
  for (j in seq_len(p)) {
    if (!(desvios[j] > 0)) {
      stop(paste0("La columna ", j, " no varía: todas sus filas valen lo mismo. Una ",
                  "variable constante no aporta nada y rompe la tipificación."),
           call. = FALSE)
    }
  }
  base <- datos
  for (j in seq_len(p)) base[, j] <- (datos[, j] - medias[j]) / desvios[j]
  list(base = base, medias = medias, desvios = desvios)
}

# Solo centrada, sin escalar: es lo que come el PCA sobre covarianzas.
centrar <- function(datos) {
  n <- nrow(datos)
  p <- ncol(datos)
  medias <- vapply(seq_len(p), function(j) media(datos[, j]), numeric(1))
  base <- datos
  for (j in seq_len(p)) base[, j] <- datos[, j] - medias[j]
  list(base = base, medias = medias)
}

# La matriz de covarianzas de una matriz ya centrada, con n − 1.
cruzada <- function(datos) {
  n <- nrow(datos)
  p <- ncol(datos)
  salida <- matrix(0, nrow = p, ncol = p)
  for (a in seq_len(p)) {
    for (b in a:p) {
      v <- suma(vapply(seq_len(n), function(i) datos[i, a] * datos[i, b],
                       numeric(1))) / (n - 1)
      salida[a, b] <- v
      salida[b, a] <- v
    }
  }
  salida
}

correlacion <- function(x, y) {
  n <- length(x)
  mx <- media(x)
  my <- media(y)
  sx <- sqrt(suma((x - mx)^2))
  sy <- sqrt(suma((y - my)^2))
  if (!(sx > 0 && sy > 0)) return(NA_real_)
  suma(vapply(seq_len(n), function(i) (x[i] - mx) * (y[i] - my), numeric(1))) / (sx * sy)
}

# La cola derecha de la chi cuadrado. En Python es `scipy.stats.chi2.sf`.
chi2_cola <- function(x, gl) pchisq(x, gl, lower.tail = FALSE)

# ------------------------------------------------------------------ escribir
SIGNIFICATIVOS <- 10

redondear <- function(v) {
  if (v == 0 || !is.finite(v)) return(v)
  decimales <- SIGNIFICATIVOS - 1 - floor(log10(abs(v)))
  if (decimales >= 6) v else round(v, decimales)
}

formatear <- function(x) {
  if (is.null(x)) return("")
  if (is.logical(x)) return(if (is.na(x)) "" else if (x) "Sí" else "No")
  if (is.integer(x)) return(if (is.na(x)) "" else sprintf("%d", x))
  if (is.numeric(x)) {
    if (is.na(x)) return("")
    if (!is.finite(x)) return(if (x > 0) "Inf" else "-Inf")
    texto <- sprintf("%.6f", redondear(x))
    return(if (texto == "-0.000000") "0.000000" else texto)
  }
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
numero_texto <- function(valor, decimales) {
  if (is.null(valor) || is.na(valor)) return("")
  if (!is.finite(valor)) return(if (valor < 0) "-infinito" else "infinito")
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

porcentaje <- function(valor, decimales = 1) {
  if (is.null(valor) || is.na(valor)) return("")
  paste0(numero_texto(valor * 100, decimales), " %")
}

p_texto <- function(p) {
  if (is.null(p) || is.na(p)) return("")
  if (p < 0.001) "< 0,001" else numero_texto(p, 3)
}

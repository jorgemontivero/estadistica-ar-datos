# Lo que comparten los tres pasos: leer, resumir y escribir.
#
# La media y el desvío están escritos acá con la misma definición que usa el
# sitio: el desvío es el muestral, con n − 1, que es el que corresponde cuando
# los datos son una muestra y no la población entera.
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
  # Declarar la codificación no es un detalle: sin esto las cadenas quedan
  # marcadas como «unknown» y `sort(method = "radix")` se niega a ordenarlas
  # en cuanto aparece una ñ o una tilde.
  Encoding(lineas) <- "UTF-8"
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

numeros <- function(datos, variable) {
  v <- suppressWarnings(as.numeric(limpiar_texto(columna(datos, variable))))
  v[!is.na(v)]
}

# La confianza y, si se conoce, el tamaño de la población.
#
# Se leen de un archivo y no del código para que cambiar el nivel de confianza
# no sea editar un script: es el parámetro que más se toca.
leer_parametros <- function(ruta) {
  filas <- leer_csv(ruta)
  claves <- columna(filas, "clave")
  valores <- columna(filas, "valor")
  buscar <- function(clave) {
    i <- which(claves == clave)
    if (length(i) == 0) NULL else numero(valores[i[1]])
  }
  confianza <- buscar("confianza")
  if (is.null(confianza)) confianza <- 0.95
  if (!(confianza > 0 && confianza < 1)) {
    stop(paste0("La confianza tiene que estar entre 0 y 1, y es ", confianza, "."))
  }
  poblacion <- buscar("poblacion")
  if (!is.null(poblacion) && poblacion <= 0) {
    stop(paste0("La población tiene que ser mayor que cero, y es ", poblacion, "."))
  }
  list(confianza = confianza, poblacion = poblacion)
}

# ---------------------------------------------------------- estadísticas
# El desvío muestral, con n − 1: `sd` de R ya lo calcula así.
desvio <- function(x) if (length(x) < 2) NA_real_ else sd(x)

# ------------------------------------------------------------------ escribir
SIGNIFICATIVOS <- 10

# Diez dígitos significativos, y ni uno más.
#
# Los seis decimales de siempre alcanzan mientras los números sean chicos,
# pero la varianza de un ingreso en pesos anda por 10¹¹: ahí seis decimales
# piden dieciocho dígitos significativos, más de los que un `double` tiene. Y
# el último bit de `qchisq` no es el mismo en R que en SciPy —son dos
# implementaciones distintas de la misma función—, así que el archivo salía
# distinto en cada idioma por un dígito que no significaba nada.
#
# Diez dígitos significativos son muchos más de los que cualquier dato de una
# encuesta justifica, y los dos idiomas coinciden en todos.
redondear <- function(v) {
  if (v == 0 || !is.finite(v)) return(v)
  decimales <- SIGNIFICATIVOS - 1 - floor(log10(abs(v)))
  if (decimales >= 6) v else round(v, decimales)
}

formatear <- function(x) {
  if (is.null(x)) return("")
  if (is.logical(x)) return(if (is.na(x)) "" else if (x) "Sí" else "No")
  if (is.integer(x)) return(if (is.na(x)) "" else sprintf("%d", x))
  if (is.numeric(x)) return(if (is.na(x)) "" else sprintf("%.6f", redondear(x)))
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

# El intervalo como se informa: «[10,60; 12,69]».
#
# El separador es punto y coma y no coma, porque los números ya llevan coma
# decimal. «[10,60, 12,69]» tiene cuatro comas y ninguna dice lo mismo.
intervalo_texto <- function(inferior, superior, decimales = NULL) {
  if (is.null(decimales)) decimales <- decimales_de(max(abs(inferior), abs(superior)))
  paste0("[", numero_texto(inferior, decimales), "; ", numero_texto(superior, decimales), "]")
}

porcentaje_texto <- function(valor, decimales = 1) {
  paste0(numero_texto(valor * 100, decimales), " %")
}

# Paso 1: importar y limpiar.
#
# Lee datos/crudos/encuesta.csv, lo deja usable y escribe
# datos/limpios/encuesta.csv. El crudo no se toca nunca.
#
# Las reglas están escritas acá y son las mismas que en python/01_importar.py:
# los dos tienen que dar el mismo archivo limpio.

LIMITES <- list(edad = c(0, 110), ingreso = c(0, 100000000), puntaje = c(1, 10))

# Un texto sin espacios de más: ni en las puntas ni repetidos adentro.
limpiar_texto <- function(x) {
  x <- gsub("[[:space:]]+", " ", x)
  trimws(x)
}

# «CONTROL», «control » y «Control» son el mismo grupo.
normalizar_grupo <- function(x) {
  x <- limpiar_texto(x)
  ifelse(x == "", "", paste0(toupper(substring(x, 1, 1)), tolower(substring(x, 2))))
}

# Un número, o NA si está vacío, no es un número o cae fuera de su rango.
a_numero <- function(x, limites) {
  x <- limpiar_texto(x)
  v <- suppressWarnings(as.numeric(x))
  v[!is.na(v) & (v < limites[1] | v > limites[2])] <- NA
  v
}

importar <- function() {
  crudo <- read.csv("datos/crudos/encuesta.csv", colClasses = "character",
                    encoding = "UTF-8", check.names = FALSE)
  filas_crudas <- nrow(crudo)

  limpio <- data.frame(
    id = limpiar_texto(crudo$id),
    grupo = normalizar_grupo(crudo$grupo),
    stringsAsFactors = FALSE
  )
  # Enteros (0L y no 0): si el contador arranca decimal, la columna entera
  # sale con decimales y deja de coincidir con la de Python.
  vacios <- 0L
  fuera <- 0L
  for (v in names(LIMITES)) {
    texto <- limpiar_texto(crudo[[v]])
    numero <- a_numero(crudo[[v]], LIMITES[[v]])
    vacios <- vacios + sum(texto == "")
    fuera <- fuera + sum(texto != "" & is.na(numero))
    limpio[[v]] <- numero
  }

  # Filas repetidas: el mismo id cargado dos veces. Se queda la primera.
  repetidas <- duplicated(limpio$id)
  limpio <- limpio[!repetidas, ]

  dir.create("datos/limpios", showWarnings = FALSE, recursive = TRUE)
  escribir_csv(limpio, "datos/limpios/encuesta.csv")

  list(
    filas_crudas = filas_crudas,
    filas_repetidas = sum(repetidas),
    valores_vacios = vacios,
    valores_fuera_de_rango = fuera,
    filas_limpias = nrow(limpio)
  )
}

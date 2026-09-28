# Leer el archivo crudo, entender sus valores y escribir los resultados.
#
# Acá están las dos decisiones que se toman antes de mirar un solo dato: con
# qué separador viene el archivo y cuál es el separador decimal. Las dos se
# detectan y las dos quedan informadas en el resumen, porque adivinar mal
# cualquiera de las dos arruina todo lo que venga después.
#
# Los números se escriben con seis decimales fijos y los conteos como enteros:
# así los archivos de R y los de Python salen idénticos byte a byte.

SEPARADORES <- c(",", ";", "\t")

# Sin espacios en las puntas ni repetidos adentro.
limpiar_texto <- function(x) {
  x[is.na(x)] <- ""
  trimws(gsub("[[:space:]]+", " ", x))
}

# El que parte el encabezado en más columnas; si empatan, la coma.
detectar_separador <- function(encabezado) {
  mejor <- ","
  cuantas <- 0
  for (sep in SEPARADORES) {
    n <- length(strsplit(encabezado, sep, fixed = TRUE)[[1]])
    if (n > cuantas) {
      mejor <- sep
      cuantas <- n
    }
  }
  mejor
}

# Compara cuántos valores tienen forma de 1.234,56 y cuántos de 1,234.56.
es_decimal_coma <- function(valores) {
  coma <- 0
  punto <- 0
  for (v in valores) {
    v <- sub("^-", "", limpiar_texto(v))
    if (v == "" || !grepl("^[0-9]", v)) next
    ultima_coma <- max(c(-1, gregexpr(",", v, fixed = TRUE)[[1]]))
    ultimo_punto <- max(c(-1, gregexpr(".", v, fixed = TRUE)[[1]]))
    if (grepl(",", v, fixed = TRUE) && ultima_coma > ultimo_punto) {
      coma <- coma + 1
    } else if (grepl(".", v, fixed = TRUE) && ultimo_punto > ultima_coma) {
      punto <- punto + 1
    }
  }
  coma > punto
}

leer_crudo <- function(ruta) {
  con <- file(ruta, open = "r", encoding = "UTF-8")
  lineas <- readLines(con, warn = FALSE)
  close(con)
  # La marca de orden de bytes que dejan algunos programas. Se arma con su
  # número: el carácter suelto sería invisible en el código. R suele sacarla
  # solo al leer con encoding = "UTF-8", pero no en todas las plataformas, y
  # dejar el BOM pegado al primer nombre de columna rompe todo lo que sigue.
  bom <- intToUtf8(65279)
  lineas[1] <- sub(paste0("^", bom), "", lineas[1])
  lineas <- lineas[trimws(lineas) != ""]
  if (length(lineas) == 0) stop(paste(ruta, "está vacío"))

  separador <- detectar_separador(lineas[1])
  columnas <- limpiar_texto(strsplit(lineas[1], separador, fixed = TRUE)[[1]])
  filas <- vector("list", length(lineas) - 1)
  for (i in seq_along(filas)) {
    partes <- strsplit(lineas[i + 1], separador, fixed = TRUE)[[1]]
    # Si a una fila le faltan o le sobran campos, se completa o se corta: es
    # preferible a perder la fila entera sin avisar.
    partes <- c(partes, rep("", length(columnas)))[seq_along(columnas)]
    fila <- as.list(limpiar_texto(partes))
    names(fila) <- columnas
    filas[[i]] <- fila
  }
  valores <- unlist(lapply(filas, function(f) unlist(f, use.names = FALSE)), use.names = FALSE)
  list(columnas = columnas, filas = filas, separador = separador,
       decimal = if (es_decimal_coma(valores)) "," else ".")
}

# ------------------------------------------------ entender un valor suelto
# El texto como número, o NULL. Dice también si hubo que convertirlo.
#
# Con coma decimal, el punto es separador de miles; con punto decimal, lo es la
# coma. Sacarlo primero es lo que permite leer «1.234,56» y «1,234.56».
a_numero <- function(texto, decimal) {
  original <- texto
  miles <- if (decimal == ",") "." else ","
  texto <- gsub(miles, "", texto, fixed = TRUE)
  if (decimal == ",") texto <- gsub(",", ".", texto, fixed = TRUE)
  convertido <- texto != original
  cuerpo <- if (substr(texto, 1, 1) %in% c("+", "-")) substring(texto, 2) else texto
  sin_punto <- gsub(".", "", cuerpo, fixed = TRUE)
  valido <- cuerpo != "" &&
    lengths(regmatches(cuerpo, gregexpr(".", cuerpo, fixed = TRUE))) <= 1 &&
    sin_punto != "" && !grepl("[^0-9]", sin_punto)
  list(numero = if (valido) as.numeric(texto) else NULL, convertido = convertido)
}

dias_del_mes <- function(anio, mes) {
  largos <- c(31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
  bisiesto <- anio %% 4 == 0 && (anio %% 100 != 0 || anio %% 400 == 0)
  if (mes == 2 && bisiesto) 29 else largos[mes]
}

# La fecha en aaaa-mm-dd, o NULL.
#
# Se aceptan dd/mm/aaaa y aaaa-mm-dd, y se rechaza una fecha que no existe: el
# 31 de febrero no es una fecha, por más que se parezca a una.
a_fecha <- function(texto) {
  for (formato in list(list(sep = "/", orden = c(3, 2, 1)), list(sep = "-", orden = c(1, 2, 3)))) {
    partes <- strsplit(texto, formato$sep, fixed = TRUE)[[1]]
    if (length(partes) != 3 || any(grepl("[^0-9]", partes)) || any(partes == "")) next
    anio_txt <- partes[formato$orden[1]]
    anio <- as.integer(anio_txt)
    mes <- as.integer(partes[formato$orden[2]])
    dia <- as.integer(partes[formato$orden[3]])
    if (nchar(anio_txt) != 4 || mes < 1 || mes > 12) next
    if (dia < 1 || dia > dias_del_mes(anio, mes)) next
    return(sprintf("%04d-%02d-%02d", anio, mes, dia))
  }
  NULL
}

codigos <- function(texto) {
  partes <- limpiar_texto(strsplit(texto, ";", fixed = TRUE)[[1]])
  partes[partes != ""]
}

# ------------------------------------------------------------------ escribir
formatear <- function(x) {
  if (is.logical(x)) {
    ifelse(is.na(x), "", ifelse(x, "Sí", "No"))
  } else if (is.integer(x)) {
    ifelse(is.na(x), "", sprintf("%d", x))
  } else if (is.numeric(x)) {
    ifelse(is.na(x), "", sprintf("%.6f", x))
  } else {
    ifelse(is.na(x), "", as.character(x))
  }
}

# Un valor de CSV: si trae una coma, va entre comillas, y las comillas de
# adentro se duplican. Sin esto, un ejemplo como «529.991,44» corre una columna
# entera del archivo.
entrecomillar <- function(x) {
  necesita <- grepl('[,"\n]', x)
  ifelse(necesita, paste0('"', gsub('"', '""', x, fixed = TRUE), '"'), x)
}

escribir_csv <- function(tabla, ruta, columnas = names(tabla)) {
  dir.create(dirname(ruta), showWarnings = FALSE, recursive = TRUE)
  if (nrow(tabla) == 0) {
    lineas <- paste(columnas, collapse = ",")
  } else {
    celdas <- lapply(columnas, function(c) entrecomillar(formatear(tabla[[c]])))
    lineas <- c(paste(columnas, collapse = ","), do.call(paste, c(celdas, sep = ",")))
  }
  con <- file(ruta, open = "w", encoding = "UTF-8")
  on.exit(close(con))
  writeLines(lineas, con, sep = "\n")
}

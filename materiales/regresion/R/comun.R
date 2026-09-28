# Lo que comparten los tres pasos: leer, resumir y escribir.
#
# La media, el desvío y la asimetría están escritos acá con las mismas
# definiciones que usa el sitio: el desvío es el muestral, con n − 1, y la
# asimetría lleva la corrección por tamaño de muestra que usan SKEW de Excel y
# `e1071::skewness` con `type = 2`.
#
# Los números se escriben con seis decimales, redondeados a diez dígitos
# significativos, así los archivos de R y los de Python salen idénticos byte a
# byte. Diez dígitos son muchos más de los que cualquier dato justifica, y son
# los que las dos implementaciones comparten: más abajo cada motor tiene su
# propio último bit.

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

# El orden lo fija `method = "radix"`, que ordena por código de carácter y no
# por la configuración regional de la máquina: así R y Python escriben las
# filas en el mismo orden en cualquier computadora.
#
# El `enc2utf8` no es decoración: el orden por radix se niega a trabajar con
# cadenas marcadas como «unknown», y una cadena armada con `paste0` a partir
# de texto del propio script queda marcada así en cuanto lleva una tilde.
ordenar <- function(x) sort(unique(enc2utf8(x)), method = "radix")

# La confianza y, sobre todo, el modelo.
#
# Qué se explica y con qué se lo explica vive en un archivo, no en el código:
# cambiar de respuesta o agregar un predictor no tiene que obligar a editar un
# script.
leer_parametros <- function(ruta) {
  filas <- leer_csv(ruta)
  claves <- columna(filas, "clave")
  valores <- columna(filas, "valor")
  buscar <- function(clave) {
    i <- which(claves == clave)
    if (length(i) == 0) "" else valores[i[1]]
  }
  lista <- function(clave) {
    partes <- trimws(strsplit(buscar(clave), ";", fixed = TRUE)[[1]])
    partes[partes != ""]
  }
  confianza <- numero(buscar("confianza"))
  if (is.null(confianza)) confianza <- 0.95
  if (!(confianza > 0 && confianza < 1)) {
    stop(paste0("La confianza tiene que estar entre 0 y 1, y es ", confianza, "."))
  }
  parametros <- list(
    confianza = confianza,
    respuesta = limpiar_texto(buscar("respuesta_numerica")),
    predictores = lista("predictores"),
    respuesta_binaria = limpiar_texto(buscar("respuesta_binaria")),
    predictores_binaria = lista("predictores_binaria"),
    exito = limpiar_texto(buscar("exito"))
  )
  if (parametros$respuesta == "" || length(parametros$predictores) == 0) {
    stop("Faltan «respuesta_numerica» o «predictores» en parametros.csv.")
  }
  parametros
}

# ---------------------------------------------------------- estadísticas
desvio <- function(x) if (length(x) < 2) NA_real_ else sd(x)

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
  # Hay tres cuentas de este proyecto que pueden irse al infinito con datos
  # legítimos: el VIF con predictores linealmente dependientes, la distancia de
  # Cook de un caso con palanca 1 y el odds ratio de una logística con
  # separación perfecta. No son errores: son resultados, y se escriben. El
  # «Inf» sale explícito y no de sprintf, para que Python pueda escribir lo
  # mismo.
  if (is.numeric(x)) {
    if (is.na(x)) return("")
    if (!is.finite(x)) return(if (x > 0) "Inf" else "-Inf")
    return(sprintf("%.6f", redondear(x)))
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
# Uno o dos decimales según la escala.
decimales_de <- function(valor) if (abs(valor) >= 10) 1 else 2

numero_texto <- function(valor, decimales) {
  # En un informe en castellano un valor que se fue al infinito se escribe con
  # la palabra. «Inf» es como lo llama el motor, no como se lee.
  if (is.na(valor)) return("")
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

# Como `numero_texto`, pero sin decimales cuando el número es entero. Unos
# grados de libertad de 2 se escriben «2» y no «2,00»; los de Welch, que salen
# con decimales de verdad, se escriben con ellos.
numero_limpio <- function(valor, decimales) {
  if (valor == round(valor)) numero_texto(valor, 0) else numero_texto(valor, decimales)
}

# El valor p como se informa: «< 0,001» o con tres decimales.
p_texto <- function(p) {
  if (is.null(p) || is.na(p)) return("")
  if (p < 0.001) "< 0,001" else numero_texto(p, 3)
}

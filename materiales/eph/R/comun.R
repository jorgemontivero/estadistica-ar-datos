# Lo que comparten los cuatro pasos: leer los microdatos, estimar y escribir.
#
# Los números se escriben con seis decimales, redondeados a diez dígitos
# significativos, así los archivos de R y los de Python salen idénticos byte a
# byte. Diez dígitos son muchos más de los que cualquier dato justifica, y son
# los que las dos implementaciones comparten: más abajo cada motor tiene su
# propio último bit.
#
# **Esta versión trabaja por columnas y la de Python por filas.** Es la única
# diferencia de fondo entre las dos, y es a propósito: recorrer cinco mil
# quinientos registros de a uno es natural en Python y es la manera equivocada
# de escribir R. Los dos hacen las mismas cuentas en el mismo orden y escriben
# los mismos bytes; lo que cambia es de qué lado se para cada uno.

limpiar_texto <- function(x) {
  x[is.na(x)] <- ""
  trimws(gsub("[[:space:]]+", " ", x))
}

sin_comillas <- function(x) sub('"+$', "", sub('^"+', "", x))

# «latin-1», «latin_1» y «latin1» son la misma cosa para Python y solo la
# última lo es para R.
nombre_de_codificacion <- function(x) {
  limpio <- tolower(gsub("[-_]", "", limpiar_texto(x)))
  if (limpio %in% c("latin1", "iso88591")) "latin1"
  else if (limpio %in% c("utf8", "utf8bom")) "UTF-8"
  else x
}

# ------------------------------------------------------------------ leer
# Lo que en un archivo del INDEC quiere decir «no hay dato».
#
# El `NA` escrito con letras no es un invento: aparece tal cual en los archivos
# de algunos trimestres —2021T1, 2024T3 y 2024T4 entre ellos— y es lo que hace
# que un lector distraído reciba ciento cincuenta columnas numéricas
# convertidas en texto. Leer todo como texto y decidir acá qué es un número
# evita el problema de raíz.
FALTANTES <- c("", "NA", "N/A", "NULL", ".", "-")

# Un CSV común y corriente: coma, UTF-8. Para los archivos del proyecto.
leer_csv <- function(ruta) {
  con <- file(ruta, open = "r", encoding = "UTF-8")
  lineas <- readLines(con, warn = FALSE)
  close(con)
  # Declarar la codificación no es un detalle: sin esto las cadenas quedan
  # marcadas como «unknown» y `sort(method = "radix")` se niega a ordenarlas
  # en cuanto aparece una ñ o una tilde.
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

# El `usu_individual_Tnnaa.txt` del INDEC, tal como viene.
#
# Tres detalles que no son detalles:
#
# - **El separador es el punto y coma**, no la coma. Abrirlo con la coma da una
#   sola columna, y algunos programas no avisan.
# - **La codificación es latin-1**, no UTF-8. Con UTF-8 el archivo de hogar
#   directamente no abre, y el de individual abre con la ñ rota.
# - **Los textos vienen entre comillas** y los números no. Las comillas se
#   sacan acá, una sola vez, y no en cada paso.
#
# Se devuelve todo como texto, una columna por elemento de la lista. Convertir
# a número es una decisión que toma el paso 1 columna por columna, con los
# códigos de la EPH a la vista. Con `read.csv` y su adivinanza de tipos, el
# trimestre que trae «NA» con letras se convierte solo en un desastre.
leer_microdatos <- function(ruta, separador, codificacion) {
  if (!file.exists(ruta)) {
    stop(paste0(
      "No encuentro ", ruta, ".\n",
      "Si querés correrlo sobre datos del INDEC, bajá el trimestre de\n",
      "https://www.indec.gob.ar/indec/web/Institucional-Indec-BasesDeDatos,\n",
      "descomprimilo en datos/ y apuntá «archivo» en datos/parametros.csv\n",
      "al usu_individual_Tnnaa.txt que salga."), call. = FALSE)
  }
  bytes <- readBin(ruta, "raw", file.size(ruta))
  # `iconv` de R no conoce «latin-1» con guion y Python sí. Como el nombre lo
  # escribe una persona en parametros.csv, se lo normaliza acá en vez de
  # devolverle un error de codepage que no dice nada.
  texto <- iconv(rawToChar(bytes), from = nombre_de_codificacion(codificacion),
                 to = "UTF-8")
  lineas <- strsplit(gsub("\r\n", "\n", texto, fixed = TRUE), "\n", fixed = TRUE)[[1]]
  lineas <- lineas[trimws(lineas) != ""]
  if (length(lineas) == 0) stop(paste0(ruta, " está vacío."), call. = FALSE)

  columnas <- toupper(sin_comillas(limpiar_texto(
    strsplit(lineas[1], separador, fixed = TRUE)[[1]])))
  if (length(columnas) < 2) {
    stop(paste0("La primera línea de ", ruta, " tiene una sola columna con el ",
                "separador «", separador, "». Si el archivo es del INDEC, el ",
                "separador es «;»."), call. = FALSE)
  }

  partes <- strsplit(lineas[-1], separador, fixed = TRUE)
  m <- matrix("", nrow = length(partes), ncol = length(columnas))
  for (i in seq_along(partes)) {
    p <- partes[[i]]
    cuantas <- min(length(p), length(columnas))
    if (cuantas > 0) m[i, seq_len(cuantas)] <- p[seq_len(cuantas)]
  }
  datos <- lapply(seq_along(columnas), function(j) sin_comillas(limpiar_texto(m[, j])))
  names(datos) <- columnas
  list(columnas = columnas, datos = datos, n = length(partes))
}

# Un texto a número, con los códigos de dato faltante de la EPH contemplados.
# Vectorizado: es lo que se le pide a una columna entera.
numeros_de <- function(x) {
  x <- limpiar_texto(x)
  v <- suppressWarnings(as.numeric(x))
  v[toupper(x) %in% FALTANTES] <- NA_real_
  v
}

numero <- function(x) {
  v <- numeros_de(x)[1]
  if (is.na(v)) NULL else v
}

# Qué archivo leer y con qué columnas trabajar, declarado en un archivo.
#
# Correr el proyecto sobre otro trimestre, sobre otro aglomerado o con otro
# ponderador no tiene que obligar a editar un script.
leer_parametros <- function(ruta) {
  filas <- leer_csv(ruta)
  claves <- vapply(filas, function(f) f$clave, character(1))
  valores <- vapply(filas, function(f) f$valor, character(1))
  texto <- function(clave, por_omision = "") {
    i <- which(claves == clave)
    v <- if (length(i) == 0) "" else limpiar_texto(valores[i[1]])
    if (v == "") por_omision else v
  }
  confianza <- numero(texto("confianza", "0.95"))
  if (is.null(confianza)) confianza <- 0.95
  if (!(confianza > 0 && confianza < 1)) {
    stop(paste0("La confianza tiene que estar entre 0 y 1, y es ", confianza, "."),
         call. = FALSE)
  }
  parametros <- list(
    archivo = texto("archivo", "datos/usu_individual_T425_simulado.txt"),
    separador = texto("separador", ";"),
    codificacion = texto("codificacion", "latin1"),
    ponderador = toupper(texto("ponderador", "PONDERA")),
    ponderador_ingreso = toupper(texto("ponderador_ingreso", "PONDIIO")),
    ingreso = toupper(texto("ingreso", "P21")),
    confianza = confianza,
    region = texto("region"),
    aglomerado = texto("aglomerado")
  )
  if (nchar(parametros$separador) != 1) {
    stop("«separador» tiene que ser un solo carácter.", call. = FALSE)
  }
  parametros
}

# El orden de las etiquetas, por código de carácter y no por el idioma de la
# máquina: así R y Python escriben las filas en el mismo orden en cualquier
# computadora.
#
# El `enc2utf8` no es decoración: el orden por radix se niega a trabajar con
# cadenas marcadas como «unknown», y una cadena armada con `paste0` a partir de
# texto del propio script queda marcada así en cuanto lleva una tilde.
ordenar <- function(x) sort(unique(enc2utf8(x)), method = "radix")

# ------------------------------------------------------------ estadísticas
# El cuantil de una distribución con pesos.
#
# `valores` y `pesos` vienen en paralelo y **ya ordenados por valor**. Se
# devuelve el primer valor cuyo peso acumulado llega a p·W.
#
# Es la definición más simple de las varias que hay, y la única que no depende
# de una convención de interpolación: con pesos de encuesta, dos programas que
# interpolan distinto dan medianas distintas sobre los mismos datos. Acá se
# elige una, se la escribe, y los dos motores dan lo mismo.
#
# La acumulación va con un bucle explícito y no con `cumsum`: `cumsum` acumula
# en long double y Python no, y en un empate justo sobre el corte los dos
# elegirían valores distintos.
cuantil_ponderado <- function(valores, pesos, p) {
  total <- sum(pesos)
  if (total <= 0 || length(valores) == 0) return(NA_real_)
  objetivo <- p * total
  acumulado <- 0
  for (i in seq_along(valores)) {
    acumulado <- acumulado + pesos[i]
    if (acumulado >= objetivo) return(valores[i])
  }
  valores[length(valores)]
}

# Las posiciones de cada hogar dentro de cada aglomerado, en orden fijo.
#
# Se calcula una sola vez y se reusa en las setenta y pico de estimaciones que
# hace el proyecto: los estratos y las unidades son siempre los mismos, y
# reagruparlos en cada una es lo que hace que esto tarde minutos en vez de
# segundos.
#
# El orden —estratos ordenados, y hogares ordenados dentro de cada uno— no es
# por prolijidad: fija en qué orden se suman los aportes, y con eso el último
# bit de la varianza. Los dos motores tienen que recorrerlos igual.
preparar_conglomerados <- function(estratos, unidades) {
  lapply(ordenar(estratos), function(h) {
    indices <- which(estratos == h)
    dentro <- unidades[indices]
    lapply(ordenar(dentro), function(u) indices[dentro == u])
  })
}

# Una razón Y/X y su error estándar, respetando el diseño de la EPH.
#
# Casi todo lo que se calcula con la EPH es una razón entre dos totales
# ponderados: la tasa de empleo es ocupados sobre población, la de desocupación
# es desocupados sobre PEA, y un ingreso medio es la suma de ingresos sobre la
# suma de pesos. Las tres salen de la misma cuenta.
#
# El error estándar **no** es el de una muestra aleatoria simple. La EPH
# selecciona conglomerados dentro de cada aglomerado, y la gente que vive cerca
# se parece: dos vecinos aportan menos información que dos personas sorteadas
# de todo el país. La varianza se calcula por el método de los conglomerados
# últimos, linealizando la razón:
#
#     z_i = w_i · (y_i − p·x_i)
#
# y después se trata a los z como si fueran un total, sumándolos por unidad
# primaria dentro de cada estrato.
#
# **Acá el estrato es el aglomerado y la unidad primaria es el hogar.** No es lo
# ideal: el conglomerado de verdad es el radio censal, y el archivo público no
# lo trae. Con el hogar como unidad se captura la parte del efecto de diseño
# que viene de que los miembros de un hogar se parecen, y se pierde la que
# viene de que los vecinos se parecen. **El error estándar que sale de acá es,
# entonces, una cota inferior**: el verdadero es más grande. Es lo mejor que se
# puede hacer con el archivo publicado, y decirlo es parte de hacerlo bien.
estimar_razon <- function(w, y, x, conglomerados, confianza) {
  total_y <- sum(w * y)
  total_x <- sum(w * x)
  if (total_x <= 0) return(NULL)
  p <- total_y / total_x
  aportes <- w * (y - p * x)

  varianza <- 0
  grados <- 0L
  unidades_primarias <- 0L
  estratos_solitarios <- 0L
  for (estrato in conglomerados) {
    zs <- vapply(estrato, function(idx) sum(aportes[idx]), numeric(1))
    a <- length(zs)
    unidades_primarias <- unidades_primarias + a
    if (a < 2) {
      # Un estrato con una sola unidad primaria no aporta grados de libertad y
      # su varianza no se puede estimar. Se lo deja pasar y se cuenta, que es
      # mejor que devolver un cero silencioso.
      estratos_solitarios <- estratos_solitarios + 1L
      next
    }
    media_z <- sum(zs) / a
    varianza <- varianza + a / (a - 1) * sum((zs - media_z)^2)
    grados <- grados + (a - 1L)
  }

  varianza <- varianza / (total_x^2)
  error <- if (varianza > 0) sqrt(varianza) else 0

  # Los grados de libertad de una encuesta compleja son (unidades primarias −
  # estratos), no (n − 1). Con 1.871 hogares y 32 aglomerados son 1.839.
  gl <- max(1L, grados)
  critico <- qt(1 - (1 - confianza) / 2, gl)
  list(estimacion = p, error_estandar = error, gl = gl,
       inferior = p - critico * error, superior = p + critico * error,
       total_numerador = total_y, total_denominador = total_x,
       unidades_primarias = unidades_primarias,
       estratos_solitarios = estratos_solitarios)
}

# Cuánto cuesta el diseño, para una proporción.
#
# Es la varianza que se obtuvo dividida por la que tendría una muestra
# aleatoria simple del mismo tamaño. Un deff de 1,8 quiere decir que los 1.000
# casos de la muestra valen como 555.
deff_de_proporcion <- function(p, error, n) {
  if (n < 2 || p <= 0 || p >= 1) return(NA_real_)
  simple <- p * (1 - p) / n
  if (simple > 0) (error^2) / simple else NA_real_
}

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
    # Un cero con signo no significa nada y además sale distinto en cada motor,
    # porque depende del último bit de una suma.
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
# El número como se escribe en un informe en castellano: miles con punto y
# decimales con coma.
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

# Una proporción escrita como porcentaje. La EPH informa sus tasas con un
# decimal; acá se usan dos, porque las diferencias que el proyecto quiere
# mostrar viven en el segundo.
porcentaje <- function(valor, decimales = 2) {
  if (is.null(valor) || is.na(valor)) return("")
  paste0(numero_texto(valor * 100, decimales), " %")
}

# Un monto en pesos, sin decimales. Escribir centavos en un ingreso medio de
# seiscientos mil finge una precisión que la muestra no tiene.
pesos_texto <- function(valor) {
  if (is.null(valor) || is.na(valor)) return("")
  paste0("$ ", numero_texto(valor, 0))
}

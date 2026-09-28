# Lo que comparten los cuatro pasos: leer, ordenar, estimar y escribir.
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

# ------------------------------------------------------------------ leer
leer_csv <- function(ruta) {
  con <- file(ruta, open = "r", encoding = "UTF-8")
  lineas <- readLines(con, warn = FALSE)
  close(con)
  # Declarar la codificación no es un detalle: sin esto las cadenas quedan
  # marcadas como «unknown» y `sort(method = "radix")` se niega a ordenarlas en
  # cuanto aparece una ñ o una tilde, que en una lista de provincias argentinas
  # pasa en la tercera fila.
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

# Qué archivo, qué estándar y contra qué comparar, declarado en un archivo.
#
# Cambiar de estándar o de par a comparar no tiene que obligar a editar un
# script: es lo que hace que un resultado se pueda repetir y discutir.
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
  multiplicador <- numero(texto("multiplicador", "100000"))
  if (is.null(multiplicador)) multiplicador <- 100000
  if (!(multiplicador %in% c(1000, 10000, 100000))) {
    stop("«multiplicador» tiene que ser 1000, 10000 o 100000.", call. = FALSE)
  }

  # Los pares van separados por punto y coma, y los dos miembros por una barra:
  # «Chaco | Ciudad de Buenos Aires; Catamarca | La Rioja».
  pares <- list()
  for (trozo in strsplit(texto("pares"), ";", fixed = TRUE)[[1]]) {
    partes <- limpiar_texto(strsplit(trozo, "|", fixed = TRUE)[[1]])
    partes <- partes[partes != ""]
    if (length(partes) == 2) {
      pares[[length(pares) + 1]] <- partes
    } else if (length(partes) > 0) {
      stop(paste0("«", trimws(trozo), "» no es un par: hacen falta dos nombres ",
                  "separados por una barra."), call. = FALSE)
    }
  }

  list(
    datos = texto("datos", "datos/mortalidad-2022.csv"),
    estandares = texto("estandares", "datos/estandares.csv"),
    estandar = texto("estandar", "oms"),
    multiplicador = multiplicador,
    confianza = confianza,
    poblacion = texto("poblacion", "jurisdiccion"),
    grupo = texto("grupo", "grupo_edad"),
    casos = texto("casos", "defunciones"),
    expuestos = texto("expuestos", "poblacion"),
    # Contra qué se compara la indirecta. Vacío quiere decir «contra el total
    # de las poblaciones del archivo», que es lo que hace la DEIS cuando
    # compara provincias contra el país.
    referencia = texto("referencia"),
    pares = pares
  )
}

# El orden de las etiquetas, por código de carácter y no por el idioma de la
# máquina: así R y Python escriben las filas en el mismo orden en cualquier
# computadora. Con «Córdoba» y «Chaco» en la misma tabla, el idioma de la
# máquina decide distinto según dónde esté.
#
# El `enc2utf8` no es decoración: el orden por radix se niega a trabajar con
# cadenas marcadas como «unknown».
ordenar <- function(x) sort(unique(enc2utf8(x)), method = "radix")

# Ordenar filas por un número de mayor a menor, rompiendo los empates por
# nombre. Sin el desempate, dos motores podrían escribir las mismas filas en
# distinto orden.
orden_por <- function(valores, nombres) {
  order(-valores, enc2utf8(nombres), method = "radix")
}

# ------------------------------------------------------------ estadística
# El cuantil de la chi cuadrado. En Python es `scipy.stats.chi2.ppf`.
#
# Las dos implementaciones coinciden mucho más allá del décimo dígito
# significativo, que es hasta donde este proyecto escribe.
chi2 <- function(p, gl) qchisq(p, gl)

# El intervalo exacto de un conteo de Poisson, por la chi cuadrado.
#
# No es la aproximación normal. Con pocos casos la normal da límites inferiores
# negativos, que para un conteo no quieren decir nada; este es exacto y
# asimétrico, que es lo que corresponde.
ic_poisson <- function(casos, confianza) {
  alfa <- 1 - confianza
  list(inferior = if (casos == 0) 0 else chi2(alfa / 2, 2 * casos) / 2,
       superior = chi2(1 - alfa / 2, 2 * (casos + 1)) / 2)
}

# El intervalo de una tasa estandarizada, por el método de Fay-Feuer (1997).
#
# Una tasa ajustada es una **suma ponderada** de conteos de Poisson, y eso no es
# un Poisson: no se le puede aplicar el intervalo de un conteo. Fay y Feuer la
# aproximan por una gamma con los mismos dos primeros momentos, y esa gamma se
# evalúa con la chi cuadrado.
#
# Es el que usan los registros de cáncer y el programa SEER, y el que hay que
# usar cuando algún grupo de edad tiene pocos casos: ahí el intervalo sale
# asimétrico, que es lo correcto. La aproximación normal, en cambio, da límites
# inferiores negativos.
#
# El `mayor_peso` —el mayor de los wᵢ/nᵢ— entra solo en el límite superior: es
# el ajuste que Fay y Feuer agregan para que el intervalo cubra bien cuando la
# tasa es cero o casi.
ic_fay_feuer <- function(tasa, varianza, mayor_peso, confianza) {
  alfa <- 1 - confianza
  if (tasa > 0 && varianza > 0) {
    inferior <- (varianza / (2 * tasa)) * chi2(alfa / 2, 2 * tasa * tasa / varianza)
    varianza_sup <- varianza + mayor_peso * mayor_peso
    tasa_sup <- tasa + mayor_peso
    superior <- (varianza_sup / (2 * tasa_sup)) *
      chi2(1 - alfa / 2, 2 * tasa_sup * tasa_sup / varianza_sup)
    return(list(inferior = inferior, superior = superior))
  }
  if (tasa == 0) {
    # Sin ningún caso el límite inferior es cero y el superior sale del peso.
    superior <- if (mayor_peso > 0) mayor_peso * chi2(1 - alfa / 2, 2) / 2 else 0
    return(list(inferior = 0, superior = superior))
  }
  list(inferior = NA_real_, superior = NA_real_)
}

# El cuantil de la normal estándar. En Python es `scipy.stats.norm.ppf`.
normal_inv <- function(p) qnorm(p)

# La razón entre dos tasas estandarizadas, con su intervalo.
#
# El intervalo se arma en escala logarítmica, como el de toda razón, y el error
# estándar de cada tasa se recupera del ancho de su propio intervalo: el de
# Fay-Feuer no tiene una fórmula cerrada para la varianza en escala log, y
# deducirla del intervalo es la manera habitual de combinarlos.
razon_de_tasas <- function(a, b, confianza) {
  if (!(a$valor > 0 && b$valor > 0)) return(NULL)
  if (any(c(a$inferior, a$superior, b$inferior, b$superior) <= 0)) return(NULL)
  z <- normal_inv(1 - (1 - confianza) / 2)
  ee_a <- (log(a$superior) - log(a$inferior)) / (2 * z)
  ee_b <- (log(b$superior) - log(b$inferior)) / (2 * z)
  ee <- sqrt(ee_a * ee_a + ee_b * ee_b)
  registro <- log(a$valor / b$valor)
  list(valor = a$valor / b$valor,
       inferior = exp(registro - z * ee),
       superior = exp(registro + z * ee),
       error_estandar_log = ee)
}

# Si dos intervalos se tocan. Que no se pisen no es una prueba de hipótesis —es
# más exigente que una—, pero que sí se pisen alcanza para decir que la
# diferencia no está establecida.
se_pisan <- function(a, b) a$inferior <= b$superior && b$inferior <= a$superior

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

porcentaje <- function(valor, decimales = 1) {
  if (is.null(valor) || is.na(valor)) return("")
  paste0(numero_texto(valor * 100, decimales), " %")
}

# Una tasa, con un decimal. Escribir tres decimales en una tasa por cien mil
# finge una precisión que los conteos no tienen.
tasa_texto <- function(valor, decimales = 1) {
  if (is.null(valor) || is.na(valor)) return("")
  numero_texto(valor, decimales)
}

# Lo que comparten los dos pasos: cómo se escriben los CSV.
#
# Los números se escriben con seis decimales fijos a propósito. Así el archivo
# de R y el de Python son idénticos byte a byte, y comparar los dos es una
# línea en la terminal. Con la notación que elige cada idioma por su cuenta
# —1e-04 acá, 0.0001 allá— habría que comparar a ojo.

formatear <- function(x) {
  # Los conteos son enteros y se escriben sin decimales; lo demás, con seis.
  # Se mira el tipo y no el valor: una media que da justo 42 tiene que
  # escribirse igual que una que da 42,000001.
  if (is.integer(x)) {
    ifelse(is.na(x), "", sprintf("%d", x))
  } else if (is.numeric(x)) {
    ifelse(is.na(x), "", sprintf("%.6f", x))
  } else {
    ifelse(is.na(x), "", as.character(x))
  }
}

escribir_csv <- function(tabla, ruta) {
  columnas <- lapply(tabla, formatear)
  lineas <- c(
    paste(names(tabla), collapse = ","),
    do.call(paste, c(columnas, sep = ","))
  )
  con <- file(ruta, open = "w", encoding = "UTF-8")
  on.exit(close(con))
  writeLines(lineas, con, sep = "\n")
}

leer_csv <- function(ruta) {
  read.csv(ruta, colClasses = "character", encoding = "UTF-8", check.names = FALSE)
}

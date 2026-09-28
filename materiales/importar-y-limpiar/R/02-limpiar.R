# Paso 2: limpiar, dejando anotado cada cambio.
#
# Cada valor que se modifica queda contado en salidas/cambios.csv, por variable
# y por regla. Una limpieza que no informa lo que tocó es indistinguible de un
# error de carga.

# Las reglas que se cuentan. Los espacios de más no están: se sacan al leer el
# archivo, antes de que el diccionario entre en juego, y el perfil los informa.
REGLAS <- c("código de faltante a vacío", "decimal convertido", "no es un número", "no es entero",
            "fuera de rango", "categoría desconocida", "categoría normalizada",
            "fecha normalizada", "fecha inválida")

limite <- function(texto, decimal) {
  if (texto == "") return(NULL)
  a_numero(texto, decimal)$numero
}

# Devuelve el valor limpio y la regla aplicada. La regla vacía es «no se tocó».
limpiar_valor <- function(valor, variable, decimal) {
  if (valor == "") return(list(valor = "", regla = ""))
  if (variable$faltante != "" && tolower(valor) == tolower(variable$faltante)) {
    return(list(valor = "", regla = "código de faltante a vacío"))
  }

  tipo <- variable$tipo
  if (tipo %in% c("entero", "decimal")) {
    leido <- a_numero(valor, decimal)
    if (is.null(leido$numero)) return(list(valor = "", regla = "no es un número"))
    numero <- leido$numero
    if (tipo == "entero" && numero != as.integer(numero)) {
      return(list(valor = "", regla = "no es entero"))
    }
    minimo <- limite(variable$minimo, decimal)
    maximo <- limite(variable$maximo, decimal)
    if ((!is.null(minimo) && numero < minimo) || (!is.null(maximo) && numero > maximo)) {
      return(list(valor = "", regla = "fuera de rango"))
    }
    salida <- if (tipo == "entero") sprintf("%d", as.integer(numero)) else sprintf("%.6f", numero)
    return(list(valor = salida, regla = if (leido$convertido) "decimal convertido" else ""))
  }

  if (tipo == "categoria") {
    for (codigo in codigos(variable$codigos)) {
      if (tolower(codigo) == tolower(valor)) {
        return(list(valor = codigo,
                    regla = if (codigo != valor) "categoría normalizada" else ""))
      }
    }
    return(list(valor = "", regla = "categoría desconocida"))
  }

  if (tipo == "fecha") {
    fecha <- a_fecha(valor)
    if (is.null(fecha)) return(list(valor = "", regla = "fecha inválida"))
    return(list(valor = fecha, regla = if (fecha != valor) "fecha normalizada" else ""))
  }

  list(valor = valor, regla = "")
}

limpiar <- function(crudo, diccionario) {
  nombres <- diccionario$nombre
  es_id <- tolower(diccionario$id) %in% c("sí", "si")
  columna_id <- if (any(es_id)) nombres[which(es_id)[1]] else NULL
  cambios <- matrix(0L, nrow = length(nombres), ncol = length(REGLAS),
                    dimnames = list(nombres, REGLAS))

  limpias <- list()
  vistos <- character(0)
  duplicadas <- 0L
  for (cruda in crudo$filas) {
    fila <- list()
    for (k in seq_along(nombres)) {
      variable <- lapply(diccionario, function(col) col[k])
      valor <- if (!is.null(cruda[[nombres[k]]])) cruda[[nombres[k]]] else ""
      resultado <- limpiar_valor(valor, variable, crudo$decimal)
      if (resultado$regla != "") {
        cambios[nombres[k], resultado$regla] <- cambios[nombres[k], resultado$regla] + 1L
      }
      fila[[nombres[k]]] <- resultado$valor
    }
    if (!is.null(columna_id) && fila[[columna_id]] != "") {
      if (fila[[columna_id]] %in% vistos) {
        duplicadas <- duplicadas + 1L
        next
      }
      vistos <- c(vistos, fila[[columna_id]])
    }
    limpias[[length(limpias) + 1]] <- fila
  }

  base <- if (length(limpias) == 0) {
    as.data.frame(setNames(rep(list(character(0)), length(nombres)), nombres), stringsAsFactors = FALSE)
  } else {
    do.call(rbind, lapply(limpias, function(f) as.data.frame(f, stringsAsFactors = FALSE)))
  }
  escribir_csv(base, "datos/limpios/base.csv", nombres)

  # En el orden del diccionario y de las reglas, para que no dependa de cómo
  # recorre cada idioma sus estructuras.
  tabla <- data.frame(variable = character(), regla = character(), casos = integer(),
                      stringsAsFactors = FALSE)
  for (nombre in nombres) {
    for (regla in REGLAS) {
      if (cambios[nombre, regla] > 0) {
        tabla <- rbind(tabla, data.frame(variable = nombre, regla = regla,
                                         casos = cambios[nombre, regla], stringsAsFactors = FALSE))
      }
    }
  }
  escribir_csv(tabla, "salidas/cambios.csv", c("variable", "regla", "casos"))

  vacios <- sum(vapply(limpias, function(f) sum(unlist(f) == ""), integer(1)))
  list(filas = length(limpias), duplicadas = duplicadas,
       modificados = as.integer(sum(cambios)), vacios = as.integer(vacios))
}

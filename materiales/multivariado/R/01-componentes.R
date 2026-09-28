# Paso 1: componentes principales.
#
# Un PCA es una rotación: los mismos datos mirados desde el eje que más los
# estira. No inventa nada ni descubre nada; ordena la variación que ya estaba.
#
# **La decisión que define el resultado no es del método: es tipificar o no.**
# Sin tipificar, cada variable pesa según el cuadrado de su unidad de medida.
# Con una población en personas y unos porcentajes en la misma matriz, el primer
# componente es la población —correlación 1,000— y los porcentajes no existen. Y
# como el resultado igual «funciona» —explica el 99 % de la varianza, que suena
# bárbaro— nadie lo mira dos veces.
#
# Este paso calcula las dos versiones y las deja al lado, en
# `sin-estandarizar.csv`. No para que se elija: para que se vea qué se está
# eligiendo.

# Los autovalores, las cargas y los puntajes, tipificando o no.
#
# Con tipificación la matriz que se descompone es la de correlaciones; sin ella,
# la de covarianzas. Es la misma cuenta sobre matrices distintas, y de ahí sale
# toda la diferencia.
calcular_componentes <- function(datos, columnas, tipificado) {
  if (tipificado) {
    preparado <- tipificar(datos)
    base <- preparado$base
    medias <- preparado$medias
    desvios <- preparado$desvios
  } else {
    preparado <- centrar(datos)
    base <- preparado$base
    medias <- preparado$medias
    desvios <- rep(1, length(columnas))
  }
  matriz <- cruzada(base)
  descompuesta <- descomponer(matriz)
  valores <- descompuesta$valores
  vectores <- descompuesta$vectores

  total <- suma(valores)
  n <- nrow(base)
  p <- length(columnas)

  # Los puntajes: cada unidad proyectada sobre cada componente. La varianza de
  # un puntaje es su autovalor, que es la definición de «componente».
  puntajes <- matrix(0, nrow = n, ncol = p)
  for (i in seq_len(n)) {
    for (j in seq_len(p)) {
      puntajes[i, j] <- suma(vapply(seq_len(p),
                                    function(k) base[i, k] * vectores[[j]][k],
                                    numeric(1)))
    }
  }

  # Las cargas: la correlación de cada variable con cada componente. Con datos
  # tipificados es el autovector por la raíz del autovalor; se calcula como
  # correlación para que valga también sin tipificar.
  cargas <- matrix(0, nrow = p, ncol = p)
  for (k in seq_len(p)) {
    for (j in seq_len(p)) {
      cargas[k, j] <- correlacion(base[, k], puntajes[, j])
    }
  }

  list(tipificado = tipificado, valores = valores, vectores = vectores,
       puntajes = puntajes, cargas = cargas, total = total, medias = medias,
       desvios = desvios, barridos = descompuesta$barridos, base = base)
}

# Un renglón por componente: cuánto explica y cuánto va acumulado.
tabla_de_componentes <- function(salida, columnas) {
  filas <- list()
  acumulado <- 0
  for (j in seq_along(salida$valores)) {
    valor <- salida$valores[j]
    proporcion <- if (salida$total > 0) valor / salida$total else NA_real_
    acumulado <- acumulado + if (is.na(proporcion)) 0 else proporcion
    filas[[j]] <- list(
      componente = as.integer(j), autovalor = valor, proporcion = proporcion,
      acumulado = acumulado,
      # El criterio de Kaiser: quedarse con los que superan el autovalor medio.
      # Con datos tipificados el promedio es uno, que es de donde sale la regla
      # famosa; sin tipificar, uno no quiere decir nada.
      supera_el_promedio = valor > salida$total / length(salida$valores))
  }
  filas
}

tabla_de_cargas <- function(salida, columnas, cuantos) {
  filas <- list()
  for (k in seq_along(columnas)) {
    fila <- list(variable = columnas[k])
    total <- 0
    for (j in seq_len(min(cuantos, length(columnas)))) {
      carga <- salida$cargas[k, j]
      fila[[paste0("componente_", j)]] <- carga
      total <- total + carga * carga
    }
    # Cuánto de la variable queda representado en los componentes elegidos. Una
    # variable con un cos² bajo está en el gráfico pero no se ve: su posición es
    # proyección de otra cosa.
    fila$representada <- total
    filas[[k]] <- fila
  }
  filas
}

tabla_de_puntajes <- function(salida, unidades, cuantos) {
  filas <- list()
  for (i in seq_along(unidades)) {
    fila <- list(unidad = unidades[i])
    for (j in seq_len(min(cuantos, length(salida$valores)))) {
      fila[[paste0("componente_", j)]] <- salida$puntajes[i, j]
    }
    filas[[i]] <- fila
  }
  filas
}

# Las dos versiones al lado, que es el punto de todo este paso.
#
# Para cada una: cuánto explica el primer componente y con qué variable está
# correlacionado. Cuando la respuesta es «con una sola, y casi perfecto», el
# primer componente no es un resumen de nada: es esa variable con otro nombre.
contraste <- function(con, sin_, columnas) {
  filas <- list()
  etiquetas <- c("tipificada", "sin tipificar")
  salidas <- list(con, sin_)
  for (e in seq_along(etiquetas)) {
    salida <- salidas[[e]]
    primero <- salida$puntajes[, 1]
    correlaciones <- vapply(seq_along(columnas),
                            function(k) abs(correlacion(salida$base[, k], primero)),
                            numeric(1))
    mayor <- 1
    for (k in seq_along(columnas)) {
      if (correlaciones[k] > correlaciones[mayor]) mayor <- k
    }
    filas[[e]] <- list(
      version = etiquetas[e],
      autovalor_1 = salida$valores[1],
      proporcion_1 = salida$valores[1] / salida$total,
      proporcion_2 = if (length(salida$valores) > 1) salida$valores[2] / salida$total
                     else NA_real_,
      variable_mas_pegada = columnas[mayor],
      correlacion_con_esa = correlaciones[mayor],
      # Cuántas variables hacen falta para llegar al noventa por ciento.
      variables_hasta_el_90 = cuantas_hasta(salida, 0.90))
  }
  filas
}

cuantas_hasta <- function(salida, umbral) {
  acumulado <- 0
  for (j in seq_along(salida$valores)) {
    acumulado <- acumulado + salida$valores[j] / salida$total
    if (acumulado >= umbral) return(as.integer(j))
  }
  as.integer(length(salida$valores))
}

avisos_de_componentes <- function(con, sin_, columnas, parametros) {
  salida <- list()
  coma1 <- function(v) sub(".", ",", sprintf("%.1f", v), fixed = TRUE)
  coma3 <- function(v) sub(".", ",", sprintf("%.3f", v), fixed = TRUE)

  proporcion_sin <- sin_$valores[1] / sin_$total
  primero <- sin_$puntajes[, 1]
  correlaciones <- vapply(seq_along(columnas),
                          function(k) abs(correlacion(sin_$base[, k], primero)),
                          numeric(1))
  mayor <- which.max(correlaciones)
  if (correlaciones[mayor] > 0.95 && proporcion_sin > 0.80) {
    salida[[length(salida) + 1]] <- list(
      donde = "componentes",
      aviso = paste0(
        "Sin tipificar, el primer componente explica el ", coma1(100 * proporcion_sin),
        " % de la varianza y su correlación con «", columnas[mayor], "» es de ",
        coma3(correlaciones[mayor]), ". No es un resumen de las variables: es esa ",
        "variable con otro nombre, porque su unidad de medida es la más grande de la ",
        "tabla."))
  }

  ultimo <- con$valores[length(con$valores)]
  razon <- if (ultimo > 0) con$valores[1] / ultimo else NA_real_
  if (!is.na(razon) && razon > 1000) {
    salida[[length(salida) + 1]] <- list(
      donde = "componentes",
      aviso = paste0(
        "El último autovalor es ", sprintf("%.0f", razon), " veces más chico que el ",
        "primero: hay al menos una variable que es casi combinación lineal de las otras. ",
        "Los componentes del final no son ruido, son redundancia, y conviene sacar una ",
        "variable en vez de rotar."))
  }

  cargas <- tabla_de_cargas(con, columnas, parametros$componentes)
  flojas <- Filter(function(f) f$representada < 0.5, cargas)
  if (length(flojas) > 0) {
    cuales <- paste(vapply(flojas, function(f) paste0("«", f$variable, "»"),
                           character(1)), collapse = ", ")
    salida[[length(salida) + 1]] <- list(
      donde = "componentes",
      aviso = paste0(
        "Con ", parametros$componentes, " componentes, ", cuales, " queda(n) ",
        "representada(s) a menos de la mitad. En un gráfico de los dos primeros ejes ",
        "esas variables aparecen igual que las demás, y su posición no dice nada: está ",
        "proyectada desde una dirección que no se está mirando."))
  }
  salida
}

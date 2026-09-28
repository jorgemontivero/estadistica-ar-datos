# Paso 2: estandarización indirecta.
#
# La directa aplica **las tasas propias** sobre una estructura ajena. La
# indirecta hace lo contrario: aplica **las tasas de una referencia** sobre la
# estructura propia, y pregunta cuántos casos habría si esta población se
# muriera como la referencia.
#
#     esperados = Σ nᵢ · mᵢ(referencia)
#     razón     = observados / esperados
#
# La razón se llama RME cuando son muertes (SMR en inglés) y RIE cuando son
# casos nuevos. Un 1,20 quiere decir veinte por ciento más de lo que la
# estructura de edad hacía esperar.
#
# **Para qué sirve si ya está la directa.** Para lo que la directa no puede: la
# indirecta solo necesita el **total** de casos observados, no el detalle por
# edad. Sirve donde la directa se rompe —poblaciones chicas, causas poco
# frecuentes, casos por edad no publicados— porque no hay que estimar una tasa
# por grupo, que es justamente lo que se vuelve inestable con pocos casos.
#
# **Lo que se paga.** Dos razones indirectas no son estrictamente comparables
# entre sí, porque cada una está ajustada a su propia estructura. Se comparan
# contra la referencia, no entre ellas. En la práctica se las compara igual, y
# este paso deja al lado la tasa directa para que se vea cuánto se parecen.

# Las tasas específicas de la referencia, grupo por grupo.
#
# Si no se nombra ninguna población, la referencia es la suma de todas: es lo
# que hace la DEIS para comparar provincias contra el total del país.
tasas_de_referencia <- function(poblaciones, grupos, cuales) {
  if (length(cuales) > 0) {
    faltan <- cuales[!(cuales %in% names(poblaciones))]
    if (length(faltan) > 0) {
      stop(paste0("La referencia «", paste(faltan, collapse = ", "),
                  "» no está en los datos."), call. = FALSE)
    }
    elegidas <- cuales
  } else {
    elegidas <- ordenar(names(poblaciones))
  }

  tasas <- list()
  casos_totales <- 0
  expuestos_totales <- 0
  for (g in grupos) {
    casos <- sum(vapply(elegidas, function(p) poblaciones[[p]][[g]]$casos, numeric(1)))
    expuestos <- sum(vapply(elegidas, function(p) poblaciones[[p]][[g]]$expuestos,
                            numeric(1)))
    tasas[[g]] <- if (expuestos > 0) casos / expuestos else 0
    casos_totales <- casos_totales + casos
    expuestos_totales <- expuestos_totales + expuestos
  }
  list(nombre = if (length(cuales) > 0) paste(elegidas, collapse = " + ")
               else "el total de las poblaciones",
       tasas = tasas, casos = casos_totales, expuestos = expuestos_totales,
       cruda = if (expuestos_totales > 0) casos_totales / expuestos_totales else 0,
       es_el_total = length(cuales) == 0)
}

# Una fila por población: observados, esperados, la razón y su intervalo.
calcular_indirecta <- function(poblaciones, grupos, referencia, directas, parametros) {
  multiplicador <- parametros$multiplicador
  confianza <- parametros$confianza
  por_nombre <- list()
  for (f in directas) por_nombre[[f$poblacion]] <- f

  filas <- list()
  for (nombre in ordenar(names(poblaciones))) {
    celdas <- poblaciones[[nombre]]
    observados <- sum(vapply(grupos, function(g) celdas[[g]]$casos, numeric(1)))
    expuestos <- sum(vapply(grupos, function(g) celdas[[g]]$expuestos, numeric(1)))
    esperados <- sum(vapply(grupos, function(g) celdas[[g]]$expuestos * referencia$tasas[[g]],
                            numeric(1)))
    if (!(esperados > 0)) next

    # El intervalo de la razón sale del intervalo exacto del CONTEO observado,
    # dividido por los esperados. Los esperados se tratan como conocidos, que es
    # la convención: vienen de una población grande.
    ic <- ic_poisson(observados, confianza)
    razon <- observados / esperados
    directa <- por_nombre[[nombre]]
    indirecta <- razon * referencia$cruda * multiplicador

    filas[[length(filas) + 1]] <- list(
      poblacion = nombre,
      observados = as.integer(observados),
      esperados = esperados,
      razon = razon,
      razon_inferior = ic$inferior / esperados,
      razon_superior = ic$superior / esperados,
      distinta_de_uno = !(ic$inferior / esperados <= 1 &&
                            1 <= ic$superior / esperados),
      estandarizada_indirecta = indirecta,
      estandarizada_directa = if (!is.null(directa)) directa$estandarizada else NA_real_,
      diferencia_con_la_directa = if (!is.null(directa))
        indirecta - directa$estandarizada else NA_real_,
      cruda = if (expuestos > 0) observados / expuestos * multiplicador else NA_real_,
      rango_indirecto = NA_integer_, rango_directo = NA_integer_)
  }

  # Los dos ordenamientos, para poder decir si coinciden.
  nombres <- vapply(filas, function(f) f$poblacion, character(1))
  for (par in list(c("razon", "rango_indirecto"),
                   c("estandarizada_directa", "rango_directo"))) {
    valores <- vapply(filas, function(f) f[[par[1]]], numeric(1))
    utiles <- which(!is.na(valores))
    orden <- utiles[orden_por(valores[utiles], nombres[utiles])]
    for (i in seq_along(orden)) filas[[orden[i]]][[par[2]]] <- i
  }
  valores <- vapply(filas, function(f) f$razon, numeric(1))
  filas[orden_por(valores, nombres)]
}

avisos_de_indirecta <- function(filas, referencia, parametros) {
  salida <- list()
  if (referencia$es_el_total) {
    # Con la referencia igual al total, los esperados tienen que sumar los
    # observados: es una identidad, no una coincidencia.
    observados <- sum(vapply(filas, function(f) f$observados, numeric(1)))
    esperados <- sum(vapply(filas, function(f) f$esperados, numeric(1)))
    if (abs(observados - esperados) > 1e-6 * max(1, observados)) {
      salida[[length(salida) + 1]] <- list(
        donde = "indirecta",
        aviso = paste0(
          "Los casos esperados no suman los observados. Con la referencia igual al total ",
          "de las poblaciones eso es una identidad, así que si no cierra hay un error en ",
          "los datos o en la cuenta."))
    }
  }

  pocos <- Filter(function(f) f$observados < 10, filas)
  if (length(pocos) > 0) {
    salida[[length(salida) + 1]] <- list(
      donde = "indirecta",
      aviso = paste0(
        "Hay ", length(pocos), " población(es) con menos de diez casos observados. El ",
        "intervalo de la razón es exacto —no falla— pero sale tan ancho que no alcanza ",
        "para concluir gran cosa."))
  }

  flacos <- Filter(function(f) f$esperados < 5, filas)
  if (length(flacos) > 0) {
    salida[[length(salida) + 1]] <- list(
      donde = "indirecta",
      aviso = paste0(
        "Hay ", length(flacos), " población(es) con menos de cinco casos esperados. La ",
        "razón se vuelve muy sensible: un caso más o menos la mueve muchísimo."))
  }

  iguales <- Filter(function(f) !f$distinta_de_uno, filas)
  if (length(iguales) > 0) {
    salida[[length(salida) + 1]] <- list(
      donde = "indirecta",
      aviso = paste0(
        "En ", length(iguales), " de las ", length(filas), " poblaciones el intervalo de ",
        "la razón contiene al uno: su mortalidad no se distingue de la que la estructura ",
        "de edad hacía esperar."))
  }

  con_las_dos <- Filter(function(f) !is.na(f$rango_directo), filas)
  if (length(con_las_dos) > 0) {
    distancias <- vapply(con_las_dos, function(f) abs(f$rango_directo - f$rango_indirecto),
                         numeric(1))
    peor <- con_las_dos[[which.max(distancias)]]
    distancia <- max(distancias)
    if (distancia > 0) {
      salida[[length(salida) + 1]] <- list(
        donde = "indirecta",
        aviso = paste0(
          "El orden por razón indirecta y el orden por tasa directa no son el mismo: ",
          "«", peor$poblacion, "» está ", distancia, " puesto(s) más arriba en uno que ",
          "en el otro. Son dos preguntas distintas y no tienen por qué coincidir; cuando ",
          "coinciden es porque las tasas específicas van casi todas para el mismo lado."))
    }
  }
  salida
}

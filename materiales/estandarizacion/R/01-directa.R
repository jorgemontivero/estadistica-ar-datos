# Paso 1: estandarización directa.
#
# La pregunta que contesta es una sola: **¿cuánto sería la tasa de cada
# población si todas tuvieran la misma estructura por edad?**
#
# Sin eso, dos tasas crudas no se pueden comparar. Una población más vieja tiene
# más muertes aunque se muera menos a cada edad, y eso no es un detalle: en los
# datos de este proyecto, la jurisdicción con la tasa cruda **más alta** del
# país es la que tiene la **segunda más baja** una vez ajustada.
#
# La cuenta es un promedio ponderado de las tasas específicas por edad, con los
# pesos de la población estándar en vez de los propios:
#
#     tasa ajustada = Σ (wᵢ / W) · (dᵢ / nᵢ)
#
# Toda la idea está en esa línea. Lo que tiene trabajo es el intervalo: una suma
# ponderada de Poisson no es Poisson, y por eso va el método de Fay-Feuer, que
# está en comun.R.

calcular <- function(poblaciones, grupos, pesos, parametros) {
  multiplicador <- parametros$multiplicador
  confianza <- parametros$confianza
  total_peso <- sum(vapply(grupos, function(g) pesos[[g]], numeric(1)))
  if (!(total_peso > 0)) {
    stop("Los pesos de la población estándar suman cero.", call. = FALSE)
  }

  filas <- list()
  for (nombre in names(poblaciones)) {
    celdas <- poblaciones[[nombre]]
    casos <- sum(vapply(grupos, function(g) celdas[[g]]$casos, numeric(1)))
    expuestos <- sum(vapply(grupos, function(g) celdas[[g]]$expuestos, numeric(1)))
    if (!(expuestos > 0)) next

    # El promedio de las tasas específicas, ponderado por la estructura
    # estándar. Y la varianza de esa suma, tratando cada conteo como Poisson:
    # Var(Σ wᵢ dᵢ/nᵢ) = Σ (wᵢ/nᵢ)² dᵢ.
    ajustada <- 0
    varianza <- 0
    mayor_peso <- 0
    for (g in grupos) {
      expuestos_g <- celdas[[g]]$expuestos
      if (!(expuestos_g > 0)) next
      peso <- pesos[[g]] / total_peso
      tasa <- celdas[[g]]$casos / expuestos_g
      ajustada <- ajustada + peso * tasa
      coeficiente <- peso / expuestos_g
      varianza <- varianza + coeficiente * coeficiente * celdas[[g]]$casos
      mayor_peso <- max(mayor_peso, coeficiente)
    }

    ic <- ic_fay_feuer(ajustada, varianza, mayor_peso, confianza)
    cruda <- casos / expuestos
    ic_cruda <- ic_poisson(casos, confianza)
    ultimo <- celdas[[grupos[length(grupos)]]]$expuestos / expuestos

    filas[[length(filas) + 1]] <- list(
      poblacion = nombre,
      casos = as.integer(casos),
      expuestos = as.integer(expuestos),
      proporcion_en_el_grupo_mayor = ultimo,
      cruda = cruda * multiplicador,
      cruda_inferior = ic_cruda$inferior / expuestos * multiplicador,
      cruda_superior = ic_cruda$superior / expuestos * multiplicador,
      estandarizada = ajustada * multiplicador,
      estandarizada_inferior = ic$inferior * multiplicador,
      estandarizada_superior = ic$superior * multiplicador,
      cambio_relativo = if (cruda > 0) ajustada / cruda - 1 else NA_real_,
      # Cuántos casos habría con la misma gente y la estructura estándar.
      casos_con_la_estructura_estandar = ajustada * expuestos)
  }

  poner_rangos(filas)
}

# El lugar de cada población en los dos ordenamientos, y cuánto se movió.
#
# El orden se rompe por nombre cuando dos tasas dan exactamente igual, para que
# los dos motores escriban las mismas filas en el mismo lugar.
poner_rangos <- function(filas) {
  nombres <- vapply(filas, function(f) f$poblacion, character(1))
  for (par in list(c("cruda", "rango_crudo"),
                   c("estandarizada", "rango_estandarizado"))) {
    valores <- vapply(filas, function(f) f[[par[1]]], numeric(1))
    orden <- orden_por(valores, nombres)
    for (i in seq_along(orden)) filas[[orden[i]]][[par[2]]] <- i
  }
  for (i in seq_along(filas)) {
    filas[[i]]$cambio_de_rango <- filas[[i]]$rango_crudo - filas[[i]]$rango_estandarizado
  }
  valores <- vapply(filas, function(f) f$estandarizada, numeric(1))
  filas[orden_por(valores, nombres)]
}

# El detalle que hay detrás de cada tasa ajustada.
#
# Es la tabla que hay que mirar cuando el resultado sorprende: ahí se ve si la
# diferencia viene de una edad en particular o está repartida.
por_edad <- function(poblaciones, grupos, pesos, parametros) {
  multiplicador <- parametros$multiplicador
  total_peso <- sum(vapply(grupos, function(g) pesos[[g]], numeric(1)))
  filas <- list()
  for (nombre in ordenar(names(poblaciones))) {
    celdas <- poblaciones[[nombre]]
    expuestos_totales <- sum(vapply(grupos, function(g) celdas[[g]]$expuestos, numeric(1)))
    for (g in grupos) {
      expuestos <- celdas[[g]]$expuestos
      casos <- celdas[[g]]$casos
      peso <- pesos[[g]] / total_peso
      tasa <- if (expuestos > 0) casos / expuestos else NA_real_
      filas[[length(filas) + 1]] <- list(
        poblacion = nombre, grupo_edad = g,
        casos = as.integer(casos), expuestos = as.integer(expuestos),
        proporcion_propia = if (expuestos_totales > 0) expuestos / expuestos_totales
                            else NA_real_,
        peso_estandar = peso,
        tasa_especifica = if (!is.na(tasa)) tasa * multiplicador else NA_real_,
        aporte = if (!is.na(tasa)) peso * tasa * multiplicador else NA_real_)
    }
  }
  filas
}

# Lo que hay que decir sobre las tasas, además de los números.
avisos_de_directa <- function(filas, detalle, parametros) {
  salida <- list()

  # El hallazgo, si está: una población que cambia de punta a punta.
  vuelcos <- Filter(function(f) abs(f$cambio_de_rango) >= length(filas) %/% 2, filas)
  if (length(vuelcos) > 0) {
    cambios <- vapply(vuelcos, function(f) abs(f$cambio_de_rango), numeric(1))
    peor <- vuelcos[[which.max(cambios)]]
    salida[[length(salida) + 1]] <- list(
      donde = "estandarización",
      aviso = paste0(
        "«", peor$poblacion, "» pasa del puesto ", peor$rango_crudo, " al ",
        peor$rango_estandarizado, " al ajustar por edad. La tasa cruda y la ajustada no ",
        "dicen lo mismo: dicen cosas distintas, y comparar poblaciones con la cruda es ",
        "comparar estructuras de edad."))
  }

  # Grupos con pocos casos: ahí la directa se vuelve inestable.
  flacos <- list()
  for (f in detalle) {
    if (f$expuestos > 0 && f$casos < 5) {
      previo <- flacos[[f$poblacion]]
      flacos[[f$poblacion]] <- if (is.null(previo)) 1L else previo + 1L
    }
  }
  if (length(flacos) > 0) {
    nombres <- ordenar(names(flacos))
    cuantos <- vapply(nombres, function(n) flacos[[n]], integer(1))
    peor <- nombres[which.max(cuantos)]
    salida[[length(salida) + 1]] <- list(
      donde = "estandarización",
      aviso = paste0(
        "Hay ", length(flacos), " población(es) con algún grupo de edad de menos de ",
        "cinco casos —«", peor, "» tiene ", flacos[[peor]], "—. Una tasa específica ",
        "calculada con cuatro muertes es muy inestable y la ajustada la arrastra: ahí ",
        "conviene mirar también la indirecta, que no necesita estimar una tasa por grupo."))
  }

  vacios <- Filter(function(f) f$expuestos == 0, detalle)
  if (length(vacios) > 0) {
    salida[[length(salida) + 1]] <- list(
      donde = "datos",
      aviso = paste0(
        "Hay ", length(vacios), " celda(s) sin nadie expuesto. Ese grupo no aporta nada a ",
        "la tasa ajustada de esa población, y su peso estándar queda sin usar: la suma de ",
        "los pesos efectivos no llega a uno y la tasa sale más baja de lo que debería."))
  }

  # Intervalos que se pisan con el de arriba: el orden no está establecido.
  pisados <- 0
  if (length(filas) > 1) {
    for (i in seq_len(length(filas) - 1)) {
      if (filas[[i]]$estandarizada_inferior <= filas[[i + 1]]$estandarizada_superior) {
        pisados <- pisados + 1
      }
    }
  }
  if (pisados > 0) {
    salida[[length(salida) + 1]] <- list(
      donde = "estandarización",
      aviso = paste0(
        "En ", pisados, " de los ", length(filas) - 1, " escalones del ranking el ",
        "intervalo de una población se pisa con el de la siguiente. Un ranking se lee ",
        "como si cada puesto estuviera decidido, y la mayoría de estos no lo están."))
  }
  salida
}

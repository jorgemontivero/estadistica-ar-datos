# Paso 4: el informe, escrito en castellano.
#
# Lo mismo que hacen los otros descargables de la serie: lo que el proyecto
# calculó, redactado para pegar. Ningún número aparece acá si no está también
# en un CSV, y ninguna conclusión se escribe más fuerte de lo que la tabla la
# sostiene.

por_nombre <- function(filas, clave, valor) {
  for (f in filas) if (!is.null(f[[clave]]) && f[[clave]] == valor) return(f)
  NULL
}

# El elemento que maximiza una función, con el primero ganando los empates:
# `max(..., key=...)` de Python hace lo mismo.
el_mayor <- function(filas, de_cual) {
  valores <- vapply(filas, de_cual, numeric(1))
  filas[[which.max(valores)]]
}

el_menor <- function(filas, de_cual) {
  valores <- vapply(filas, de_cual, numeric(1))
  filas[[which.min(valores)]]
}

redactar <- function(parametros, base, tasas, identidad_, contraste_, ingresos, deciles,
                     ingresos_grupo, informal, avisos) {
  conf <- paste0(numero_texto(parametros$confianza * 100, 0), " %")
  periodo <- if (nchar(base$periodo) > 0) base$periodo else "el período del archivo"
  lineas <- c(paste0("# Mercado de trabajo, ", periodo), "")

  lineas <- c(lineas, paste0(
    "Fuente: `", parametros$archivo, "`, ", base$columnas_del_archivo,
    " columnas. Quedaron ", numero_texto(base$n, 0), " personas en ",
    numero_texto(base$hogares, 0), " hogares de ", base$aglomerados,
    " aglomerados, que representan a ", numero_texto(base$peso_total, 0),
    " habitantes."), "")

  # Lo primero que hay que leer, porque es lo que se hace mal.
  correcto <- if (length(contraste_) > 0) contraste_[[1]] else NULL
  los_dos <- por_nombre(contraste_, "caso",
                        "Con el ponderador general y los que no declaran adentro")
  solo_peso <- por_nombre(contraste_, "caso", "Con el ponderador general")
  if (!is.null(correcto) && !is.null(los_dos) && !is.null(solo_peso)) {
    lineas <- c(lineas, paste0(
      "> **El mismo ingreso medio, tres veces.** Con `", correcto$ponderador,
      "` y sacando a los que no declaran da ", pesos_texto(correcto$media),
      ". Cambiando nada más que el ponderador da ", pesos_texto(solo_peso$media),
      ", un ", porcentaje(abs(solo_peso$diferencia_relativa), 1),
      " menos. Cambiando además el filtro —dejando adentro al −9, que en la EPH ",
      "quiere decir «no responde» y no «menos nueve pesos»— da ",
      pesos_texto(los_dos$media), ", un ",
      porcentaje(abs(los_dos$diferencia_relativa), 1),
      " menos. Son los mismos datos y las mismas personas."), "")
  }

  # ------------------------------------------------------------- las tasas
  lineas <- c(lineas, "## Las cuatro tasas", "")
  lineas <- c(lineas, paste0(
    "Cada una tiene su propio denominador, y no es un detalle de presentación: la ",
    "desocupación se calcula sobre la población económicamente activa y no sobre ",
    "la población."), "")
  for (t in tasas) {
    lineas <- c(lineas, paste0(
      "- **Tasa de ", t$tasa, ":** ", porcentaje(t$valor, 2), ", IC ", conf, " [",
      porcentaje(t$inferior, 2), "; ", porcentaje(t$superior, 2), "]. ", t$numerador,
      " sobre ", tolower(t$denominador), ", ", numero_texto(t$n_denominador, 0),
      " casos."))
  }
  lineas <- c(lineas, "")

  if (!is.null(identidad_)) {
    lineas <- c(lineas, paste0(
      "Las tres primeras tienen que cerrar entre sí: empleo = actividad × ",
      "(1 − desocupación). Da ", porcentaje(identidad_$empleo_por_la_identidad, 4),
      " contra el ", porcentaje(identidad_$empleo_observado, 4),
      " calculado aparte. Es la única comprobación que no depende de tener razón ",
      "sobre nada más."), "")
  }

  con_sin_ponderar <- Filter(function(t) !is.na(t$sin_ponderar), tasas)
  if (length(con_sin_ponderar) > 0) {
    peor <- el_mayor(con_sin_ponderar, function(t) abs(t$diferencia_con_la_ponderada))
    lineas <- c(lineas, paste0(
      "Contar casos en vez de ponderar cambia las tasas. Donde más cambia es en la de ",
      peor$tasa, ": ", porcentaje(peor$sin_ponderar, 2), " sin ponderar contra ",
      porcentaje(peor$valor, 2), " ponderando. La EPH no es una muestra ",
      "autoponderada, y un caso de un aglomerado chico no vale lo mismo que uno del ",
      "conurbano."), "")
  }

  con_deff <- Filter(function(t) !is.na(t$deff), tasas)
  if (length(con_deff) > 0) {
    peor <- el_mayor(con_deff, function(t) t$deff)
    lineas <- c(lineas, paste0(
      "El efecto de diseño más alto es el de la tasa de ", peor$tasa, ": ",
      numero_texto(peor$deff, 2), ". Los ", numero_texto(peor$n_denominador, 0),
      " casos de su denominador valen como ", numero_texto(peor$n_efectivo, 0),
      ". Y está calculado con el hogar como unidad primaria, que es lo más fino que ",
      "trae el archivo público: el conglomerado de verdad es el radio censal, así ",
      "que el efecto real es todavía mayor y estos intervalos son una cota ",
      "optimista."), "")
  }

  # ---------------------------------------------------------- los ingresos
  lineas <- c(lineas, "## Los ingresos de la ocupación principal", "")
  valor <- list()
  for (f in ingresos) valor[[f$estadistico]] <- f$valor
  if (length(valor) > 0) {
    lineas <- c(lineas, paste0(
      "Sobre ", numero_texto(valor[["casos"]], 0), " ocupados con ingreso declarado, ",
      "que representan a ", numero_texto(valor[["población representada"]], 0),
      " personas. La media es ", pesos_texto(valor[["media"]]), ", IC ", conf, " [",
      pesos_texto(valor[["límite inferior"]]), "; ",
      pesos_texto(valor[["límite superior"]]), "]. La mediana es ",
      pesos_texto(valor[["mediana"]]), "."), "")
    lineas <- c(lineas, paste0(
      "El décimo decil gana ",
      numero_texto(valor[["razón entre el décimo y el primer decil"]], 1),
      " veces lo que el primero. El primer decil corta en ",
      pesos_texto(valor[["primer decil"]]), " y el noveno en ",
      pesos_texto(valor[["noveno decil"]]), "."), "")
  }

  if (length(deciles) > 0) {
    lineas <- c(lineas, "| Decil | Corte superior | Ingreso medio | Participación |",
                "| --- | --- | --- | --- |")
    for (d in deciles) {
      corte <- if (!is.na(d$corte_superior)) pesos_texto(d$corte_superior) else "—"
      lineas <- c(lineas, paste0(
        "| ", d$decil, " | ", corte, " | ", pesos_texto(d$ingreso_medio), " | ",
        porcentaje(d$participacion, 1), " |"))
    }
    lineas <- c(lineas, "")
  }

  # ------------------------------------------------- el contraste, en tabla
  if (length(contraste_) > 0) {
    lineas <- c(lineas, "## El mismo promedio, de cinco maneras", "",
                "| Cómo se calculó | Ponderador | El −9 | El 0 | Media | Diferencia |",
                "| --- | --- | --- | --- | --- | --- |")
    for (i in seq_along(contraste_)) {
      c_ <- contraste_[[i]]
      # La primera fila es la referencia. Que la segunda diga «la misma» es el
      # hallazgo, así que se escribe con todas las letras en vez de dejar un
      # guion que se confunda con el de arriba.
      dif <- if (i == 1) "referencia"
             else if (abs(c_$diferencia) < 1e-9) "**exactamente la misma**"
             else porcentaje(c_$diferencia_relativa, 1)
      lineas <- c(lineas, paste0(
        "| ", c_$caso, " | `", c_$ponderador, "` | ", c_$que_hace_con_el_menos_nueve,
        " | ", c_$que_hace_con_el_cero, " | ", pesos_texto(c_$media), " | ", dif, " |"))
    }
    lineas <- c(lineas, "", paste0(
      "Las dos primeras filas dan lo mismo, y eso es lo importante: con el ponderador ",
      "de ingreso, el −9 ya está sacado, porque el INDEC le pone el peso en cero. El ",
      "filtro que nunca se escribió no hace falta… hasta que el ponderador no está."),
      "")
  }

  # ------------------------------------------------------- por grupo
  sexos <- Filter(function(f) f$corte == "Sexo", ingresos_grupo)
  if (length(sexos) == 2) {
    varon <- por_nombre(sexos, "grupo", "Varón")
    mujer <- por_nombre(sexos, "grupo", "Mujer")
    if (!is.null(varon) && !is.null(mujer)) {
      lineas <- c(lineas, "### Por sexo", "", paste0(
        "Los varones ocupados declaran en promedio ", pesos_texto(varon$media),
        " y las mujeres ", pesos_texto(mujer$media), ": ellas ganan el ",
        porcentaje(mujer$media / varon$media, 1),
        " de lo que ganan ellos. Es una diferencia de ingresos entre ocupados, no una ",
        "diferencia de salario a igual tarea: la EPH no alcanza para lo segundo."), "")
    }
  }

  # ---------------------------------------------------------- informalidad
  total_informal <- por_nombre(informal, "corte", "Total")
  if (!is.null(total_informal)) {
    lineas <- c(lineas, "## Informalidad", "", paste0(
      "El ", porcentaje(total_informal$tasa, 2), " de los asalariados no tiene ",
      "descuento jubilatorio, IC ", conf, " [", porcentaje(total_informal$inferior, 2),
      "; ", porcentaje(total_informal$superior, 2), "]. Son ",
      numero_texto(total_informal$sin_descuento, 0), " personas sobre ",
      numero_texto(total_informal$asalariados, 0), " asalariados."), "")
    otros <- Filter(function(f) f$corte != "Total", informal)
    if (length(otros) > 0) {
      peor <- el_mayor(otros, function(f) f$tasa)
      mejor <- el_menor(otros, function(f) f$tasa)
      lineas <- c(lineas, paste0(
        "El grupo con más informalidad es «", peor$grupo, "» (",
        tolower(peor$corte), "), con ", porcentaje(peor$tasa, 1), "; el que menos, «",
        mejor$grupo, "» (", tolower(mejor$corte), "), con ",
        porcentaje(mejor$tasa, 1), "."), "")
    }
  }

  # --------------------------------------------------------------- avisos
  if (length(avisos) > 0) {
    lineas <- c(lineas, "## Qué revisar antes de publicar esto", "")
    for (a in avisos) {
      donde <- a$donde
      lineas <- c(lineas, paste0("- **", toupper(substring(donde, 1, 1)),
                                 substring(donde, 2), ".** ", a$aviso))
    }
    lineas <- c(lineas, "")
  }

  lineas
}

# Paso 4: el informe, escrito en castellano.
#
# Lo mismo que hacen los otros descargables de la serie: lo que el proyecto
# calculó, redactado para pegar. Ningún número aparece acá si no está también
# en un CSV, y ninguna conclusión se escribe más fuerte de lo que la tabla la
# sostiene.

QUE <- list(media = "la media", total = "el total", proporcion = "la proporción")

cifra <- function(v, decimales = NULL) {
  if (is.null(decimales)) decimales <- decimales_de(v)
  numero_texto(v, decimales)
}

porcentaje <- function(v) paste0(numero_texto(v * 100, 1), " %")

mayuscula <- function(x) paste0(toupper(substring(x, 1, 1)), substring(x, 2))

redactar <- function(parametros, seleccion, ponderadores, estimaciones, por_estrato,
                     cobertura, poblacion) {
  conf <- paste0(numero_texto(parametros$confianza * 100, 0), " %")
  lineas <- c("# Muestreo", "")
  lineas <- c(lineas, paste0(
    "Marco: ", cifra(poblacion, 0), " unidades. Muestra: ", seleccion$n,
    " en cada uno de los ", length(seleccion$disenos), " diseños. Semilla ",
    parametros$semilla, "."), "")

  # El caso que el proyecto quiere mostrar: cuando el intervalo ingenuo se
  # equivoca y el del diseño no.
  fallados <- Filter(function(e) {
    e$diseno == "bietápico" && isTRUE(e$contiene_al_verdadero) && !isTRUE(e$contiene_ingenuo)
  }, estimaciones)
  if (length(fallados) > 0) {
    e <- fallados[[1]]
    lineas <- c(lineas, paste0(
      "> **El intervalo que ignora el diseño no contiene al valor verdadero.** Para ",
      QUE[[e$que]], " de `", e$variable, "`, el valor de la población es ",
      cifra(e$verdadero), ". El intervalo ", conf, " calculado con el diseño va de ",
      cifra(e$inferior), " a ", cifra(e$superior), " y lo contiene. El que sale de tratar ",
      "la muestra como si fuera aleatoria simple va de ", cifra(e$inferior_ingenuo), " a ",
      cifra(e$superior_ingenuo), " y no. Es la misma muestra y la misma estimación: lo ",
      "único que cambia es la fórmula del error estándar."), "")
  }

  lineas <- c(lineas, "## Cómo se sacó la muestra", "")
  lineas <- c(lineas, paste0(
    "El diseño principal es bietápico: ", parametros$conglomerados_por_estrato,
    " conglomerados por estrato y ", parametros$hogares_por_conglomerado,
    " unidades por conglomerado."), "")
  for (d in seleccion$detalle_bietapico) {
    lineas <- c(lineas, paste0("- **", d$estrato, ".** ", d$conglomerados_elegidos, " de ",
                               d$conglomerados_en_el_marco, " conglomerados."))
  }
  lineas <- c(lineas, "", paste0(
    "El sistemático usó un intervalo de ", cifra(seleccion$intervalo, 4),
    " con arranque en ", cifra(seleccion$arranque, 4), "."), "")

  p <- ponderadores$despues
  lineas <- c(lineas, "## Los ponderadores", "")
  lineas <- c(lineas, paste0(
    "Suman ", cifra(p$suma, 0), " sobre una población de ", cifra(p$poblacion, 0),
    ". Van de ", cifra(p$minimo), " a ", cifra(p$maximo),
    ", con un coeficiente de variación de ",
    numero_texto(p$coeficiente_de_variacion, 3), "."), "")
  lineas <- c(lineas, paste0(
    "El efecto de Kish —lo que cuestan los pesos desiguales por sí solos— es ",
    numero_texto(p$deff_de_kish, 3), ", o sea que la muestra de ", p$n,
    " vale como una de ", cifra(p$n_efectivo_de_kish, 0),
    " antes de contar lo que cuesta el conglomerado."), "")

  lineas <- c(lineas, "## Las estimaciones, diseño por diseño", "")
  variables <- character(0)
  for (e in estimaciones) {
    if (!(e$variable %in% variables)) variables <- c(variables, e$variable)
  }
  for (variable in variables) {
    del_grupo <- Filter(function(e) e$variable == variable, estimaciones)
    lineas <- c(lineas, paste0(
      "**", mayuscula(QUE[[del_grupo[[1]]$que]]), " de `", variable, "`** (verdadera: ",
      cifra(del_grupo[[1]]$verdadero), ")"), "")
    for (e in del_grupo) {
      lineas <- c(lineas, paste0(
        "- **", e$diseno, ".** ", cifra(e$estimacion), ", IC ", conf, " [",
        cifra(e$inferior), "; ", cifra(e$superior), "], deff ",
        numero_texto(e$deff, 2), ", n efectivo ", cifra(e$n_efectivo, 0), "."))
    }
    lineas <- c(lineas, "")
  }

  if (length(por_estrato) > 0) {
    lineas <- c(lineas, paste0("## La media de `", parametros$variable,
                               "` dentro de cada estrato"), "")
    for (e in por_estrato) {
      lineas <- c(lineas, paste0(
        "- **", e$estrato, ".** n = ", e$n, " en ", e$unidades_primarias,
        " conglomerados. ", cifra(e$estimacion), ", IC ", conf, " [", cifra(e$inferior),
        "; ", cifra(e$superior), "]. Verdadera: ", cifra(e$verdadero), "."))
    }
    lineas <- c(lineas, "")
  }

  if (!is.null(cobertura)) {
    lineas <- c(lineas, "## Cuántas veces le acierta cada intervalo", "")
    lineas <- c(lineas, paste0(
      "Sacando la muestra ", cobertura$replicas,
      " veces y armando los dos intervalos cada vez:"), "")
    lineas <- c(lineas, paste0(
      "- **Con el diseño:** cubre el valor verdadero el ",
      porcentaje(cobertura$cobertura_del_diseno), " de las veces, contra el ",
      porcentaje(cobertura$nominal), " que promete."))
    lineas <- c(lineas, paste0(
      "- **Ignorando el diseño:** cubre el ", porcentaje(cobertura$cobertura_ingenua), "."))
    lineas <- c(lineas, "", paste0(
      "El intervalo ingenuo es en promedio ",
      numero_texto(cobertura$ancho_medio_del_diseno / cobertura$ancho_medio_ingenuo, 1),
      " veces más angosto, y esa es exactamente la precisión que no tiene."), "")
  }

  lineas
}

# Paso 4: el informe, escrito en castellano.
#
# Lo mismo que hacen los otros descargables de la serie: lo que el proyecto
# calculó, redactado para pegar. Ningún número aparece acá si no está también
# en un CSV, y ninguna conclusión se escribe más fuerte de lo que la tabla la
# sostiene.

mayuscula <- function(x) paste0(toupper(substring(x, 1, 1)), substring(x, 2))

cifra <- function(v, decimales = 3) numero_texto(v, decimales)

redactar <- function(parametros, unidades, columnas, filas_componentes, filas_cargas,
                     filas_contraste, filas_siluetas, filas_grupos, nulo, ca,
                     filas_ejes, filas_puntos, avisos, columnas_tabla) {
  lineas <- c("# Análisis multivariado", "")
  lineas <- c(lineas, paste0(
    length(unidades), " unidades y ", length(columnas), " variables. Enlace: «",
    parametros$enlace, "», ", parametros$conglomerados, " conglomerados."), "")

  tipificada <- filas_contraste[[1]]
  cruda <- filas_contraste[[2]]
  lineas <- c(lineas, paste0(
    "> **Tipificar o no tipificar no es un detalle del preprocesamiento: es el ",
    "análisis.** Sin tipificar, el primer componente explica el ",
    porcentaje(cruda$proporcion_1), " de la varianza y su correlación con «",
    cruda$variable_mas_pegada, "» es de ", cifra(cruda$correlacion_con_esa),
    ": no resume nada, es esa variable con otro nombre. Tipificando, el primero explica ",
    "el ", porcentaje(tipificada$proporcion_1), " y hacen falta ",
    tipificada$variables_hasta_el_90, " componentes para llegar al 90 %."), "")

  # ------------------------------------------------------- los componentes
  lineas <- c(lineas, "## Los componentes", "",
              "| Componente | Autovalor | Explica | Acumulado |",
              "| --- | --- | --- | --- |")
  for (f in filas_componentes) {
    lineas <- c(lineas, paste0(
      "| ", f$componente, " | ", cifra(f$autovalor), " | ", porcentaje(f$proporcion),
      " | ", porcentaje(f$acumulado), " |"))
  }
  lineas <- c(lineas, "")

  cuantos <- sum(vapply(filas_componentes, function(f) f$supera_el_promedio, logical(1)))
  lineas <- c(lineas, paste0(
    "Con el criterio de quedarse con los que superan el autovalor promedio —que con ",
    "datos tipificados es uno— quedan ", cuantos, ". Es una regla, no un resultado: no ",
    "hay nada en los datos que diga que ", cuantos, " es el número."), "")

  # Las cargas del primer componente, ordenadas.
  primeras_valores <- vapply(filas_cargas, function(f) {
    v <- f[["componente_1"]]
    if (is.null(v)) 0 else abs(v)
  }, numeric(1))
  primeras <- filas_cargas[order(-primeras_valores, method = "radix")]
  lineas <- c(lineas, "Lo que pesa en el primer componente, de mayor a menor:", "")
  for (f in primeras) {
    carga <- f[["componente_1"]]
    if (is.null(carga)) next
    lineas <- c(lineas, paste0("- **", f$variable, ":** ", cifra(carga)))
  }
  lineas <- c(lineas, "")

  flojas <- Filter(function(f) f$representada < 0.5, filas_cargas)
  if (length(flojas) > 0) {
    cuales <- paste(vapply(flojas, function(f) paste0("«", f$variable, "»"),
                           character(1)), collapse = ", ")
    lineas <- c(lineas, paste0(
      "Con los componentes elegidos, ", cuales, " queda(n) representada(s) a menos de la ",
      "mitad. En un gráfico de los dos primeros ejes esas variables se ven igual que las ",
      "demás y su posición no dice nada."), "")
  }

  # ------------------------------------------------------ los conglomerados
  elegido <- parametros$enlace
  lineas <- c(lineas, "## Los conglomerados", "",
              "| Enlace | Grupos | El mayor | Silueta | Negativas | Acuerdo |",
              "| --- | --- | --- | --- | --- | --- |")
  for (f in filas_siluetas) {
    lineas <- c(lineas, paste0(
      "| ", f$enlace, " | ", f$grupos, " | ", f$mayor, " | ", cifra(f$silueta), " | ",
      f$negativas, " | ", cifra(f$acuerdo_con_el_elegido), " |"))
  }
  lineas <- c(lineas, "", paste0(
    "La última columna es el índice de Rand ajustado contra «", elegido, "», que es el ",
    "enlace elegido: vale uno cuando las dos particiones son la misma. Los cuatro ",
    "árboles salen de la misma matriz de distancias, y lo único que cambia entre ellos ",
    "es cómo se mide la distancia entre dos grupos ya armados."), "")

  lineas <- c(lineas, "### Contra el azar", "", paste0(
    "Agrupar siempre devuelve grupos. Para saber si estos dicen algo, el proyecto ",
    "desordena cada variable por separado —cada columna conserva exactamente sus ",
    "valores y se rompe la relación entre ellas—, vuelve a agrupar y mira la silueta. ",
    "Con ", nulo$replicas, " corrimientos:"), "")
  lineas <- c(lineas, paste0("- **Datos de verdad:** ", cifra(nulo$silueta_real)))
  lineas <- c(lineas, paste0("- **Desordenados:** de ", cifra(nulo$menor), " a ",
                             cifra(nulo$mayor), ", con mediana ", cifra(nulo$mediana)))
  lineas <- c(lineas, paste0("- **Cuántos igualan o superan al real:** ",
                             nulo$nulos_que_igualan_o_superan, " de ", nulo$replicas), "")
  if (nulo$nulos_que_igualan_o_superan == 0) {
    lineas <- c(lineas, paste0(
      "Ninguno lo alcanza, así que hay estructura. Eso **no** dice que los grupos sean ",
      "los correctos ni que sean los que hay: dice que no son un invento del método."))
  } else {
    lineas <- c(lineas, paste0(
      "Los datos desordenados llegan igual de lejos. Los grupos que salen son del ",
      "método y no de los datos."))
  }
  lineas <- c(lineas, "")

  numeros <- sort(unique(vapply(filas_grupos, function(f) f[[elegido]], numeric(1))))
  lineas <- c(lineas, paste0("Los ", length(numeros), " grupos con «", elegido, "»:"), "")
  for (numero in numeros) {
    miembros <- vapply(Filter(function(f) f[[elegido]] == numero, filas_grupos),
                       function(f) f$unidad, character(1))
    lineas <- c(lineas, paste0("- **Grupo ", numero, "** (", length(miembros), "): ",
                               paste(miembros, collapse = ", ")))
  }
  lineas <- c(lineas, "")

  # --------------------------------------------------- las correspondencias
  lineas <- c(lineas, "## Las correspondencias", "", paste0(
    "La tabla cruza ", length(unidades), " filas con ", length(columnas_tabla),
    " columnas y suma ", numero_texto(ca$total, 0), " casos. El χ² de independencia es ",
    numero_texto(ca$chi2, 1), " con ", ca$gl, " grados de libertad, p ", p_texto(ca$p),
    ", y la inercia total —que es ese χ² dividido por el total— es ",
    cifra(ca$inercia_total, 4), "."), "")
  lineas <- c(lineas, "| Eje | Inercia | Explica | Acumulado |", "| --- | --- | --- | --- |")
  for (f in filas_ejes) {
    lineas <- c(lineas, paste0(
      "| ", f$eje, " | ", cifra(f$inercia, 4), " | ", porcentaje(f$proporcion), " | ",
      porcentaje(f$acumulado), " |"))
  }
  lineas <- c(lineas, "")

  columnas_ca <- Filter(function(p) p$tipo == "columna", filas_puntos)
  if (length(columnas_ca) > 0 && !is.null(columnas_ca[[1]][["eje_1"]])) {
    valores <- vapply(columnas_ca, function(p) p[["eje_1"]], numeric(1))
    orden <- columnas_ca[order(valores, method = "radix")]
    lineas <- c(lineas, paste0(
      "Sobre el primer eje, las columnas se ordenan de «", orden[[1]]$punto, "» (",
      cifra(orden[[1]][["eje_1"]]), ") a «", orden[[length(orden)]]$punto, "» (",
      cifra(orden[[length(orden)]][["eje_1"]]), "). Un punto lejos del centro no es ",
      "«mucho»: es **distinto del perfil promedio**, y una fila con el reparto ",
      "exactamente igual al del total cae en el origen por grande que sea."), "")
    filas_ca <- Filter(function(p) p$tipo == "fila", filas_puntos)
    suyos <- vapply(filas_ca, function(p) p[["eje_1"]], numeric(1))
    extremos <- filas_ca[order(suyos, method = "radix")]
    lineas <- c(lineas, paste0(
      "Del lado de «", orden[[1]]$punto, "» queda «", extremos[[1]]$punto, "» (",
      cifra(extremos[[1]][["eje_1"]]), "); del otro, «",
      extremos[[length(extremos)]]$punto, "» (",
      cifra(extremos[[length(extremos)]][["eje_1"]]), ")."), "")
  }

  # --------------------------------------------------------------- avisos
  if (length(avisos) > 0) {
    lineas <- c(lineas, "## Qué revisar antes de publicar esto", "")
    for (a in avisos) {
      lineas <- c(lineas, paste0("- **", mayuscula(a$donde), ".** ", a$aviso))
    }
    lineas <- c(lineas, "")
  }

  lineas
}

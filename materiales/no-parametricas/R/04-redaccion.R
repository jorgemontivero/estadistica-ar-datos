# Paso 4: el informe, escrito en castellano.
#
# Lo mismo que hacen los otros descargables de la serie: lo que el proyecto
# calculó, redactado para pegar. Ningún número aparece acá si no está también
# en un CSV, y ninguna conclusión se escribe más fuerte de lo que la tabla la
# sostiene.

NOMBRES_LARGOS <- list(
  mediana = "la mediana", media = "la media", ric = "el rango intercuartílico",
  desvio = "el desvío estándar",
  diferencia_de_medianas = "la diferencia de medianas",
  diferencia_de_medias = "la diferencia de medias")

valor_p <- function(p) {
  texto <- p_texto(p)
  if (texto == "") return("")
  paste0(if (substr(texto, 1, 1) == "<") "p " else "p = ", texto)
}

cifra <- function(v) numero_texto(v, decimales_de(v))

mayuscula <- function(x) paste0(toupper(substring(x, 1, 1)), substring(x, 2))

redactar <- function(parametros, apareadas, independientes, bootstrap, casos) {
  conf <- paste0(numero_texto(parametros$confianza * 100, 0), " %")
  lineas <- c("# Pruebas no paramétricas", "", paste0("Casos en la base: ", casos, "."), "")

  if (!is.null(apareadas)) {
    w <- apareadas$wilcoxon
    s <- apareadas$signos
    mal <- apareadas$como_independientes
    if (isTRUE(apareadas$cambia_la_conclusion)) {
      lineas <- c(lineas, paste0(
        "> **El apareamiento decide el resultado.** Tomando los datos como lo que son —",
        apareadas$n_pares, " personas medidas dos veces— Wilcoxon da ", valor_p(w$p),
        ". Tratándolos como dos muestras independientes, Mann-Whitney da ",
        valor_p(mal$mann_whitney_p), ". Es la misma tabla: lo único que cambia es si se ",
        "usa la información de quién es quién."), "")
    }

    lineas <- c(lineas, paste0("## Antes y después: `", parametros$antes, "` contra `",
                               parametros$despues, "`"), "")
    lineas <- c(lineas, paste0(
      apareadas$n_pares, " pares completos",
      if (apareadas$descartados > 0)
        paste0(", ", apareadas$descartados,
               " descartados por falta de alguna de las dos mediciones.") else "."), "")
    if (!is.null(w)) {
      lineas <- c(lineas, paste0(
        "- **Wilcoxon de rangos con signo.** W = ", cifra(w$w), ", z = ",
        numero_texto(w$z, 3), ", ", valor_p(w$p), ". El desplazamiento estimado ",
        "(Hodges-Lehmann) es ", cifra(w$hodges_lehmann), "."))
    }
    if (!is.null(s)) {
      lineas <- c(lineas, paste0(
        "- **Prueba de los signos.** Subieron ", s$subieron, " y bajaron ", s$bajaron,
        " de ", s$n, ", ", valor_p(s$p), "."))
    }
    lineas <- c(lineas, paste0(
      "- **Lo mismo sin aparear.** Mann-Whitney ", valor_p(mal$mann_whitney_p),
      ", t de Welch ", valor_p(mal$t_de_welch_p), "."))
    if (!is.null(w)) {
      lineas <- c(lineas, "", paste0(
        "El cambio típico es de ", cifra(w$mediana_del_cambio), " y su desvío es ",
        cifra(w$desvio_del_cambio), ". Esa es la razón aritmética de todo lo anterior: lo ",
        "que separa a una persona de otra es mucho más grande que lo que cada una cambió, ",
        "así que la comparación sin aparear tiene que buscar el efecto adentro de un ruido ",
        "que la apareada ni ve."))
    }
    lineas <- c(lineas, "")
  }

  u <- if (is.null(independientes)) NULL else independientes$mann_whitney
  kw <- if (is.null(independientes)) NULL else independientes$kruskal
  if (!is.null(u)) {
    nombres <- independientes$nombres
    lineas <- c(lineas, paste0("## Dos muestras: `", parametros$respuesta, "` por `",
                               parametros$grupo, "`"), "")
    lineas <- c(lineas, paste0("- **Mann-Whitney.** U = ", cifra(u$u), ", ",
                               valor_p(u$p), "."))
    lineas <- c(lineas, paste0(
      "- **P(X > Y) = ", numero_texto(u$probabilidad_de_superar, 3), "**: esa es la ",
      "probabilidad de que un caso de «", nombres[1], "» supere a uno de «", nombres[2],
      "» tomados al azar. Es lo que la prueba contrasta, y no la igualdad de medianas."))
    lineas <- c(lineas, paste0(
      "- Medianas: ", cifra(u$mediana_a), " y ", cifra(u$mediana_b),
      ". Desplazamiento de Hodges-Lehmann: ", cifra(u$hodges_lehmann), "."))
    t <- independientes$t_de_welch
    if (!is.null(t)) {
      lineas <- c(lineas, paste0("- **t de Welch**, para comparar: t = ",
                                 numero_texto(t$t, 3), ", ", valor_p(t$p), "."))
    }
    lineas <- c(lineas, "")
  }

  if (!is.null(kw)) {
    lineas <- c(lineas, "## Más de dos muestras", "")
    lineas <- c(lineas, paste0("Kruskal-Wallis: H = ", numero_texto(kw$h, 3), " con ",
                               kw$gl, " gl, ", valor_p(kw$p), ". ε² = ",
                               numero_texto(kw$epsilon_cuadrado, 3), "."), "")
    for (g in kw$grupos) {
      lineas <- c(lineas, paste0("- **", g$grupo, ".** n = ", g$n, ", mediana ",
                                 cifra(g$mediana), ", rango promedio ",
                                 numero_texto(g$rango_promedio, 1), "."))
    }
    lineas <- c(lineas, "")
  }

  if (!is.null(bootstrap) && length(bootstrap$intervalos) > 0) {
    lineas <- c(lineas, paste0("## Intervalos por bootstrap (", bootstrap$replicas,
                               " réplicas)"), "")
    for (fila in bootstrap$intervalos) {
      nombre <- NOMBRES_LARGOS[[fila$estadistico]]
      if (is.null(nombre)) nombre <- fila$estadistico
      partes <- c(paste0("- **", mayuscula(nombre), "**: ", cifra(fila$observado)),
                  paste0("percentil [", cifra(fila$percentil_inferior), "; ",
                         cifra(fila$percentil_superior), "]"))
      if (!is.null(fila$bca_inferior)) {
        partes <- c(partes, paste0("BCa [", cifra(fila$bca_inferior), "; ",
                                   cifra(fila$bca_superior), "]"))
      }
      lineas <- c(lineas, paste0(paste(partes, collapse = ", "), "."))
    }
    lineas <- c(lineas, "")
    p <- bootstrap$permutacion
    if (!is.null(p)) {
      lineas <- c(lineas, paste0(
        "Prueba de permutación sobre la diferencia de medianas: observada ",
        cifra(p$observada), ", ", valor_p(p$p), " con ", p$replicas,
        " reordenamientos."), "")
    }
  }

  lineas
}

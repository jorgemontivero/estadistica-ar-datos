# Paso 4: el informe, escrito en castellano.
#
# Lo mismo que hacen los otros descargables de la serie: lo que el proyecto
# calculó, redactado para pegar. La regla es que ningún número aparezca acá si
# no está también en un CSV, y que ninguna conclusión se escriba más fuerte de
# lo que la tabla la sostiene.

valor_p <- function(p) {
  texto <- p_texto(p)
  if (texto == "") return("")
  paste0(if (substr(texto, 1, 1) == "<") "p " else "p = ", texto)
}

enumerar <- function(cosas) {
  if (length(cosas) == 0) return("")
  if (length(cosas) == 1) return(cosas[1])
  paste0(paste(cosas[-length(cosas)], collapse = ", "), " y ", cosas[length(cosas)])
}

redactar <- function(parametros, supuestos, anova, post_hoc, celdas, casos) {
  conf <- paste0(numero_texto(parametros$confianza * 100, 0), " %")
  uf <- anova$un_factor
  lineas <- c("# ANOVA", "")

  diseno <- paste0("`", parametros$respuesta, " ~ ", parametros$factor)
  if (parametros$factor_2 != "") diseno <- paste0(diseno, " * ", parametros$factor_2)
  diseno <- paste0(diseno, "`")
  lineas <- c(lineas, paste0("Diseño: ", diseno, ". Casos en la base: ", casos,
                             "; usados: ", uf$n, "."))
  if (casos - uf$n > 0) {
    faltan <- casos - uf$n
    lineas <- c(lineas, paste0("Se ", if (faltan == 1) "descartó" else "descartaron", " ",
                               faltan, " ", if (faltan == 1) "caso" else "casos",
                               " sin respuesta o sin factor."))
  }
  lineas <- c(lineas, "")

  # Lo primero es la advertencia, si hace falta, porque cambia cómo se lee todo
  # lo que sigue.
  if (isTRUE(anova$interaccion_significativa)) {
    interaccion <- anova$dos_factores$tipo_iii[[3]]
    principal <- anova$tipos[[2]]
    lineas <- c(lineas, paste0(
      "> **La interacción manda.** ", interaccion$termino, " da F(",
      numero_limpio(interaccion$gl, 0), "; ",
      numero_limpio(anova$dos_factores$gl_error, 0), ") = ",
      numero_texto(interaccion$f, 2), ", ", valor_p(interaccion$p), ". Con la interacción ",
      "significativa, el efecto principal de ", principal$termino, " —",
      valor_p(principal$p_tipo_iii), "— es el promedio de efectos que apuntan para lados ",
      "distintos: no describe a ningún grupo. Lo que hay que leer son los efectos ",
      "simples."), "")
  }

  lineas <- c(lineas, "## Las celdas", "")
  for (c_ in celdas) {
    lineas <- c(lineas, paste0("- **", c_$celda, ".** n = ", c_$n, ", media ",
                               numero_texto(c_$media, 1), ", DE ",
                               numero_texto(c_$desvio, 1), "."))
  }
  lineas <- c(lineas, "")

  lineas <- c(lineas, "## Los supuestos", "")
  con_veredicto <- Filter(function(f) !is.null(f$normal), supuestos$normalidad)
  no_normales <- vapply(Filter(function(f) !isTRUE(f$normal), con_veredicto),
                        function(f) f$celda, character(1))
  if (length(con_veredicto) > 0) {
    lineas <- c(lineas, paste0(
      "- **Normalidad por celda.** Shapiro-Wilk rechaza en ", length(no_normales), " de ",
      length(con_veredicto), " celdas",
      if (length(no_normales) > 0) paste0(": ", enumerar(no_normales), ".") else "."))
  }
  h <- supuestos$homogeneidad
  if (!is.null(h)) {
    lineas <- c(lineas, paste0(
      "- **Igualdad de varianzas.** Levene con centro en la mediana: F(",
      numero_limpio(h$gl1, 0), "; ", numero_limpio(h$gl2, 0), ") = ",
      numero_texto(h$w, 3), ", ", valor_p(h$p), "."))
  }
  lineas <- c(lineas, "")

  lineas <- c(lineas, paste0("## ANOVA de un factor: ", parametros$factor), "")
  lineas <- c(lineas, paste0(
    "F(", numero_limpio(uf$gl_entre, 0), "; ", numero_limpio(uf$gl_dentro, 0), ") = ",
    numero_texto(uf$f, 3), ", ", valor_p(uf$p), ". η² = ",
    numero_texto(uf$eta_cuadrado, 3), ", ω² = ",
    numero_texto(uf$omega_cuadrado, 3), "."), "")
  lineas <- c(lineas, paste0(
    "El factor explica el ", numero_texto(uf$eta_cuadrado * 100, 1), " % de la variación. ",
    "El ω², que descuenta el sesgo del η², da ",
    numero_texto(uf$omega_cuadrado * 100, 1), " %: esa es la cifra que conviene informar."))
  if (!is.null(anova$welch)) {
    w <- anova$welch
    lineas <- c(lineas, "", paste0(
      "Sin suponer varianzas iguales, la versión de Welch da F(",
      numero_limpio(w$gl1, 0), "; ", numero_texto(w$gl2, 1), ") = ",
      numero_texto(w$f, 3), ", ", valor_p(w$p), "."))
  }
  lineas <- c(lineas, "")

  if (!is.null(anova$dos_factores)) {
    m <- anova$dos_factores
    lineas <- c(lineas, "## ANOVA de dos factores", "",
                "Sumas de cuadrados de tipo III, que no dependen del orden:", "")
    for (f in m$tipo_iii) {
      lineas <- c(lineas, paste0(
        "- **", f$termino, ".** SC = ", numero_texto(f$sc, 2), ", F(",
        numero_limpio(f$gl, 0), "; ", numero_limpio(m$gl_error, 0), ") = ",
        numero_texto(f$f, 3), ", ", valor_p(f$p), "."))
    }
    cambian <- Filter(function(t) isTRUE(t$cambia_la_conclusion), anova$tipos)
    cola <- if (length(cambian) > 0) {
      paste0("la conclusión de ",
             enumerar(vapply(cambian, function(t) paste0("**", t$termino, "**"),
                             character(1))),
             " cambia según cuál se use, y eso hay que declararlo.")
    } else {
      paste0("ninguna conclusión cambia, aunque las sumas de cuadrados difieran; está ",
             "todo en `tipos-de-suma.csv`.")
    }
    lineas <- c(lineas, "", paste0(
      "Con celdas desbalanceadas el tipo I y el tipo III no dan lo mismo. En este caso ",
      cola), "")
  }

  if (length(anova$efectos_simples) > 0) {
    lineas <- c(lineas, paste0("## Efectos simples: ", parametros$factor_2,
                               " dentro de cada ", parametros$factor), "")
    for (e in anova$efectos_simples) {
      partes <- paste0("- **", e$nivel, ".** F(", numero_limpio(e$gl, 0), "; ",
                       numero_limpio(anova$dos_factores$gl_error, 0), ") = ",
                       numero_texto(e$f, 3), ", ", valor_p(e$p))
      if (!is.null(e$diferencia)) {
        partes <- c(partes, paste0(e$entre, " = ", numero_texto(e$diferencia, 2),
                                   " (IC ", conf, " [", numero_texto(e$inferior, 2), "; ",
                                   numero_texto(e$superior, 2), "])"))
      }
      lineas <- c(lineas, paste0(paste(partes, collapse = ", "), "."))
    }
    con_efecto <- Filter(function(e) isTRUE(e$significativo), anova$efectos_simples)
    if (length(con_efecto) > 1 &&
        all(vapply(con_efecto, function(e) !is.null(e$diferencia), logical(1)))) {
      signos <- unique(vapply(con_efecto, function(e) e$diferencia > 0, logical(1)))
      if (length(signos) > 1) {
        lineas <- c(lineas, "", paste0(
          "Los efectos simples significativos **apuntan para lados distintos**. Por eso el ",
          "efecto principal da chico: los dos se cancelan al promediarlos. Informar solo ",
          "el promedio sería esconder el resultado."))
      }
    }
    lineas <- c(lineas, "")
  }

  if (length(post_hoc$pares) > 0) {
    lineas <- c(lineas, paste0("## Comparaciones de a pares (", post_hoc$sobre, ")"), "",
                paste0(post_hoc$cuantas, " comparaciones, con los cuatro métodos. Con ",
                       "Tukey:"), "")
    significativas <- Filter(function(f) f$metodo == "tukey" && isTRUE(f$significativa),
                             post_hoc$pares)
    if (length(significativas) > 0) {
      for (f in significativas) {
        lineas <- c(lineas, paste0(
          "- **", f$a, " vs ", f$b, ".** Diferencia ", numero_texto(f$diferencia, 2),
          " (IC ", conf, " [", numero_texto(f$inferior, 2), "; ",
          numero_texto(f$superior, 2), "]), ", valor_p(f$p), "."))
      }
    } else {
      lineas <- c(lineas, "- Ninguna comparación queda significativa.")
    }
    discrepan <- Filter(function(f) f$metodo == "tukey" &&
                          isTRUE(f$cambia_entre_correcciones), post_hoc$pares)
    if (length(discrepan) > 0) {
      lineas <- c(lineas, "", paste0(
        "**Ojo:** en ",
        enumerar(vapply(discrepan, function(f) paste0(f$a, " vs ", f$b), character(1))),
        " los cuatro métodos no coinciden. Ahí la conclusión la decide la corrección ",
        "elegida, no los datos."))
    }
    lineas <- c(lineas, "")
  }

  lineas
}

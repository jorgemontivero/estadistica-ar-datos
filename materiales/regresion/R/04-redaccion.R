# Paso 4: el informe en Markdown, listo para pegar.
#
# Cada coeficiente se informa como corresponde: la estimación, su intervalo de
# confianza y el valor p. Nunca el p solo, que no dice ni cuánto ni en qué
# dirección.
#
# Arriba de todo va lo único que hay que leer antes que nada: si algún
# resultado depende de un solo caso.

# «p = 0,032» o «p < 0,001»: con el «< 0,001» no va el signo igual.
valor_p <- function(p) {
  texto <- p_texto(p)
  if (startsWith(texto, "<")) paste0("p ", texto) else paste0("p = ", texto)
}

enumerar <- function(cosas) {
  if (length(cosas) == 1) return(cosas[1])
  paste0(paste(cosas[-length(cosas)], collapse = ", "), " y ", cosas[length(cosas)])
}

# Los coeficientes de un modelo cambian de escala según la variable: el de una
# edad anda por las décimas y el de un ingreso por las millonésimas. Se usan
# más decimales cuando el número es muy chico.
cifra <- function(v, decimales = 3) {
  if (is.null(v)) return("")
  a <- abs(v)
  if (a != 0 && a < 0.001) return(numero_texto(v, 9))
  if (a != 0 && a < 0.1) return(numero_texto(v, 5))
  numero_texto(v, decimales)
}

redactar <- function(parametros, modelo, diagnostico, logistica, casos) {
  conf <- paste0(numero_texto(parametros$confianza * 100, 0), " %")
  lineas <- c("# Regresión", "")
  formula <- paste0(parametros$respuesta, " ~ ",
                    paste(parametros$predictores, collapse = " + "))
  lineas <- c(lineas, paste0("Modelo: `", formula, "`. Casos en la base: ", casos,
                             "; usados en el ajuste: ", modelo$n, "."))
  if (modelo$descartados > 0) {
    lineas <- c(lineas, if (modelo$descartados == 1)
      paste0("Se descartó ", modelo$descartados,
             " caso al que le faltaba alguna variable del modelo.")
      else paste0("Se descartaron ", modelo$descartados,
                  " casos a los que les faltaba alguna variable del modelo."))
  }

  reajuste <- diagnostico$reajuste
  if (!is.null(reajuste) && reajuste$cuantos_cambian > 0) {
    cambian <- character(0)
    for (c in reajuste$comparacion) {
      if (isTRUE(c$cambia_la_conclusion)) cambian <- c(cambian, paste0("**", c$termino, "**"))
    }
    lineas <- c(lineas, "",
                paste0("> **Un solo caso decide parte de este modelo.** Sacar el caso ",
                       reajuste$caso, " —el de mayor distancia de Cook, ",
                       numero_texto(reajuste$cook, 3), "— cambia la conclusión de ",
                       enumerar(cambian), ". Un resultado que depende de una observación entre ",
                       modelo$n, " no es un resultado sobre la población: es un resultado sobre ",
                       "esa observación."))
  }

  lineas <- c(lineas, "", "## El modelo lineal", "")
  for (f in modelo$coeficientes) {
    if (f$termino == "(ordenada)") next
    partes <- c(paste0("**", f$termino, ".** b = ", cifra(f$estimacion)),
                paste0("IC ", conf, " [", cifra(f$inferior), "; ", cifra(f$superior), "]"),
                paste0("t(", numero_limpio(f$gl, 0), ") = ", numero_texto(f$t, 2)),
                valor_p(f$p))
    if (!is.null(f$vif)) partes <- c(partes, paste0("VIF = ", numero_texto(f$vif, 2)))
    lineas <- c(lineas, paste0("- ", paste(partes, collapse = ", "), "."))
  }

  lineas <- c(lineas, "",
              paste0("El modelo explica el ", numero_texto(modelo$r2 * 100, 1),
                     " % de la variación (", numero_texto(modelo$r2_ajustado * 100, 1),
                     " % ajustado por la cantidad de predictores), con un error estándar ",
                     "residual de ", cifra(modelo$ee_residual, 3), "."))
  if (!is.null(modelo$f)) {
    lineas <- c(lineas, paste0("La prueba F del modelo completo da F(",
                               numero_limpio(modelo$gl_modelo, 0), "; ",
                               numero_limpio(modelo$gl, 0), ") = ",
                               numero_texto(modelo$f, 2), ", ", valor_p(modelo$p_f), "."))
  }

  lineas <- c(lineas, "", "## El diagnóstico", "")
  s <- diagnostico$shapiro
  if (!is.null(s$p)) {
    lineas <- c(lineas, paste0("- **Normalidad de los residuos.** Shapiro-Wilk W = ",
                               numero_texto(s$w, 4), ", ", valor_p(s$p), "."))
  }
  bp <- diagnostico$breusch_pagan
  if (!is.null(bp)) {
    lineas <- c(lineas, paste0("- **Homocedasticidad.** Breusch-Pagan LM = ",
                               numero_texto(bp$lm, 3), " con ", bp$gl, " gl, ",
                               valor_p(bp$p), "."))
  }
  lineas <- c(lineas, paste0("- **Independencia.** Durbin-Watson = ",
                             numero_texto(diagnostico$durbin_watson, 3),
                             ". Solo significa algo si las filas tienen un orden."))
  altas <- sum(vapply(diagnostico$influencia, function(f) isTRUE(f$palanca_alta), logical(1)))
  grandes <- sum(vapply(diagnostico$influencia, function(f) isTRUE(f$residuo_grande), logical(1)))
  lineas <- c(lineas, paste0("- **Influencia.** ", altas, " casos con palanca alta y ", grandes,
                             " con residuo estandarizado mayor que 2 en valor absoluto."))

  if (!is.null(reajuste)) {
    lineas <- c(lineas, "", "## Qué pasa sin el caso más influyente", "",
                paste0("El caso ", reajuste$caso, " tiene una distancia de Cook de ",
                       numero_texto(reajuste$cook, 3), " y una palanca de ",
                       numero_texto(reajuste$palanca, 3), ". Sacándolo:"), "")
    for (c in reajuste$comparacion) {
      if (c$termino == "(ordenada)") next
      marca <- if (isTRUE(c$cambia_la_conclusion)) " ←" else ""
      lineas <- c(lineas, paste0("- **", c$termino, ".** b pasa de ", cifra(c$con_el_caso),
                                 " (", valor_p(c$p_con), ") a ", cifra(c$sin_el_caso),
                                 " (", valor_p(c$p_sin), ").", marca))
    }
  }

  if (!is.null(logistica)) {
    lineas <- c(lineas, "", "## La regresión logística", "",
                paste0("Respuesta: `", logistica$respuesta, "`, con «", logistica$exito,
                       "» como resultado de interés (", logistica$positivos, " casos de ",
                       logistica$modelo$n, ")."), "")
    if (!logistica$convergio) {
      lineas <- c(lineas,
                  paste0("**El ajuste no convergió, así que no hay coeficientes que ",
                         "informar.** Lo que sigue es la clasificación, que es la que deja ",
                         "ver el problema."), "")
    }
    for (f in logistica$coeficientes) {
      if (f$termino == "(ordenada)") next
      lineas <- c(lineas, paste0("- **", f$termino, ".** OR = ",
                                 numero_texto(f$odds_ratio, 3), " (IC ", conf, " [",
                                 numero_texto(f$or_inferior, 3), "; ",
                                 numero_texto(f$or_superior, 3), "]), ", valor_p(f$p), "."))
    }
    cl <- logistica$clasificacion
    if (!is.null(cl$auc)) {
      lineas <- c(lineas, "",
                  paste0("Clasificando al corte de 0,5: exactitud ",
                         numero_texto(cl$exactitud * 100, 1), " %, sensibilidad ",
                         numero_texto(cl$sensibilidad * 100, 1), " %, especificidad ",
                         numero_texto(cl$especificidad * 100, 1), " %. El AUC es ",
                         numero_texto(cl$auc, 3), "."),
                  "",
                  paste0("Conviene comparar la exactitud contra la del modelo que siempre ",
                         "contesta la clase más frecuente, que acá sería ",
                         numero_texto(cl$exactitud_trivial * 100, 1),
                         " %. Una exactitud alta con clases desbalanceadas no dice nada por ",
                         "sí sola."))
    }
  }

  lineas
}

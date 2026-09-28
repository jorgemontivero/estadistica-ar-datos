# Paso 2: el diagnóstico, que es donde el modelo se gana la confianza.
#
# Un ajuste siempre devuelve números. Que esos números signifiquen algo depende
# de cosas que el ajuste no mira: si los residuos tienen varianza constante, si
# son independientes, si hay un puñado de casos decidiendo todo.
#
# Se calculan cuatro cosas:
#
#     normalidad       Shapiro-Wilk sobre los residuos. Es el supuesto menos
#                      importante de los cuatro y el que más se cita.
#
#     homocedasticidad Breusch-Pagan: se regresan los residuos al cuadrado
#                      sobre los predictores. Si algo explica el tamaño del
#                      error, la varianza no es constante.
#
#     independencia    Durbin-Watson. Cerca de 2 no hay autocorrelación; cerca
#                      de 0, positiva. Solo tiene sentido si las filas tienen
#                      un orden —tiempo, espacio—; con una muestra desordenada
#                      no dice nada y el proyecto lo aclara.
#
#     influencia       palanca, residuo estandarizado y distancia de Cook, que
#                      combina las dos formas de ser raro: estar lejos en la x
#                      y estar lejos en la y.
#
# Y después lo que justifica el paso entero: **el modelo se vuelve a ajustar
# sin el caso más influyente** y se comparan los dos. Si alguna conclusión
# cambia, queda escrito.

# La diagonal del sombrero: h = xᵢ (X'X)⁻¹ xᵢ'.
#
# Mide cuán lejos está ese caso del centro de los predictores. Su suma es
# siempre k, así que la palanca media es k/n y se suele mirar el doble de eso
# como umbral.
palancas <- function(x, inversa) {
  rowSums((x %*% inversa) * x)
}

durbin_watson <- function(residuos) {
  numerador <- sum(diff(residuos)^2)
  denominador <- sum(residuos^2)
  if (denominador > 0) numerador / denominador else 0
}

# Se regresan los residuos al cuadrado sobre los mismos predictores.
#
# El estadístico es n·R² de esa regresión auxiliar y se compara contra una
# chi-cuadrado con tantos grados de libertad como predictores.
breusch_pagan <- function(x, residuos) {
  n <- nrow(x)
  k <- ncol(x)
  u <- residuos^2
  r <- resolver(x, u)
  if (is.null(r$coeficientes)) return(NULL)
  sc_total <- sum((u - mean(u))^2)
  if (sc_total <= 0) return(NULL)
  ajustados <- as.numeric(x %*% r$coeficientes)
  r2 <- 1 - sum((u - ajustados)^2) / sc_total
  lm_ <- n * r2
  gl <- k - 1
  list(lm = lm_, gl = as.integer(gl), p = pchisq(lm_, gl, lower.tail = FALSE))
}

# Palanca, residuo estandarizado y distancia de Cook, caso por caso.
influencia <- function(modelo) {
  h <- palancas(modelo$x, modelo$inversa)
  s <- sqrt(modelo$varianza)
  n <- modelo$n
  k <- modelo$k

  filas <- vector("list", n)
  for (i in seq_len(n)) {
    resto <- 1 - h[i]
    estandarizado <- if (resto > 0 && s > 0) modelo$residuos[i] / (s * sqrt(resto)) else 0
    # Cook combina las dos formas de ser influyente: estar lejos en y (el
    # residuo) y estar lejos en x (la palanca).
    cook <- if (resto > 0) (estandarizado^2 / k) * (h[i] / resto) else Inf
    filas[[i]] <- list(
      caso = as.integer(i), observado = modelo$y[i], ajustado = modelo$ajustados[i],
      residuo = modelo$residuos[i], estandarizado = estandarizado,
      palanca = h[i], cook = cook,
      palanca_alta = h[i] > 2 * k / n,
      residuo_grande = abs(estandarizado) > 2)
  }
  filas
}

# Vuelve a ajustar el modelo sacando el caso de mayor distancia de Cook.
#
# Es la única forma honesta de contestar «¿cuánto de esto lo decide un solo
# caso?». Comparar el antes y el después, coeficiente por coeficiente.
sin_el_influyente <- function(modelo, filas_influencia, parametros) {
  cooks <- vapply(filas_influencia, function(f) f$cook, numeric(1))
  peor <- which.max(cooks)
  x <- modelo$x[-peor, , drop = FALSE]
  y <- modelo$y[-peor]
  otro <- ajustar(x, y, parametros$confianza, parametros$predictores)
  if (is.null(otro)) return(NULL)

  comparacion <- vector("list", length(modelo$coeficientes))
  for (j in seq_along(modelo$coeficientes)) {
    antes <- modelo$coeficientes[[j]]
    despues <- otro$coeficientes[[j]]
    comparacion[[j]] <- list(
      termino = antes$termino,
      con_el_caso = antes$estimacion, p_con = antes$p,
      sin_el_caso = despues$estimacion, p_sin = despues$p,
      cambio_relativo = if (antes$estimacion != 0)
        (despues$estimacion - antes$estimacion) / antes$estimacion else NULL,
      cambia_la_conclusion = antes$significativo != despues$significativo,
      cambia_de_signo = (antes$estimacion > 0) != (despues$estimacion > 0))
  }
  list(caso = as.integer(peor), cook = cooks[peor],
       palanca = filas_influencia[[peor]]$palanca,
       comparacion = comparacion, r2_con = modelo$r2, r2_sin = otro$r2,
       cuantos_cambian = as.integer(sum(vapply(comparacion,
                                               function(c) isTRUE(c$cambia_la_conclusion),
                                               logical(1)))))
}

calcular_diagnostico <- function(modelo, parametros) {
  residuos <- modelo$residuos
  alfa <- 1 - parametros$confianza

  if (length(residuos) >= 3 && sum(residuos^2) > 0) {
    s <- shapiro.test(residuos)
    shapiro <- list(w = as.numeric(s$statistic), p = as.numeric(s$p.value),
                    normales = as.numeric(s$p.value) >= alfa)
  } else {
    shapiro <- list(w = NULL, p = NULL, normales = NULL)
  }

  bp <- breusch_pagan(modelo$x, residuos)
  dw <- durbin_watson(residuos)
  filas <- influencia(modelo)
  reajuste <- sin_el_influyente(modelo, filas, parametros)

  avisos <- list()
  anotar <- function(donde, aviso) {
    avisos[[length(avisos) + 1]] <<- list(donde = donde, aviso = aviso)
  }

  if (!is.null(shapiro$p) && shapiro$p < alfa) {
    anotar("normalidad",
           paste0("Shapiro-Wilk rechaza la normalidad de los residuos. Con n grande esto casi ",
                  "no afecta a los coeficientes ni a sus errores estándar: el teorema central ",
                  "del límite se ocupa. Donde sí importa es en los intervalos de predicción ",
                  "para un caso individual."))
  }
  if (!is.null(bp) && bp$p < alfa) {
    anotar("homocedasticidad",
           paste0("Breusch-Pagan rechaza la varianza constante. Los coeficientes siguen siendo ",
                  "insesgados, pero sus errores estándar están mal y con ellos los valores p. ",
                  "Corresponde usar errores robustos o transformar la respuesta."))
  }
  if (dw < 1.5 || dw > 2.5) {
    anotar("independencia",
           paste0("El Durbin-Watson da ", gsub(".", ",", sprintf("%.2f", dw), fixed = TRUE),
                  ", lejos de 2. Si las filas tienen un orden —tiempo, espacio, escuela— hay ",
                  "autocorrelación y los errores estándar están subestimados. Si el orden de ",
                  "las filas es arbitrario, este número no significa nada."))
  }
  for (f in modelo$coeficientes) {
    if (!is.null(f$vif) && f$vif > 10) {
      anotar("multicolinealidad",
             paste0("El VIF de «", f$termino, "» es ",
                    gsub(".", ",", sprintf("%.1f", f$vif), fixed = TRUE),
                    ". Por encima de 10 el coeficiente y su signo dejan de ser interpretables ",
                    "por separado: ese predictor y los otros están midiendo casi lo mismo."))
    }
  }
  altas <- sum(vapply(filas, function(f) isTRUE(f$palanca_alta), logical(1)))
  if (altas > 0) {
    anotar("influencia",
           paste0("Hay ", altas, " caso", if (altas == 1) "" else "s",
                  " con palanca mayor que 2k/n. No es un problema en sí: significa que están ",
                  "lejos del centro de los predictores y que pesan más que el resto en el ",
                  "ajuste."))
  }
  if (!is.null(reajuste) && reajuste$cuantos_cambian > 0) {
    anotar("influencia",
           paste0("Sacar el caso ", reajuste$caso, " cambia la conclusión de ",
                  reajuste$cuantos_cambian, " coeficiente",
                  if (reajuste$cuantos_cambian == 1) "" else "s",
                  ". Un resultado que depende de un solo caso entre ", modelo$n,
                  " no es un resultado: es ese caso."))
  }

  list(shapiro = shapiro, breusch_pagan = bp, durbin_watson = dw,
       influencia = filas, reajuste = reajuste, avisos = avisos,
       palanca_umbral = 2 * modelo$k / modelo$n)
}

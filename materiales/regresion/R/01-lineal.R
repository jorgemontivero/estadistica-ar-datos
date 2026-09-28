# Paso 1: la regresión lineal múltiple.
#
# Los coeficientes, sus errores estándar, sus intervalos de confianza y el
# ajuste del modelo. Nada de esto es difícil; lo que suele faltar es el paso 2.
#
# El VIF va acá y no en el diagnóstico a propósito: no es un supuesto que se
# verifica después, es una propiedad de los predictores que uno eligió. Si dos
# miden casi lo mismo, el modelo no está mal ajustado —está mal planteado—, y
# eso se decide antes de mirar un residuo.

# Las filas completas, con la columna de unos adelante para la ordenada.
#
# Se descarta la fila a la que le falte cualquiera de las variables del
# modelo. Es lo que hacen `lm` y statsmodels por omisión, y conviene saber
# cuántas se fueron: el número va al resumen.
matriz <- function(datos, respuesta, predictores) {
  columnas <- c(respuesta, predictores)
  valores <- lapply(columnas, function(v) {
    suppressWarnings(as.numeric(limpiar_texto(columna(datos, v))))
  })
  completas <- Reduce(`&`, lapply(valores, function(v) !is.na(v)))
  indices <- which(completas)
  y <- valores[[1]][completas]
  x <- cbind(1, do.call(cbind, lapply(valores[-1], function(v) v[completas])))
  list(x = x, y = y, indices = indices)
}

# Factor de inflación de la varianza: cuánto se infla el error estándar de
# cada coeficiente por culpa de la correlación con los otros predictores.
#
# Se calcula regresando cada predictor contra todos los demás. Un VIF de 10
# quiere decir que el error estándar es √10 ≈ 3,2 veces más grande de lo que
# sería si ese predictor fuera independiente del resto.
vif <- function(x, predictores) {
  k <- length(predictores)
  salida <- vector("list", k)
  names(salida) <- predictores
  if (k < 2) {
    for (p in predictores) salida[[p]] <- NULL
    return(salida)
  }
  for (j in seq_len(k)) {
    objetivo <- x[, j + 1]
    otros <- cbind(1, x[, setdiff(seq_len(k) + 1, j + 1), drop = FALSE])
    r <- resolver(otros, objetivo)
    if (is.null(r$coeficientes)) { salida[[j]] <- NULL; next }
    sc_total <- sum((objetivo - mean(objetivo))^2)
    ajustados <- as.numeric(otros %*% r$coeficientes)
    sc_residual <- sum((objetivo - ajustados)^2)
    r2 <- if (sc_total > 0) 1 - sc_residual / sc_total else 0
    salida[[j]] <- if (r2 >= 1) Inf else 1 / (1 - r2)
  }
  salida
}

# El ajuste completo. Devuelve todo lo que los pasos siguientes necesitan.
ajustar <- function(x, y, confianza, predictores) {
  n <- nrow(x)
  k <- ncol(x)
  if (n <= k) return(NULL)
  r <- resolver(x, y)
  if (is.null(r$coeficientes)) return(NULL)
  coef <- r$coeficientes
  inversa <- r$inversa

  ajustados <- as.numeric(x %*% coef)
  residuos <- y - ajustados
  gl <- n - k
  sc_residual <- sum(residuos^2)
  varianza <- sc_residual / gl
  sc_total <- sum((y - mean(y))^2)
  sc_modelo <- sc_total - sc_residual

  r2 <- if (sc_total > 0) 1 - sc_residual / sc_total else 0
  # El R² ajustado penaliza por cada predictor agregado. El R² común nunca
  # baja al sumar variables, así que solo no sirve para elegir modelo.
  r2_ajustado <- if (gl > 0) 1 - (1 - r2) * (n - 1) / gl else 0

  critico <- qt(1 - (1 - confianza) / 2, gl)
  terminos <- c("(ordenada)", predictores)
  factores <- vif(x, predictores)

  filas <- list()
  for (j in seq_along(terminos)) {
    ee <- sqrt(varianza * inversa[j, j])
    t <- if (ee > 0) coef[j] / ee else NA_real_
    p <- if (ee > 0) 2 * pt(abs(t), gl, lower.tail = FALSE) else NA_real_
    filas[[j]] <- list(
      termino = terminos[j], estimacion = coef[j], error_estandar = ee,
      t = t, gl = as.integer(gl), p = p,
      inferior = coef[j] - critico * ee, superior = coef[j] + critico * ee,
      significativo = !is.na(p) && p < 1 - confianza,
      vif = if (terminos[j] == "(ordenada)") NULL else factores[[terminos[j]]])
  }

  gl_modelo <- k - 1
  f <- if (gl_modelo > 0 && varianza > 0) (sc_modelo / gl_modelo) / varianza else NULL
  list(coeficientes = filas, ajustados = ajustados, residuos = residuos,
       inversa = inversa, n = as.integer(n), k = as.integer(k), gl = as.integer(gl),
       varianza = varianza, sc_total = sc_total, sc_modelo = sc_modelo,
       sc_residual = sc_residual, r2 = r2, r2_ajustado = r2_ajustado,
       ee_residual = sqrt(varianza), f = f, gl_modelo = as.integer(gl_modelo),
       p_f = if (is.null(f)) NULL else pf(f, gl_modelo, gl, lower.tail = FALSE))
}

calcular_lineal <- function(datos, parametros) {
  m <- matriz(datos, parametros$respuesta, parametros$predictores)
  modelo <- ajustar(m$x, m$y, parametros$confianza, parametros$predictores)
  if (is.null(modelo)) stop("No hay casos completos suficientes para ajustar el modelo.")
  modelo$x <- m$x
  modelo$y <- m$y
  modelo$indices <- m$indices
  modelo$descartados <- as.integer(length(datos) - length(m$indices))
  modelo
}

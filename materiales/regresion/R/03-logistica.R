# Paso 3: la regresión logística, ajustada a mano.
#
# El ajuste no tiene fórmula cerrada: se llega iterando. El método se llama
# **IRLS** —mínimos cuadrados ponderados iterativamente— y es más simple de lo
# que suena. En cada vuelta:
#
#     1. con los coeficientes actuales se calcula la probabilidad de cada caso;
#     2. se arma una variable de trabajo y un peso para cada caso;
#     3. se resuelve un mínimos cuadrados ponderado común;
#     4. se repite hasta que los coeficientes dejan de moverse.
#
# Está escrito a mano por la misma razón que Levene y la ANOVA de Welch en el
# descargable de pruebas: `glm` de R y `Logit` de statsmodels llegan al mismo
# resultado pero **paran de iterar con criterios distintos**, y los
# coeficientes terminan difiriendo en el octavo dígito. Escribir el ajuste una
# vez de cada lado, con la misma tolerancia y el mismo máximo de vueltas, es lo
# único que hace que los dos archivos salgan idénticos.
#
# Lo que se informa es el **odds ratio**, no el riesgo relativo. No son lo
# mismo y la confusión es diaria: con un resultado frecuente, el odds ratio
# exagera bastante el riesgo relativo.

TOLERANCIA <- 1e-10
MAXIMO_VUELTAS <- 50

# `exp` que no se cae.
#
# Con separación perfecta los coeficientes se van al infinito y el odds ratio
# con ellos. R devuelve `Inf` y sigue; Python levanta `OverflowError` y corta
# el programa. Acá la función no hace falta —existe para que las dos versiones
# digan lo mismo en el mismo lugar—, pero del lado de Python sí.
exponencial <- function(p) exp(p)

logistica_de <- function(p) ifelse(p > -700, 1 / (1 + exp(-p)), 0)

matriz_binaria <- function(datos, respuesta, predictores, exito) {
  etiquetas <- limpiar_texto(columna(datos, respuesta))
  valores <- lapply(predictores, function(v) {
    suppressWarnings(as.numeric(limpiar_texto(columna(datos, v))))
  })
  completas <- etiquetas != "" & Reduce(`&`, lapply(valores, function(v) !is.na(v)))
  y <- as.numeric(etiquetas[completas] == exito)
  x <- cbind(1, do.call(cbind, lapply(valores, function(v) v[completas])))
  list(x = x, y = y)
}

# IRLS. Devuelve los coeficientes, la inversa de la información y cuántas
# vueltas hicieron falta.
ajustar_logistica <- function(x, y, maximo = MAXIMO_VUELTAS, tolerancia = TOLERANCIA) {
  n <- nrow(x)
  k <- ncol(x)
  coef <- rep(0, k)
  inversa <- NULL
  vueltas <- 0

  for (vuelta in seq_len(maximo)) {
    vueltas <- vuelta
    eta <- as.numeric(x %*% coef)
    mu <- logistica_de(eta)
    # El peso de cada caso es μ(1−μ): los casos con probabilidad cerca de 0 o
    # de 1 casi no informan sobre dónde está la frontera.
    w <- pmax(mu * (1 - mu), 1e-10)
    # La variable de trabajo: la linealización de la respuesta.
    z <- eta + (y - mu) / w
    r <- resolver_ponderado(x, z, w)
    if (is.null(r$coeficientes)) return(NULL)
    cambio <- max(abs(r$coeficientes - coef))
    coef <- r$coeficientes
    inversa <- r$inversa
    if (cambio < tolerancia) break
  }

  eta <- as.numeric(x %*% coef)
  mu <- logistica_de(eta)

  # La información se recalcula con los coeficientes finales, no con los de la
  # vuelta anterior: la inversa que sale del bucle corresponde a los pesos de
  # un paso antes.
  #
  # Con la tolerancia de acá —1e-10 sobre los coeficientes— las dos coinciden
  # hasta el duodécimo decimal, así que esta línea no cambia ningún número.
  # Está igual porque lo que la hace innecesaria es la tolerancia, no la
  # cuenta: con un criterio de corte más flojo la diferencia aparece, y es
  # exactamente la que separa a este proyecto de `summary(glm)`, que corta por
  # devianza y se queda con los pesos que tenía guardados. Está contado en el
  # README.
  w <- pmax(mu * (1 - mu), 1e-10)
  inversa <- resolver_ponderado(x, rep(0, n), w)$inversa

  # Devianza: −2 por la log-verosimilitud. Es el residuo de la logística.
  devianza <- -2 * sum(y * log(pmax(mu, 1e-300)) + (1 - y) * log(pmax(1 - mu, 1e-300)))
  positivos <- sum(y)
  base <- positivos / n
  devianza_nula <- if (base > 0 && base < 1)
    -2 * (positivos * log(base) + (n - positivos) * log(1 - base)) else 0
  list(coeficientes = coef, inversa = inversa, vueltas = as.integer(vueltas), mu = mu,
       devianza = devianza, devianza_nula = devianza_nula,
       n = as.integer(n), k = as.integer(k))
}

# La matriz de confusión al corte elegido, y el AUC.
#
# El AUC se calcula por el estadístico de Mann-Whitney sobre las
# probabilidades: es la proporción de pares —un positivo y un negativo— en los
# que el modelo le da más probabilidad al positivo. Los empates cuentan medio.
clasificacion <- function(y, mu, corte = 0.5) {
  pred <- as.numeric(mu >= corte)
  vp <- sum(y == 1 & pred == 1)
  fp <- sum(y == 0 & pred == 1)
  vn <- sum(y == 0 & pred == 0)
  fn <- sum(y == 1 & pred == 0)

  positivos <- mu[y == 1]
  negativos <- mu[y == 0]
  auc <- if (length(positivos) > 0 && length(negativos) > 0) {
    mejores <- sum(vapply(positivos, function(p) {
      sum(p > negativos) + 0.5 * sum(p == negativos)
    }, numeric(1)))
    mejores / (length(positivos) * length(negativos))
  } else NULL

  total <- vp + fp + vn + fn
  list(verdaderos_positivos = as.integer(vp), falsos_positivos = as.integer(fp),
       verdaderos_negativos = as.integer(vn), falsos_negativos = as.integer(fn),
       sensibilidad = if (vp + fn > 0) vp / (vp + fn) else NULL,
       especificidad = if (vn + fp > 0) vn / (vn + fp) else NULL,
       exactitud = if (total > 0) (vp + vn) / total else NULL,
       # La exactitud del modelo trivial que siempre dice la clase mayoritaria.
       exactitud_trivial = if (total > 0) max(vp + fn, vn + fp) / total else NULL,
       auc = auc, corte = corte)
}

calcular_logistica <- function(datos, parametros) {
  respuesta <- parametros$respuesta_binaria
  predictores <- parametros$predictores_binaria
  if (respuesta == "" || length(predictores) == 0) return(NULL)

  m <- matriz_binaria(datos, respuesta, predictores, parametros$exito)
  if (nrow(m$x) <= length(predictores) + 1 || length(unique(m$y)) < 2) return(NULL)

  modelo <- ajustar_logistica(m$x, m$y)
  if (is.null(modelo)) return(NULL)

  # Si el ajuste no convergió, no hay coeficientes que informar.
  #
  # Pasa cuando los predictores **separan** las dos clases: si existe una
  # combinación de ellos que las parte sin ningún caso del lado equivocado, el
  # máximo de la verosimilitud no está en ningún punto finito. Cada vuelta del
  # IRLS agranda los coeficientes y mejora un poquito el ajuste, para siempre.
  # Lo que queda en la vuelta cincuenta no es una estimación: es dónde estaba
  # el algoritmo cuando se le acabaron las vueltas, y con otra tolerancia o en
  # otra computadora daría otra cosa.
  #
  # Escribirlo igual sería el error que este proyecto denuncia en todos los
  # otros pasos: un número plausible que no significa nada. Así que la tabla de
  # coeficientes queda vacía, y lo que se escribe es el aviso y la
  # clasificación, que es justamente la que deja ver la separación.
  convergio <- modelo$vueltas < MAXIMO_VUELTAS
  probables <- modelo$mu[m$y == 1]
  improbables <- modelo$mu[m$y == 0]
  separadas <- length(probables) > 0 && length(improbables) > 0 &&
    min(probables) > max(improbables)

  critico <- qnorm(1 - (1 - parametros$confianza) / 2)
  terminos <- if (convergio) c("(ordenada)", predictores) else character(0)
  filas <- vector("list", length(terminos))
  for (j in seq_along(terminos)) {
    b <- modelo$coeficientes[j]
    ee <- sqrt(modelo$inversa[j, j])
    z <- if (ee > 0) b / ee else NA_real_
    p <- if (ee > 0) 2 * pnorm(abs(z), lower.tail = FALSE) else NA_real_
    filas[[j]] <- list(
      termino = terminos[j], estimacion = b, error_estandar = ee, z = z, p = p,
      odds_ratio = exponencial(b), or_inferior = exponencial(b - critico * ee),
      or_superior = exponencial(b + critico * ee),
      significativo = !is.na(p) && p < 1 - parametros$confianza)
  }

  avisos <- list()
  if (!convergio) {
    avisos[[length(avisos) + 1]] <- list(
      donde = "logística",
      aviso = paste0("El ajuste no convergió en ", MAXIMO_VUELTAS, " vueltas, así que la ",
                     "tabla de coeficientes queda vacía a propósito. Lo que había en la ",
                     "última vuelta no es una estimación: es dónde estaba el algoritmo cuando ",
                     "se le acabaron las vueltas."))
  }
  if (separadas) {
    avisos[[length(avisos) + 1]] <- list(
      donde = "logística",
      aviso = paste0("Los predictores separan perfectamente las dos clases: no hay un solo ",
                     "caso del lado equivocado. Con separación el máximo de la verosimilitud ",
                     "no existe y los coeficientes se van al infinito. La salida no es ",
                     "insistir con el ajuste: es juntar más datos, sacar el predictor que ",
                     "separa —muchas veces es uno que se construyó a partir de la respuesta— ",
                     "o usar una logística penalizada."))
  }
  for (f in filas) {
    if (f$termino != "(ordenada)" && f$odds_ratio > 50) {
      avisos[[length(avisos) + 1]] <- list(
        donde = "logística",
        aviso = paste0("El odds ratio de «", f$termino, "» es enorme. Con pocos casos en una ",
                       "de las celdas, eso es casi siempre separación y no un efecto real."))
    }
  }
  positivos <- sum(m$y)
  por_variable <- positivos / length(predictores)
  if (por_variable < 10) {
    avisos[[length(avisos) + 1]] <- list(
      donde = "logística",
      aviso = paste0("Hay ", positivos, " casos con el resultado de interés y ",
                     length(predictores), " predictores: ",
                     gsub(".", ",", sprintf("%.1f", por_variable), fixed = TRUE),
                     " por predictor. La regla práctica pide al menos diez; con menos, los ",
                     "coeficientes están sesgados y los intervalos son demasiado angostos."))
  }

  list(coeficientes = filas, modelo = modelo,
       clasificacion = clasificacion(m$y, modelo$mu),
       positivos = as.integer(positivos), avisos = avisos,
       convergio = convergio, separadas = separadas,
       respuesta = respuesta, exito = parametros$exito)
}

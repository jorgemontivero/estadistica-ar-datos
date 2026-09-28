# Paso 2: las tablas de ANOVA.
#
# Tres cosas, en este orden:
#
#     un factor      la tabla clásica sobre el primer factor, con el tamaño del
#                    efecto y la versión de Welch al lado.
#
#     dos factores   si hay un segundo factor, el modelo completo con la
#                    interacción, por sumas de cuadrados de **tipo III** y
#                    también de **tipo I en los dos órdenes posibles**.
#
#     efectos simples cuando la interacción es significativa, el efecto del
#                    segundo factor **dentro de cada nivel** del primero. Es lo
#                    único que se puede interpretar en ese caso.
#
# Sobre los tipos de suma de cuadrados, que es donde más gente se quema sin
# enterarse. Con las celdas balanceadas los tres tipos dan lo mismo y la
# discusión no existe. Con celdas de tamaños distintos —o sea, casi siempre—
# dan distinto:
#
#     tipo I     secuencial: cada término se mide por lo que agrega a los
#                anteriores. Depende del ORDEN en que se escriben los factores.
#                Es lo que devuelve `anova()` de R.
#     tipo III   cada término se mide por lo que agrega al modelo que ya tiene
#                a todos los demás. No depende del orden. Es lo que devuelve
#                SPSS por omisión, y lo que informa `car::Anova(type = 3)`.
#
# Dos personas con los mismos datos y distinto programa pueden publicar valores
# p distintos para el mismo efecto sin haberse equivocado en nada. Por eso este
# proyecto escribe los tres y marca si alguna conclusión cambia.

# --------------------------------------------------------------- un factor
# El ANOVA de un factor, desde los datos de cada grupo.
tabla_anova <- function(grupos, confianza) {
  usables <- Filter(function(g) length(g$valores) > 1, grupos)
  k <- length(usables)
  if (k < 2) return(NULL)

  resumenes <- lapply(usables, function(g) {
    list(grupo = g$etiqueta, n = as.integer(length(g$valores)),
         media = mean(g$valores), desvio = sd(g$valores))
  })
  n <- sum(vapply(resumenes, function(r) r$n, integer(1)))
  gl_entre <- k - 1
  gl_dentro <- n - k
  if (gl_dentro < 1) return(NULL)

  media_general <- sum(vapply(resumenes, function(r) r$n * r$media, numeric(1))) / n
  sc_entre <- sum(vapply(resumenes, function(r) r$n * (r$media - media_general)^2,
                         numeric(1)))
  # La suma de cuadrados dentro se reconstruye desde los desvíos de cada grupo.
  sc_dentro <- sum(vapply(resumenes, function(r) (r$n - 1) * r$desvio^2, numeric(1)))
  sc_total <- sc_entre + sc_dentro

  cm_entre <- sc_entre / gl_entre
  cm_dentro <- sc_dentro / gl_dentro
  f <- if (cm_dentro > 0) cm_entre / cm_dentro else Inf

  eta <- if (sc_total > 0) sc_entre / sc_total else 0
  # Omega² descuenta el sesgo del eta², que siempre sobreestima porque el
  # factor explica algo de variabilidad aunque no haya ningún efecto real.
  omega <- if (sc_total + cm_dentro > 0)
    max(0, (sc_entre - gl_entre * cm_dentro) / (sc_total + cm_dentro)) else 0

  list(resumenes = resumenes, n = as.integer(n), k = as.integer(k),
       sc_entre = sc_entre, gl_entre = as.integer(gl_entre), cm_entre = cm_entre,
       sc_dentro = sc_dentro, gl_dentro = as.integer(gl_dentro), cm_dentro = cm_dentro,
       sc_total = sc_total, gl_total = as.integer(n - 1),
       f = f, p = pf(f, gl_entre, gl_dentro, lower.tail = FALSE),
       critico = qf(confianza, gl_entre, gl_dentro),
       eta_cuadrado = eta, omega_cuadrado = omega, media_general = media_general)
}

# ANOVA de Welch: no supone varianzas iguales.
#
# Es al ANOVA clásico lo que la t de Welch es a la t clásica, y conviene por
# defecto cuando las varianzas difieren. Está escrito a mano porque
# `oneway.test` de R y `scipy.stats.alexandergovern` no son la misma prueba, y
# ninguna de las dos coincide con la otra hasta el último dígito.
welch <- function(resumenes) {
  k <- length(resumenes)
  if (k < 2) return(NULL)
  if (any(vapply(resumenes, function(r) r$n < 2 || !(r$desvio > 0), logical(1)))) {
    return(NULL)
  }

  w <- vapply(resumenes, function(r) r$n / r$desvio^2, numeric(1))
  suma_w <- sum(w)
  media_ponderada <- sum(vapply(seq_along(resumenes), function(i) {
    w[i] * resumenes[[i]]$media
  }, numeric(1))) / suma_w

  numerador <- sum(vapply(seq_along(resumenes), function(i) {
    w[i] * (resumenes[[i]]$media - media_ponderada)^2
  }, numeric(1))) / (k - 1)
  # Este término aparece en el denominador del F y en los grados de libertad,
  # así que se calcula una sola vez.
  lambda <- sum(vapply(seq_along(resumenes), function(i) {
    (1 - w[i] / suma_w)^2 / (resumenes[[i]]$n - 1)
  }, numeric(1)))

  denominador <- 1 + ((2 * (k - 2)) / (k * k - 1)) * lambda
  f <- numerador / denominador
  gl2 <- (k * k - 1) / (3 * lambda)
  list(f = f, gl1 = as.integer(k - 1), gl2 = gl2,
       p = pf(f, k - 1, gl2, lower.tail = FALSE))
}

# ------------------------------------------------------------ dos factores
# Codificación por efectos: 1 en su nivel, −1 en el último, 0 en el resto.
#
# Se usa esta y no la de indicadoras 0/1 porque es la que hace que el término
# de interacción sea ortogonal a los efectos principales cuando el diseño está
# balanceado, que es la condición bajo la cual los tipos de suma de cuadrados
# coinciden. Con indicadoras, el tipo III daría otra cosa.
columnas_de_efectos <- function(valores, niveles) {
  ultimo <- niveles[length(niveles)]
  cols <- lapply(niveles[-length(niveles)], function(l) {
    ifelse(valores == l, 1, ifelse(valores == ultimo, -1, 0))
  })
  matrix(unlist(cols), nrow = length(valores), ncol = length(niveles) - 1)
}

sc_residual_de <- function(x, y) {
  r <- resolver(x, y)
  if (is.null(r$coeficientes)) return(NULL)
  sum((y - as.numeric(x %*% r$coeficientes))^2)
}

# El modelo completo, por tipo III y por tipo I en los dos órdenes.
#
# `observaciones` es una lista con los vectores a, b e y, en un orden fijo.
dos_factores <- function(observaciones, niveles_a, niveles_b, nombre_a, nombre_b) {
  if (length(niveles_a) < 2 || length(niveles_b) < 2) return(NULL)

  y <- observaciones$y
  n <- length(y)
  uno <- matrix(1, nrow = n, ncol = 1)
  a <- columnas_de_efectos(observaciones$a, niveles_a)
  b <- columnas_de_efectos(observaciones$b, niveles_b)
  ab <- matrix(unlist(lapply(seq_len(ncol(a)), function(i) {
    lapply(seq_len(ncol(b)), function(j) a[, i] * b[, j])
  }), recursive = TRUE), nrow = n)

  bloques <- list(a = a, b = b, ab = ab)
  anchos <- lapply(bloques, ncol)
  completo <- cbind(uno, a, b, ab)
  gl_error <- n - ncol(completo)
  if (gl_error < 1) return(NULL)

  sc_residual <- sc_residual_de(completo, y)
  if (is.null(sc_residual)) {
    # Pasa cuando falta alguna celda: sin datos en una combinación, la columna
    # de interacción que le corresponde no aporta nada nuevo y la matriz queda
    # sin inversa.
    return(list(singular = TRUE))
  }
  cm_error <- sc_residual / gl_error

  nombres <- list(a = nombre_a, b = nombre_b,
                  ab = paste0(nombre_a, " × ", nombre_b))

  fila <- function(etiqueta, sc, gl) {
    f <- if (cm_error > 0 && gl > 0) (sc / gl) / cm_error else Inf
    list(termino = etiqueta, sc = sc, gl = as.integer(gl),
         cm = if (gl > 0) sc / gl else NULL, f = f,
         p = pf(f, gl, gl_error, lower.tail = FALSE))
  }

  # Tipo III: cada término contra el modelo que ya tiene a todos los demás.
  tipo_iii <- list()
  for (clave in c("a", "b", "ab")) {
    otros <- c(list(uno), bloques[setdiff(c("a", "b", "ab"), clave)])
    sc_sin <- sc_residual_de(do.call(cbind, otros), y)
    if (is.null(sc_sin)) return(list(singular = TRUE))
    tipo_iii[[length(tipo_iii) + 1]] <- fila(nombres[[clave]], sc_sin - sc_residual,
                                             anchos[[clave]])
  }

  # Tipo I: secuencial, en el orden en que se entra.
  secuencial <- function(orden) {
    acumulado <- list(uno)
    previo <- sc_residual_de(uno, y)
    salida <- list()
    for (clave in orden) {
      acumulado[[length(acumulado) + 1]] <- bloques[[clave]]
      ahora <- sc_residual_de(do.call(cbind, acumulado), y)
      salida[[length(salida) + 1]] <- fila(nombres[[clave]], previo - ahora,
                                           anchos[[clave]])
      previo <- ahora
    }
    salida
  }

  list(singular = FALSE, tipo_iii = tipo_iii,
       tipo_i_a = secuencial(c("a", "b", "ab")),
       tipo_i_b = secuencial(c("b", "a", "ab")),
       sc_residual = sc_residual, gl_error = as.integer(gl_error), cm_error = cm_error,
       n = as.integer(n), nombres = nombres)
}

# El efecto del segundo factor dentro de cada nivel del primero.
#
# Se prueba contra el cuadrado medio del error del modelo completo y no contra
# el de cada nivel por separado: usar todos los datos para estimar la varianza
# es lo que le da potencia a la prueba, y es lo que hace cualquier programa
# cuando informa efectos simples.
efectos_simples <- function(celdas, niveles_a, niveles_b, cm_error, gl_error, confianza) {
  filas <- list()
  critico <- qt(1 - (1 - confianza) / 2, gl_error)
  for (nivel in niveles_a) {
    claves <- paste(nivel, niveles_b, sep = " / ")
    presentes <- claves[claves %in% names(celdas)]
    if (length(presentes) < 2) next
    valores <- celdas[presentes]
    n <- sum(vapply(valores, length, integer(1)))
    cuentas <- vapply(valores, length, integer(1))
    medias <- vapply(valores, mean, numeric(1))
    media_nivel <- sum(cuentas * medias) / n
    sc <- sum(cuentas * (medias - media_nivel)^2)
    gl <- length(presentes) - 1
    f <- if (cm_error > 0) (sc / gl) / cm_error else Inf
    p <- pf(f, gl, gl_error, lower.tail = FALSE)

    fila <- list(nivel = nivel, n = as.integer(n), gl = as.integer(gl), f = f, p = p,
                 significativo = p < 1 - confianza,
                 diferencia = NULL, inferior = NULL, superior = NULL, entre = "")
    # Con exactamente dos niveles, el efecto simple es una diferencia y se
    # puede escribir con su intervalo, que es mucho más legible que un F.
    if (length(presentes) == 2) {
      etiquetas <- sub("^.* / ", "", presentes)
      diferencia <- medias[[2]] - medias[[1]]
      ee <- sqrt(cm_error * (1 / cuentas[[1]] + 1 / cuentas[[2]]))
      fila$diferencia <- diferencia
      fila$entre <- paste0(etiquetas[2], " − ", etiquetas[1])
      fila$inferior <- diferencia - critico * ee
      fila$superior <- diferencia + critico * ee
    }
    filas[[length(filas) + 1]] <- fila
  }
  filas
}

# ------------------------------------------------------------------ armado
calcular_anova <- function(grupos_factor, grupos_celda, parametros) {
  confianza <- parametros$confianza
  alfa <- 1 - confianza
  un_factor <- tabla_anova(grupos_factor, confianza)
  if (is.null(un_factor)) stop("No hay al menos dos grupos con dos casos cada uno.")
  welch_ <- welch(un_factor$resumenes)

  avisos <- list()
  salida <- list(un_factor = un_factor, welch = welch_, dos_factores = NULL,
                 efectos_simples = list(), interaccion_significativa = FALSE,
                 tipos = list(), avisos = avisos)

  if (parametros$factor_2 == "") return(salida)

  niveles_a <- ordenar(vapply(grupos_celda, function(g) g$niveles[1], character(1)))
  niveles_b <- ordenar(vapply(grupos_celda, function(g) g$niveles[2], character(1)))
  celdas <- lapply(grupos_celda, function(g) g$valores)
  names(celdas) <- vapply(grupos_celda, function(g) g$etiqueta, character(1))
  observaciones <- list(
    a = unlist(lapply(grupos_celda, function(g) rep(g$niveles[1], length(g$valores)))),
    b = unlist(lapply(grupos_celda, function(g) rep(g$niveles[2], length(g$valores)))),
    y = unlist(lapply(grupos_celda, function(g) g$valores)))

  modelo <- dos_factores(observaciones, niveles_a, niveles_b,
                         parametros$factor, parametros$factor_2)
  if (is.null(modelo) || isTRUE(modelo$singular)) {
    salida$avisos <- list(list(
      donde = "diseño",
      aviso = paste0("No se pudo ajustar el modelo de dos factores: alguna combinación ",
                     "de niveles no tiene ningún caso. Con celdas vacías la interacción ",
                     "no está definida y no hay tabla que escribir.")))
    return(salida)
  }

  salida$dos_factores <- modelo
  interaccion <- modelo$tipo_iii[[3]]
  salida$interaccion_significativa <- interaccion$p < alfa

  # Los tres tipos, uno al lado del otro, con la marca de si difieren en la
  # conclusión y no solo en el número.
  buscar <- function(lista, nombre, campo) {
    for (f in lista) if (f$termino == nombre) return(f[[campo]])
    NULL
  }
  tipos <- list()
  for (i in seq_len(3)) {
    nombre <- modelo$tipo_iii[[i]]$termino
    p3 <- modelo$tipo_iii[[i]]$p
    pa <- buscar(modelo$tipo_i_a, nombre, "p")
    pb <- buscar(modelo$tipo_i_b, nombre, "p")
    veredictos <- unique(c(p3 < alfa, pa < alfa, pb < alfa))
    tipos[[i]] <- list(
      termino = nombre,
      sc_tipo_iii = modelo$tipo_iii[[i]]$sc, p_tipo_iii = p3,
      sc_tipo_i_primero = buscar(modelo$tipo_i_a, nombre, "sc"), p_tipo_i_primero = pa,
      sc_tipo_i_segundo = buscar(modelo$tipo_i_b, nombre, "sc"), p_tipo_i_segundo = pb,
      cambia_la_conclusion = length(veredictos) > 1)
  }
  salida$tipos <- tipos

  cambian <- Filter(function(t) isTRUE(t$cambia_la_conclusion), tipos)
  if (length(cambian) > 0) {
    cuales <- vapply(cambian, function(t) t$termino, character(1))
    avisos[[length(avisos) + 1]] <- list(
      donde = "tipos de suma",
      aviso = paste0("El veredicto de ", paste(cuales, collapse = ", "), " depende del ",
                     "tipo de suma de cuadrados. Con celdas desbalanceadas eso pasa, y ",
                     "significa que el efecto no está separado del otro factor: informar ",
                     "uno solo de los dos números sin decir cuál es elegir la conclusión."))
  }

  if (salida$interaccion_significativa) {
    salida$efectos_simples <- efectos_simples(celdas, niveles_a, niveles_b,
                                              modelo$cm_error, modelo$gl_error, confianza)
    principales <- Filter(function(t) t$p_tipo_iii >= alfa, tipos[1:2])
    aviso <- paste0("La interacción ", interaccion$termino, " es significativa. Los ",
                    "efectos principales son promedios de efectos que no son iguales ",
                    "entre sí, así que no describen a nadie: lo que hay que interpretar ",
                    "son los efectos simples.")
    if (length(principales) > 0) {
      aviso <- paste0(aviso, " Ojo con ",
                      paste(vapply(principales, function(t) t$termino, character(1)),
                            collapse = " y "),
                      ": el efecto principal no da significativo, y eso NO significa que ",
                      "no pase nada.")
    }
    avisos[[length(avisos) + 1]] <- list(donde = "interacción", aviso = aviso)
  }

  salida$avisos <- avisos
  salida
}

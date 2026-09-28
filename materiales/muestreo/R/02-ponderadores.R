# Paso 2: los ponderadores.
#
# El ponderador de diseño de una unidad es **la inversa de su probabilidad de
# inclusión**. Nada más que eso, y nada menos: no es un ajuste ni una
# corrección, es cuántas unidades de la población representa la que se
# seleccionó.
#
# De ahí sale la única comprobación que siempre hay que hacer y que casi nunca
# se hace: **la suma de los ponderadores tiene que dar el tamaño de la
# población.** Si da otra cosa, hay un error en el diseño o en el cálculo, y
# todo lo que venga después está mal sin que se note.
#
# Este paso también hace dos cosas que en cualquier encuesta real hay que hacer
# y que el ejemplo muestra en chico:
#
#     no respuesta         los hogares que no contestan se descuentan dentro de
#                          su propio conglomerado, y el peso de los que sí
#                          contestaron se agranda para cubrirlos. Supone que el
#                          que no contestó se parece a sus vecinos, que es un
#                          supuesto fuerte y hay que decirlo.
#     post-estratificación se ajustan los pesos para que los totales por región
#                          den exactamente los del marco. Baja la varianza y
#                          corrige parte del sesgo de no respuesta.
#
# Y avisa cuando los pesos quedan muy desparejos, que es lo que hace que una
# muestra de trescientos casos tenga la precisión de ochenta.

# El peso de diseño: uno sobre la probabilidad de inclusión.
pesos_de_diseno <- function(seleccion) {
  lapply(seleccion, function(f) {
    list(fila = f$fila, conglomerado = f$conglomerado,
         probabilidad = f$probabilidad, peso = 1 / f$probabilidad)
  })
}

# Reparte el peso de los que no contestaron entre los que sí, dentro del mismo
# conglomerado.
#
# Es el ajuste por celdas más simple que existe y el que se usa por omisión
# cuando no hay nada mejor. Cuando un conglomerado entero no contesta no hay a
# quién repartirle, y ahí el ajuste no puede hacer nada: eso queda escrito.
ajustar_por_no_respuesta <- function(pesos, respondieron) {
  claves <- vapply(pesos, function(p) {
    if (is.null(p$conglomerado)) "—" else p$conglomerado
  }, character(1))

  salida <- list()
  celdas_perdidas <- 0L
  for (clave in ordenar(claves)) {
    indices <- which(claves == clave)
    total <- sum(vapply(pesos[indices], function(p) p$peso, numeric(1)))
    con_dato <- indices[respondieron[indices]]
    if (length(con_dato) == 0) {
      celdas_perdidas <- celdas_perdidas + 1L
      next
    }
    logrado <- sum(vapply(pesos[con_dato], function(p) p$peso, numeric(1)))
    factor <- total / logrado
    for (i in con_dato) {
      p <- pesos[[i]]
      p$factor_no_respuesta <- factor
      p$peso <- p$peso * factor
      salida[[length(salida) + 1]] <- p
    }
  }
  salida <- salida[order(vapply(salida, function(p) p$fila, numeric(1)), method = "radix")]
  list(pesos = salida, celdas_perdidas = celdas_perdidas)
}

# Ajusta los pesos para que los totales por celda den los del marco.
#
# El factor de cada celda es el total verdadero sobre el total estimado. Con
# una sola variable de calibración es una cuenta de una línea; con varias a la
# vez hay que iterar (el «raking»), que este proyecto no trae.
post_estratificar <- function(datos, pesos, columna_) {
  if (columna_ == "") return(list(pesos = pesos, detalle = list()))
  verdaderos <- vapply(indices_por(datos, columna_), length, integer(1))
  etiquetas <- limpiar_texto(columna(datos, columna_))

  estimados <- list()
  for (p in pesos) {
    clave <- etiquetas[p$fila]
    estimados[[clave]] <- (if (is.null(estimados[[clave]])) 0 else estimados[[clave]]) + p$peso
  }

  detalle <- list()
  factores <- list()
  for (clave in names(verdaderos)) {
    estimado <- if (is.null(estimados[[clave]])) 0 else estimados[[clave]]
    factor <- if (estimado > 0) verdaderos[[clave]] / estimado else 1
    factores[[clave]] <- factor
    detalle[[length(detalle) + 1]] <- list(
      celda = clave, en_el_marco = as.integer(verdaderos[[clave]]),
      estimado_antes = estimado, factor = factor)
  }

  salida <- lapply(pesos, function(p) {
    clave <- etiquetas[p$fila]
    f <- if (is.null(factores[[clave]])) 1 else factores[[clave]]
    p$factor_post <- f
    p$peso <- p$peso * f
    p
  })
  list(pesos = salida, detalle = detalle)
}

# Lo que hay que mirar de un vector de pesos antes de usarlo.
resumir_pesos <- function(pesos, poblacion) {
  valores <- vapply(pesos, function(p) p$peso, numeric(1))
  n <- length(valores)
  suma <- sum(valores)
  media <- suma / n
  varianza <- if (n > 1) sum((valores - media)^2) / (n - 1) else 0
  cv <- if (media > 0) sqrt(varianza) / media else 0
  list(n = as.integer(n), suma = suma, poblacion = as.integer(poblacion),
       diferencia_con_la_poblacion = suma - poblacion,
       minimo = min(valores), maximo = max(valores), media = media,
       coeficiente_de_variacion = cv,
       razon_maximo_minimo = if (min(valores) > 0) max(valores) / min(valores) else Inf,
       # El efecto de los pesos desiguales sobre la varianza, de Kish. Es
       # cuánto se paga por ponderar, aparte de lo que se paga por conglomerar.
       deff_de_kish = 1 + cv^2,
       n_efectivo_de_kish = n / (1 + cv^2))
}

# Los tres momentos del ponderador: de diseño, ajustado y calibrado.
#
# Se escriben los tres porque cada uno responde una pregunta distinta. El de
# diseño tiene que sumar exactamente la población: si no, hay un error. El
# ajustado tiene que volver a sumarla después de la no respuesta. Y el
# calibrado tiene que dar los totales conocidos por celda.
calcular_ponderadores <- function(datos, parametros, seleccion, respondieron = NULL) {
  poblacion <- length(datos)
  pesos <- pesos_de_diseno(seleccion)
  avisos <- list()
  antes <- resumir_pesos(pesos, poblacion)

  celdas_perdidas <- 0L
  if (!is.null(respondieron)) {
    logrados <- sum(respondieron)
    sin_ajustar <- resumir_pesos(pesos[respondieron], poblacion)
    ajustado <- ajustar_por_no_respuesta(pesos, respondieron)
    pesos <- ajustado$pesos
    celdas_perdidas <- ajustado$celdas_perdidas
    if (celdas_perdidas > 0) {
      avisos[[length(avisos) + 1]] <- list(
        donde = "no respuesta",
        aviso = paste0("Hay ", celdas_perdidas, " conglomerados donde no contestó nadie. ",
                       "Ahí el ajuste no tiene a quién repartirle el peso, así que esos ",
                       "casos quedan afuera y la muestra representa menos población de la ",
                       "que debería."))
    }
    avisos[[length(avisos) + 1]] <- list(
      donde = "no respuesta",
      aviso = paste0("Contestaron ", logrados, " de ", length(respondieron), " hogares. Sin ",
                     "ajustar, los pesos sumarían ",
                     gsub(".", ",", sprintf("%.0f", sin_ajustar$suma), fixed = TRUE),
                     " y no ", poblacion, ": la encuesta estaría representando menos ",
                     "población de la que hay. El ajuste reparte el peso de los que faltan ",
                     "entre sus vecinos del mismo conglomerado, y eso supone que se ",
                     "parecen. Es un supuesto, no un dato."))
  }
  tras_no_respuesta <- resumir_pesos(pesos, poblacion)

  columna_ <- if (parametros$calibrar_por != "") parametros$calibrar_por
              else parametros$estrato
  calibrado <- post_estratificar(datos, pesos, columna_)
  pesos <- calibrado$pesos
  despues <- resumir_pesos(pesos, poblacion)

  if (abs(antes$diferencia_con_la_poblacion) > 1e-6) {
    avisos[[length(avisos) + 1]] <- list(
      donde = "ponderadores",
      aviso = paste0("La suma de los pesos de diseño no da el tamaño de la población. Con ",
                     "una selección sin no respuesta tiene que dar exacto: si no da, hay un ",
                     "error en las probabilidades de inclusión y todo lo que venga después ",
                     "está mal."))
  }
  if (despues$razon_maximo_minimo > 5) {
    avisos[[length(avisos) + 1]] <- list(
      donde = "ponderadores",
      aviso = paste0("El peso más grande es más de cinco veces el más chico. Con pesos así ",
                     "de desparejos unos pocos casos mandan sobre la estimación: conviene ",
                     "mirar si vale la pena recortarlos, aunque recortar introduce sesgo."))
  }
  if (despues$deff_de_kish > 1.2) {
    avisos[[length(avisos) + 1]] <- list(
      donde = "ponderadores",
      aviso = paste0("Los pesos desiguales por sí solos ya inflan la varianza un ",
                     gsub(".", ",", sprintf("%.0f", (despues$deff_de_kish - 1) * 100),
                          fixed = TRUE),
                     " % (efecto de Kish). Eso es aparte de lo que cueste el conglomerado, ",
                     "y se suma."))
  }

  factores <- vapply(calibrado$detalle, function(c_) c_$factor, numeric(1))
  if (length(factores) > 0 && all(abs(factores - 1) < 1e-9)) {
    avisos[[length(avisos) + 1]] <- list(
      donde = "calibración",
      aviso = paste0("La post-estratificación no cambió ningún peso: todos los factores ",
                     "dieron uno. Es lo que tiene que pasar cuando se calibra sobre la ",
                     "misma variable que ya estratificó el diseño, y conviene saberlo, ",
                     "porque calibrar sobre algo que el diseño ya controla da la sensación ",
                     "de haber corregido algo sin haber corregido nada."))
  } else if (length(factores) > 0) {
    avisos[[length(avisos) + 1]] <- list(
      donde = "calibración",
      aviso = paste0("La post-estratificación movió los pesos hasta un ",
                     gsub(".", ",", sprintf("%.1f", max(abs(factores - 1)) * 100),
                          fixed = TRUE),
                     " %. Eso es lo que la muestra se había desviado de los totales ",
                     "conocidos, y es la parte del sesgo de no respuesta que la ",
                     "calibración sí puede corregir."))
  }

  list(pesos = pesos, antes = antes, tras_no_respuesta = tras_no_respuesta,
       despues = despues, calibracion = calibrado$detalle,
       celdas_perdidas = celdas_perdidas, avisos = avisos)
}

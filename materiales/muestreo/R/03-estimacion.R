# Paso 3: estimar, con la varianza que le corresponde al diseño.
#
# Acá está lo que este proyecto existe para mostrar.
#
# La estimación puntual de una encuesta compleja no tiene misterio: se
# promedian los valores con los ponderadores y listo. **El error estándar sí lo
# tiene**, y es donde se equivoca casi todo el mundo: se calcula el promedio
# con los pesos y después el error estándar con la fórmula del muestreo
# aleatorio simple, que es s/√n. El resultado es un intervalo que se ve bien,
# que es angosto, y que no cubre lo que dice cubrir.
#
# **Un solo estimador para los cuatro diseños.** La varianza se calcula siempre
# con el método de la *última etapa* (ultimate cluster): dentro de cada
# estrato, la variabilidad entre los totales ponderados de cada unidad
# primaria.
#
#     v = Σ_h (1 − f_h) · a_h/(a_h − 1) · Σ_i (z_hi − z̄_h)²
#
# Con conglomerados, la unidad primaria es el conglomerado. Sin conglomerados,
# cada unidad es su propia unidad primaria, y entonces la fórmula **se reduce
# exactamente** a la del estratificado; y con un solo estrato, a la del
# aleatorio simple con corrección por población finita. No hay cuatro fórmulas:
# hay una, mirada desde cuatro diseños.
#
# El **efecto de diseño** es el cociente entre esa varianza y la que habría
# dado un aleatorio simple del mismo tamaño. Mayor que uno significa que el
# diseño costó precisión —lo típico de los conglomerados—; menor que uno, que
# la ganó —lo típico de la estratificación—. Y el **tamaño efectivo**, n/deff,
# dice a cuántos casos de un aleatorio simple equivale la muestra que se pagó.

# El residuo que hay que acumular por unidad primaria, según qué se estima.
#
# Para un total, el aporte de cada caso es su peso por su valor. Para una media
# o una proporción —que son razones— hay que restarle la estimación, porque el
# denominador también es aleatorio: eso es la linealización de Taylor, y
# saltearla infla la varianza de una media hasta el absurdo.
linealizar <- function(valores, pesos, clase) {
  suma_w <- sum(pesos)
  if (clase == "total") {
    return(list(aportes = pesos * valores, suma_w = suma_w, estimacion = NULL))
  }
  estimacion <- sum(pesos * valores) / suma_w
  list(aportes = pesos * (valores - estimacion), suma_w = suma_w, estimacion = estimacion)
}

# La estimación y su error estándar por el método de la última etapa.
#
# `fracciones` es, por estrato, qué proporción de las unidades primarias entró
# en la muestra: es la corrección por población finita de la primera etapa. Con
# una fracción chica casi no cambia nada; con una muestra que se come media
# población, cambia mucho.
estimar <- function(valores, pesos, estratos, unidades, fracciones, clase, confianza) {
  n <- length(valores)
  if (n < 2) return(NULL)
  lin <- linealizar(valores, pesos, clase)
  estimacion <- if (clase == "total") sum(lin$aportes) else lin$estimacion

  # Los aportes, acumulados por unidad primaria dentro de cada estrato.
  clave <- paste(estratos, unidades, sep = "\u0001")
  acumulado <- tapply(lin$aportes, clave, sum)
  estrato_de <- vapply(strsplit(names(acumulado), "\u0001", fixed = TRUE),
                       function(p) p[1], character(1))

  varianza <- 0
  grados <- 0L
  upm_totales <- 0L
  for (h in ordenar(estratos)) {
    zs <- as.numeric(acumulado[estrato_de == h])
    a <- length(zs)
    upm_totales <- upm_totales + a
    if (a < 2) {
      # Un estrato con una sola unidad primaria no aporta grados de libertad y
      # su varianza no se puede estimar. Se lo deja pasar y se avisa, que es
      # mejor que devolver un cero silencioso.
      next
    }
    media_z <- sum(zs) / a
    f <- if (is.null(fracciones[[h]])) 0 else fracciones[[h]]
    varianza <- varianza + (1 - f) * a / (a - 1) * sum((zs - media_z)^2)
    grados <- grados + a - 1L
  }

  if (clase != "total") varianza <- varianza / (lin$suma_w^2)
  error <- if (varianza > 0) sqrt(varianza) else 0

  # Los grados de libertad de una encuesta compleja son (unidades primarias −
  # estratos), no (n − 1). Con 32 conglomerados y 4 estratos son 28, no 319:
  # usar n − 1 angosta el intervalo de más.
  gl <- max(1L, grados)
  critico <- qt(1 - (1 - confianza) / 2, gl)
  list(estimacion = estimacion, error_estandar = error, gl = as.integer(gl),
       inferior = estimacion - critico * error,
       superior = estimacion + critico * error,
       unidades_primarias = upm_totales, suma_de_pesos = lin$suma_w)
}

# El error estándar que saldría de ignorar el diseño.
#
# Es lo que devuelve cualquier programa al que se le pasa la columna sin
# decirle nada más, y lo que aparece en la mayoría de los informes. Se calcula
# acá para poder ponerlo al lado del otro.
como_si_fuera_simple <- function(valores, pesos, poblacion, clase, confianza) {
  n <- length(valores)
  if (n < 2) return(NULL)
  media <- sum(valores) / n
  s2 <- sum((valores - media)^2) / (n - 1)
  if (clase == "total") {
    error <- poblacion * sqrt((1 - n / poblacion) * s2 / n)
    estimacion <- poblacion * media
  } else {
    error <- sqrt((1 - n / poblacion) * s2 / n)
    estimacion <- media
  }
  critico <- qt(1 - (1 - confianza) / 2, n - 1)
  list(estimacion = estimacion, error_estandar = error, gl = as.integer(n - 1),
       inferior = estimacion - critico * error,
       superior = estimacion + critico * error)
}

# El valor de la población. Solo se puede calcular porque el marco es la
# población entera: en la vida real esta columna no existe, y es justamente por
# eso que el intervalo importa.
verdadero <- function(datos, columna_, clase, exito = "") {
  if (clase == "proporcion") {
    return(sum(limpiar_texto(columna(datos, columna_)) == exito) / length(datos))
  }
  valores <- suppressWarnings(as.numeric(limpiar_texto(columna(datos, columna_))))
  valores <- valores[!is.na(valores)]
  if (clase == "total") sum(valores) else sum(valores) / length(valores)
}

# `estratificado` dice si el DISEÑO usó los estratos al seleccionar.
#
# No es un detalle: aplicarle la fórmula estratificada a una muestra que se
# sacó sin estratificar no es un error de cuenta, es estimar otra cosa —la
# varianza de un post-estratificado— y da un efecto de diseño menor que uno que
# no le corresponde a nadie. Un aleatorio simple tiene deff 1 por definición, y
# si la tabla dice otra cosa, la tabla está mal.
calcular_estimacion <- function(datos, parametros, pesos, fracciones, nombre_diseno,
                                estratificado = TRUE) {
  confianza <- parametros$confianza
  poblacion <- length(datos)
  filas <- vapply(pesos, function(p) p$fila, numeric(1))
  w <- vapply(pesos, function(p) p$peso, numeric(1))
  etiquetas <- if (parametros$estrato != "" && estratificado)
    limpiar_texto(columna(datos, parametros$estrato)) else NULL
  estratos <- if (is.null(etiquetas)) rep("—", length(filas)) else etiquetas[filas]
  # Sin conglomerados, cada unidad es su propia unidad primaria: ahí la fórmula
  # de la última etapa se vuelve la del estratificado.
  unidades <- vapply(pesos, function(p) {
    if (is.null(p$conglomerado)) paste0("u", p$fila) else p$conglomerado
  }, character(1))

  objetivos <- list()
  if (parametros$variable != "") objetivos[[length(objetivos) + 1]] <-
    list(parametros$variable, "media")
  if (parametros$variable_total != "") objetivos[[length(objetivos) + 1]] <-
    list(parametros$variable_total, "total")
  if (parametros$variable_binaria != "") objetivos[[length(objetivos) + 1]] <-
    list(parametros$variable_binaria, "proporcion")

  salida <- list()
  for (obj in objetivos) {
    columna_ <- obj[[1]]
    clase <- obj[[2]]
    if (clase == "proporcion") {
      todos <- limpiar_texto(columna(datos, columna_))
      valores <- as.numeric(todos[filas] == parametros$exito)
    } else {
      todos <- suppressWarnings(as.numeric(limpiar_texto(columna(datos, columna_))))
      valores <- todos[filas]
    }

    diseno <- estimar(valores, w, estratos, unidades, fracciones, clase, confianza)
    simple <- como_si_fuera_simple(valores, w, poblacion, clase, confianza)
    if (is.null(diseno) || is.null(simple)) next
    real <- verdadero(datos, columna_, clase, parametros$exito)
    deff <- if (simple$error_estandar > 0)
      (diseno$error_estandar / simple$error_estandar)^2 else Inf
    salida[[length(salida) + 1]] <- list(
      diseno = nombre_diseno, variable = columna_, que = clase,
      verdadero = real, estimacion = diseno$estimacion,
      error_estandar = diseno$error_estandar,
      inferior = diseno$inferior, superior = diseno$superior, gl = diseno$gl,
      contiene_al_verdadero = diseno$inferior <= real && real <= diseno$superior,
      ee_ingenuo = simple$error_estandar,
      inferior_ingenuo = simple$inferior, superior_ingenuo = simple$superior,
      contiene_ingenuo = simple$inferior <= real && real <= simple$superior,
      deff = deff,
      n_efectivo = if (deff > 0) length(valores) / deff else NA_real_,
      error_relativo = if (real != 0) abs(diseno$estimacion - real) / abs(real) else NA_real_)
  }
  salida
}

# La misma media, estimada dentro de cada estrato.
#
# Es lo que casi siempre se pide después de la cifra general, y es donde el
# tamaño de muestra se vuelve el problema: una muestra que alcanza para el
# total puede no alcanzar para ninguna de sus partes.
estimar_por_estrato <- function(datos, parametros, pesos, fracciones) {
  estrato <- parametros$estrato
  columna_ <- parametros$variable
  if (estrato == "" || columna_ == "") return(list())
  confianza <- parametros$confianza
  etiquetas <- limpiar_texto(columna(datos, estrato))
  todos <- suppressWarnings(as.numeric(limpiar_texto(columna(datos, columna_))))
  filas <- vapply(pesos, function(p) p$fila, numeric(1))
  claves <- etiquetas[filas]

  salida <- list()
  for (clave in ordenar(claves)) {
    cuales <- which(claves == clave)
    grupo <- pesos[cuales]
    valores <- todos[filas[cuales]]
    w <- vapply(grupo, function(p) p$peso, numeric(1))
    unidades <- vapply(grupo, function(p) {
      if (is.null(p$conglomerado)) paste0("u", p$fila) else p$conglomerado
    }, character(1))
    fr <- list()
    fr[[clave]] <- if (is.null(fracciones[[clave]])) 0 else fracciones[[clave]]
    r <- estimar(valores, w, rep(clave, length(grupo)), unidades, fr, "media", confianza)
    if (is.null(r)) next
    real <- mean(todos[etiquetas == clave])
    salida[[length(salida) + 1]] <- list(
      estrato = clave, n = as.integer(length(grupo)),
      unidades_primarias = r$unidades_primarias,
      verdadero = real, estimacion = r$estimacion, error_estandar = r$error_estandar,
      inferior = r$inferior, superior = r$superior,
      contiene_al_verdadero = r$inferior <= real && real <= r$superior,
      error_relativo_del_ee = if (r$estimacion != 0) r$error_estandar / r$estimacion
        else NA_real_)
  }
  salida
}

# Cuántas veces le acierta cada intervalo, sacando la muestra muchas veces.
#
# Es la única prueba concluyente y la única que en la vida real no se puede
# hacer, porque haría falta conocer la población. Acá se puede: el marco **es**
# la población.
#
# Se saca la muestra `replicas` veces, con una semilla distinta cada vez, y se
# cuenta qué proporción de los intervalos contiene al valor verdadero. Un
# intervalo del 95 % que cubra el 95 % está bien construido. Uno que cubra el
# 70 % está mintiendo, y la diferencia no se ve mirando un solo intervalo: el
# de una muestra puntual se ve igual de respetable.
calcular_cobertura <- function(datos, parametros, seleccionar, replicas) {
  if (replicas < 1) return(NULL)
  confianza <- parametros$confianza
  columna_ <- parametros$variable
  etiquetas <- limpiar_texto(columna(datos, parametros$estrato))
  todos <- suppressWarnings(as.numeric(limpiar_texto(columna(datos, columna_))))
  real <- verdadero(datos, columna_, "media")

  aciertos_diseno <- 0L
  aciertos_ingenuo <- 0L
  anchos_diseno <- numeric(0)
  anchos_ingenuos <- numeric(0)
  for (r in seq_len(replicas)) {
    par <- seleccionar(parametros$semilla + r)
    sel <- par$muestra
    filas <- vapply(sel, function(s) s$fila, numeric(1))
    w <- vapply(sel, function(s) 1 / s$probabilidad, numeric(1))
    valores <- todos[filas]
    estratos <- if (parametros$estrato != "") etiquetas[filas] else rep("—", length(filas))
    unidades <- vapply(sel, function(s) {
      if (is.null(s$conglomerado)) paste0("u", s$fila) else s$conglomerado
    }, character(1))

    d <- estimar(valores, w, estratos, unidades, par$fracciones, "media", confianza)
    s <- como_si_fuera_simple(valores, w, length(datos), "media", confianza)
    if (is.null(d) || is.null(s)) next
    if (d$inferior <= real && real <= d$superior) aciertos_diseno <- aciertos_diseno + 1L
    if (s$inferior <= real && real <= s$superior) aciertos_ingenuo <- aciertos_ingenuo + 1L
    anchos_diseno <- c(anchos_diseno, d$superior - d$inferior)
    anchos_ingenuos <- c(anchos_ingenuos, s$superior - s$inferior)
  }

  hechas <- length(anchos_diseno)
  if (hechas == 0) return(NULL)
  list(replicas = as.integer(hechas), verdadero = real, nominal = confianza,
       cobertura_del_diseno = aciertos_diseno / hechas,
       cobertura_ingenua = aciertos_ingenuo / hechas,
       ancho_medio_del_diseno = sum(anchos_diseno) / hechas,
       ancho_medio_ingenuo = sum(anchos_ingenuos) / hechas)
}

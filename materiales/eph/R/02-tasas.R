# Paso 2: las cuatro tasas del mercado de trabajo.
#
# Las cuatro salen de la misma cuenta —un numerador ponderado sobre un
# denominador ponderado— y **cada una tiene su propio denominador**. Ese es el
# error más común con la EPH después del de los ingresos:
#
#     actividad      PEA / población total
#     empleo         ocupados / población total
#     desocupación   desocupados / **PEA**
#     subocupación   subocupados / **PEA**
#
# La desocupación no se calcula sobre la población: se calcula sobre los que
# están en el mercado de trabajo. Un 7 % de desocupación no quiere decir que
# siete de cada cien personas no tengan trabajo; quiere decir que siete de cada
# cien que lo buscan no lo consiguen. Dividir por la población total da algo así
# como la mitad, y da un número que no es comparable con nada de lo que publica
# el INDEC.
#
# Las cuatro se calculan además **sin ponderar**, que es lo que sale de contar
# casos. La diferencia entre las dos columnas es lo que hacen los ponderadores,
# y no es chica.

# Cada tasa: cómo se llama, qué cuenta arriba y qué cuenta abajo.
TASAS <- list(
  list(nombre = "actividad", arriba = "Población económicamente activa",
       abajo = "Población total"),
  list(nombre = "empleo", arriba = "Ocupados", abajo = "Población total"),
  list(nombre = "desocupación", arriba = "Desocupados",
       abajo = "Población económicamente activa"),
  list(nombre = "subocupación", arriba = "Subocupados",
       abajo = "Población económicamente activa")
)

es_activo <- function(r) es(r$estado, 1) | es(r$estado, 2)

numerador_de <- function(nombre, r) {
  if (nombre == "actividad") return(es_activo(r))
  if (nombre == "empleo") return(es(r$estado, 1))
  if (nombre == "desocupación") return(es(r$estado, 2))
  # Subocupado es el ocupado que trabaja menos horas de las que querría:
  # INTENSI = 1. No es un desocupado y no se suma con ellos.
  es(r$estado, 1) & es(r$intensi, 1)
}

denominador_de <- function(nombre, r) {
  if (nombre %in% c("actividad", "empleo")) return(rep(TRUE, length(r$estado)))
  es_activo(r)
}

# Una tasa sobre un subconjunto, estimada como dominio.
#
# `dentro` marca el grupo —las mujeres, el Noroeste— y **no** se aplica
# filtrando la muestra: se aplica poniendo en cero el numerador y el
# denominador de los que quedan afuera. Es lo mismo para la estimación y no es
# lo mismo para el error estándar: filtrar rompe los conglomerados y pierde los
# hogares que quedaron sin ningún caso del grupo.
una_tasa <- function(registros, conglomerados, nombre, confianza, dentro = NULL) {
  if (is.null(dentro)) dentro <- rep(TRUE, length(registros$pondera))
  abajo <- dentro & denominador_de(nombre, registros)
  arriba <- abajo & numerador_de(nombre, registros)

  w <- registros$pondera
  y <- as.numeric(arriba)
  x <- as.numeric(abajo)
  salida <- estimar_razon(w, y, x, conglomerados, confianza)
  if (is.null(salida)) return(NULL)

  n_abajo <- as.integer(sum(x))
  n_arriba <- as.integer(sum(y))
  salida$tasa <- nombre
  salida$n_numerador <- n_arriba
  salida$n_denominador <- n_abajo
  salida$sin_ponderar <- if (n_abajo > 0) n_arriba / n_abajo else NA_real_
  salida$deff <- deff_de_proporcion(salida$estimacion, salida$error_estandar, n_abajo)
  salida
}

# Las cuatro tasas del total, con su error estándar y su efecto de diseño.
calcular <- function(registros, conglomerados, parametros) {
  confianza <- parametros$confianza
  filas <- list()
  for (definicion in TASAS) {
    t <- una_tasa(registros, conglomerados, definicion$nombre, confianza)
    if (is.null(t)) next
    deff <- t$deff
    filas[[length(filas) + 1]] <- list(
      tasa = definicion$nombre,
      numerador = definicion$arriba,
      denominador = definicion$abajo,
      poblacion_numerador = t$total_numerador,
      poblacion_denominador = t$total_denominador,
      n_denominador = t$n_denominador,
      valor = t$estimacion,
      error_estandar = t$error_estandar,
      inferior = t$inferior,
      superior = t$superior,
      gl = t$gl,
      deff = deff,
      n_efectivo = if (!is.na(deff) && deff > 0) t$n_denominador / deff else NA_real_,
      sin_ponderar = t$sin_ponderar,
      diferencia_con_la_ponderada = if (!is.na(t$sin_ponderar))
        t$sin_ponderar - t$estimacion else NA_real_)
  }
  filas
}

# Las mismas cuatro tasas, abiertas por sexo, por edad y por región.
#
# `cortes` es una lista con el nombre del corte, las etiquetas en orden y la
# función que devuelve la etiqueta de cada registro. El orden de las etiquetas
# lo fija el corte y no el alfabeto: «65 y más» va último porque es el último
# tramo, no porque empiece con seis.
por_grupo <- function(registros, conglomerados, parametros, cortes) {
  confianza <- parametros$confianza
  filas <- list()
  for (corte in cortes) {
    cuales <- corte$de_cual(registros)
    for (grupo in corte$etiquetas) {
      dentro <- cuales == grupo
      for (definicion in TASAS) {
        t <- una_tasa(registros, conglomerados, definicion$nombre, confianza, dentro)
        if (is.null(t) || t$n_denominador == 0) next
        filas[[length(filas) + 1]] <- list(
          corte = corte$corte, grupo = grupo, tasa = definicion$nombre,
          n_denominador = t$n_denominador,
          poblacion_denominador = t$total_denominador,
          valor = t$estimacion, error_estandar = t$error_estandar,
          inferior = t$inferior, superior = t$superior,
          sin_ponderar = t$sin_ponderar)
      }
    }
  }
  filas
}

# La comprobación que no puede fallar: empleo = actividad × (1 − desocupación).
#
# No es una casualidad aritmética: sale de que los tres cocientes comparten
# numeradores y denominadores. Si no cierra, algún denominador está mal, y como
# los tres se calculan por separado, el residuo de esta resta es la única señal
# que hay de que están bien.
identidad <- function(tasas) {
  nombres <- vapply(tasas, function(t) t$tasa, character(1))
  buscar <- function(n) {
    i <- which(nombres == n)
    if (length(i) == 0) NULL else tasas[[i[1]]]$valor
  }
  actividad <- buscar("actividad")
  empleo <- buscar("empleo")
  desocupacion <- buscar("desocupación")
  if (is.null(actividad) || is.null(empleo) || is.null(desocupacion)) return(NULL)
  esperado <- actividad * (1 - desocupacion)
  list(actividad = actividad, desocupacion = desocupacion,
       empleo_observado = empleo, empleo_por_la_identidad = esperado,
       residuo = empleo - esperado)
}

# Lo que hay que decir sobre las tasas, además de los números.
avisos_de <- function(tasas, identidad_, registros) {
  salida <- list()
  peores <- Filter(function(t) !is.na(t$deff) && t$deff > 2, tasas)
  if (length(peores) > 0) {
    cuales <- paste(vapply(peores, function(t) paste0("«", t$tasa, "»"),
                           character(1)), collapse = ", ")
    salida[[length(salida) + 1]] <- list(
      donde = "tasas",
      aviso = paste0(
        "El efecto de diseño de ", cuales, " pasa de 2. El efecto de diseño es un ",
        "cociente de varianzas, así que un 2 no duplica el intervalo: lo ensancha ",
        "un 41 %, que es la raíz de 2. Un programa al que se le pasa la columna sin ",
        "contarle del diseño informa el error de la raíz de abajo, y el intervalo le ",
        "sale así de corto."))
  }
  if (!is.null(identidad_) && abs(identidad_$residuo) > 1e-12) {
    salida[[length(salida) + 1]] <- list(
      donde = "tasas",
      aviso = paste0(
        "La identidad empleo = actividad × (1 − desocupación) no cierra. Los tres ",
        "denominadores tienen que salir de la misma población: si no cierra, alguno ",
        "no salió de ahí."))
  }
  chicos <- Filter(function(t) t$n_denominador < 100, tasas)
  if (length(chicos) > 0) {
    salida[[length(salida) + 1]] <- list(
      donde = "tasas",
      aviso = paste0(
        "Hay ", length(chicos), " tasas con menos de cien casos en el denominador. El ",
        "intervalo que sale es tan ancho que la tasa no distingue casi nada."))
  }
  # El aglomerado con un solo hogar en la muestra no aporta varianza. Con la EPH
  # entera no pasa; con un filtro por región o con un aglomerado chico, sí.
  aglomerados <- ordenar(registros$aglomerado)
  solitarios <- sum(vapply(aglomerados, function(a) {
    length(unique(registros$hogar[registros$aglomerado == a])) < 2
  }, logical(1)))
  if (solitarios > 0) {
    salida[[length(salida) + 1]] <- list(
      donde = "tasas",
      aviso = paste0(
        "Hay ", solitarios, " aglomerados con un solo hogar en la muestra. Un estrato ",
        "con una sola unidad no aporta varianza: su aporte al error estándar es cero, ",
        "y eso hace que el error total salga más chico de lo que corresponde."))
  }
  salida
}

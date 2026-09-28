# Paso 3: los ingresos, que es donde la EPH se cobra los descuidos.
#
# Con el ingreso de la ocupación principal hay dos decisiones que tomar, y las
# dos parecen menores:
#
# 1. **Qué hacer con el −9.** En la EPH, `P21 = −9` no es un ingreso negativo:
#    es «no responde». Un cero tampoco es lo mismo: el cero es un ocupado que no
#    cobra por su ocupación principal, y existe de verdad.
# 2. **Con qué ponderador.** `PONDERA` reparte la población; `PONDIIO` reparte
#    la población **de los que declararon ingreso de la ocupación principal**.
#    No son el mismo número y no sirven para lo mismo.
#
# Lo que hace difícil el asunto es que **cada error por separado casi no se
# nota, y juntos hunden el promedio un cuarto**. La tabla
# `ponderador-e-ingreso.csv` está armada para mostrar exactamente eso:
#
# - Con PONDIIO, meter o sacar a los que no declaran **da igual**, hasta el
#   último decimal. Es que el INDEC les pone el ponderador en cero: ya están
#   sacados.
# - Con PONDERA y sacando a los que no declaran, el promedio se corre poco.
# - Con PONDERA y los que no declaran adentro, se derrumba.
#
# De ahí la moraleja, que no es «acordate del −9» sino otra: los dos descuidos
# se tapan entre sí. El que usa PONDIIO nunca se entera de que nunca filtró el
# −9, y el día que corre el mismo script sobre un trimestre anterior a 2016T2
# —donde PONDIIO no existe— el filtro que nunca escribió deja de estar y nada
# avisa.

# Cuántos grupos tiene la tabla de deciles.
GRUPOS <- 10

ocupados_de <- function(r) es(r$estado, 1) & !is.na(r$p21)

# Los valores y sus pesos, ordenados por valor, que es lo que pide el cuantil.
ordenados_de <- function(r, cuales, peso) {
  valores <- r$p21[cuales]
  pesos <- r[[peso]][cuales]
  orden <- order(valores, method = "radix")
  list(valores = valores[orden], pesos = pesos[orden])
}

resumen_de <- function(r, cuales, peso) {
  if (!any(cuales)) return(NULL)
  pesos <- r[[peso]][cuales]
  total <- sum(pesos)
  if (total <= 0) return(NULL)
  media <- sum(r$p21[cuales] * pesos) / total
  o <- ordenados_de(r, cuales, peso)
  list(n = sum(cuales), poblacion = total, media = media,
       mediana = cuantil_ponderado(o$valores, o$pesos, 0.5))
}

# Las cinco maneras de calcular el mismo promedio. La primera es la correcta y
# las otras cuatro son las que salen de saltearse una decisión.
CASOS <- list(
  list(etiqueta = "Lo correcto", cual = "ingreso", menos_nueve = FALSE, cero = FALSE),
  list(etiqueta = "Con los que no declaran adentro", cual = "ingreso",
       menos_nueve = TRUE, cero = FALSE),
  list(etiqueta = "Con el ponderador general", cual = "general",
       menos_nueve = FALSE, cero = FALSE),
  list(etiqueta = "Con el ponderador general y los que no declaran adentro",
       cual = "general", menos_nueve = TRUE, cero = FALSE),
  list(etiqueta = "Con los ocupados sin ingreso adentro", cual = "ingreso",
       menos_nueve = FALSE, cero = TRUE)
)

# El mismo ingreso medio, calculado de las cinco maneras.
contraste <- function(registros, nombre_ponderador_ingreso, nombre_ponderador) {
  ocupados <- ocupados_de(registros)
  filas <- list()
  correcto <- NULL
  for (caso in CASOS) {
    peso <- if (caso$cual == "ingreso") "pondera_ingreso" else "pondera"
    cuales <- ocupados &
      (caso$menos_nueve | registros$p21 >= 0) &
      (caso$cero | registros$p21 != 0)
    cuales[is.na(cuales)] <- FALSE
    res <- resumen_de(registros, cuales, peso)
    if (is.null(res)) next
    if (is.null(correcto)) correcto <- res$media
    filas[[length(filas) + 1]] <- list(
      caso = caso$etiqueta,
      ponderador = if (caso$cual == "ingreso") nombre_ponderador_ingreso
                   else nombre_ponderador,
      que_hace_con_el_menos_nueve = if (caso$menos_nueve) "lo deja" else "lo saca",
      que_hace_con_el_cero = if (caso$cero) "lo deja" else "lo saca",
      n = res$n, poblacion = res$poblacion, media = res$media, mediana = res$mediana,
      diferencia = res$media - correcto,
      diferencia_relativa = if (correcto != 0) (res$media - correcto) / correcto
                            else NA_real_)
  }
  filas
}

# La media con su intervalo, la mediana y los diez grupos de la distribución.
distribucion <- function(registros, conglomerados, parametros) {
  casos <- ocupados_de(registros) & !is.na(registros$p21) & registros$p21 > 0
  casos[is.na(casos)] <- FALSE
  if (!any(casos)) return(list(resumen = list(), grupos = list()))

  # La media es una razón: suma de ingresos sobre suma de pesos. Se estima con
  # el mismo procedimiento que las tasas, y por la misma razón.
  w <- registros$pondera_ingreso
  y <- ifelse(casos, registros$p21, 0)
  y[is.na(y)] <- 0
  x <- as.numeric(casos)
  est <- estimar_razon(w, y, x, conglomerados, parametros$confianza)

  o <- ordenados_de(registros, casos, "pondera_ingreso")
  total_peso <- sum(o$pesos)
  total_ingreso <- sum(o$valores * o$pesos)
  cortes <- vapply(seq_len(GRUPOS - 1), function(k) {
    cuantil_ponderado(o$valores, o$pesos, k / GRUPOS)
  }, numeric(1))

  # A qué decil cae cada caso: uno más la cantidad de cortes que deja atrás. Un
  # empate justo sobre el corte cae del lado de abajo, y con ingresos declarados
  # en cifras redondas los empates son muchos: por eso los deciles no salen del
  # mismo tamaño.
  p21 <- registros$p21[casos]
  peso_caso <- registros$pondera_ingreso[casos]
  decil_de <- vapply(p21, function(v) 1L + sum(cortes < v), integer(1))

  grupos <- list()
  for (k in seq_len(GRUPOS)) {
    del_grupo <- decil_de == k
    peso <- sum(peso_caso[del_grupo])
    ingreso <- sum(p21[del_grupo] * peso_caso[del_grupo])
    grupos[[length(grupos) + 1]] <- list(
      decil = as.integer(k),
      corte_superior = if (k < GRUPOS) cortes[k] else NA_real_,
      n = sum(del_grupo), poblacion = peso,
      ingreso_medio = if (peso > 0) ingreso / peso else NA_real_,
      participacion = if (total_ingreso > 0) ingreso / total_ingreso else NA_real_)
  }

  media_simple <- sum(p21) / length(p21)
  d1 <- grupos[[1]]$ingreso_medio
  d10 <- grupos[[GRUPOS]]$ingreso_medio
  resumen <- list(
    list(estadistico = "casos", valor = sum(casos)),
    list(estadistico = "población representada", valor = total_peso),
    list(estadistico = "media", valor = if (!is.null(est)) est$estimacion else NA_real_),
    list(estadistico = "error estándar",
         valor = if (!is.null(est)) est$error_estandar else NA_real_),
    list(estadistico = "límite inferior",
         valor = if (!is.null(est)) est$inferior else NA_real_),
    list(estadistico = "límite superior",
         valor = if (!is.null(est)) est$superior else NA_real_),
    list(estadistico = "mediana", valor = cuantil_ponderado(o$valores, o$pesos, 0.5)),
    list(estadistico = "primer decil", valor = cortes[1]),
    list(estadistico = "noveno decil", valor = cortes[GRUPOS - 1]),
    list(estadistico = "razón entre el décimo y el primer decil",
         valor = if (!is.na(d1) && d1 != 0) d10 / d1 else NA_real_),
    list(estadistico = "media sin ponderar", valor = media_simple)
  )
  list(resumen = resumen, grupos = grupos)
}

# El ingreso medio y la mediana dentro de cada grupo, con PONDIIO.
por_grupo_ingreso <- function(registros, cortes) {
  casos <- ocupados_de(registros) & !is.na(registros$p21) & registros$p21 > 0
  casos[is.na(casos)] <- FALSE
  total <- resumen_de(registros, casos, "pondera_ingreso")
  filas <- list()
  for (corte in cortes) {
    cuales <- corte$de_cual(registros)
    for (grupo in corte$etiquetas) {
      del_grupo <- casos & cuales == grupo
      res <- resumen_de(registros, del_grupo, "pondera_ingreso")
      if (is.null(res)) next
      filas[[length(filas) + 1]] <- list(
        corte = corte$corte, grupo = grupo, n = res$n, poblacion = res$poblacion,
        media = res$media, mediana = res$mediana,
        razon_con_el_total = if (!is.null(total) && total$media != 0)
          res$media / total$media else NA_real_)
    }
  }
  filas
}

# Asalariados a los que no les hacen el descuento jubilatorio.
#
# Es la medida de informalidad que sale de la EPH sin pedirle nada más:
# `PP07H = 2` entre los `CAT_OCUP = 3`. No es «trabajo en negro» en sentido
# amplio —no dice nada de los cuentapropistas— pero es la que se puede calcular
# con esta base y la que el INDEC informa.
#
# El denominador son los asalariados, no los ocupados. Sobre los ocupados da
# bastante menos y no se compara con nada.
informalidad <- function(registros, conglomerados, parametros, cortes) {
  confianza <- parametros$confianza
  filas <- list()
  todos <- c(list(list(corte = "Total", etiquetas = "Total",
                       de_cual = function(r) rep("Total", length(r$pondera)))), cortes)
  for (corte in todos) {
    cuales <- corte$de_cual(registros)
    for (grupo in corte$etiquetas) {
      asalariado <- es(registros$estado, 1) & es(registros$cat_ocup, 3) & cuales == grupo
      n <- as.integer(sum(asalariado))
      if (n < 2) next
      x <- as.numeric(asalariado)
      y <- as.numeric(asalariado & es(registros$pp07h, 2))
      est <- estimar_razon(registros$pondera, y, x, conglomerados, confianza)
      if (is.null(est)) next
      filas[[length(filas) + 1]] <- list(
        corte = corte$corte, grupo = grupo, n_asalariados = n,
        asalariados = est$total_denominador, sin_descuento = est$total_numerador,
        tasa = est$estimacion, error_estandar = est$error_estandar,
        inferior = est$inferior, superior = est$superior)
    }
  }
  filas
}

# Lo que hay que decir sobre los ingresos, además de los números.
avisos_de_ingresos <- function(contraste_, grupos) {
  salida <- list()
  if (length(contraste_) >= 4) {
    correcto <- contraste_[[1]]
    igual <- contraste_[[2]]
    solo_peso <- contraste_[[3]]
    los_dos <- contraste_[[4]]
    if (abs(igual$diferencia) < 1e-9) {
      salida[[length(salida) + 1]] <- list(
        donde = "ingresos",
        aviso = paste0(
          "Con «", correcto$ponderador, "», dejar adentro a los que no declaran ",
          "ingreso **no cambia nada**: el promedio da igual hasta el último decimal, ",
          "porque ese ponderador les vale cero. Por eso el filtro del −9 se puede no ",
          "escribir nunca sin que nadie lo note."))
    }
    coma <- function(v) sub(".", ",", sprintf("%.1f", v), fixed = TRUE)
    salida[[length(salida) + 1]] <- list(
      donde = "ingresos",
      aviso = paste0(
        "Cambiar de ponderador corre el promedio ",
        coma(abs(100 * solo_peso$diferencia_relativa)),
        " %; dejar adentro al −9 con el ponderador general lo corre ",
        coma(abs(100 * los_dos$diferencia_relativa)),
        " %. Los dos descuidos por separado se disimulan y juntos no. Y van juntos ",
        "justo cuando el script se reusa sobre un trimestre anterior a 2016T2, que es ",
        "donde el ponderador de ingreso no existe."))
  }
  total_n <- sum(vapply(grupos, function(g) g$n, integer(1)))
  desparejos <- Filter(function(g) {
    fraccion <- g$n / max(1, total_n)
    !is.na(g$participacion) && g$poblacion > 0 && !(fraccion >= 0.05 && fraccion <= 0.16)
  }, grupos)
  if (length(desparejos) > 0) {
    salida[[length(salida) + 1]] <- list(
      donde = "ingresos",
      aviso = paste0(
        "Hay ", length(desparejos), " deciles con bastante más o bastante menos casos ",
        "que la décima parte. No es un error de cálculo: los ingresos declarados se ",
        "amontonan en cifras redondas, y un corte que cae sobre un montón se lleva ",
        "todo el montón para un lado."))
  }
  salida
}

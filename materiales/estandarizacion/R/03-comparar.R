# Paso 3: comparar, y saber cuánto de la comparación es real.
#
# Tres cosas que la tasa ajustada sola no contesta:
#
# 1. **¿Cuánto depende del estándar elegido?** Una tasa ajustada no es un número
#    de la población: es un número de la población *y del estándar*. Cambiar de
#    estándar cambia el nivel muchísimo —en estos datos, hasta el doble— y a
#    veces también el orden. Este paso recalcula todo con cada estándar
#    disponible y deja escrito exactamente qué pares se dan vuelta.
#
# 2. **¿La diferencia entre dos poblaciones es de estructura o de riesgo?** La
#    descomposición de Kitagawa parte la diferencia entre dos tasas crudas en
#    dos sumandos que suman exactamente la diferencia:
#
#        C_a − C_b = Σ (p_ai − p_bi)·(m_ai + m_bi)/2   ← estructura
#                  + Σ (m_ai − m_bi)·(p_ai + p_bi)/2   ← tasas
#
#    La primera suma es cuánto de la brecha viene de que las poblaciones tienen
#    edades distintas; la segunda, de que a cada edad se muere distinto. La
#    identidad es exacta y no aproximada, y por eso sirve de comprobación.
#
# 3. **¿La diferencia entre dos tasas ajustadas está establecida?** La razón
#    entre dos tasas, con su intervalo en escala logarítmica.

# La misma tasa ajustada, con cada estándar disponible.
por_estandar <- function(poblaciones, grupos, todos_los_pesos, parametros,
                         calcular_directa) {
  filas <- list()
  cuadro <- list()
  for (estandar in ordenar(names(todos_los_pesos))) {
    resultado <- calcular_directa(poblaciones, grupos, todos_los_pesos[[estandar]],
                                  parametros)
    por_nombre <- list()
    for (f in resultado) por_nombre[[f$poblacion]] <- f
    cuadro[[estandar]] <- por_nombre
    for (f in resultado) {
      filas[[length(filas) + 1]] <- list(
        estandar = estandar, poblacion = f$poblacion, tasa = f$estandarizada,
        inferior = f$estandarizada_inferior, superior = f$estandarizada_superior,
        rango = f$rango_estandarizado)
    }
  }
  # Ya salen ordenadas por estándar y por rango, que es como se leen.
  list(filas = filas, cuadro = cuadro)
}

# Los pares cuyo orden depende de con qué estándar se los mire.
#
# Es la comprobación de una frase que se dice mucho y es falsa: que el estándar
# cambia el nivel pero no el orden. Cambia el orden. Lo que hay que ver es
# **cuáles** pares se dan vuelta, y si son pares que alguien hubiera afirmado
# distintos.
sensibilidad <- function(cuadro, parametros) {
  estandares <- ordenar(names(cuadro))
  poblaciones <- ordenar(names(cuadro[[estandares[1]]]))
  filas <- list()
  if (length(estandares) < 2 || length(poblaciones) < 2) return(filas)
  pares_estandar <- combn(estandares, 2, simplify = FALSE)
  pares_poblacion <- combn(poblaciones, 2, simplify = FALSE)
  for (pe in pares_estandar) {
    for (pp in pares_poblacion) {
      ta <- cuadro[[pe[1]]][[pp[1]]]; tb <- cuadro[[pe[1]]][[pp[2]]]
      oa <- cuadro[[pe[2]]][[pp[1]]]; ob <- cuadro[[pe[2]]][[pp[2]]]
      primero <- ta$estandarizada - tb$estandarizada
      segundo <- oa$estandarizada - ob$estandarizada
      if (primero == 0 || segundo == 0 || (primero > 0) == (segundo > 0)) next
      # El solapamiento se mira con CADA estándar por separado. Un par que se da
      # vuelta y cuyos intervalos se pisan con los dos no estaba ordenado de
      # entrada; uno que se da vuelta y NO se pisa con alguno es el caso
      # peligroso: con ese estándar la diferencia parecía establecida.
      con_1 <- se_pisan(
        list(inferior = ta$estandarizada_inferior, superior = ta$estandarizada_superior),
        list(inferior = tb$estandarizada_inferior, superior = tb$estandarizada_superior))
      con_2 <- se_pisan(
        list(inferior = oa$estandarizada_inferior, superior = oa$estandarizada_superior),
        list(inferior = ob$estandarizada_inferior, superior = ob$estandarizada_superior))
      filas[[length(filas) + 1]] <- list(
        estandar_1 = pe[1], estandar_2 = pe[2],
        poblacion_a = pp[1], poblacion_b = pp[2],
        tasa_a_1 = ta$estandarizada, tasa_b_1 = tb$estandarizada,
        tasa_a_2 = oa$estandarizada, tasa_b_2 = ob$estandarizada,
        distancia_1 = abs(primero), distancia_2 = abs(segundo),
        se_pisan_con_1 = con_1, se_pisan_con_2 = con_2,
        se_pisan_con_los_dos = con_1 && con_2)
    }
  }
  filas
}

# Cuánto cambia el NIVEL de una misma tasa según el estándar.
niveles <- function(cuadro) {
  estandares <- ordenar(names(cuadro))
  poblaciones <- ordenar(names(cuadro[[estandares[1]]]))
  filas <- list()
  for (p in poblaciones) {
    valores <- vapply(estandares, function(e) cuadro[[e]][[p]]$estandarizada, numeric(1))
    menor <- min(valores); mayor <- max(valores)
    filas[[length(filas) + 1]] <- list(
      poblacion = p, menor = menor, mayor = mayor,
      razon_entre_niveles = if (menor > 0) mayor / menor else NA_real_,
      estandar_del_menor = estandares[which(valores == menor)[1]],
      estandar_del_mayor = estandares[which(valores == mayor)[1]])
  }
  filas
}

# Los dos efectos, grupo por grupo. Suman exactamente la diferencia.
kitagawa <- function(celdas_a, celdas_b, grupos) {
  na <- sum(vapply(grupos, function(g) celdas_a[[g]]$expuestos, numeric(1)))
  nb <- sum(vapply(grupos, function(g) celdas_b[[g]]$expuestos, numeric(1)))
  lapply(grupos, function(g) {
    pa <- if (na > 0) celdas_a[[g]]$expuestos / na else 0
    pb <- if (nb > 0) celdas_b[[g]]$expuestos / nb else 0
    ma <- if (celdas_a[[g]]$expuestos > 0) celdas_a[[g]]$casos / celdas_a[[g]]$expuestos
          else 0
    mb <- if (celdas_b[[g]]$expuestos > 0) celdas_b[[g]]$casos / celdas_b[[g]]$expuestos
          else 0
    list(grupo_edad = g, proporcion_a = pa, proporcion_b = pb, tasa_a = ma, tasa_b = mb,
         efecto_estructura = (pa - pb) * (ma + mb) / 2,
         efecto_tasas = (ma - mb) * (pa + pb) / 2)
  })
}

# La descomposición de Kitagawa para cada par pedido, grupo por grupo.
descomponer <- function(poblaciones, grupos, pares, parametros) {
  multiplicador <- parametros$multiplicador
  filas <- list()
  for (par in pares) {
    a <- par[1]; b <- par[2]
    if (is.null(poblaciones[[a]]) || is.null(poblaciones[[b]])) next
    for (fila in kitagawa(poblaciones[[a]], poblaciones[[b]], grupos)) {
      filas[[length(filas) + 1]] <- list(
        poblacion_a = a, poblacion_b = b, grupo_edad = fila$grupo_edad,
        proporcion_a = fila$proporcion_a, proporcion_b = fila$proporcion_b,
        tasa_a = fila$tasa_a * multiplicador, tasa_b = fila$tasa_b * multiplicador,
        efecto_estructura = fila$efecto_estructura * multiplicador,
        efecto_tasas = fila$efecto_tasas * multiplicador)
    }
  }
  filas
}

# Por cada par: la brecha cruda partida en dos, y la razón entre ajustadas.
comparar <- function(poblaciones, grupos, directas, pares, parametros) {
  multiplicador <- parametros$multiplicador
  confianza <- parametros$confianza
  por_nombre <- list()
  for (f in directas) por_nombre[[f$poblacion]] <- f
  filas <- list()
  for (par in pares) {
    a <- par[1]; b <- par[2]
    if (is.null(poblaciones[[a]]) || is.null(poblaciones[[b]])) {
      stop(paste0("«", a, "» o «", b, "» no está en los datos. Revisá «pares» ",
                  "en datos/parametros.csv."), call. = FALSE)
    }
    fa <- por_nombre[[a]]; fb <- por_nombre[[b]]
    partes <- kitagawa(poblaciones[[a]], poblaciones[[b]], grupos)
    estructura <- sum(vapply(partes, function(p) p$efecto_estructura, numeric(1))) *
      multiplicador
    tasas_ <- sum(vapply(partes, function(p) p$efecto_tasas, numeric(1))) * multiplicador
    diferencia <- fa$cruda - fb$cruda
    razon <- razon_de_tasas(
      list(valor = fa$estandarizada, inferior = fa$estandarizada_inferior,
           superior = fa$estandarizada_superior),
      list(valor = fb$estandarizada, inferior = fb$estandarizada_inferior,
           superior = fb$estandarizada_superior), confianza)
    filas[[length(filas) + 1]] <- list(
      poblacion_a = a, poblacion_b = b,
      cruda_a = fa$cruda, cruda_b = fb$cruda,
      diferencia_cruda = diferencia,
      efecto_estructura = estructura, efecto_tasas = tasas_,
      residuo_de_la_identidad = diferencia - (estructura + tasas_),
      # Qué proporción de la brecha cruda explica cada efecto. Puede pasar de
      # uno, y pasa: cuando los dos efectos van para lados contrarios, la
      # estructura explica más del 100 % y las tasas restan.
      parte_estructura = if (diferencia != 0) estructura / diferencia else NA_real_,
      estandarizada_a = fa$estandarizada, estandarizada_b = fb$estandarizada,
      diferencia_estandarizada = fa$estandarizada - fb$estandarizada,
      razon = if (!is.null(razon)) razon$valor else NA_real_,
      razon_inferior = if (!is.null(razon)) razon$inferior else NA_real_,
      razon_superior = if (!is.null(razon)) razon$superior else NA_real_,
      la_razon_excluye_al_uno = if (!is.null(razon))
        !(razon$inferior <= 1 && 1 <= razon$superior) else NA,
      se_dan_vuelta = (diferencia > 0) != (fa$estandarizada > fb$estandarizada))
  }
  filas
}

avisos_de_comparar <- function(sensibles, niveles_, comparaciones) {
  salida <- list()
  coma <- function(v) sub(".", ",", sprintf("%.1f", v), fixed = TRUE)

  if (length(sensibles) > 0) {
    pisados <- sum(vapply(sensibles, function(f) f$se_pisan_con_los_dos, logical(1)))
    peligrosos <- length(sensibles) - pisados
    aviso <- paste0(
      "Hay ", length(sensibles), " par(es) de poblaciones cuyo orden se da vuelta según ",
      "con qué estándar se las mire, y en ", pisados, " de ellos los intervalos se pisan ",
      "con los dos estándares. Es la respuesta a la frase de que el estándar cambia el ",
      "nivel pero no el orden: cambia el orden, y casi siempre lo cambia donde no estaba ",
      "establecido.")
    if (peligrosos > 0) {
      aviso <- paste0(aviso, " Casi siempre, pero no siempre: en ", peligrosos,
                      " par(es) los intervalos NO se pisan con alguno de los dos ",
                      "estándares, así que con ese estándar la diferencia parecía ",
                      "establecida y con el otro se da vuelta. Están marcados en ",
                      "sensibilidad.csv.")
    }
    salida[[length(salida) + 1]] <- list(donde = "estándar", aviso = aviso)
  }

  if (length(niveles_) > 0) {
    razones <- vapply(niveles_, function(f) if (is.na(f$razon_entre_niveles)) 0
                      else f$razon_entre_niveles, numeric(1))
    peor <- niveles_[[which.max(razones)]]
    if (!is.na(peor$razon_entre_niveles) && peor$razon_entre_niveles > 1.2) {
      salida[[length(salida) + 1]] <- list(
        donde = "estándar",
        aviso = paste0(
          "La tasa de «", peor$poblacion, "» va de ", coma(peor$menor),
          " con el estándar «", peor$estandar_del_menor, "» a ", coma(peor$mayor),
          " con «", peor$estandar_del_mayor, "». Son los mismos datos y el mismo método. ",
          "Una tasa ajustada sin el nombre de su estándar al lado no quiere decir nada, y ",
          "dos tasas ajustadas con estándares distintos no se comparan."))
    }
  }

  for (f in comparaciones) {
    if (isTRUE(f$se_dan_vuelta)) {
      salida[[length(salida) + 1]] <- list(
        donde = "comparación",
        aviso = paste0(
          "Entre «", f$poblacion_a, "» y «", f$poblacion_b, "» la tasa cruda y la ",
          "ajustada van para lados contrarios. La descomposición dice por qué: el efecto ",
          "de la estructura es ", coma(f$efecto_estructura), " y el de las tasas ",
          coma(f$efecto_tasas), ", y el primero es más grande que la brecha entera."))
    }
  }
  salida
}

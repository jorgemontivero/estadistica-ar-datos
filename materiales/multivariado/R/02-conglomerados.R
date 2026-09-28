# Paso 2: conglomerados jerárquicos.
#
# Dos cosas que un dendrograma no dice y este paso sí.
#
# **La primera: el enlace cambia los grupos.** «Agrupamiento jerárquico» no es un
# método, son cuatro, y sobre los mismos datos dan particiones distintas. El
# simple encadena —arma una serpiente larga y deja afuera a los raros—, el
# completo y el de Ward hacen bolas compactas. No hay uno correcto: hay uno
# elegido, y hay que decir cuál.
#
# **La segunda, y es la importante: agrupar siempre devuelve grupos.** Pedirle
# cuatro conglomerados a una nube sin ninguna estructura devuelve cuatro
# conglomerados prolijos, con su dendrograma y todo. Para saber si los grupos
# dicen algo hay que compararlos contra el caso en que no dicen nada, y eso es
# lo que hace la parte del nulo: se desordena cada columna por separado —con lo
# cual cada variable conserva exactamente sus valores y se rompe la relación
# entre ellas—, se vuelve a agrupar y se mira la silueta. Si la silueta de los
# datos de verdad no le gana a la de los datos desordenados, los grupos son del
# método y no de los datos.

ENLACES <- c("simple", "completo", "promedio", "ward")

# La matriz de distancias euclídeas entre unidades.
#
# Sobre los datos **tipificados**, siempre. Una distancia euclídea sobre
# columnas en unidades distintas es una suma de cosas que no se suman: la
# variable de números más grandes decide toda la distancia.
distancias <- function(base) {
  n <- nrow(base)
  p <- ncol(base)
  d <- matrix(0, nrow = n, ncol = n)
  for (i in seq_len(n)) {
    if (i == n) break
    for (j in (i + 1):n) {
      total <- 0
      for (k in seq_len(p)) {
        diferencia <- base[i, k] - base[j, k]
        total <- total + diferencia * diferencia
      }
      valor <- sqrt(total)
      d[i, j] <- valor
      d[j, i] <- valor
    }
  }
  d
}

# La fórmula que actualiza la distancia al fusionar i con j.
#
# Los cuatro enlaces son la misma recurrencia con otros coeficientes, y
# escribirlos juntos deja ver que la diferencia entre ellos es de tres números y
# no de método.
lance_williams <- function(enlace, dik, djk, dij, ni, nj, nk) {
  if (enlace == "simple") return(min(dik, djk))
  if (enlace == "completo") return(max(dik, djk))
  if (enlace == "promedio") return((ni * dik + nj * djk) / (ni + nj))
  # Ward trabaja sobre distancias **al cuadrado**; la altura que se informa
  # después es su raíz. Es lo que hace `hclust(method = "ward.D2")`.
  total <- ni + nj + nk
  ((ni + nk) * dik + (nj + nk) * djk - nk * dij) / total
}

# El árbol completo, de n grupos de a uno hasta uno solo de n.
#
# En cada paso se fusiona el par más cercano. **Los empates se rompen por
# índice**, del más chico al más grande: sin esa regla, dos motores podrían
# fusionar en distinto orden y devolver árboles distintos con las mismas
# distancias.
agrupar <- function(d, enlace) {
  n <- nrow(d)
  trabajo <- if (enlace == "ward") d * d else d
  activos <- seq_len(n)
  miembros <- lapply(seq_len(n), function(i) i)
  fusiones <- list()

  while (length(activos) > 1) {
    mejor <- NULL
    for (a in seq_len(length(activos) - 1)) {
      for (b in (a + 1):length(activos)) {
        i <- activos[a]
        j <- activos[b]
        valor <- trabajo[i, j]
        if (is.null(mejor) || valor < mejor$valor) {
          mejor <- list(valor = valor, i = i, j = j)
        }
      }
    }
    i <- mejor$i
    j <- mejor$j
    altura <- if (enlace == "ward") sqrt(mejor$valor) else mejor$valor
    fusiones[[length(fusiones) + 1]] <- list(
      paso = as.integer(length(fusiones) + 1), grupo_a = i, grupo_b = j,
      altura = altura,
      tamano = as.integer(length(miembros[[i]]) + length(miembros[[j]])))

    ni <- length(miembros[[i]])
    nj <- length(miembros[[j]])
    dij <- trabajo[i, j]
    for (k in activos) {
      if (k == i || k == j) next
      nuevo <- lance_williams(enlace, trabajo[i, k], trabajo[j, k], dij, ni, nj,
                              length(miembros[[k]]))
      trabajo[i, k] <- nuevo
      trabajo[k, i] <- nuevo
    }
    miembros[[i]] <- c(miembros[[i]], miembros[[j]])
    miembros[[j]] <- integer(0)
    activos <- activos[activos != j]
  }
  fusiones
}

# La partición en k grupos: se rehacen las fusiones hasta que queden k.
#
# Las etiquetas salen **por el miembro más chico de cada grupo**, para que el
# grupo 1 sea siempre el mismo grupo y no dependa del orden en que el algoritmo
# los fue armando.
#
# Con el `agrupar` de acá arriba la regla es redundante —el par se elige
# recorriendo los activos en orden, así que la raíz de un grupo ya es su miembro
# más chico— y está escrita igual: si alguien cambia cómo se elige el par, la
# numeración tiene que seguir siendo la misma.
cortar <- function(fusiones, n, k) {
  miembros <- lapply(seq_len(n), function(i) i)
  vivos <- seq_len(n)
  cuantas <- max(0, n - k)
  if (cuantas > 0) {
    for (f in fusiones[seq_len(cuantas)]) {
      miembros[[f$grupo_a]] <- c(miembros[[f$grupo_a]], miembros[[f$grupo_b]])
      miembros[[f$grupo_b]] <- integer(0)
      vivos <- vivos[vivos != f$grupo_b]
    }
  }
  minimos <- vapply(vivos, function(r) min(miembros[[r]]), numeric(1))
  orden <- vivos[order(minimos, method = "radix")]
  etiquetas <- integer(n)
  for (numero in seq_along(orden)) {
    for (m in miembros[[orden[numero]]]) etiquetas[m] <- numero
  }
  etiquetas
}

# La silueta de cada unidad y el promedio.
#
# Para cada unidad: `a` es lo lejos que está de las de su propio grupo, `b` lo
# lejos que está del grupo ajeno más cercano, y la silueta es (b − a) dividido
# por el mayor de los dos. Uno quiere decir «clavada en su grupo», cero «justo
# en el borde» y negativo «está en el grupo equivocado».
#
# Una unidad sola en su grupo tiene silueta cero por convención: no hay con
# quién compararla adentro.
silueta <- function(d, etiquetas) {
  n <- length(etiquetas)
  grupos <- sort(unique(etiquetas))
  por_unidad <- numeric(n)
  for (i in seq_len(n)) {
    propio <- which(etiquetas == etiquetas[i] & seq_len(n) != i)
    if (length(propio) == 0) {
      por_unidad[i] <- 0
      next
    }
    a <- suma(vapply(propio, function(j) d[i, j], numeric(1))) / length(propio)
    b <- NA_real_
    for (g in grupos) {
      if (g == etiquetas[i]) next
      ajenos <- which(etiquetas == g)
      if (length(ajenos) == 0) next
      promedio <- suma(vapply(ajenos, function(j) d[i, j], numeric(1))) / length(ajenos)
      if (is.na(b) || promedio < b) b <- promedio
    }
    if (is.na(b)) {
      por_unidad[i] <- 0
    } else {
      por_unidad[i] <- if (max(a, b) > 0) (b - a) / max(a, b) else 0
    }
  }
  list(por_unidad = por_unidad, media = suma(por_unidad) / n)
}

# Cuánto se parecen dos particiones, corregido por el azar.
#
# Vale 1 si son la misma partición y alrededor de 0 si coinciden lo que
# coincidirían dos particiones cualesquiera. Hace falta porque las etiquetas de
# los grupos son arbitrarias: el grupo 1 de un enlace no tiene por qué ser el
# grupo 1 del otro.
rand_ajustado <- function(a, b) {
  n <- length(a)
  ga <- sort(unique(a))
  gb <- sort(unique(b))
  tabla <- matrix(0, nrow = length(ga), ncol = length(gb))
  for (x in seq_along(ga)) {
    for (y in seq_along(gb)) {
      tabla[x, y] <- sum(a == ga[x] & b == gb[y])
    }
  }
  combina <- function(x) x * (x - 1) / 2
  # `t(tabla)` puesta en vector recorre por filas, que es el orden en que la
  # otra versión la recorre.
  juntos <- suma(vapply(as.vector(t(tabla)), combina, numeric(1)))
  filas <- suma(vapply(seq_along(ga), function(x) combina(sum(tabla[x, ])), numeric(1)))
  columnas <- suma(vapply(seq_along(gb), function(y) combina(sum(tabla[, y])), numeric(1)))
  total <- combina(n)
  esperado <- filas * columnas / total
  maximo <- (filas + columnas) / 2
  if (maximo == esperado) return(1)
  (juntos - esperado) / (maximo - esperado)
}

# Cada columna corrida un poco más que la anterior.
#
# Es la manera de romper la relación entre las variables **sin tocar los
# valores**: cada columna conserva exactamente los suyos, su media y su desvío,
# y lo único que se pierde es con qué fila iba cada uno. No hace falta ningún
# generador de azar, así que los dos idiomas arman exactamente los mismos nulos.
desplazar <- function(base, corrimiento) {
  n <- nrow(base)
  p <- ncol(base)
  salida <- base
  for (i in seq_len(n)) {
    for (j in seq_len(p)) {
      salida[i, j] <- base[((i - 1 + j * corrimiento) %% n) + 1, j]
    }
  }
  salida
}

calcular_conglomerados <- function(base, unidades, parametros) {
  d <- distancias(base)
  n <- length(unidades)
  k <- parametros$conglomerados
  if (k > n) {
    stop(paste0("Se piden ", k, " conglomerados y hay ", n, " unidades."), call. = FALSE)
  }
  por_enlace <- list()
  for (enlace in ENLACES) {
    fusiones <- agrupar(d, enlace)
    etiquetas <- cortar(fusiones, n, k)
    s <- silueta(d, etiquetas)
    por_enlace[[enlace]] <- list(fusiones = fusiones, etiquetas = etiquetas,
                                 siluetas = s$por_unidad, silueta = s$media)
  }
  if (is.null(por_enlace[[parametros$enlace]])) {
    stop(paste0("«", parametros$enlace, "» no es un enlace conocido. Hay: ",
                paste(ENLACES, collapse = ", "), "."), call. = FALSE)
  }
  list(d = d, por_enlace = por_enlace)
}

tabla_de_grupos <- function(unidades, por_enlace, parametros) {
  elegido <- parametros$enlace
  filas <- list()
  for (i in seq_along(unidades)) {
    fila <- list(unidad = unidades[i])
    for (enlace in ENLACES) fila[[enlace]] <- por_enlace[[enlace]]$etiquetas[i]
    fila$silueta <- por_enlace[[elegido]]$siluetas[i]
    filas[[i]] <- fila
  }
  filas
}

tabla_de_fusiones <- function(por_enlace, unidades) {
  filas <- list()
  for (enlace in ENLACES) {
    for (f in por_enlace[[enlace]]$fusiones) {
      filas[[length(filas) + 1]] <- list(
        enlace = enlace, paso = f$paso,
        unidad_a = unidades[f$grupo_a], unidad_b = unidades[f$grupo_b],
        altura = f$altura, tamano = f$tamano)
    }
  }
  filas
}

tabla_de_siluetas <- function(por_enlace, parametros) {
  elegido <- parametros$enlace
  referencia <- por_enlace[[elegido]]$etiquetas
  filas <- list()
  for (e in seq_along(ENLACES)) {
    enlace <- ENLACES[e]
    etiquetas <- por_enlace[[enlace]]$etiquetas
    tamanos <- vapply(sort(unique(etiquetas)), function(g) sum(etiquetas == g), numeric(1))
    filas[[e]] <- list(
      enlace = enlace, grupos = as.integer(length(tamanos)),
      mayor = as.integer(max(tamanos)), menor = as.integer(min(tamanos)),
      silueta = por_enlace[[enlace]]$silueta,
      negativas = as.integer(sum(por_enlace[[enlace]]$siluetas < 0)),
      acuerdo_con_el_elegido = rand_ajustado(etiquetas, referencia))
  }
  filas
}

# La misma silueta, sobre datos a los que se les rompió la relación.
#
# Hay tantos nulos como corrimientos posibles: con n unidades, n − 1. Ninguno
# inventa datos y todos conservan cada columna intacta.
contra_el_nulo <- function(base, parametros) {
  n <- nrow(base)
  k <- parametros$conglomerados
  enlace <- parametros$enlace
  filas <- list()
  for (corrimiento in seq_len(n - 1)) {
    movida <- desplazar(base, corrimiento)
    d <- distancias(movida)
    fusiones <- agrupar(d, enlace)
    etiquetas <- cortar(fusiones, n, k)
    s <- silueta(d, etiquetas)
    filas[[corrimiento]] <- list(corrimiento = as.integer(corrimiento), silueta = s$media)
  }
  filas
}

resumen_del_nulo <- function(nulos, real) {
  valores <- sort(vapply(nulos, function(f) f$silueta, numeric(1)))
  n <- length(valores)
  mediana <- if (n %% 2 == 1) valores[(n + 1) %/% 2]
             else (valores[n / 2] + valores[n / 2 + 1]) / 2
  mejores <- sum(valores >= real)
  list(replicas = as.integer(n), silueta_real = real, menor = valores[1],
       mediana = mediana, mayor = valores[n],
       nulos_que_igualan_o_superan = as.integer(mejores),
       # La proporción de nulos que llegan a la silueta real. No es un valor p
       # —los nulos no son independientes entre sí— pero se lee parecido.
       proporcion = mejores / n)
}

avisos_de_conglomerados <- function(por_enlace, nulo, parametros, unidades) {
  salida <- list()
  elegido <- parametros$enlace
  coma3 <- function(v) sub(".", ",", sprintf("%.3f", v), fixed = TRUE)

  if (nulo$mayor >= nulo$silueta_real) {
    salida[[length(salida) + 1]] <- list(
      donde = "conglomerados",
      aviso = paste0(
        "La silueta de los datos de verdad es ", coma3(nulo$silueta_real),
        " y la de los datos desordenados llega hasta ", coma3(nulo$mayor),
        ". Los grupos que salen no son mejores que los que salen de una tabla a la que ",
        "se le rompió la relación entre variables: son del método, no de los datos."))
  } else {
    salida[[length(salida) + 1]] <- list(
      donde = "conglomerados",
      aviso = paste0(
        "La silueta de los datos de verdad es ", coma3(nulo$silueta_real), " y ninguno ",
        "de los ", nulo$replicas, " desordenados la alcanza: el mejor llega a ",
        coma3(nulo$mayor), ". Hay estructura. Eso no dice que los grupos sean los ",
        "correctos ni que sean cuatro: dice que no son un invento del método."))
  }

  acuerdos <- tabla_de_siluetas(por_enlace, parametros)
  otros <- Filter(function(f) f$enlace != elegido, acuerdos)
  valores <- vapply(otros, function(f) f$acuerdo_con_el_elegido, numeric(1))
  peor <- otros[[which.min(valores)]]
  salida[[length(salida) + 1]] <- list(
    donde = "conglomerados",
    aviso = paste0(
      "Cambiar de enlace cambia los grupos. Entre «", elegido, "» y «", peor$enlace,
      "» el índice de Rand ajustado es ", coma3(peor$acuerdo_con_el_elegido),
      ". Los cuatro árboles salen de la misma matriz de distancias: lo único que cambia ",
      "es cómo se mide la distancia entre dos grupos ya armados."))

  for (enlace in c("simple")) {
    etiquetas <- por_enlace[[enlace]]$etiquetas
    tamanos <- vapply(sort(unique(etiquetas)), function(g) sum(etiquetas == g), numeric(1))
    if (max(tamanos) >= length(unidades) - length(tamanos)) {
      salida[[length(salida) + 1]] <- list(
        donde = "conglomerados",
        aviso = paste0(
          "El enlace ", enlace, " deja ", max(tamanos), " de las ", length(unidades),
          " unidades en un solo grupo y el resto casi sueltas. Es lo que hace: encadena. ",
          "No está roto, está haciendo lo que la fórmula dice, y por eso casi nunca se ",
          "usa para armar tipologías."))
    }
  }

  negativas <- sum(por_enlace[[elegido]]$siluetas < 0)
  if (negativas > 0) {
    salida[[length(salida) + 1]] <- list(
      donde = "conglomerados",
      aviso = paste0(
        "Hay ", negativas, " unidad(es) con silueta negativa: están más cerca del grupo ",
        "de al lado que del propio. Un dendrograma no las muestra, y en un mapa de los ",
        "dos primeros componentes tampoco se ven."))
  }
  salida
}

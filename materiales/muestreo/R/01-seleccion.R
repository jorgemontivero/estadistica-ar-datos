# Paso 1: sacar la muestra, de cuatro maneras.
#
# Los cuatro diseños salen del **mismo marco y con la misma semilla**, y cada
# uno deja escrito cuál es la probabilidad de inclusión de cada unidad. Esa
# probabilidad es todo lo que el paso siguiente necesita: el ponderador es su
# inversa, y de ahí sale cualquier estimación.
#
#     aleatorio simple   n de N, todos con la misma probabilidad.
#     sistemático        un arranque al azar y después cada k. Es el más fácil
#                        de ejecutar en campo y el único de los cuatro que **no
#                        tiene un estimador insesgado de la varianza**.
#     estratificado      se reparte la muestra entre los estratos y dentro de
#                        cada uno se hace un aleatorio simple. Con afijación
#                        proporcional o de Neyman.
#     bietápico          primero se sortean conglomerados dentro de cada
#                        estrato, y después hogares dentro de cada conglomerado
#                        elegido. Es el diseño de cualquier encuesta de hogares
#                        que salga a la calle.
#
# **Esta versión usa `set.seed` y `sample.int` directamente.** La de Python
# reimplementa el Mersenne-Twister de R bit por bit para poder dar la misma
# muestra. La asimetría es a propósito: el estándar de hecho para documentar
# una selección es R, y quien quiera auditarla tiene que poder correr dos
# líneas y obtener exactamente los mismos casos.

aleatorio_simple <- function(datos, n, semilla) {
  total <- length(datos)
  set.seed(semilla)
  elegidos <- sort(sample.int(total, n))
  probabilidad <- n / total
  lapply(elegidos, function(i) {
    list(fila = i, probabilidad = probabilidad, conglomerado = NULL)
  })
}

# Arranque al azar en (0, k] y después cada k, con k = N/n.
#
# El intervalo se deja decimal a propósito. Redondearlo es lo que hace que una
# muestra sistemática termine con un caso de más o de menos, y con el último
# tramo del marco sin representar.
#
# **Ojo con el orden del marco.** Un sistemático sobre un marco ordenado por
# una variable relacionada con lo que se mide es, en los hechos, un
# estratificado —y sale mejor que un aleatorio simple—. Sobre un marco con una
# periodicidad que coincida con k, sale mucho peor. El diseño no está en el
# algoritmo: está en cómo viene ordenado el archivo.
sistematico <- function(datos, n, semilla) {
  total <- length(datos)
  k <- total / n
  set.seed(semilla)
  arranque <- runif(1) * k
  posiciones <- vapply(seq_len(n) - 1, function(i) {
    max(1, min(total, ceiling(arranque + i * k)))
  }, numeric(1))
  probabilidad <- n / total
  list(muestra = lapply(sort(unique(posiciones)), function(p) {
    list(fila = as.integer(p), probabilidad = probabilidad, conglomerado = NULL)
  }), intervalo = k, arranque = arranque)
}

# Cuántos casos le tocan a cada estrato.
#
# proporcional   en proporción a su tamaño. Es la que casi siempre se usa y la
#                que hace que todos los pesos salgan iguales.
# neyman         en proporción a N_h·S_h: más muestra donde hay más dispersión.
#                Minimiza la varianza para un n dado, y a cambio deja pesos
#                desiguales.
#
# El reparto se hace por restos mayores y no redondeando cada cuota, para que
# la suma dé exactamente n. Redondear una por una es lo que hace que una
# muestra de 320 termine teniendo 318 o 323.
afijar <- function(tamanos, desvios, n, metodo) {
  pesos <- if (metodo == "neyman") tamanos * desvios else as.numeric(tamanos)
  suma <- sum(pesos)
  if (suma <= 0) {
    pesos <- rep(1, length(tamanos))
    suma <- length(tamanos)
  }
  exactos <- n * pesos / suma
  enteros <- floor(exactos)
  # Los que sobran van a los estratos con el resto más grande; entre restos
  # iguales manda el orden del estrato, para que no dependa del azar.
  faltan <- n - sum(enteros)
  orden <- order(-(exactos - enteros), seq_along(pesos), method = "radix")
  if (faltan > 0) {
    for (i in seq_len(faltan)) {
      j <- orden[((i - 1) %% length(orden)) + 1]
      enteros[j] <- enteros[j] + 1
    }
  }
  # Nadie puede quedar con menos de dos casos ni con más de los que tiene.
  as.integer(pmin(tamanos, pmax(2, enteros)))
}

# Un aleatorio simple dentro de cada estrato, con las cuotas ya repartidas.
#
# La semilla se siembra una sola vez y el generador sigue de estrato en
# estrato. Sembrar de nuevo en cada estrato daría muestras correlacionadas
# entre estratos, que es un error silencioso y bastante común.
estratificado <- function(datos, n, semilla, estrato, metodo, valores) {
  grupos <- indices_por(datos, estrato)
  nombres <- names(grupos)
  tamanos <- vapply(grupos, length, integer(1))
  desvios <- vapply(grupos, function(idx) {
    v <- valores[idx]
    if (length(v) > 1) sd(v) else 0
  }, numeric(1))

  cuotas <- afijar(tamanos, desvios, n, metodo)
  set.seed(semilla)
  salida <- list()
  for (j in seq_along(nombres)) {
    posiciones <- grupos[[j]]
    elegidos <- sort(sample.int(length(posiciones), cuotas[j]))
    probabilidad <- cuotas[j] / length(posiciones)
    for (e in elegidos) {
      salida[[length(salida) + 1]] <- list(
        fila = as.integer(posiciones[e]), probabilidad = probabilidad,
        conglomerado = NULL)
    }
  }
  salida <- salida[order(vapply(salida, function(f) f$fila, numeric(1)), method = "radix")]
  cuotas_con_nombre <- as.list(cuotas)
  names(cuotas_con_nombre) <- nombres
  list(muestra = salida, cuotas = cuotas_con_nombre)
}

# Conglomerados dentro de cada estrato, y hogares dentro de cada uno.
#
# La probabilidad de inclusión de un hogar es el producto de las dos etapas:
#
#     π = (a_h / A_h) · (m / M_i)
#
# donde a_h de los A_h conglomerados del estrato salieron sorteados, y m de los
# M_i hogares del conglomerado i. Si todos los conglomerados tuvieran el mismo
# tamaño, esa probabilidad sería igual para todos y los pesos saldrían parejos;
# como no lo son, no salen parejos, y ahí empieza a importar el ponderador.
bietapico <- function(datos, semilla, estrato, conglomerado, por_estrato, por_conglomerado) {
  por_estr <- indices_por(datos, estrato)
  todos_cong <- limpiar_texto(columna(datos, conglomerado))
  set.seed(semilla)
  salida <- list()
  detalle <- list()
  for (h in names(por_estr)) {
    indices <- por_estr[[h]]
    nombres <- ordenar(todos_cong[indices])
    cuantos <- min(por_estrato, length(nombres))
    elegidos <- sort(sample.int(length(nombres), cuantos))
    detalle[[length(detalle) + 1]] <- list(
      estrato = h, conglomerados_en_el_marco = as.integer(length(nombres)),
      conglomerados_elegidos = as.integer(cuantos))
    for (e in elegidos) {
      nombre <- nombres[e]
      dentro <- indices[todos_cong[indices] == nombre]
      m <- min(por_conglomerado, length(dentro))
      hogares <- sort(sample.int(length(dentro), m))
      probabilidad <- (cuantos / length(nombres)) * (m / length(dentro))
      for (g in hogares) {
        salida[[length(salida) + 1]] <- list(
          fila = as.integer(dentro[g]), probabilidad = probabilidad,
          conglomerado = nombre)
      }
    }
  }
  salida <- salida[order(vapply(salida, function(f) f$fila, numeric(1)), method = "radix")]
  list(muestra = salida, detalle = detalle)
}

# Los cuatro diseños, con el mismo tamaño de muestra.
#
# El tamaño lo fija el bietápico —conglomerados por estrato × hogares por
# conglomerado × estratos— y los otros tres lo copian, porque comparar diseños
# de distinto n no diría nada sobre el diseño.
calcular_seleccion <- function(datos, parametros, valores) {
  semilla <- parametros$semilla
  estrato <- parametros$estrato
  conglomerado <- parametros$conglomerado

  dos <- bietapico(datos, semilla, estrato, conglomerado,
                   parametros$conglomerados_por_estrato,
                   parametros$hogares_por_conglomerado)
  n <- length(dos$muestra)

  sis <- sistematico(datos, n, semilla)
  prop <- estratificado(datos, n, semilla, estrato, "proporcional", valores)
  ney <- estratificado(datos, n, semilla, estrato, "neyman", valores)

  disenos <- list(
    "aleatorio simple" = aleatorio_simple(datos, n, semilla),
    "sistemático" = sis$muestra,
    "estratificado proporcional" = prop$muestra,
    "estratificado de Neyman" = ney$muestra,
    "bietápico" = dos$muestra)

  list(n = as.integer(n), disenos = disenos,
       intervalo = sis$intervalo, arranque = sis$arranque,
       cuotas_proporcional = prop$cuotas, cuotas_neyman = ney$cuotas,
       detalle_bietapico = dos$detalle)
}

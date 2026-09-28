# Autovalores y autovectores de una matriz simétrica, a mano y sin dependencias.
#
# Es la pieza de la que cuelga todo el proyecto: componentes principales,
# correspondencias y hasta las distancias salen de descomponer una matriz
# simétrica. Está escrita a mano por dos razones.
#
# **La primera es que tiene que dar lo mismo en los dos idiomas.** `eigen` de R
# y `numpy.linalg.eigh` usan LAPACK, y aun así no devuelven los mismos bits:
# eligen distinto el orden de los autovalores empatados, y sobre todo eligen
# distinto el **signo** de cada autovector. Un componente principal con el signo
# cambiado es el mismo componente —la varianza explicada no cambia, las cargas
# cambian todas de signo a la vez— pero es la causa número uno de que dos
# personas digan que «el PCA les dio distinto». Acá el signo lo fija una regla
# escrita más abajo.
#
# **La segunda es que el método de Jacobi se puede leer.** Son cuarenta líneas
# de rotaciones de dos por dos que van poniendo ceros fuera de la diagonal, y
# cada una se entiende sola. Para matrices chicas —las de este proyecto tienen
# ocho y cinco filas— es tan preciso como cualquier otro método y bastante más
# transparente.
#
# **No hay ninguna suma vectorizada acá adentro.** En el resto del proyecto las
# sumas van con `sum`, que en R acumula en long double; acá todo se acumula con
# sumas comunes en un orden fijo, así que las dos versiones hacen exactamente
# las mismas operaciones de punto flotante y devuelven exactamente los mismos
# bits.

# Cuándo se considera que ya no queda nada fuera de la diagonal. Es una suma de
# cuadrados, así que la tolerancia se compara contra su raíz.
TOLERANCIA <- 1e-14
BARRIDOS <- 100

identidad <- function(n) {
  a <- matrix(0, nrow = n, ncol = n)
  for (i in seq_len(n)) a[i, i] <- 1
  a
}

es_simetrica <- function(a) {
  n <- nrow(a)
  if (n < 2) return(TRUE)
  for (i in seq_len(n - 1)) {
    for (j in (i + 1):n) if (a[i, j] != a[j, i]) return(FALSE)
  }
  TRUE
}

# La suma de los cuadrados de lo que hay fuera de la diagonal.
#
# Es lo que el método va llevando a cero: cuando esto es cero, la matriz es
# diagonal y en la diagonal están los autovalores.
fuera_de_la_diagonal <- function(a) {
  n <- nrow(a)
  total <- 0
  if (n < 2) return(total)
  for (p in seq_len(n - 1)) {
    for (q in (p + 1):n) total <- total + a[p, q] * a[p, q]
  }
  total
}

# Una rotación de Jacobi: la que pone en cero el elemento (p, q).
#
# El ángulo sale de resolver una cuadrática. La forma en que se calcula `t` —con
# el signo adelante y la raíz en el denominador— no es capricho: es la que evita
# restar dos números parecidos, que es donde una implementación ingenua pierde
# precisión.
rotar <- function(a, v, p, q) {
  n <- nrow(a)
  theta <- (a[q, q] - a[p, p]) / (2 * a[p, q])
  if (theta >= 0) {
    t <- 1 / (theta + sqrt(theta * theta + 1))
  } else {
    t <- -1 / (-theta + sqrt(theta * theta + 1))
  }
  c_ <- 1 / sqrt(t * t + 1)
  s <- t * c_

  for (k in seq_len(n)) {
    akp <- a[k, p]
    akq <- a[k, q]
    a[k, p] <- c_ * akp - s * akq
    a[k, q] <- s * akp + c_ * akq
  }
  for (k in seq_len(n)) {
    apk <- a[p, k]
    aqk <- a[q, k]
    a[p, k] <- c_ * apk - s * aqk
    a[q, k] <- s * apk + c_ * aqk
  }
  # Los dos que la rotación acaba de anular se ponen en cero exacto: el valor
  # que queda es del orden del error de redondeo y dejarlo hace que el criterio
  # de corte tarde de más.
  a[p, q] <- 0
  a[q, p] <- 0

  for (k in seq_len(n)) {
    vkp <- v[k, p]
    vkq <- v[k, q]
    v[k, p] <- c_ * vkp - s * vkq
    v[k, q] <- s * vkp + c_ * vkq
  }
  list(a = a, v = v)
}

# Los autovalores de mayor a menor, y el signo de cada vector decidido.
#
# **El signo de un autovector es arbitrario**: si v es autovector, −v también,
# con el mismo autovalor. Ningún método lo determina, así que cada biblioteca
# devuelve el que le sale, y de ahí vienen los «me dio al revés que a vos».
#
# La regla de acá: el elemento de mayor valor absoluto de cada vector queda
# **positivo**, y si hay empate manda el de índice más chico. Es arbitraria
# igual que cualquier otra, pero está escrita, así que el resultado se puede
# reproducir. Es la misma convención que usan varios paquetes de PCA.
ordenar_y_fijar_signo <- function(valores, vectores) {
  n <- length(valores)
  orden <- order(-valores, seq_len(n), method = "radix")
  nuevos <- valores[orden]
  columnas <- list()
  for (j in seq_along(orden)) {
    columna <- vectores[, orden[j]]
    mayor <- 1
    if (n > 1) {
      for (k in 2:n) if (abs(columna[k]) > abs(columna[mayor])) mayor <- k
    }
    if (columna[mayor] < 0) columna <- -columna
    columnas[[j]] <- columna
  }
  list(valores = nuevos, vectores = columnas)
}

# Los autovalores y autovectores de una matriz simétrica.
#
# Devuelve los autovalores de mayor a menor y los autovectores como una lista de
# columnas: `vectores[[j]][i]` es la coordenada i del autovector j.
descomponer <- function(a, tolerancia = TOLERANCIA, barridos = BARRIDOS) {
  n <- nrow(a)
  if (n == 0) return(list(valores = numeric(0), vectores = list(), barridos = 0L))
  if (!es_simetrica(a)) {
    stop(paste0("La matriz que se quiere descomponer no es simétrica. Jacobi ",
                "solo sirve para simétricas."), call. = FALSE)
  }

  trabajo <- a
  v <- identidad(n)
  usados <- 0L
  convergio <- FALSE
  for (barrido in seq_len(barridos)) {
    if (sqrt(fuera_de_la_diagonal(trabajo)) <= tolerancia) {
      convergio <- TRUE
      break
    }
    usados <- usados + 1L
    if (n > 1) {
      for (p in seq_len(n - 1)) {
        for (q in (p + 1):n) {
          if (trabajo[p, q] != 0) {
            resultado <- rotar(trabajo, v, p, q)
            trabajo <- resultado$a
            v <- resultado$v
          }
        }
      }
    }
  }
  if (!convergio && sqrt(fuera_de_la_diagonal(trabajo)) > tolerancia) {
    stop(paste0("Jacobi no convergió en ", barridos, " barridos. La matriz debe ",
                "tener algo raro: revisá que no haya infinitos."), call. = FALSE)
  }

  valores <- vapply(seq_len(n), function(i) trabajo[i, i], numeric(1))
  salida <- ordenar_y_fijar_signo(valores, v)
  list(valores = salida$valores, vectores = salida$vectores, barridos = usados)
}

# El producto de una matriz por un vector, en orden fijo.
por_vector <- function(a, v) {
  vapply(seq_len(nrow(a)), function(i) {
    total <- 0
    for (j in seq_along(v)) total <- total + a[i, j] * v[j]
    total
  }, numeric(1))
}

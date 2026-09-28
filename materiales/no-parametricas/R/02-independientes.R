# Paso 2: dos o más muestras independientes.
#
# Mann-Whitney para dos grupos, Kruskal-Wallis para tres o más, y la t de Welch
# al lado, siempre, para que se vea cuándo las dos miran lo mismo y cuándo no.
#
# **Lo que Mann-Whitney contrasta no es la igualdad de medianas.** Es la
# afirmación más repetida sobre esta prueba y es falsa. Lo que contrasta es
# P(X > Y) = ½: la probabilidad de que un caso tomado al azar de un grupo
# supere a uno tomado al azar del otro. Solo cuando las dos distribuciones
# tienen la misma forma y difieren nada más que en un desplazamiento, esa
# hipótesis equivale a la de medianas iguales.
#
# No es una sutileza de manual. Se pueden construir dos grupos con **la misma
# mediana exacta** donde Mann-Whitney rechaza con toda la fuerza, y dos grupos
# con medianas muy distintas donde no rechaza. Por eso este paso escribe
# P(X > Y) en la tabla, al lado del valor p: es lo que la prueba realmente
# estimó, y quien lea el informe tiene derecho a verlo.
#
# Lo que sí es un desplazamiento —bajo el supuesto de forma igual— lo estima el
# **Hodges-Lehmann**: la mediana de todas las diferencias entre un caso de un
# grupo y uno del otro. Ese es el número que corresponde informar como «de
# cuánto es la diferencia».

# Mann-Whitney por la aproximación normal, con corrección por empates.
#
# La aproximación se usa siempre, por lo mismo que en Wilcoxon: el valor p
# exacto solo es viable con muestras chicas, y cambiar de régimen según el n
# hace que dos corridas parecidas den números que no se pueden comparar.
mann_whitney <- function(a, b, confianza) {
  na <- length(a)
  nb <- length(b)
  if (na < 1 || nb < 1) return(NULL)

  r <- rangos_con_empates(c(a, b))
  suma_a <- sum(r$rangos[seq_len(na)])
  u_a <- suma_a - na * (na + 1) / 2
  u_b <- na * nb - u_a

  esperado <- na * nb / 2
  n <- na + nb
  varianza <- (na * nb / 12) * ((n + 1) - r$correccion / (n * (n - 1)))
  if (varianza <= 0) return(NULL)
  u <- min(u_a, u_b)
  z <- (u - esperado + 0.5) / sqrt(varianza)
  p <- 2 * pnorm(abs(z), lower.tail = FALSE)

  # Hodges-Lehmann: la mediana de todas las diferencias entre pares.
  diferencias <- sort(as.numeric(outer(b, a, "-")))
  list(n_a = as.integer(na), n_b = as.integer(nb), u = u, u_a = u_a, z = z, p = p,
       significativa = p < 1 - confianza,
       # P(X > Y) con los empates contando medio, que es exactamente U dividido
       # por el total de pares. La orientación es la del sitio: la probabilidad
       # de que gane el PRIMER grupo, el que sale primero al ordenar las
       # etiquetas.
       probabilidad_de_superar = u_a / (na * nb),
       hodges_lehmann = cuantil(diferencias, 0.5),
       mediana_a = cuantil(sort(a), 0.5), mediana_b = cuantil(sort(b), 0.5))
}

# Kruskal-Wallis: la extensión de Mann-Whitney a más de dos grupos.
#
# Vale la misma advertencia: contrasta que ninguna de las distribuciones tienda
# a dar valores más altos que las otras, no que las medianas sean iguales.
kruskal_wallis <- function(grupos, confianza) {
  usables <- grupos[vapply(grupos, length, integer(1)) > 0]
  k <- length(usables)
  if (k < 2) return(NULL)
  todos <- unlist(usables, use.names = FALSE)
  n <- length(todos)
  if (n < 3) return(NULL)

  r <- rangos_con_empates(todos)
  h <- 0
  inicio <- 0
  por_grupo_ <- list()
  for (i in seq_along(usables)) {
    v <- usables[[i]]
    suma <- sum(r$rangos[(inicio + 1):(inicio + length(v))])
    por_grupo_[[i]] <- list(grupo = names(usables)[i], n = as.integer(length(v)),
                            suma_de_rangos = suma, rango_promedio = suma / length(v),
                            mediana = cuantil(sort(v), 0.5))
    h <- h + suma^2 / length(v)
    inicio <- inicio + length(v)
  }
  h <- 12 / (n * (n + 1)) * h - 3 * (n + 1)
  # La corrección por empates: sin ella el H sale chico y la prueba pierde
  # potencia sin que nada lo avise.
  divisor <- if (n > 1) 1 - r$correccion / (n^3 - n) else 1
  h_corregido <- if (divisor > 0) h / divisor else h
  p <- pchisq(h_corregido, k - 1, lower.tail = FALSE)

  # Epsilon cuadrado: la proporción de la variabilidad de los rangos que
  # explica el factor. Es el tamaño del efecto que corresponde a una prueba de
  # rangos, y casi nunca se informa.
  #
  # Ojo: circulan dos fórmulas con el mismo nombre. La clásica de Kelley es
  # H(n+1)/(n²−1); la de acá, (H − k + 1)/(n − k), es la que usan `rstatix` y
  # la calculadora del sitio. Con n grande dan parecido, con n chico no. Se
  # eligió esta para que el descargable y `calc-no-parametricas` informen el
  # mismo número.
  epsilon <- if (n > k) (h_corregido - k + 1) / (n - k) else 0
  list(h = h_corregido, h_sin_corregir = h, gl = as.integer(k - 1), p = p,
       significativa = p < 1 - confianza, n = as.integer(n), k = as.integer(k),
       epsilon_cuadrado = min(1, max(0, epsilon)), grupos = por_grupo_)
}

calcular_independientes <- function(datos, parametros, grupos, por_factor) {
  confianza <- parametros$confianza
  alfa <- 1 - confianza
  avisos <- list()
  salida <- list(mann_whitney = NULL, kruskal = NULL, t_de_welch = NULL,
                 nombres = names(grupos), kruskal_factor = NULL)

  if (length(grupos) == 2) {
    a <- grupos[[1]]
    b <- grupos[[2]]
    u <- mann_whitney(a, b, confianza)
    salida$mann_whitney <- u
    if (length(a) > 1 && length(b) > 1) {
      t <- t.test(a, b, var.equal = FALSE)
      salida$t_de_welch <- list(t = as.numeric(t$statistic), p = as.numeric(t$p.value),
                                significativa = as.numeric(t$p.value) < alfa)
    }

    if (!is.null(u) && !is.null(salida$t_de_welch)) {
      if ((u$p < alfa) != (salida$t_de_welch$p < alfa)) {
        cual <- if (u$p < alfa) "Mann-Whitney" else "la t de Welch"
        otra <- if (u$p < alfa) "la t de Welch" else "Mann-Whitney"
        avisos[[length(avisos) + 1]] <- list(
          donde = "independientes",
          aviso = paste0(cual, " rechaza y ", otra, " no. No es que una esté bien y la ",
                         "otra mal: miden cosas distintas. La t compara promedios y le ",
                         "pesan los valores extremos; Mann-Whitney compara posiciones en ",
                         "el orden y no los ve. Con datos muy asimétricos, la de rangos ",
                         "suele tener más potencia, al revés de lo que se cree."))
      }
    }
    if (!is.null(u)) {
      lejos <- abs(u$probabilidad_de_superar - 0.5)
      if (u$significativa) {
        avisos[[length(avisos) + 1]] <- list(
          donde = "independientes",
          aviso = paste0("Mann-Whitney rechaza, y lo que rechaza es que P(X > Y) valga un ",
                         "medio: acá vale ",
                         gsub(".", ",", sprintf("%.3f", u$probabilidad_de_superar),
                              fixed = TRUE),
                         ". Eso NO es lo mismo que decir que las medianas difieren. Solo ",
                         "lo es si las dos distribuciones tienen la misma forma; si no, ",
                         "hay que informar P(X > Y) y no una diferencia de medianas."))
      }
      if (lejos < 0.02 && u$significativa) {
        avisos[[length(avisos) + 1]] <- list(
          donde = "independientes",
          aviso = paste0("El valor p es chico pero P(X > Y) está pegado a un medio: la ",
                         "diferencia es real y minúscula. Con esta cantidad de casos, la ",
                         "prueba detecta cosas que no importan."))
      }
    }
  } else if (length(grupos) > 2) {
    salida$kruskal <- kruskal_wallis(grupos, confianza)
    if (!is.null(salida$kruskal) && salida$kruskal$significativa) {
      avisos[[length(avisos) + 1]] <- list(
        donde = "independientes",
        aviso = paste0("Kruskal-Wallis rechaza, y como el F de un ANOVA no dice entre ",
                       "cuáles grupos está la diferencia. Las comparaciones de a pares ",
                       "con corrección están en el descargable de ANOVA."))
    }
  }

  if (length(por_factor) > 2) {
    salida$kruskal_factor <- kruskal_wallis(por_factor, confianza)
  }

  salida$avisos <- avisos
  salida
}

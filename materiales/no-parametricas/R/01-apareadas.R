# Paso 1: dos mediciones sobre la misma unidad.
#
# Cuando cada caso aporta dos valores —antes y después, mano izquierda y mano
# derecha, dos evaluadores sobre la misma historia clínica— lo que se analiza
# **no son dos muestras**: es una sola, la de las diferencias. Ignorar eso es
# el error más caro y más común con datos apareados, y por eso este paso corre
# las dos cosas y las pone una al lado de la otra.
#
# El motivo es de aritmética, no de doctrina. En una comparación apareada, la
# variabilidad que importa es la de los cambios; en una comparación entre
# muestras independientes, la que importa es la que hay entre personas. Si la
# gente difiere mucho entre sí y cambia poco, el segundo denominador es enorme
# y el efecto se pierde adentro.
#
# Se corren dos pruebas apareadas:
#
#     Wilcoxon de rangos con signo   usa el tamaño de cada cambio, no solo su
#                                    signo. Supone que la distribución de las
#                                    diferencias es simétrica.
#     la prueba de los signos        solo cuenta cuántos subieron y cuántos
#                                    bajaron. No supone nada sobre la forma, y
#                                    por eso tiene menos potencia.
#
# La de los signos casi nunca se informa, y es la única que sigue valiendo
# cuando las diferencias son marcadamente asimétricas.

MAXIMO_EXACTO <- 1000

# Los rangos promediados en los empates, y la corrección que necesitan.
#
# Devuelve los rangos y la suma de (t³ − t) sobre cada grupo de empatados, que
# es el término que corrige la varianza del estadístico.
rangos_con_empates <- function(valores) {
  n <- length(valores)
  orden <- order(valores, method = "radix")
  rangos <- numeric(n)
  correccion <- 0
  i <- 1
  while (i <= n) {
    j <- i
    while (j < n && valores[orden[j + 1]] == valores[orden[i]]) j <- j + 1
    promedio <- (i + j) / 2
    rangos[orden[i:j]] <- promedio
    t <- j - i + 1
    if (t > 1) correccion <- correccion + t^3 - t
    i <- j + 1
  }
  list(rangos = rangos, correccion = correccion)
}

# Wilcoxon de rangos con signo, por la aproximación normal.
#
# Los pares sin cambio se descartan, que es la convención de Wilcoxon y la que
# usa `wilcox.test`. No es inocente: descartarlos reduce el n y puede exagerar
# el efecto si los empates son muchos, así que el proyecto escribe cuántos
# hubo.
#
# La aproximación normal se usa siempre, también con n chico, para que los dos
# idiomas den lo mismo: el valor p exacto por enumeración es viable hasta unos
# veinte pares y después no, y tener dos regímenes distintos según el n es una
# fuente de sorpresas.
wilcoxon <- function(a, b, confianza) {
  diferencias <- b - a
  sin_cambio <- sum(diferencias == 0)
  usadas <- diferencias[diferencias != 0]
  n <- length(usadas)
  if (n < 1) return(NULL)

  r <- rangos_con_empates(abs(usadas))
  w_mas <- sum(r$rangos[usadas > 0])
  w_menos <- sum(r$rangos[usadas < 0])
  w <- min(w_mas, w_menos)

  esperado <- n * (n + 1) / 4
  varianza <- n * (n + 1) * (2 * n + 1) / 24 - r$correccion / 48
  if (varianza <= 0) return(NULL)
  # Corrección por continuidad: el estadístico es discreto y la normal no.
  z <- if (w < esperado) (w - esperado + 0.5) / sqrt(varianza) else
    (w - esperado - 0.5) / sqrt(varianza)
  p <- 2 * pnorm(abs(z), lower.tail = FALSE)

  # Hodges-Lehmann: la mediana de los promedios de cada par de diferencias. Es
  # el desplazamiento que la prueba está estimando, y el que corresponde
  # informar al lado del valor p.
  promedios <- numeric(n * (n + 1) / 2)
  k <- 0
  for (i in seq_len(n)) {
    for (j in i:n) {
      k <- k + 1
      promedios[k] <- (usadas[i] + usadas[j]) / 2
    }
  }
  list(n = as.integer(n), sin_cambio = as.integer(sin_cambio),
       w_mas = w_mas, w_menos = w_menos, w = w, z = z, p = p,
       significativa = p < 1 - confianza,
       hodges_lehmann = cuantil(sort(promedios), 0.5),
       mediana_del_cambio = cuantil(sort(diferencias), 0.5),
       media_del_cambio = mean(diferencias), desvio_del_cambio = desvio(diferencias))
}

# P(X ≤ k) con n ensayos y probabilidad un medio.
#
# Se calcula por recurrencia y no con coeficientes binomiales: C(148, 51) tiene
# cuarenta y una cifras, y aunque Python lo representa exacto, R no tiene
# enteros de ese tamaño y su `choose` lo aproxima por logaritmos. Con la
# recurrencia —arrancar en 2⁻ⁿ y multiplicar por (n − i + 1)/i— los dos hacen
# exactamente las mismas operaciones sobre los mismos números.
#
# El límite es el de la doble precisión: 2⁻ⁿ deja de ser representable
# alrededor de n = 1070, y por eso arriba de mil pares se usa la aproximación
# normal.
cola_binomial <- function(k, n) {
  termino <- 2^(-n)
  acumulado <- termino
  if (k >= 1) {
    for (i in seq_len(k)) {
      termino <- termino * (n - i + 1) / i
      acumulado <- acumulado + termino
    }
  }
  min(1, acumulado)
}

# La prueba de los signos: solo cuenta cuántos suben y cuántos bajan.
#
# Con hasta mil pares el valor p sale exacto de la binomial; con más, de la
# aproximación normal con corrección por continuidad. El corte está escrito en
# la salida, porque no es lo mismo y quien lea tiene que saber cuál le tocó.
signos <- function(a, b, confianza) {
  diferencias <- b - a
  subieron <- sum(diferencias > 0)
  bajaron <- sum(diferencias < 0)
  n <- subieron + bajaron
  if (n < 1) return(NULL)

  k <- min(subieron, bajaron)
  if (n <= MAXIMO_EXACTO) {
    p <- min(1, 2 * cola_binomial(k, n))
    como <- "binomial exacta"
  } else {
    z <- (k + 0.5 - n / 2) / sqrt(n / 4)
    p <- min(1, 2 * pnorm(z))
    como <- "aproximación normal"
  }
  list(n = as.integer(n), subieron = as.integer(subieron), bajaron = as.integer(bajaron),
       empates = as.integer(length(diferencias) - n), p = p, como = como,
       proporcion_que_sube = subieron / n, significativa = p < 1 - confianza)
}

# La misma comparación, tirando el apareamiento.
#
# Está para que se vea el precio, no para informarla. Se corre la de
# Mann-Whitney y también la t de Welch, porque el error se comete con las dos
# por igual.
como_si_fueran_independientes <- function(a, b, confianza) {
  u <- mann_whitney(a, b, confianza)
  t <- t.test(a, b, var.equal = FALSE)
  list(mann_whitney_p = if (is.null(u)) NULL else u$p,
       t_de_welch_p = as.numeric(t$p.value))
}

calcular_apareadas <- function(datos, parametros, pares) {
  a <- pares$antes
  b <- pares$despues
  if (length(a) < 2) return(NULL)

  confianza <- parametros$confianza
  alfa <- 1 - confianza
  w <- wilcoxon(a, b, confianza)
  s <- signos(a, b, confianza)
  mal <- como_si_fueran_independientes(a, b, confianza)

  avisos <- list()
  cambia <- FALSE
  if (!is.null(w) && !is.null(mal$mann_whitney_p)) {
    # La columna que justifica el paso: si tirar el apareamiento cambia la
    # conclusión, hay que decirlo con todas las letras.
    cambia <- (w$p < alfa) != (mal$mann_whitney_p < alfa)
    if (cambia) {
      avisos[[length(avisos) + 1]] <- list(
        donde = "apareadas",
        aviso = paste0("Tratar estos datos como dos muestras independientes cambia la ",
                       "conclusión. No es una diferencia de matiz: el apareamiento es ",
                       "información que está en los datos, y tirarla no es una decisión ",
                       "conservadora, es perder el resultado."))
    }
  }

  if (!is.null(w) && !is.null(s) && (w$p < alfa) != (s$p < alfa)) {
    avisos[[length(avisos) + 1]] <- list(
      donde = "apareadas",
      aviso = paste0("Wilcoxon y la prueba de los signos no coinciden. Wilcoxon usa el ",
                     "tamaño de los cambios y supone que su distribución es simétrica; la ",
                     "de los signos solo cuenta direcciones y no supone nada. Si las ",
                     "diferencias son asimétricas, la que vale es la segunda."))
  }
  if (!is.null(w) && w$sin_cambio > 0) {
    avisos[[length(avisos) + 1]] <- list(
      donde = "apareadas",
      aviso = paste0("Hay ", w$sin_cambio, " pares sin ningún cambio, y Wilcoxon los ",
                     "descarta. Con muchos empates eso infla el efecto aparente: la ",
                     "prueba termina hablando solo de los que se movieron."))
  }
  if (!is.null(w) && length(a) < 10) {
    avisos[[length(avisos) + 1]] <- list(
      donde = "apareadas",
      aviso = paste0("Con ", length(a), " pares, la aproximación normal de Wilcoxon es ",
                     "apenas orientativa. Conviene la prueba exacta, que este proyecto no ",
                     "trae."))
  }

  list(wilcoxon = w, signos = s, como_independientes = mal,
       cambia_la_conclusion = cambia, descartados = pares$descartados,
       n_pares = as.integer(length(a)), avisos = avisos)
}

# La distribución del rango studentizado, que es lo que necesita Tukey.
#
# Es la única distribución de este proyecto que no sale de una función ya
# hecha. Su función de distribución es una integral doble:
#
#     P(Q ≤ q) = ∫₀^∞ fν(s) · R(q·s; k) ds
#
# donde R(w; k) = k ∫ φ(z) [Φ(z) − Φ(z−w)]^{k−1} dz es la probabilidad de que
# el rango de k normales estándar no supere w, y fν(s) es la densidad de
# s = √(χ²ν/ν), el desvío muestral en unidades del poblacional. Las dos se
# resuelven con cuadratura de Gauss-Legendre.
#
# **Por qué no se usa `ptukey`, que R trae de fábrica.** Por lo mismo que el
# descargable de regresión no usa `lm`: Python no tiene un equivalente exacto y
# las dos versiones tienen que escribir los mismos archivos byte a byte.
#
# Pero acá hay además una razón que no es de comodidad. Medido contra
# `scipy.stats.studentized_range`, que es una implementación independiente:
#
#     q = 3,5  k = 3  ν = 144       cola
#     esto                          3,828330160608e-02
#     scipy                         3,828330160611e-02
#     ptukey de R                   3,828330160648e-02
#
#     confianza 0,95  k = 4  ν = 20   valor crítico
#     esto                          3,958293560921
#     scipy                         3,958293560945
#     qtukey de R                   3,958293461450
#
# Las dos implementaciones por cuadratura fina coinciden en once dígitos y la
# de R se despega en el octavo, porque `ptukey` integra con dieciséis puntos
# fijos. Para decidir si un valor p es mayor o menor que 0,05 da exactamente
# igual; vale la pena saberlo igual, porque quien compare este proyecto contra
# R va a ver la diferencia y merece saber de dónde sale.

# Nodos de cada cuadratura. Con 120 el peor error absoluto contra scipy es
# 1,1·10⁻¹⁰; con 200 baja a 9·10⁻¹³ y con 300 no mejora más, porque ahí ya
# manda el redondeo de la doble precisión y no la cuadratura.
NODOS <- 200

# Nodos de la integral EXTERNA cuando hay que evaluar la CDF muchas veces
# seguidas, como en la bisección del valor crítico. Cada CDF son
# nodos_interna × nodos_externa evaluaciones, así que la externa es la que
# conviene recortar. La externa solo hace falta fina con ν chico, que es donde
# la densidad de s es ancha y asimétrica; de ν = 10 en adelante —o sea, en
# cualquier ANOVA de tamaño razonable— sesenta nodos dan todo lo que la doble
# precisión permite.
NODOS_EXTERNOS_POCOS <- 60
UMBRAL_GL <- 10

.cuadraturas <- new.env(parent = emptyenv())
.criticos <- new.env(parent = emptyenv())

# Nodos y pesos de Gauss-Legendre en [−1, 1].
#
# Se calculan por el método de Newton sobre los polinomios de Legendre, una vez
# por cantidad de nodos. Es aritmética pura: ni R ni Python tienen nada que
# aportar de su lado, así que los dos llegan al mismo bit.
gauss_legendre <- function(n) {
  clave <- as.character(n)
  guardado <- .cuadraturas[[clave]]
  if (!is.null(guardado)) return(guardado)

  nodos <- numeric(n)
  pesos <- numeric(n)
  m <- bitwShiftR(n + 1, 1)

  for (i in seq_len(m) - 1) {
    # Aproximación inicial de la i-ésima raíz (Abramowitz-Stegun 25.4.30).
    x <- cos(pi * (i + 0.75) / (n + 0.5))
    dp <- 0
    for (paso in seq_len(100)) {
      # Recurrencia de Legendre para P_n(x) y su derivada.
      p0 <- 1
      p1 <- 0
      for (j in seq_len(n) - 1) {
        p2 <- p1
        p1 <- p0
        p0 <- ((2 * j + 1) * x * p1 - j * p2) / (j + 1)
      }
      dp <- (n * (x * p0 - p1)) / (x * x - 1)
      delta <- p0 / dp
      x <- x - delta
      if (abs(delta) < 1e-15) break
    }
    nodos[i + 1] <- -x
    nodos[n - i] <- x
    w <- 2 / ((1 - x * x) * dp * dp)
    pesos[i + 1] <- w
    pesos[n - i] <- w
  }

  .cuadraturas[[clave]] <- list(nodos = nodos, pesos = pesos)
  .cuadraturas[[clave]]
}

# Integra f entre a y b con n nodos.
#
# `f` recibe el vector entero de puntos y devuelve el vector de valores: es el
# mismo producto y la misma suma que haría un bucle, pero de una sola vez. Del
# lado de Python la suma la hace `fsum`, que es exacta; acá la hace `sum`, que
# acumula en precisión extendida. Las dos dan lo mismo hasta mucho más allá de
# los diez dígitos que este proyecto escribe.
integrar <- function(f, a, b, n) {
  g <- gauss_legendre(n)
  medio <- (a + b) / 2
  semi <- (b - a) / 2
  sum(g$pesos * f(medio + semi * g$nodos)) * semi
}

normal_pdf <- function(z) exp(-0.5 * z * z) / sqrt(2 * pi)

# R(w; k): probabilidad de que el rango de k normales estándar no supere w.
#
# El integrando decae como una normal, así que integrar sobre ±9 desvíos deja
# afuera una parte despreciable.
rango_normal <- function(w, k, nodos) {
  if (w <= 0) return(0)
  f <- function(z) {
    d <- pnorm(z) - pnorm(z - w)
    salida <- numeric(length(z))
    sirve <- d > 0
    # La potencia k−1 se hace en logaritmos para no perder precisión con k
    # grande.
    salida[sirve] <- normal_pdf(z[sirve]) * exp((k - 1) * log(d[sirve]))
    salida
  }
  k * integrar(f, -9, 9 + w, nodos)
}

# P(Q ≤ q) para k grupos y ν grados de libertad del error.
#
# Con ν muy grande, s se concentra tanto en 1 que la integral externa deja de
# aportar y se puede usar directamente el rango de normales: eso además evita
# que la densidad de s, que se vuelve altísima y angosta, exija demasiados
# nodos.
cdf_rango <- function(q, k, v, nodos_interna, nodos_externa) {
  if (q <= 0 || k < 2) return(0)
  if (!is.finite(v) || v > 25000) return(rango_normal(q, k, nodos_interna))

  # Densidad de s = √(χ²ν/ν), en logaritmos.
  ln_constante <- (v / 2) * log(v / 2) - lgamma(v / 2) + log(2)
  densidad_s <- function(s) exp(ln_constante + (v - 1) * log(s) - (v * s * s) / 2)

  # s tiene media cercana a 1 y desvío ≈ 1/√(2ν), así que nueve desvíos a cada
  # lado cubren todo lo que aporta.
  desvio <- 1 / sqrt(2 * v)
  desde <- max(1e-8, 1 - 9 * desvio)
  hasta <- 1 + 9 * desvio

  integrar(function(s) {
    densidad_s(s) * vapply(s, function(u) rango_normal(q * u, k, nodos_interna), numeric(1))
  }, desde, hasta, nodos_externa)
}

externos_de <- function(v) if (v < UMBRAL_GL) NODOS else NODOS_EXTERNOS_POCOS

rango_cdf <- function(q, k, v) cdf_rango(q, k, v, NODOS, externos_de(v))

# Cola superior: el valor p de una comparación de Tukey.
#
# Ojo con los valores p diminutos. La cola se calcula como 1 − CDF, y la CDF se
# arma integrando cantidades de orden 1, así que arrastra un error absoluto de
# alrededor de 10⁻¹³ que no se puede bajar en doble precisión. Mientras el p sea
# mayor que ~10⁻¹⁰ eso no se nota; por debajo, la resta se come todos los
# dígitos y el número solo alcanza para decir «prácticamente cero». Es la misma
# limitación que tienen scipy y `ptukey`.
rango_cola <- function(q, k, v) min(1, max(0, 1 - rango_cdf(q, k, v)))

# El valor crítico de Tukey, por bisección sobre la CDF.
#
# Se guarda en memoria porque el post hoc lo pide una vez por comparación y
# siempre con los mismos argumentos: cada paso de la bisección es una CDF
# entera, o sea sesenta mil evaluaciones.
rango_inv <- function(p, k, v) {
  if (p <= 0) return(0)
  if (p >= 1) return(Inf)

  clave <- paste(p, k, v, sep = "|")
  guardado <- .criticos[[clave]]
  if (!is.null(guardado)) return(guardado)

  externos <- externos_de(v)
  FF <- function(q) cdf_rango(q, k, v, NODOS, externos)

  lo <- 0
  hi <- 2
  while (hi < 1e4 && FF(hi) < p) hi <- hi * 2
  # Se corta cuando el intervalo es más fino de lo que la CDF puede distinguir.
  vueltas <- 0
  while (vueltas < 60 && hi - lo > 1e-10) {
    medio <- (lo + hi) / 2
    if (FF(medio) < p) lo <- medio else hi <- medio
    vueltas <- vueltas + 1
  }

  .criticos[[clave]] <- (lo + hi) / 2
  .criticos[[clave]]
}

# Los cinco intervalos, escritos como funciones puras.
#
# Son los mismos que calcula la calculadora de estadistica.ar, con los mismos
# avisos y palabra por palabra: el verificador del sitio compara las dos cosas.
# Si alguna vez dejaran de coincidir, sería un error de una de las dos y no una
# diferencia de criterio.
#
#     ic_media                     una media, con t o con z
#     ic_proporcion                una proporción, por Wilson, Wald o Clopper-Pearson
#     ic_diferencia_medias         dos medias, por Welch o con varianzas iguales
#     ic_diferencia_proporciones   dos proporciones
#     ic_varianza                  la varianza y el desvío, por chi-cuadrado
#
# Los cuantiles —qnorm, qt, qchisq y qbeta— vienen de fábrica. En Python hacen
# falta los de SciPy.

# Los números que van DENTRO de un aviso llevan coma decimal: son texto para
# leer, no valores para volver a calcular.
coma_aviso <- function(v, decimales = 2) {
  gsub(".", ",", sprintf(paste0("%.", decimales, "f"), v), fixed = TRUE)
}

# El z o el t que deja (1 − confianza)/2 en cada cola.
critico <- function(confianza, gl = NULL) {
  p <- 1 - (1 - confianza) / 2
  if (is.null(gl)) qnorm(p) else qt(p, gl)
}

# Corrección por población finita.
#
# Cuando la muestra es una parte grande de la población, el muestreo sin
# reposición reduce la variabilidad: en el extremo, si se releva a todos, no
# hay error de muestreo.
fpc <- function(n, N = NULL) {
  if (is.null(N) || !is.finite(N) || N <= 0 || n >= N) {
    return(if (!is.null(N) && n >= N) 0 else 1)
  }
  sqrt((N - n) / (N - 1))
}

ic_media <- function(media, desvio, n, confianza, sigma_conocida = FALSE, N = NULL) {
  if (!(n > 1) || !(desvio >= 0) || !(confianza > 0 && confianza < 1)) return(NULL)

  gl <- if (sigma_conocida) NULL else n - 1
  c_ <- critico(confianza, gl)
  correccion <- fpc(n, N)
  ee <- desvio / sqrt(n) * correccion
  margen <- c_ * ee

  avisos <- character(0)
  if (n < 30 && !sigma_conocida) {
    avisos <- c(avisos, paste0("Con menos de 30 casos, el intervalo depende de que la variable ",
                               "sea aproximadamente normal. Mirá el histograma antes de confiar ",
                               "en él."))
  }
  if (sigma_conocida) {
    avisos <- c(avisos, paste0("Estás usando z, que supone σ conocida. Si el desvío lo ",
                               "calculaste con estos mismos datos, σ no es conocida y ",
                               "corresponde la t."))
  }
  if (!is.null(N) && n / N > 0.05) {
    avisos <- c(avisos, paste0("La muestra es el ", coma_aviso(100 * n / N, 1), " % de la ",
                               "población, así que la corrección por población finita está ",
                               "achicando el margen un ",
                               coma_aviso((1 - correccion) * 100, 1), " %."))
  }

  list(estimacion = media, inferior = media - margen, superior = media + margen,
       margen = margen, error_estandar = ee, critico = c_, gl = gl,
       distribucion = if (sigma_conocida) "z" else "t", avisos = avisos)
}

ic_proporcion <- function(exitos, n, confianza, metodo = "wilson", N = NULL) {
  if (!(n > 0) || exitos < 0 || exitos > n || !(confianza > 0 && confianza < 1)) return(NULL)

  p <- exitos / n
  z <- critico(confianza)
  correccion <- fpc(n, N)

  avisos <- character(0)
  esperados <- min(exitos, n - exitos)
  if (esperados < 5) {
    avisos <- c(avisos, paste0("Hay solo ", esperados, " caso", if (esperados == 1) "" else "s",
                               " en la categoría menos frecuente. La aproximación normal no ",
                               "sirve acá: usá el intervalo exacto de Clopper-Pearson."))
  }
  if (!is.null(N) && n / N > 0.05) {
    avisos <- c(avisos, paste0("La muestra es el ", coma_aviso(100 * n / N, 1), " % de la ",
                               "población: la corrección por población finita está achicando ",
                               "el margen."))
  }

  if (metodo == "clopper-pearson") {
    # El intervalo exacto: invierte la binomial usando su relación con la beta.
    alfa <- 1 - confianza
    inferior <- if (exitos == 0) 0 else qbeta(alfa / 2, exitos, n - exitos + 1)
    superior <- if (exitos == n) 1 else qbeta(1 - alfa / 2, exitos + 1, n - exitos)
    return(list(
      estimacion = p, inferior = inferior, superior = superior,
      margen = (superior - inferior) / 2,
      error_estandar = sqrt(p * (1 - p) / n) * correccion,
      critico = z, gl = NULL, distribucion = "beta",
      avisos = c(avisos, paste0("El intervalo exacto no es simétrico alrededor de la proporción ",
                                "observada, así que el «margen» de acá es la mitad del ancho y ",
                                "no un ± en el sentido habitual."))))
  }

  if (metodo == "wald") {
    ee <- sqrt(p * (1 - p) / n) * correccion
    margen <- z * ee
    extra <- paste0("El método de Wald es el de la fórmula clásica p ± z·√(p(1−p)/n). ",
                    "Tiene mala cobertura con n chico o proporciones cerca de 0 o 1, y ahí ",
                    "conviene Wilson.")
    if (p == 0 || p == 1) {
      extra <- c(extra, paste0("Con una proporción de 0 o de 1, Wald da un intervalo de ancho ",
                               "cero, que es absurdo: no hay certeza total con una muestra."))
    }
    return(list(
      estimacion = p, inferior = max(0, p - margen), superior = min(1, p + margen),
      margen = margen, error_estandar = ee, critico = z, gl = NULL,
      distribucion = "z", avisos = c(avisos, extra)))
  }

  # Wilson: el recomendado por omisión. Invierte la prueba de puntaje en vez de
  # suponer que la proporción muestral tiene distribución normal.
  z2 <- z * z
  denominador <- 1 + z2 / n
  centro <- (p + z2 / (2 * n)) / denominador
  semiancho <- z * sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / denominador * correccion
  extra <- character(0)
  if (abs(centro - p) > 0.01) {
    extra <- paste0("El intervalo de Wilson no está centrado en la proporción observada: se ",
                    "corre hacia 0,5. Eso es correcto y es justamente lo que lo hace mejor que ",
                    "Wald con muestras chicas.")
  }

  list(estimacion = p, inferior = max(0, centro - semiancho),
       superior = min(1, centro + semiancho), margen = semiancho,
       error_estandar = sqrt(p * (1 - p) / n) * correccion, critico = z, gl = NULL,
       distribucion = "z", avisos = c(avisos, extra))
}

ic_diferencia_medias <- function(m1, s1, n1, m2, s2, n2, confianza, varianzas_iguales = FALSE) {
  if (!(n1 > 1) || !(n2 > 1) || !(confianza > 0 && confianza < 1)) return(NULL)

  diferencia <- m1 - m2
  v1 <- s1 * s1 / n1
  v2 <- s2 * s2 / n2

  if (varianzas_iguales) {
    # Varianza combinada, ponderada por los grados de libertad de cada grupo.
    sp2 <- ((n1 - 1) * s1 * s1 + (n2 - 1) * s2 * s2) / (n1 + n2 - 2)
    ee <- sqrt(sp2 * (1 / n1 + 1 / n2))
    gl <- as.numeric(n1 + n2 - 2)
  } else {
    # Welch-Satterthwaite: los grados de libertad casi nunca son enteros.
    ee <- sqrt(v1 + v2)
    gl <- (v1 + v2)^2 / (v1^2 / (n1 - 1) + v2^2 / (n2 - 1))
  }

  c_ <- critico(confianza, gl)
  margen <- c_ * ee

  avisos <- character(0)
  razon <- if (min(s1, s2) > 0) max(s1, s2) / min(s1, s2) else Inf
  if (varianzas_iguales && razon > 2) {
    avisos <- c(avisos, paste0("Los desvíos difieren en un factor de ", coma_aviso(razon, 1),
                               ", y estás suponiendo varianzas iguales. Conviene Welch, que no ",
                               "lo supone."))
  }
  if (!varianzas_iguales) {
    avisos <- c(avisos, paste0("Welch da ", coma_aviso(gl, 2), " grados de libertad, con ",
                               "decimales. No es un error: es lo que devuelve la fórmula de ",
                               "Welch-Satterthwaite, y es lo que corre R por defecto."))
  }
  if (min(n1, n2) < 30) {
    avisos <- c(avisos, paste0("Con algún grupo de menos de 30 casos, el intervalo depende de ",
                               "la normalidad dentro de cada grupo."))
  }

  list(estimacion = diferencia, inferior = diferencia - margen, superior = diferencia + margen,
       margen = margen, error_estandar = ee, critico = c_, gl = gl, distribucion = "t",
       avisos = avisos)
}

ic_diferencia_proporciones <- function(x1, n1, x2, n2, confianza) {
  if (!(n1 > 0) || !(n2 > 0) || x1 < 0 || x1 > n1 || x2 < 0 || x2 > n2) return(NULL)

  p1 <- x1 / n1
  p2 <- x2 / n2
  diferencia <- p1 - p2
  z <- critico(confianza)
  ee <- sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
  margen <- z * ee

  avisos <- character(0)
  minimo <- min(x1, n1 - x1, x2, n2 - x2)
  if (minimo < 5) {
    avisos <- c(avisos, paste0("Hay una celda con solo ", minimo, " caso",
                               if (minimo == 1) "" else "s", ". Con conteos tan chicos este ",
                               "intervalo no es confiable: corresponde un método exacto."))
  }
  if (diferencia != 0 && ((diferencia > 0 && diferencia - margen < 0) ||
                          (diferencia < 0 && diferencia + margen > 0))) {
    avisos <- c(avisos, paste0("El intervalo incluye el cero: los datos son compatibles con que ",
                               "no haya diferencia entre los dos grupos."))
  }

  list(estimacion = diferencia, inferior = max(-1, diferencia - margen),
       superior = min(1, diferencia + margen), margen = margen, error_estandar = ee,
       critico = z, gl = NULL, distribucion = "z", avisos = avisos)
}

ic_varianza <- function(desvio, n, confianza) {
  if (!(n > 1) || !(desvio > 0) || !(confianza > 0 && confianza < 1)) return(NULL)

  gl <- n - 1
  alfa <- 1 - confianza
  s2 <- desvio * desvio
  # Ojo con el cruce: el cuantil GRANDE del chi² va en el límite INFERIOR.
  inferior <- gl * s2 / qchisq(1 - alfa / 2, gl)
  superior <- gl * s2 / qchisq(alfa / 2, gl)

  list(estimacion = s2, inferior = inferior, superior = superior,
       margen = (superior - inferior) / 2, error_estandar = NULL, critico = NULL,
       gl = gl, distribucion = "chi2",
       avisos = c(
         paste0("Este intervalo es extremadamente sensible a la normalidad: si la variable no ",
                "es normal, la cobertura real puede estar muy lejos del nivel nominal, incluso ",
                "con muestras grandes. Es el intervalo menos robusto de todos."),
         paste0("No es simétrico alrededor de la varianza observada, porque la distribución ",
                "chi-cuadrado tampoco lo es.")))
}

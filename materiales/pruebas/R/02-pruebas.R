# Paso 2: la prueba que corresponde, la que no, y el tamaño del efecto.
#
# El árbol de decisión de estadistica.ar da un par para cada situación: una
# prueba y una alternativa. El árbol no mira los datos —no puede, son seis
# preguntas—, así que quién de las dos corresponde lo deciden los supuestos
# del paso 1:
#
#     dos grupos, los dos normales        t de Welch
#     dos grupos, alguno no normal        Mann-Whitney
#     tres o más, todos normales          ANOVA; de Welch si Levene rechaza
#     tres o más, alguno no normal        Kruskal-Wallis
#     categórica, esperadas ≥ 5           chi-cuadrado
#     categórica 2×2, alguna esperada < 5 Fisher exacta
#
# Y las dos se corren igual. No para elegir después la que más guste —eso
# sería hacer trampa—, sino para que quede escrito cuándo la decisión importó:
# la columna `cambia_la_conclusion` dice «Sí» cuando las dos pruebas no
# coinciden en rechazar. Es el único caso en que discutir el supuesto cambia
# la conclusión del informe; en todos los demás, la discusión es académica.
#
# Cada fila lleva el tamaño del efecto, siempre. Un valor p sin tamaño del
# efecto dice que algo pasa y no dice cuánto.

# Los nombres son los que devuelve el árbol del sitio, no una traducción.
WELCH <- "Prueba t de Welch para dos muestras"
MANN <- "Mann-Whitney"
ANOVA <- "ANOVA de un factor"
ANOVA_WELCH <- "ANOVA de Welch"
KRUSKAL <- "Kruskal-Wallis"
CHI2_DOS <- "Prueba z para dos proporciones, o chi-cuadrado"
CHI2_TRES <- "Chi-cuadrado de homogeneidad"
FISHER <- "Prueba exacta de Fisher"

# Cómo se llama el estadístico de cada una cuando se lo escribe en el informe.
SIMBOLO <- c("t", "U", "F", "F", "H", "χ²", "χ²", "")
names(SIMBOLO) <- c(WELCH, MANN, ANOVA, ANOVA_WELCH, KRUSKAL, CHI2_DOS, CHI2_TRES, FISHER)

# Los cortes de Cohen, los mismos que usa la calculadora de tamaño del efecto.
CORTES <- list(d = c(0.2, 0.5, 0.8), r = c(0.1, 0.3, 0.5), eta2 = c(0.01, 0.06, 0.14))

# La etiqueta de Cohen, que conviene usar con pinzas: él mismo las publicó
# como provisorias. Una d de 0,2 es enorme si se trata de mortalidad.
calificar <- function(medida, valor) {
  cortes <- CORTES[[medida]]
  v <- abs(valor)
  if (v < cortes[1]) return("insignificante")
  if (v < cortes[2]) return("chico")
  if (v < cortes[3]) return("medio")
  "grande"
}

# ------------------------------------------------------------ las pruebas
welch <- function(a, b) {
  r <- t.test(a, b, var.equal = FALSE)
  list(estadistico = as.numeric(r$statistic), gl = as.numeric(r$parameter),
       gl2 = NULL, p = as.numeric(r$p.value))
}

# Sin corrección por continuidad y por la aproximación normal, que es lo único
# que R y SciPy calculan igual: con el método exacto cada uno decide por su
# cuenta cuándo usarlo.
mann_whitney <- function(a, b) {
  r <- suppressWarnings(wilcox.test(a, b, correct = FALSE, exact = FALSE))
  list(estadistico = as.numeric(r$statistic), gl = NULL, gl2 = NULL,
       p = as.numeric(r$p.value))
}

anova_clasica <- function(grupos) {
  k <- length(grupos)
  n <- sum(vapply(grupos, length, integer(1)))
  y <- unlist(grupos)
  g <- factor(rep(seq_len(k), vapply(grupos, length, integer(1))))
  r <- oneway.test(y ~ g, var.equal = TRUE)
  list(estadistico = as.numeric(r$statistic), gl = as.numeric(k - 1),
       gl2 = as.numeric(n - k), p = as.numeric(r$p.value))
}

# La ANOVA de Welch, escrita a mano: R la trae en `oneway.test` y SciPy no.
#
# Es la misma idea que la t de Welch llevada a k grupos: cada grupo pesa por su
# propia precisión, y los grados de libertad del denominador salen con
# decimales.
anova_welch <- function(grupos) {
  k <- length(grupos)
  w <- vapply(grupos, function(g) length(g) / (desvio(g)^2), numeric(1))
  suma <- sum(w)
  mg <- sum(w * vapply(grupos, mean, numeric(1))) / suma
  entre <- sum(w * (vapply(grupos, mean, numeric(1)) - mg)^2) / (k - 1)
  lam <- 3 / (k * k - 1) * sum((1 - w / suma)^2 / (vapply(grupos, length, integer(1)) - 1))
  f <- entre / (1 + 2 * (k - 2) / (k + 1) * lam)
  gl2 <- 1 / lam
  list(estadistico = f, gl = as.numeric(k - 1), gl2 = gl2,
       p = pf(f, k - 1, gl2, lower.tail = FALSE))
}

kruskal <- function(grupos) {
  r <- kruskal.test(grupos)
  list(estadistico = as.numeric(r$statistic), gl = as.numeric(length(grupos) - 1),
       gl2 = NULL, p = as.numeric(r$p.value))
}

chi_cuadrado <- function(tabla) {
  m <- matrix(unlist(tabla), nrow = length(tabla), byrow = TRUE)
  r <- suppressWarnings(chisq.test(m, correct = FALSE))
  list(estadistico = as.numeric(r$statistic), gl = as.numeric(r$parameter),
       gl2 = NULL, p = as.numeric(r$p.value))
}

# Solo para tablas de 2×2: es la única que SciPy y R resuelven igual.
fisher <- function(tabla) {
  if (length(tabla) != 2 || length(tabla[[1]]) != 2) return(NULL)
  m <- matrix(unlist(tabla), nrow = 2, byrow = TRUE)
  r <- fisher.test(m)
  list(estadistico = NULL, gl = NULL, gl2 = NULL, p = as.numeric(r$p.value))
}

# ------------------------------------------------------- tamaños del efecto
# d de Cohen con la corrección de Hedges, que la insesga con n chico.
hedges <- function(a, b) {
  n1 <- length(a)
  n2 <- length(b)
  sp <- sqrt(((n1 - 1) * desvio(a)^2 + (n2 - 1) * desvio(b)^2) / (n1 + n2 - 2))
  if (sp == 0) return(NULL)
  d <- (mean(a) - mean(b)) / sp
  gl <- n1 + n2 - 2
  d * (1 - 3 / (4 * gl - 1))
}

# El r de la no paramétrica: |Z| / √n, con el Z que devuelve el valor p. Con un
# p pegado al cero el Z se va a infinito; se corta en 1, que es el máximo que
# la medida puede valer.
r_de_rangos <- function(p, n) {
  if (!(p > 0)) return(1)
  z <- abs(qnorm(p / 2, lower.tail = FALSE))
  min(1, z / sqrt(n))
}

eta_cuadrado <- function(grupos) {
  todos <- unlist(grupos)
  total <- mean(todos)
  entre <- sum(vapply(grupos, function(g) length(g) * (mean(g) - total)^2, numeric(1)))
  st <- sum((todos - total)^2)
  if (st > 0) entre / st else NULL
}

# El de Kruskal-Wallis, que se lee en la misma escala que el eta². Cuando H
# queda por debajo de k − 1 la fórmula da negativo, que como proporción de
# varianza no significa nada: ahí es cero.
epsilon_cuadrado <- function(h, n, k) {
  if (n <= k) return(NULL)
  max(0, (h - k + 1) / (n - k))
}

v_de_cramer <- function(chi2, n, filas, columnas) {
  m <- min(filas, columnas) - 1
  if (m > 0 && n > 0) sqrt(chi2 / (n * m)) else NULL
}

# --------------------------------------------------------------- el paso
calcular_pruebas <- function(datos, variables, parametros, supuestos) {
  alfa <- parametros$alfa
  factores <- which(variables$tipo == "grupo")
  numericas <- which(variables$tipo == "numerica")
  categoricas <- which(variables$tipo == "categorica")

  buscar_normal <- function(variable, factor, grupo) {
    for (f in supuestos$supuestos) {
      if (f$variable == variable && f$factor == factor && f$grupo == grupo) return(f$veredicto)
    }
    NULL
  }
  buscar_homogeneas <- function(variable, factor) {
    for (f in supuestos$homogeneidad) {
      if (f$variable == variable && f$factor == factor) return(f$homogeneas)
    }
    TRUE
  }
  buscar_esperada <- function(variable, factor) {
    for (f in supuestos$esperadas) {
      if (f$variable == variable && f$factor == factor) return(f$esperada_minima)
    }
    5
  }

  filas <- list()
  avisos <- list()

  agregar <- function(base, elegida, otra, cortes, medida, efecto) {
    significativa <- elegida$p < alfa
    alternativa <- if (is.null(otra)) NULL else otra$p < alfa
    filas[[length(filas) + 1]] <<- c(base, list(
      simbolo = unname(SIMBOLO[[base$prueba]]),
      estadistico = elegida$estadistico, gl = elegida$gl, gl2 = elegida$gl2, p = elegida$p,
      significativa = significativa, medida = medida, efecto = efecto,
      calificacion = if (is.null(efecto)) "" else calificar(cortes, efecto),
      p_alternativa = if (is.null(otra)) NULL else otra$p,
      significativa_alternativa = alternativa,
      cambia_la_conclusion = !is.null(alternativa) && alternativa != significativa))
  }

  for (fi in factores) {
    factor_nombre <- variables$nombre[fi]
    valores_factor <- columna(datos, factor_nombre)
    niveles <- ordenar(valores_factor[valores_factor != ""])
    if (length(niveles) < 2) next

    for (vi in numericas) {
      grupos <- list()
      nombres <- character(0)
      for (nivel in niveles) {
        x <- numeros(datos[valores_factor == nivel], variables$nombre[vi])
        if (length(x) >= 2) {
          grupos[[length(grupos) + 1]] <- x
          nombres <- c(nombres, nivel)
        }
      }
      if (length(grupos) < 2) next
      # Sin variación en ningún grupo no hay nada que comparar: SciPy devuelve
      # «nan» y R directamente falla. Mejor decirlo.
      if (all(vapply(grupos, function(g) desvio(g) == 0, logical(1)))) {
        avisos[[length(avisos) + 1]] <- list(
          variable = variables$nombre[vi], factor = factor_nombre,
          aviso = paste0("Los valores no varían en ningún grupo: no hay prueba que ",
                         "aplicar."))
        next
      }
      n <- sum(vapply(grupos, length, integer(1)))
      k <- length(grupos)
      todos_normales <- all(vapply(nombres, function(nivel) {
        identical(buscar_normal(variables$nombre[vi], factor_nombre, nivel), "normal")
      }, logical(1)))
      base <- list(variable = variables$nombre[vi], etiqueta = variables$etiqueta[vi],
                   factor = factor_nombre, que = "numérica",
                   k = as.integer(k), n = as.integer(n))

      if (k == 2) {
        a <- grupos[[1]]
        b <- grupos[[2]]
        par <- WELCH
        alterna <- MANN
        if (todos_normales) {
          elegida <- welch(a, b)
          otra <- mann_whitney(a, b)
          prueba <- WELCH
          motivo <- "hay dos grupos y los dos pasan Shapiro-Wilk"
          cortes <- "d"
          medida <- "d de Hedges"
          efecto <- hedges(a, b)
        } else {
          elegida <- mann_whitney(a, b)
          otra <- welch(a, b)
          prueba <- MANN
          motivo <- "hay dos grupos y alguno no pasa Shapiro-Wilk"
          cortes <- "r"
          medida <- "r de rangos"
          efecto <- r_de_rangos(elegida$p, n)
        }
      } else {
        par <- ANOVA
        alterna <- KRUSKAL
        if (todos_normales) {
          if (buscar_homogeneas(variables$nombre[vi], factor_nombre)) {
            elegida <- anova_clasica(grupos)
            prueba <- ANOVA
            motivo <- "hay tres o más grupos, todos normales y con varianzas homogéneas"
          } else {
            elegida <- anova_welch(grupos)
            prueba <- ANOVA_WELCH
            motivo <- "hay tres o más grupos normales, pero Levene rechaza la homogeneidad"
          }
          otra <- kruskal(grupos)
          cortes <- "eta2"
          medida <- "eta²"
          efecto <- eta_cuadrado(grupos)
        } else {
          elegida <- kruskal(grupos)
          otra <- anova_clasica(grupos)
          prueba <- KRUSKAL
          motivo <- "hay tres o más grupos y alguno no pasa Shapiro-Wilk"
          cortes <- "eta2"
          medida <- "épsilon²"
          efecto <- epsilon_cuadrado(elegida$estadistico, n, k)
        }
      }

      base <- c(base, list(prueba_del_arbol = par, alternativa_del_arbol = alterna,
                           prueba = prueba, motivo = motivo))
      agregar(base, elegida, otra, cortes, medida, efecto)
    }

    for (vi in categoricas) {
      todos <- columna(datos, variables$nombre[vi])
      categorias <- ordenar(todos[todos != ""])
      tabla <- lapply(categorias, function(categoria) {
        vapply(niveles, function(nivel) sum(todos == categoria & valores_factor == nivel),
               numeric(1))
      })
      tabla <- tabla[vapply(tabla, sum, numeric(1)) > 0]
      n <- sum(unlist(tabla))
      if (length(tabla) < 2 || n == 0) next
      minima <- buscar_esperada(variables$nombre[vi], factor_nombre)
      par <- if (length(niveles) == 2) CHI2_DOS else CHI2_TRES
      alterna <- if (length(niveles) == 2 && length(tabla) == 2) FISHER else ""
      chi <- chi_cuadrado(tabla)
      exacta <- fisher(tabla)
      if (minima < 5 && !is.null(exacta)) {
        elegida <- exacta
        otra <- chi
        prueba <- FISHER
        motivo <- "alguna frecuencia esperada es menor que 5, y la tabla es de 2×2"
      } else {
        elegida <- chi
        otra <- exacta
        prueba <- par
        motivo <- if (minima >= 5) "todas las frecuencias esperadas llegan a 5"
                  else "alguna esperada es menor que 5, pero la tabla no es de 2×2"
      }
      if (minima < 5 && is.null(exacta)) {
        avisos[[length(avisos) + 1]] <- list(
          variable = variables$nombre[vi], factor = factor_nombre,
          aviso = paste0("La prueba exacta de Fisher para tablas de más de 2×2 no está en ",
                         "este proyecto: R y SciPy no la resuelven igual. Con esperadas tan ",
                         "chicas conviene juntar categorías o usar una prueba de ",
                         "permutaciones."))
      }
      base <- list(variable = variables$nombre[vi], etiqueta = variables$etiqueta[vi],
                   factor = factor_nombre, que = "categórica",
                   k = as.integer(length(niveles)), n = as.integer(n),
                   prueba_del_arbol = par, alternativa_del_arbol = alterna,
                   prueba = prueba, motivo = motivo)
      agregar(base, elegida, otra, "r", "V de Cramér",
              v_de_cramer(chi$estadistico, n, length(tabla), length(niveles)))
    }
  }

  list(pruebas = filas, avisos = avisos)
}

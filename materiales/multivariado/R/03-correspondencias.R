# Paso 3: análisis de correspondencias.
#
# Es el PCA de una tabla de contingencia. En vez de variables numéricas hay
# conteos, y en vez de varianza hay **inercia**: exactamente el chi cuadrado
# dividido por el total de casos.
#
#     inercia total = χ² / n
#
# Eso es lo que lo hace distinto de dibujar la tabla. Cada eje se lleva una parte
# de esa inercia, y lo que el mapa muestra es de dónde sale el χ²: qué filas y
# qué columnas se apartan de lo que habría si fueran independientes.
#
# **Lo que hay que tener presente al leerlo.** Un punto lejos del centro no es
# «mucho»: es **distinto del perfil promedio**. Una jurisdicción con el reparto
# educativo exactamente igual al del país cae en el origen aunque sea la más
# grande o la más chica. Y las distancias entre una fila y una columna no se
# leen directamente: lo que se lee es la dirección.

# Los ejes, con los perfiles de fila y de columna proyectados.
#
# La cuenta es una descomposición en valores singulares de los residuos
# tipificados de la tabla:
#
#     S = D_r^(-1/2) · (P − r·cᵀ) · D_c^(-1/2)
#
# Como la tabla tiene muchas más filas que columnas, se descompone `SᵀS`, que es
# de cinco por cinco: los autovalores de esa matriz son los cuadrados de los
# valores singulares, y de sus autovectores salen las columnas. Las filas se
# obtienen proyectando.
calcular_correspondencias <- function(tabla, filas_nombres, columnas_nombres, parametros) {
  nf <- length(filas_nombres)
  nc <- length(columnas_nombres)
  total <- suma(as.vector(t(tabla)))
  if (!(total > 0)) stop("La tabla de contingencia suma cero.", call. = FALSE)

  p <- tabla / total
  masa_fila <- vapply(seq_len(nf), function(i) suma(p[i, ]), numeric(1))
  masa_columna <- vapply(seq_len(nc), function(j) suma(p[, j]), numeric(1))
  for (i in seq_len(nf)) {
    if (!(masa_fila[i] > 0)) {
      stop(paste0("La fila «", filas_nombres[i], "» está toda en cero."), call. = FALSE)
    }
  }
  for (j in seq_len(nc)) {
    if (!(masa_columna[j] > 0)) {
      stop(paste0("La columna «", columnas_nombres[j], "» está toda en cero."),
           call. = FALSE)
    }
  }

  s <- matrix(0, nrow = nf, ncol = nc)
  for (i in seq_len(nf)) {
    for (j in seq_len(nc)) {
      s[i, j] <- (p[i, j] - masa_fila[i] * masa_columna[j]) /
        sqrt(masa_fila[i] * masa_columna[j])
    }
  }

  # SᵀS, que es chiquita y simétrica.
  gram <- matrix(0, nrow = nc, ncol = nc)
  for (a in seq_len(nc)) {
    for (b in a:nc) {
      v <- suma(vapply(seq_len(nf), function(i) s[i, a] * s[i, b], numeric(1)))
      gram[a, b] <- v
      gram[b, a] <- v
    }
  }
  descompuesta <- descomponer(gram)

  # El último autovalor de una tabla de contingencia es cero por construcción:
  # los perfiles viven en un espacio de una dimensión menos.
  inercias <- vapply(descompuesta$valores, function(v) max(0, v), numeric(1))
  inercia_total <- suma(inercias)
  ejes_posibles <- min(nf, nc) - 1

  # Las coordenadas de columna: el autovector dividido por la raíz de su masa y
  # multiplicado por el valor singular. Las de fila salen proyectando S.
  columnas <- list()
  filas <- list()
  for (j in seq_len(nc)) {
    singular <- if (inercias[j] > 0) sqrt(inercias[j]) else 0
    vector <- descompuesta$vectores[[j]]
    columnas[[j]] <- vapply(seq_len(nc),
                            function(k) vector[k] / sqrt(masa_columna[k]) * singular,
                            numeric(1))
    if (singular > 0) {
      filas[[j]] <- vapply(seq_len(nf), function(i) {
        suma(vapply(seq_len(nc), function(k) s[i, k] * vector[k], numeric(1))) /
          sqrt(masa_fila[i])
      }, numeric(1))
    } else {
      filas[[j]] <- rep(0, nf)
    }
  }

  chi2 <- inercia_total * total
  gl <- (nf - 1) * (nc - 1)
  list(total = total, inercias = inercias, inercia_total = inercia_total,
       ejes_posibles = ejes_posibles, masa_fila = masa_fila,
       masa_columna = masa_columna, coordenadas_fila = filas,
       coordenadas_columna = columnas, chi2 = chi2, gl = as.integer(gl),
       p = chi2_cola(chi2, gl), barridos = descompuesta$barridos, perfiles = p)
}

tabla_de_ejes <- function(salida) {
  filas <- list()
  acumulado <- 0
  for (j in seq_len(salida$ejes_posibles)) {
    inercia <- salida$inercias[j]
    proporcion <- if (salida$inercia_total > 0) inercia / salida$inercia_total
                  else NA_real_
    acumulado <- acumulado + if (is.na(proporcion)) 0 else proporcion
    filas[[j]] <- list(eje = as.integer(j), valor_singular = sqrt(inercia),
                       inercia = inercia, proporcion = proporcion,
                       acumulado = acumulado, chi2_del_eje = inercia * salida$total)
  }
  filas
}

# Filas y columnas en la misma tabla, con su masa, su aporte y su calidad.
#
# Las tres columnas del final son las que evitan leer mal un mapa. **El aporte**
# dice cuánto de ese eje lo construyó este punto: un eje puede estar definido por
# una sola jurisdicción. **La calidad** dice cuánto de ese punto se ve en los
# ejes elegidos: un punto con calidad baja está dibujado donde está por
# casualidad de la proyección.
tabla_de_puntos <- function(salida, filas_nombres, columnas_nombres, parametros) {
  ejes <- min(parametros$ejes, salida$ejes_posibles)
  puntos <- list()
  grupos <- list(
    list(tipo = "fila", nombres = filas_nombres, masas = salida$masa_fila,
         coordenadas = salida$coordenadas_fila),
    list(tipo = "columna", nombres = columnas_nombres, masas = salida$masa_columna,
         coordenadas = salida$coordenadas_columna))
  for (g in grupos) {
    for (i in seq_along(g$nombres)) {
      # La inercia del punto: su masa por su distancia al centro al cuadrado,
      # sumada sobre todos los ejes.
      propia <- suma(vapply(seq_len(salida$ejes_posibles),
                            function(j) g$masas[i] * g$coordenadas[[j]][i]^2,
                            numeric(1)))
      fila <- list(tipo = g$tipo, punto = g$nombres[i], masa = g$masas[i],
                   inercia = propia)
      vistos <- 0
      for (j in seq_len(ejes)) {
        coordenada <- g$coordenadas[[j]][i]
        fila[[paste0("eje_", j)]] <- coordenada
        fila[[paste0("aporte_", j)]] <- if (salida$inercias[j] > 0)
          g$masas[i] * coordenada * coordenada / salida$inercias[j] else NA_real_
        vistos <- vistos + g$masas[i] * coordenada * coordenada
      }
      fila$calidad <- if (propia > 0) vistos / propia else NA_real_
      puntos[[length(puntos) + 1]] <- fila
    }
  }
  puntos
}

avisos_de_correspondencias <- function(salida, filas_nombres, columnas_nombres,
                                       parametros, tabla) {
  avisos <- list()
  coma1 <- function(v) sub(".", ",", sprintf("%.1f", v), fixed = TRUE)
  coma3 <- function(v) sub(".", ",", sprintf("%.3f", v), fixed = TRUE)
  coma4 <- function(v) sub(".", ",", sprintf("%.4f", v), fixed = TRUE)
  # `numero_texto` en vez de `formatC`: formatC avisa cada vez que el separador
  # de miles y el decimal son el mismo punto, y en castellano lo son.
  miles <- function(v) numero_texto(v, 0)

  ejes <- min(parametros$ejes, salida$ejes_posibles)
  acumulado <- suma(vapply(seq_len(ejes), function(j) salida$inercias[j], numeric(1))) /
    salida$inercia_total
  avisos[[length(avisos) + 1]] <- list(
    donde = "correspondencias",
    aviso = paste0(
      "Los ", ejes, " ejes que se grafican se llevan el ", coma1(100 * acumulado),
      " % de la inercia. El resto está en las otras ", salida$ejes_posibles - ejes,
      " dimensiones, que el mapa no muestra."))

  if (salida$p >= 0.05) {
    avisos[[length(avisos) + 1]] <- list(
      donde = "correspondencias",
      aviso = paste0(
        "La prueba de independencia de la tabla no se rechaza. Con filas y columnas ",
        "independientes no hay nada que mapear: la inercia que el análisis reparte ",
        "entre los ejes es ruido."))
  } else {
    # El χ² crece con el total de casos: con una tabla de millones, rechaza
    # siempre. Lo que mide la fuerza de la asociación es la inercia, y la V de
    # Cramér es esa inercia puesta en una escala de cero a uno.
    v <- sqrt(salida$inercia_total /
                (min(length(filas_nombres), length(columnas_nombres)) - 1))
    if (salida$total > 100000 && v < 0.2) {
      avisos[[length(avisos) + 1]] <- list(
        donde = "correspondencias",
        aviso = paste0(
          "El χ² da ", miles(salida$chi2), " y el p es diminuto, pero eso no dice ",
          "nada: el χ² crece con el total de casos y acá hay ", miles(salida$total),
          ". Lo que mide la fuerza de la asociación es la inercia, que es ",
          coma4(salida$inercia_total), "; puesta en escala de cero a uno —la V de ",
          "Cramér— da ", coma3(v), ". La asociación existe y es débil. El mapa muestra ",
          "su forma, no su tamaño."))
    }
  }

  puntos <- tabla_de_puntos(salida, filas_nombres, columnas_nombres, parametros)
  flojos <- Filter(function(p) !is.na(p$calidad) && p$calidad < 0.5, puntos)
  if (length(flojos) > 0) {
    cuales <- paste(vapply(flojos[seq_len(min(4, length(flojos)))],
                           function(p) paste0("«", p$punto, "»"), character(1)),
                    collapse = ", ")
    avisos[[length(avisos) + 1]] <- list(
      donde = "correspondencias",
      aviso = paste0(
        "Hay ", length(flojos), " punto(s) con menos de la mitad de su inercia ",
        "representada en los ejes que se grafican —", cuales, "—. Están en el mapa, ",
        "se ven igual que los demás, y su posición es una sombra: están lejos en una ",
        "dirección que no se está mirando."))
  }

  for (j in seq_len(ejes)) {
    clave <- paste0("aporte_", j)
    del_eje <- Filter(function(p) !is.na(p[[clave]]), puntos)
    if (length(del_eje) == 0) next
    valores <- vapply(del_eje, function(p) p[[clave]], numeric(1))
    peor <- del_eje[[which.max(valores)]]
    if (peor[[clave]] > 0.5) {
      avisos[[length(avisos) + 1]] <- list(
        donde = "correspondencias",
        aviso = paste0(
          "El eje ", j, " lo construye casi solo «", peor$punto, "», que aporta el ",
          coma1(100 * peor[[clave]]), " % de su inercia. Un eje definido por un punto ",
          "describe a ese punto, no a la tabla."))
    }
  }
  avisos
}

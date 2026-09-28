# Paso 3: intervalos por bootstrap y la prueba de permutación.
#
# Una prueba de rangos dice si hay diferencia. No dice **de cuánto**, y para
# casi cualquier estadístico que no sea una media no hay fórmula cerrada que dé
# un intervalo. El bootstrap la reemplaza por fuerza bruta: se vuelve a
# muestrear la propia muestra, con reposición, miles de veces, y se mira cómo
# se mueve el estadístico.
#
# Se calculan tres intervalos para cada estadístico, porque no dan lo mismo:
#
#     percentil   los cuantiles de las réplicas, directo. Es el que todo el
#                 mundo usa y el que peor cobertura tiene cuando el estadístico
#                 es sesgado o su dispersión depende del valor.
#     básico      refleja las réplicas alrededor del valor observado. Corrige
#                 el sesgo de traslación y nada más.
#     BCa         corrige el sesgo y la asimetría, con dos constantes: z₀, que
#                 mide cuántas réplicas caen por debajo del valor observado, y
#                 a, la aceleración, que sale de un jackknife. Es el mejor de
#                 los tres y el que casi nadie calcula.
#
# Con un estadístico simétrico y sin sesgo los tres coinciden y la elección no
# importa. Con uno asimétrico —la media de un gasto, un desvío, una razón— se
# separan, y ahí el percentil empieza a mentir. El proyecto los escribe a los
# tres para que la diferencia se vea en vez de discutirse.
#
# **La prueba de permutación** es aparte y es la otra cara. En vez de suponer
# una distribución para el estadístico, se la construye: si los dos grupos
# vinieran de la misma población, las etiquetas serían intercambiables, así que
# se barajan y se mira con qué frecuencia el azar solo produce una diferencia
# tan grande como la observada. No supone nada sobre la forma y sirve para
# cualquier estadístico, incluso los que no tienen teoría.

# Redondea a diez dígitos significativos, sin depender de `round`.
#
# Hacen falta las dos cosas —redondear, y hacerlo a mano— y cada una por su
# motivo.
#
# **Redondear**, porque las réplicas se ORDENAN para sacar los cuantiles. Dos
# réplicas que difieren en el último bit pueden intercambiar su lugar en ese
# orden, y ahí el cuantil interpola entre otro par de vecinos y el intervalo
# cambia en el sexto decimal.
#
# **A mano**, porque `round()` de Python y `round()` de R **no desempatan
# igual**. Sobre exactamente el mismo número de doble precisión:
#
#     round(54955.843065, 5)    Python → 54955,84307
#                               R      → 54955,84306
#
# No es un error de ninguno de los dos: es un valor que cae justo en la mitad,
# y cada lenguaje eligió una regla distinta para ese caso. Con dos mil réplicas
# y un cuantil interpolado, caer en la mitad deja de ser raro. Acá se usa
# «medio para arriba en valor absoluto», que es una regla aritmética y da lo
# mismo en los dos idiomas.
a_diez_digitos <- function(v) {
  if (v == 0 || !is.finite(v)) return(v)
  # Con valores así de chicos la escala se iría fuera de lo que un doble
  # representa exacto, y el número se escribe como cero de todos modos.
  if (abs(v) < 1e-13) return(v)
  escala <- 10^(9 - floor(log10(abs(v))))
  (if (v > 0) floor(v * escala + 0.5) else ceiling(v * escala - 0.5)) / escala
}

# La fila entera pasada por el mismo redondeo.
#
# Se aplica al final y no en cada cuenta: así ningún número del bootstrap llega
# al archivo sin haber pasado por la misma regla.
redondeadas <- function(fila) {
  for (k in names(fila)) {
    # `is.double` y no `is.numeric`: un entero se escribe sin decimales y
    # redondearlo lo convertiría en 2.000000 en vez de 2.
    if (is.double(fila[[k]]) && length(fila[[k]]) == 1) {
      fila[[k]] <- a_diez_digitos(fila[[k]])
    }
  }
  fila
}

ric <- function(orden) cuantil(orden, 0.75) - cuantil(orden, 0.25)

NOMBRES_ESTADISTICOS <- c("mediana", "media", "ric", "desvio")

# Los cuatro estadísticos sobre una muestra. Recibe la muestra y su versión
# ordenada, así no se ordena dos veces: sobre 2.000 réplicas eso se nota.
evaluar <- function(valores, orden) {
  vapply(c(cuantil(orden, 0.5), mean(valores), ric(orden), desvio(valores)),
         a_diez_digitos, numeric(1))
}

# Los tres intervalos para cada estadístico, con las mismas réplicas.
#
# Se remuestrea una sola vez y se evalúan todos los estadísticos sobre cada
# réplica. No es solo por velocidad: usar las mismas réplicas hace que los
# intervalos sean comparables entre sí, porque comparten el azar.
intervalos <- function(valores, azar, replicas, confianza) {
  n <- length(valores)
  if (n < 3) return(list())
  observados <- evaluar(valores, sort(valores))

  replicados <- matrix(0, nrow = replicas, ncol = length(NOMBRES_ESTADISTICOS))
  for (r in seq_len(replicas)) {
    muestra <- valores[remuestrear(azar, n) + 1]
    replicados[r, ] <- evaluar(muestra, sort(muestra))
  }

  # El jackknife, para la aceleración del BCa: cada estadístico recalculado
  # sacando un caso por vez.
  jack <- matrix(0, nrow = n, ncol = length(NOMBRES_ESTADISTICOS))
  for (i in seq_len(n)) {
    sin_i <- valores[-i]
    jack[i, ] <- evaluar(sin_i, sort(sin_i))
  }

  alfa <- 1 - confianza
  z_baja <- qnorm(alfa / 2)
  z_alta <- qnorm(1 - alfa / 2)

  salida <- list()
  for (j in seq_along(NOMBRES_ESTADISTICOS)) {
    observado <- observados[j]
    if (!is.finite(observado)) next
    rep <- sort(replicados[, j])

    percentil <- c(cuantil(rep, alfa / 2), cuantil(rep, 1 - alfa / 2))
    # El básico refleja: si las réplicas quedaron por encima del observado, el
    # intervalo tiene que correrse hacia abajo.
    basico <- c(2 * observado - percentil[2], 2 * observado - percentil[1])

    base <- list(estadistico = NOMBRES_ESTADISTICOS[j], observado = observado,
                 error_estandar = desvio(replicados[, j]),
                 sesgo = mean(replicados[, j]) - observado,
                 percentil_inferior = percentil[1], percentil_superior = percentil[2],
                 basico_inferior = basico[1], basico_superior = basico[2],
                 bca_inferior = NULL, bca_superior = NULL, z0 = NULL, aceleracion = NULL)

    # z₀: cuántas réplicas cayeron por debajo del observado, en unidades
    # normales. Mide el sesgo de la distribución bootstrap.
    proporcion <- sum(replicados[, j] < observado) / replicas
    if (proporcion <= 0 || proporcion >= 1) {
      # Con todas las réplicas de un lado no hay corrección posible, y forzarla
      # daría un infinito. Se deja el percentil y se avisa.
      salida[[length(salida) + 1]] <- redondeadas(base)
      next
    }
    z0 <- qnorm(proporcion)

    promedio_jack <- mean(jack[, j])
    d <- promedio_jack - jack[, j]
    suma2 <- sum(d * d)
    aceleracion <- if (suma2 > 0) sum(d^3) / (6 * suma2^1.5) else 0

    ajustado <- function(z) {
      denominador <- 1 - aceleracion * (z0 + z)
      if (denominador == 0) return(NULL)
      pnorm(z0 + (z0 + z) / denominador)
    }
    baja <- ajustado(z_baja)
    alta <- ajustado(z_alta)

    base$z0 <- z0
    base$aceleracion <- aceleracion
    if (!is.null(baja) && !is.null(alta)) {
      base$bca_inferior <- cuantil(rep, baja)
      base$bca_superior <- cuantil(rep, alta)
    }
    salida[[length(salida) + 1]] <- redondeadas(base)
  }
  salida
}

# El intervalo para la diferencia entre dos grupos, remuestreando cada uno por
# separado.
#
# Es lo que corresponde con muestras independientes: remuestrear todo junto
# supondría que vienen de la misma población, que es justamente lo que se está
# poniendo en duda.
diferencia_entre <- function(a, b, azar, replicas, confianza) {
  na <- length(a)
  nb <- length(b)
  if (na < 3 || nb < 3) return(list())
  observados <- vapply(c(cuantil(sort(b), 0.5) - cuantil(sort(a), 0.5),
                         mean(b) - mean(a)), a_diez_digitos, numeric(1))

  replicados <- matrix(0, nrow = replicas, ncol = 2)
  for (r in seq_len(replicas)) {
    ra <- sort(a[remuestrear(azar, na) + 1])
    rb <- sort(b[remuestrear(azar, nb) + 1])
    replicados[r, 1] <- a_diez_digitos(cuantil(rb, 0.5) - cuantil(ra, 0.5))
    replicados[r, 2] <- a_diez_digitos(mean(rb) - mean(ra))
  }

  alfa <- 1 - confianza
  claves <- c("diferencia_de_medianas", "diferencia_de_medias")
  salida <- list()
  for (j in 1:2) {
    rep <- sort(replicados[, j])
    inferior <- cuantil(rep, alfa / 2)
    superior <- cuantil(rep, 1 - alfa / 2)
    salida[[j]] <- redondeadas(list(
      estadistico = claves[j], observado = observados[j],
      error_estandar = desvio(replicados[, j]),
      sesgo = mean(replicados[, j]) - observados[j],
      percentil_inferior = inferior, percentil_superior = superior,
      basico_inferior = 2 * observados[j] - superior,
      basico_superior = 2 * observados[j] - inferior,
      bca_inferior = NULL, bca_superior = NULL, z0 = NULL, aceleracion = NULL,
      # Un intervalo que no contiene al cero dice lo mismo que un valor p menor
      # que alfa, y dice además de cuánto es la diferencia.
      excluye_el_cero = (inferior > 0) == (superior > 0)))
  }
  salida
}

# La prueba de permutación sobre la diferencia de medianas.
#
# El valor p va con la corrección de Davison y Hinkley: (aciertos + 1) sobre
# (réplicas + 1), y no aciertos sobre réplicas. La razón es simple: la
# permutación observada es una de las posibles, así que contarla evita el
# absurdo de informar p = 0, que diría que ninguna reordenación del azar podría
# dar lo que se vio.
permutacion <- function(a, b, azar, replicas, confianza) {
  na <- length(a)
  nb <- length(b)
  if (na < 2 || nb < 2) return(NULL)
  todos <- c(a, b)
  n <- na + nb
  observada <- a_diez_digitos(cuantil(sort(b), 0.5) - cuantil(sort(a), 0.5))

  extremas <- 0
  for (r in seq_len(replicas)) {
    orden <- permutar(azar, n)
    ra <- sort(todos[orden[seq_len(na)] + 1])
    rb <- sort(todos[orden[(na + 1):n] + 1])
    if (abs(a_diez_digitos(cuantil(rb, 0.5) - cuantil(ra, 0.5))) >=
        abs(observada) - 1e-12) {
      extremas <- extremas + 1
    }
  }

  p <- (extremas + 1) / (replicas + 1)
  redondeadas(list(observada = observada, extremas = as.integer(extremas),
                   replicas = as.integer(replicas), p = p,
                   significativa = p < 1 - confianza))
}

calcular_bootstrap <- function(parametros, valores, grupos) {
  replicas <- parametros$replicas
  confianza <- parametros$confianza
  # Cada bloque arranca de su propia semilla derivada, así agregar o sacar un
  # bloque no corre el azar de los demás.
  azar_uno <- nuevo_azar(parametros$semilla)
  azar_dos <- nuevo_azar(parametros$semilla + 1)
  azar_tres <- nuevo_azar(parametros$semilla + 2)

  filas <- if (length(valores) > 0) intervalos(valores, azar_uno, replicas, confianza)
           else list()
  perm <- NULL
  if (length(grupos) == 2) {
    a <- grupos[[1]]
    b <- grupos[[2]]
    filas <- c(filas, diferencia_entre(a, b, azar_dos, replicas, confianza))
    perm <- permutacion(a, b, azar_tres, replicas, confianza)
  }

  avisos <- list()
  for (fila in filas) {
    if (is.null(fila$bca_inferior) && is.null(fila$z0) &&
        is.null(fila$excluye_el_cero)) {
      avisos[[length(avisos) + 1]] <- list(
        donde = "bootstrap",
        aviso = paste0("No se pudo calcular el BCa de «", fila$estadistico, "»: todas las ",
                       "réplicas quedaron del mismo lado del valor observado. Suele pasar ",
                       "con estadísticos que toman pocos valores distintos."))
      next
    }
    if (is.null(fila$bca_inferior)) next
    # Cuánto se mueve el intervalo al corregir. Si se mueve mucho, el percentil
    # —que es el que todo el mundo informa— está mal.
    ancho <- fila$percentil_superior - fila$percentil_inferior
    corrimiento <- max(abs(fila$bca_inferior - fila$percentil_inferior),
                       abs(fila$bca_superior - fila$percentil_superior))
    if (ancho > 0 && corrimiento / ancho > 0.1) {
      avisos[[length(avisos) + 1]] <- list(
        donde = "bootstrap",
        aviso = paste0("En «", fila$estadistico, "», el intervalo BCa se corre ",
                       gsub(".", ",", sprintf("%.0f", corrimiento / ancho * 100),
                            fixed = TRUE),
                       " % del ancho respecto del percentil. El percentil es el que casi ",
                       "todo el mundo informa, y acá está sesgado: el que corresponde es ",
                       "el BCa."))
    }
  }

  if (!is.null(perm) && length(grupos) == 2) {
    # El p de permutación no puede bajar de 1/(réplicas+1): si dio el mínimo,
    # lo único que se sabe es «menor que eso».
    minimo <- 1 / (replicas + 1)
    if (perm$p <= minimo + 1e-12) {
      avisos[[length(avisos) + 1]] <- list(
        donde = "bootstrap",
        aviso = paste0("La prueba de permutación dio el valor p más chico que puede dar ",
                       "con ", replicas, " réplicas. No significa que sea cero: significa ",
                       "que hace falta correr más réplicas para ponerle un número."))
    }
  }

  list(intervalos = filas, permutacion = perm, replicas = as.integer(replicas),
       avisos = avisos)
}

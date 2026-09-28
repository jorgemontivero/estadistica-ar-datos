# Paso 2: analizar.
#
# Lee datos/limpios/encuesta.csv —nunca el crudo— y escribe las tablas en
# salidas/. Se puede correr las veces que haga falta sin volver a limpiar.

VARIABLES <- c("edad", "ingreso", "puntaje")

descriptivos <- function(x) {
  x <- x[!is.na(x)]
  n <- length(x)
  list(
    n = n,
    media = if (n >= 1) mean(x) else NA,
    desvio = if (n >= 2) sd(x) else NA,
    minimo = if (n >= 1) min(x) else NA,
    mediana = if (n >= 1) median(x) else NA,
    maximo = if (n >= 1) max(x) else NA
  )
}

analizar <- function() {
  datos <- leer_csv("datos/limpios/encuesta.csv")
  for (v in VARIABLES) datos[[v]] <- suppressWarnings(as.numeric(datos[[v]]))
  dir.create("salidas", showWarnings = FALSE, recursive = TRUE)

  tabla <- data.frame(variable = character(), n = numeric(), media = numeric(),
                      desvio = numeric(), minimo = numeric(), mediana = numeric(),
                      maximo = numeric(), stringsAsFactors = FALSE)
  for (v in VARIABLES) {
    d <- descriptivos(datos[[v]])
    tabla <- rbind(tabla, data.frame(variable = v, n = d$n, media = d$media,
                                     desvio = d$desvio, minimo = d$minimo,
                                     mediana = d$mediana, maximo = d$maximo,
                                     stringsAsFactors = FALSE))
  }
  escribir_csv(tabla, "salidas/descriptivos.csv")

  # Por grupo, en orden alfabético para que R y Python coincidan.
  grupos <- sort(unique(datos$grupo[datos$grupo != ""]))
  por_grupo <- data.frame(grupo = character(), variable = character(), n = numeric(),
                          media = numeric(), desvio = numeric(), stringsAsFactors = FALSE)
  for (g in grupos) {
    for (v in VARIABLES) {
      d <- descriptivos(datos[[v]][datos$grupo == g])
      por_grupo <- rbind(por_grupo, data.frame(grupo = g, variable = v, n = d$n,
                                               media = d$media, desvio = d$desvio,
                                               stringsAsFactors = FALSE))
    }
  }
  escribir_csv(por_grupo, "salidas/por-grupo.csv")

  list(grupos = length(grupos), casos = nrow(datos))
}

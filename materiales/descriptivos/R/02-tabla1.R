# Paso 2: la tabla 1, la que abre todo informe.
#
# Una fila por variable —o por categoría, si es categórica—, una columna por
# grupo, más el total y la comparación. Se escribe dos veces: en CSV para
# seguir trabajando y en Markdown para pegar en el informe.
#
# Cómo se llena cada celda:
#
#     numérica simétrica     media (DE)
#     numérica asimétrica    mediana [Q1–Q3]
#     categórica             n (%)
#
# La asimetría decide sola, con la regla del sitio: |asimetría| > 1. Así la
# misma variable no se informa con media en una tabla y con mediana en otra.

RAYA <- "–"  # raya de rango, no guion: «18–65»

celda_numerica <- function(valores, forma) {
  if (length(valores) == 0) return("—")
  d <- descriptivos(valores)
  if (forma == "asimétrica") {
    dec <- decimales_de(d$mediana)
    return(paste0(numero_texto(d$mediana, dec), " [", numero_texto(d$q1, dec), RAYA,
                  numero_texto(d$q3, dec), "]"))
  }
  dec <- decimales_de(d$media)
  desvio <- if (!is.null(d$desvio)) numero_texto(d$desvio, dec) else "—"
  paste0(numero_texto(d$media, dec), " (", desvio, ")")
}

celda_categorica <- function(cuantos, total) {
  if (total == 0) return("—")
  paste0(cuantos, " (", numero_texto(cuantos / total * 100, 1), "%)")
}

armar <- function(datos, variables, calculado) {
  es_grupo <- variables$tipo == "grupo"
  grupo <- if (any(es_grupo)) variables$nombre[which(es_grupo)[1]] else NULL
  niveles <- if (!is.null(grupo)) {
    valores <- columna(datos, grupo)
    sort(unique(valores[valores != ""]))
  } else character(0)
  columnas <- c("variable", "categoria", "total", niveles, "p", "prueba", "nota")

  subconjunto <- function(nivel) datos[columna(datos, grupo) == nivel]

  filas <- list()
  for (k in seq_along(variables$nombre)) {
    nombre <- variables$nombre[k]
    etiqueta <- if (variables$etiqueta[k] != "") variables$etiqueta[k] else nombre
    tipo <- variables$tipo[k]
    if (tipo == "numerica") {
      todos <- numeros(columna(datos, nombre))
      forma <- if (length(todos) > 0) descriptivos(todos)$forma else "simétrica"
      por_grupo <- lapply(niveles, function(n) numeros(columna(subconjunto(n), nombre)))
      fila <- list(variable = etiqueta, categoria = "", total = celda_numerica(todos, forma))
      for (i in seq_along(niveles)) fila[[niveles[i]]] <- celda_numerica(por_grupo[[i]], forma)
      comparacion <- if (length(niveles) > 0) {
        comparar_numerica(por_grupo[vapply(por_grupo, length, integer(1)) > 0], forma)
      } else list(p = NULL, prueba = "", nota = "")
      fila$p <- p_texto(comparacion$p)
      fila$prueba <- comparacion$prueba
      fila$nota <- comparacion$nota
      filas[[length(filas) + 1]] <- fila
    } else if (tipo == "categorica") {
      valores <- columna(datos, nombre)
      llenos <- valores[valores != ""]
      categorias <- sort(unique(llenos))
      tabla <- matrix(0L, nrow = length(categorias), ncol = max(1, length(niveles)))
      for (i in seq_along(categorias)) {
        for (j in seq_along(niveles)) {
          tabla[i, j] <- sum(columna(subconjunto(niveles[j]), nombre) == categorias[i])
        }
      }
      comparacion <- if (length(niveles) > 0) comparar_categorica(tabla) else
        list(p = NULL, prueba = "", nota = "")
      for (i in seq_along(categorias)) {
        fila <- list(variable = if (i == 1) etiqueta else "", categoria = categorias[i],
                     total = celda_categorica(sum(llenos == categorias[i]), length(llenos)))
        for (j in seq_along(niveles)) {
          fila[[niveles[j]]] <- celda_categorica(tabla[i, j], length(subconjunto(niveles[j])))
        }
        fila$p <- if (i == 1) p_texto(comparacion$p) else ""
        fila$prueba <- if (i == 1) comparacion$prueba else ""
        fila$nota <- if (i == 1) comparacion$nota else ""
        filas[[length(filas) + 1]] <- fila
      }
    }
  }

  escribir_csv(filas, "salidas/tabla1.csv", columnas)
  escribir_texto(markdown(filas, datos, niveles, grupo), "salidas/tabla1.md")
  list(filas = filas, niveles = niveles)
}

# La misma tabla, para pegar en el informe.
markdown <- function(filas, datos, niveles, grupo) {
  n_de <- function(nivel) sum(columna(datos, grupo) == nivel)
  encabezado <- c("Variable", paste0("Total (n = ", length(datos), ")"),
                  vapply(niveles, function(n) paste0(n, " (n = ", n_de(n), ")"), character(1)),
                  "p", "Prueba")
  lineas <- c(paste0("**Tabla 1.** Características de la muestra",
                     if (!is.null(grupo)) paste0(", según ", grupo, ".") else "."),
              "",
              paste0("| ", paste(encabezado, collapse = " | "), " |"),
              paste0("|", paste(rep("---|", length(encabezado)), collapse = "")))
  for (fila in filas) {
    nombre <- fila$variable
    if (fila$categoria != "") {
      nombre <- if (nombre != "") paste0("**", nombre, "**, ", fila$categoria) else
        paste0("  ", fila$categoria)
    }
    celdas <- c(nombre, fila$total,
                vapply(niveles, function(n) fila[[n]], character(1)), fila$p, fila$prueba)
    lineas <- c(lineas, paste0("| ", paste(celdas, collapse = " | "), " |"))
  }
  notas <- sort(unique(vapply(filas, function(f) f$nota, character(1))))
  notas <- notas[notas != ""]
  if (length(notas) > 0) lineas <- c(lineas, "", paste0("Nota: ", notas, "."))
  c(lineas, "",
    paste0("Las variables simétricas se informan como media (desvío estándar) y las ",
           "asimétricas como mediana [Q1", RAYA, "Q3]. Las categóricas, como n (%)."))
}

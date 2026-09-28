# Paso 1: los descriptivos de cada variable.
#
# Escribe dos archivos: uno con las numéricas y otro con las categóricas. Son
# los números completos; la tabla 1 del paso 2 los resume.

COLUMNAS_NUM <- c("variable", "etiqueta", "n", "faltantes", "media", "desvio", "minimo", "q1",
                  "mediana", "q3", "maximo", "asimetria", "forma")
COLUMNAS_CAT <- c("variable", "etiqueta", "categoria", "n", "pct")

# Las categorías presentes, en orden alfabético: no depende del orden de los
# datos, así que dos bases con las mismas categorías dan la misma tabla.
categorias_de <- function(valores) sort(unique(valores[valores != ""]))

calcular <- function(datos, variables) {
  numericas <- list()
  categoricas <- list()
  for (k in seq_along(variables$nombre)) {
    nombre <- variables$nombre[k]
    etiqueta <- if (variables$etiqueta[k] != "") variables$etiqueta[k] else nombre
    tipo <- variables$tipo[k]
    if (tipo == "numerica") {
      valores <- numeros(columna(datos, nombre))
      fila <- c(list(variable = nombre, etiqueta = etiqueta,
                     faltantes = as.integer(length(datos) - length(valores))),
                descriptivos(valores))
      numericas[[length(numericas) + 1]] <- fila
    } else if (tipo == "categorica") {
      todos <- columna(datos, nombre)
      llenos <- todos[todos != ""]
      for (categoria in categorias_de(todos)) {
        cuantos <- sum(llenos == categoria)
        categoricas[[length(categoricas) + 1]] <- list(
          variable = nombre, etiqueta = etiqueta, categoria = categoria,
          n = as.integer(cuantos),
          pct = if (length(llenos) > 0) cuantos / length(llenos) * 100 else 0
        )
      }
    }
  }
  escribir_csv(numericas, "salidas/descriptivos.csv", COLUMNAS_NUM)
  escribir_csv(categoricas, "salidas/frecuencias.csv", COLUMNAS_CAT)
  list(numericas = numericas, categoricas = categoricas)
}

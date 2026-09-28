# Calcula los descriptivos y arma la tabla 1.
#
#     source("R/correr.R")
#
# Desde la carpeta del proyecto, no desde R/.

DATOS <- "datos/base.csv"
VARIABLES <- "datos/variables.csv"

for (archivo in c(DATOS, VARIABLES)) {
  if (!file.exists(archivo)) {
    stop(paste0("No encuentro ", archivo, ". ¿Estás parado en la carpeta del proyecto?"))
  }
}

source("R/comun.R")
source("R/pruebas.R")
source("R/01-descriptivos.R")
source("R/02-tabla1.R")

datos <- leer_csv(DATOS)
filas_var <- leer_csv(VARIABLES)
variables <- list(
  nombre = columna(filas_var, "nombre"),
  etiqueta = columna(filas_var, "etiqueta"),
  tipo = columna(filas_var, "tipo")
)
con_nombre <- variables$nombre != ""
variables <- lapply(variables, function(v) v[con_nombre])

calculado <- calcular(datos, variables)
tabla <- armar(datos, variables, calculado)

resumen <- list(
  list(clave = "casos", valor = length(datos)),
  list(clave = "variables", valor = length(variables$nombre)),
  list(clave = "numericas", valor = sum(variables$tipo == "numerica")),
  list(clave = "categoricas", valor = sum(variables$tipo == "categorica")),
  list(clave = "grupos", valor = length(tabla$niveles)),
  list(clave = "filas_de_la_tabla", valor = length(tabla$filas)),
  list(clave = "asimetricas", valor = sum(vapply(calculado$numericas,
                                                 function(f) identical(f$forma, "asimétrica"),
                                                 logical(1))))
)
resumen <- lapply(resumen, function(f) list(clave = f$clave, valor = as.integer(f$valor)))
escribir_csv(resumen, "salidas/resumen.csv", c("clave", "valor"))

cat("Listo. Salidas en salidas/:\n")
cat("  descriptivos.csv, frecuencias.csv, tabla1.csv y tabla1.md\n")
cat(sprintf("  %d casos, %d variables, %d grupos\n",
            length(datos), length(variables$nombre), length(tabla$niveles)))

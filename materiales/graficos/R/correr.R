# Dibuja todas las figuras, cada una con su tabla.
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
source("R/01-figuras.R")

datos <- leer_csv(DATOS)
filas_var <- leer_csv(VARIABLES)
variables <- list(
  nombre = columna(filas_var, "nombre"),
  etiqueta = columna(filas_var, "etiqueta"),
  tipo = columna(filas_var, "tipo")
)
con_nombre <- variables$nombre != ""
variables <- lapply(variables, function(v) v[con_nombre])

hechas <- dibujar(datos, variables)
escribir_csv(lapply(hechas, function(n) list(figura = n)), "indice", c("figura"))

cat("Listo. Figuras en salidas/figuras/:\n")
for (nombre in hechas) cat(sprintf("  %s.png · %s.csv\n", nombre, nombre))

# Corre todo el análisis, de los datos crudos a las tablas.
#
#     source("R/correr.R")
#
# Desde la carpeta del proyecto, no desde R/.

if (!file.exists("datos/crudos/encuesta.csv")) {
  stop("No encuentro datos/crudos/encuesta.csv. ¿Estás parado en la carpeta del proyecto?")
}

source("R/comun.R")
source("R/01-importar.R")
source("R/02-analizar.R")

importado <- importar()
analizado <- analizar()

resumen <- data.frame(
  clave = c("filas_crudas", "filas_repetidas", "valores_vacios", "valores_fuera_de_rango",
            "filas_limpias", "grupos", "casos_analizados"),
  valor = c(importado$filas_crudas, importado$filas_repetidas, importado$valores_vacios,
            importado$valores_fuera_de_rango, importado$filas_limpias,
            analizado$grupos, analizado$casos),
  stringsAsFactors = FALSE
)
escribir_csv(resumen, "salidas/resumen.csv")

cat("Listo. Salidas en salidas/:\n")
cat("  descriptivos.csv, por-grupo.csv, resumen.csv\n")
cat(sprintf("  %d filas crudas → %d limpias\n", importado$filas_crudas, importado$filas_limpias))

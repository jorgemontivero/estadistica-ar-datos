# Calcula todos los intervalos y escribe el informe.
#
#     source("R/correr.R")
#
# Desde la carpeta del proyecto, no desde R/.

DATOS <- "datos/base.csv"
VARIABLES <- "datos/variables.csv"
PARAMETROS <- "datos/parametros.csv"

for (archivo in c(DATOS, VARIABLES, PARAMETROS)) {
  if (!file.exists(archivo)) {
    stop(paste0("No encuentro ", archivo, ". ¿Estás parado en la carpeta del proyecto?"))
  }
}

source("R/comun.R")
source("R/intervalos.R")
source("R/01-una-muestra.R")
source("R/02-diferencias.R")
source("R/03-redaccion.R")

datos <- leer_csv(DATOS)
filas_var <- leer_csv(VARIABLES)
variables <- list(
  nombre = columna(filas_var, "nombre"),
  etiqueta = columna(filas_var, "etiqueta"),
  tipo = columna(filas_var, "tipo")
)
con_nombre <- variables$nombre != ""
variables <- lapply(variables, function(v) v[con_nombre])
parametros <- leer_parametros(PARAMETROS)

calculado <- calcular(datos, variables, parametros)
diferencias <- calcular_diferencias(datos, variables, parametros, calculado)

escribir_csv(calculado$medias, "salidas/ic-medias.csv",
             c("variable", "etiqueta", "ambito", "n", "media", "desvio", "error_estandar",
               "gl", "critico", "margen", "inferior", "superior"))
escribir_csv(calculado$varianzas, "salidas/ic-varianzas.csv",
             c("variable", "etiqueta", "ambito", "n", "gl", "varianza", "desvio",
               "var_inferior", "var_superior", "desvio_inferior", "desvio_superior"))
escribir_csv(calculado$proporciones, "salidas/ic-proporciones.csv",
             c("variable", "etiqueta", "categoria", "ambito", "n", "exitos", "proporcion",
               "metodo", "inferior", "superior", "ancho"))
escribir_csv(diferencias$diferencias, "salidas/ic-diferencias.csv",
             c("variable", "etiqueta", "que", "categoria", "grupo_1", "grupo_2", "n_1", "n_2",
               "estimacion_1", "estimacion_2", "diferencia", "error_estandar", "gl", "critico",
               "inferior", "superior", "excluye_cero", "se_pisan_los_individuales",
               "conclusion_distinta"))
escribir_csv(c(calculado$avisos, diferencias$avisos), "salidas/avisos.csv",
             c("intervalo", "variable", "ambito", "detalle", "aviso"))

escribir_texto(redactar(calculado, diferencias, parametros, length(datos)),
               "salidas/intervalos.md")

enganosas <- sum(vapply(diferencias$diferencias,
                        function(f) isTRUE(f$conclusion_distinta), logical(1)))
resumen <- list(
  list(clave = "casos", valor = as.integer(length(datos))),
  list(clave = "variables", valor = as.integer(length(variables$nombre))),
  list(clave = "confianza", valor = as.numeric(parametros$confianza)),
  list(clave = "grupos", valor = as.integer(length(diferencias$niveles))),
  list(clave = "ic_de_medias", valor = as.integer(length(calculado$medias))),
  list(clave = "ic_de_varianzas", valor = as.integer(length(calculado$varianzas))),
  list(clave = "ic_de_proporciones", valor = as.integer(length(calculado$proporciones))),
  list(clave = "ic_de_diferencias", valor = as.integer(length(diferencias$diferencias))),
  list(clave = "avisos", valor = as.integer(length(calculado$avisos) +
                                              length(diferencias$avisos))),
  list(clave = "conclusiones_distintas", valor = as.integer(enganosas))
)
escribir_csv(resumen, "salidas/resumen.csv", c("clave", "valor"))

cat("Listo. Salidas en salidas/:\n")
cat("  ic-medias.csv, ic-varianzas.csv, ic-proporciones.csv, ic-diferencias.csv,\n")
cat("  avisos.csv, resumen.csv e intervalos.md\n")
if (enganosas > 0) {
  cuantas <- if (enganosas == 1) "1 comparación" else paste0(enganosas, " comparaciones")
  cat(sprintf("  Ojo: en %s los intervalos por separado llevan a la conclusión contraria.\n",
              cuantas))
}

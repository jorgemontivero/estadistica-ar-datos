# Verifica los supuestos, corre las pruebas y escribe el informe.
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
source("R/01-supuestos.R")
source("R/02-pruebas.R")
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

supuestos <- calcular_supuestos(datos, variables, parametros)
pruebas <- calcular_pruebas(datos, variables, parametros, supuestos)

escribir_csv(supuestos$supuestos, "salidas/normalidad.csv",
             c("variable", "etiqueta", "factor", "grupo", "n", "media", "desvio", "asimetria",
               "shapiro_w", "shapiro_p", "veredicto"))
escribir_csv(supuestos$homogeneidad, "salidas/homogeneidad.csv",
             c("variable", "etiqueta", "factor", "k", "levene_f", "gl1", "gl2", "levene_p",
               "homogeneas", "decide"))
escribir_csv(supuestos$esperadas, "salidas/esperadas.csv",
             c("variable", "etiqueta", "factor", "filas", "columnas", "n", "esperada_minima",
               "todas_mayores_que_5"))
escribir_csv(pruebas$pruebas, "salidas/pruebas.csv",
             c("variable", "etiqueta", "factor", "que", "k", "n", "prueba_del_arbol",
               "alternativa_del_arbol", "prueba", "motivo", "simbolo", "estadistico", "gl",
               "gl2", "p", "significativa", "medida", "efecto", "calificacion",
               "p_alternativa", "significativa_alternativa", "cambia_la_conclusion"))
escribir_csv(c(supuestos$avisos, pruebas$avisos), "salidas/avisos.csv",
             c("variable", "factor", "aviso"))

escribir_texto(redactar(supuestos, pruebas, parametros, variables, length(datos)),
               "salidas/pruebas.md")

cambian <- sum(vapply(pruebas$pruebas, function(f) isTRUE(f$cambia_la_conclusion), logical(1)))
no_normales <- sum(vapply(supuestos$supuestos,
                          function(f) identical(f$veredicto, "no-normal"), logical(1)))
significativas <- sum(vapply(pruebas$pruebas, function(f) isTRUE(f$significativa), logical(1)))
resumen <- list(
  list(clave = "casos", valor = as.integer(length(datos))),
  list(clave = "alfa", valor = as.numeric(parametros$alfa)),
  list(clave = "factores", valor = as.integer(sum(variables$tipo == "grupo"))),
  list(clave = "comparaciones", valor = as.integer(length(pruebas$pruebas))),
  list(clave = "grupos_evaluados", valor = as.integer(length(supuestos$supuestos))),
  list(clave = "grupos_no_normales", valor = as.integer(no_normales)),
  list(clave = "significativas", valor = as.integer(significativas)),
  list(clave = "cambian_la_conclusion", valor = as.integer(cambian)),
  list(clave = "avisos", valor = as.integer(length(supuestos$avisos) + length(pruebas$avisos)))
)
escribir_csv(resumen, "salidas/resumen.csv", c("clave", "valor"))

cat("Listo. Salidas en salidas/:\n")
cat("  normalidad.csv, homogeneidad.csv, esperadas.csv, pruebas.csv,\n")
cat("  avisos.csv, resumen.csv y pruebas.md\n")
if (cambian > 0) {
  cuantas <- if (cambian == 1) "1 comparación" else paste0(cambian, " comparaciones")
  cat(sprintf("  Ojo: en %s el supuesto decide la conclusión, no solo la prueba.\n", cuantas))
}

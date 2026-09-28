# Corre el ANOVA completo y escribe el informe.
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
source("R/algebra.R")
source("R/rango.R")
source("R/01-supuestos.R")
source("R/02-anova.R")
source("R/03-posthoc.R")
source("R/04-redaccion.R")

datos <- leer_csv(DATOS)
parametros <- leer_parametros(PARAMETROS)

factores <- parametros$factor
if (parametros$factor_2 != "") factores <- c(factores, parametros$factor_2)

# Las celdas son la unidad del proyecto: con un factor coinciden con sus
# niveles, con dos son las combinaciones.
partido <- agrupar(datos, factores, parametros$respuesta)
grupos_celda <- partido$grupos
descartados <- partido$descartados
grupos_factor <- agrupar(datos, parametros$factor, parametros$respuesta)$grupos
if (length(grupos_celda) == 0) {
  stop("Ninguna fila tiene a la vez la respuesta y todos los factores.")
}

supuestos <- calcular_supuestos(grupos_celda, parametros)
anova <- calcular_anova(grupos_factor, grupos_celda, parametros)

# Con dos factores el post hoc va sobre las celdas; con uno, sobre sus niveles.
if (parametros$factor_2 != "") {
  sobre <- paste0(parametros$factor, " × ", parametros$factor_2)
  tabla_post_hoc <- tabla_anova(grupos_celda, parametros$confianza)
} else {
  sobre <- parametros$factor
  tabla_post_hoc <- anova$un_factor
}
post_hoc <- calcular_posthoc(tabla_post_hoc, parametros, sobre)

celdas <- lapply(grupos_celda, function(g) {
  list(celda = g$etiqueta, n = as.integer(length(g$valores)), media = mean(g$valores),
       desvio = desvio(g$valores), mediana = median(g$valores),
       minimo = min(g$valores), maximo = max(g$valores))
})
escribir_csv(celdas, "salidas/celdas.csv",
             c("celda", "n", "media", "desvio", "mediana", "minimo", "maximo"))

escribir_csv(supuestos$normalidad, "salidas/supuestos.csv",
             c("celda", "n", "w", "p", "normal", "por_que"))

uf <- anova$un_factor
w <- anova$welch
escribir_csv(list(
  list(fuente = "Entre grupos", sc = uf$sc_entre, gl = uf$gl_entre, cm = uf$cm_entre,
       f = uf$f, p = uf$p),
  list(fuente = "Dentro de los grupos", sc = uf$sc_dentro, gl = uf$gl_dentro,
       cm = uf$cm_dentro, f = NULL, p = NULL),
  list(fuente = "Total", sc = uf$sc_total, gl = uf$gl_total, cm = NULL, f = NULL, p = NULL)
), "salidas/anova-un-factor.csv", c("fuente", "sc", "gl", "cm", "f", "p"))

escribir_csv(list(list(
  n = uf$n, grupos = uf$k, f = uf$f, gl_entre = uf$gl_entre, gl_dentro = uf$gl_dentro,
  p = uf$p, critico = uf$critico, significativo = uf$p < 1 - parametros$confianza,
  eta_cuadrado = uf$eta_cuadrado, omega_cuadrado = uf$omega_cuadrado,
  welch_f = if (is.null(w)) NULL else w$f,
  welch_gl2 = if (is.null(w)) NULL else w$gl2,
  welch_p = if (is.null(w)) NULL else w$p,
  levene_w = if (is.null(supuestos$homogeneidad)) NULL else supuestos$homogeneidad$w,
  levene_p = if (is.null(supuestos$homogeneidad)) NULL else supuestos$homogeneidad$p
)), "salidas/efecto-y-welch.csv",
  c("n", "grupos", "f", "gl_entre", "gl_dentro", "p", "critico", "significativo",
    "eta_cuadrado", "omega_cuadrado", "welch_f", "welch_gl2", "welch_p",
    "levene_w", "levene_p"))

dos <- anova$dos_factores
filas_dos <- list()
if (!is.null(dos)) {
  for (f in dos$tipo_iii) {
    f$significativo <- f$p < 1 - parametros$confianza
    filas_dos[[length(filas_dos) + 1]] <- f
  }
  filas_dos[[length(filas_dos) + 1]] <- list(
    termino = "Error", sc = dos$sc_residual, gl = dos$gl_error, cm = dos$cm_error,
    f = NULL, p = NULL, significativo = NULL)
}
escribir_csv(filas_dos, "salidas/anova-dos-factores.csv",
             c("termino", "sc", "gl", "cm", "f", "p", "significativo"))

escribir_csv(anova$tipos, "salidas/tipos-de-suma.csv",
             c("termino", "sc_tipo_iii", "p_tipo_iii", "sc_tipo_i_primero",
               "p_tipo_i_primero", "sc_tipo_i_segundo", "p_tipo_i_segundo",
               "cambia_la_conclusion"))

escribir_csv(anova$efectos_simples, "salidas/efectos-simples.csv",
             c("nivel", "n", "gl", "f", "p", "significativo", "entre", "diferencia",
               "inferior", "superior"))

escribir_csv(post_hoc$pares, "salidas/post-hoc.csv",
             c("a", "b", "metodo", "diferencia", "error_estandar", "estadistico",
               "p_sin_corregir", "p", "inferior", "superior", "significativa",
               "cambia_entre_correcciones"))

avisos <- c(supuestos$avisos, anova$avisos, post_hoc$avisos)
escribir_csv(avisos, "salidas/avisos.csv", c("donde", "aviso"))

escribir_texto(redactar(parametros, supuestos, anova, post_hoc, celdas, length(datos)),
               "salidas/anova.md")

interaccion <- if (is.null(dos)) NULL else dos$tipo_iii[[3]]
cuantos <- function(metodo, campo) {
  sum(vapply(post_hoc$pares, function(f) f$metodo == metodo && isTRUE(f[[campo]]),
             logical(1)))
}
con_tukey <- cuantos("tukey", "significativa")
sin_corregir <- cuantos("sin corregir", "significativa")
discrepan <- cuantos("tukey", "cambia_entre_correcciones")
escribir_csv(list(
  list(clave = "casos", valor = as.integer(length(datos))),
  list(clave = "usados", valor = uf$n),
  list(clave = "celdas", valor = as.integer(length(celdas))),
  list(clave = "f_un_factor", valor = uf$f),
  list(clave = "p_un_factor", valor = uf$p),
  list(clave = "eta_cuadrado", valor = uf$eta_cuadrado),
  list(clave = "p_interaccion", valor = if (is.null(interaccion)) NULL else interaccion$p),
  list(clave = "interaccion_significativa", valor = anova$interaccion_significativa),
  list(clave = "efectos_simples_significativos",
       valor = as.integer(sum(vapply(anova$efectos_simples,
                                     function(e) isTRUE(e$significativo), logical(1))))),
  list(clave = "comparaciones", valor = as.integer(post_hoc$cuantas)),
  list(clave = "significativas_sin_corregir", valor = as.integer(sin_corregir)),
  list(clave = "significativas_con_tukey", valor = as.integer(con_tukey)),
  list(clave = "pares_donde_discrepan_los_metodos", valor = as.integer(discrepan)),
  list(clave = "avisos", valor = as.integer(length(avisos)))
), "salidas/resumen.csv", c("clave", "valor"))

cat("Listo. Salidas en salidas/:\n")
cat("  celdas.csv, supuestos.csv, anova-un-factor.csv, efecto-y-welch.csv,\n")
cat("  anova-dos-factores.csv, tipos-de-suma.csv, efectos-simples.csv,\n")
cat("  post-hoc.csv, avisos.csv, resumen.csv y anova.md\n")
if (descartados > 0) {
  cat(sprintf("  Se descartaron %d casos sin respuesta o sin factor.\n", descartados))
}
if (isTRUE(anova$interaccion_significativa)) {
  cat("  Ojo: la interacción es significativa. Los efectos principales no se leen solos.\n")
}
if (discrepan > 0) {
  cuantas <- if (discrepan == 1) "1 comparación" else paste(discrepan, "comparaciones")
  cat(sprintf("  Ojo: en %s los cuatro métodos no coinciden.\n", cuantas))
}

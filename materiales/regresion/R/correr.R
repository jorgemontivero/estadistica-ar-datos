# Ajusta los modelos, los diagnostica y escribe el informe.
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
source("R/01-lineal.R")
source("R/02-diagnostico.R")
source("R/03-logistica.R")
source("R/04-redaccion.R")

datos <- leer_csv(DATOS)
parametros <- leer_parametros(PARAMETROS)

modelo <- calcular_lineal(datos, parametros)
diagnostico <- calcular_diagnostico(modelo, parametros)
logistica <- calcular_logistica(datos, parametros)

escribir_csv(modelo$coeficientes, "salidas/coeficientes.csv",
             c("termino", "estimacion", "error_estandar", "t", "gl", "p", "inferior",
               "superior", "significativo", "vif"))

escribir_csv(list(list(
  n = modelo$n, predictores = as.integer(modelo$k - 1), gl = modelo$gl,
  r2 = modelo$r2, r2_ajustado = modelo$r2_ajustado, ee_residual = modelo$ee_residual,
  sc_modelo = modelo$sc_modelo, sc_residual = modelo$sc_residual, sc_total = modelo$sc_total,
  f = modelo$f, gl_modelo = modelo$gl_modelo, p_f = modelo$p_f,
  descartados = modelo$descartados)), "salidas/ajuste.csv",
  c("n", "predictores", "gl", "r2", "r2_ajustado", "ee_residual", "sc_modelo", "sc_residual",
    "sc_total", "f", "gl_modelo", "p_f", "descartados"))

s <- diagnostico$shapiro
bp <- diagnostico$breusch_pagan
cooks <- vapply(diagnostico$influencia, function(f) f$cook, numeric(1))
escribir_csv(list(list(
  shapiro_w = s$w, shapiro_p = s$p, residuos_normales = s$normales,
  breusch_pagan_lm = if (is.null(bp)) NULL else bp$lm,
  breusch_pagan_gl = if (is.null(bp)) NULL else bp$gl,
  breusch_pagan_p = if (is.null(bp)) NULL else bp$p,
  varianza_constante = if (is.null(bp)) NULL else bp$p >= 1 - parametros$confianza,
  durbin_watson = diagnostico$durbin_watson,
  palanca_umbral = diagnostico$palanca_umbral,
  casos_palanca_alta = as.integer(sum(vapply(diagnostico$influencia,
                                             function(f) isTRUE(f$palanca_alta), logical(1)))),
  casos_residuo_grande = as.integer(sum(vapply(diagnostico$influencia,
                                               function(f) isTRUE(f$residuo_grande), logical(1)))),
  cook_maximo = max(cooks))), "salidas/diagnostico.csv",
  c("shapiro_w", "shapiro_p", "residuos_normales", "breusch_pagan_lm", "breusch_pagan_gl",
    "breusch_pagan_p", "varianza_constante", "durbin_watson", "palanca_umbral",
    "casos_palanca_alta", "casos_residuo_grande", "cook_maximo"))

escribir_csv(diagnostico$influencia, "salidas/influencia.csv",
             c("caso", "observado", "ajustado", "residuo", "estandarizado", "palanca", "cook",
               "palanca_alta", "residuo_grande"))

reajuste <- diagnostico$reajuste
escribir_csv(if (is.null(reajuste)) list() else reajuste$comparacion,
             "salidas/sin-el-influyente.csv",
             c("termino", "con_el_caso", "p_con", "sin_el_caso", "p_sin", "cambio_relativo",
               "cambia_la_conclusion", "cambia_de_signo"))

escribir_csv(if (is.null(logistica)) list() else logistica$coeficientes,
             "salidas/logistica.csv",
             c("termino", "estimacion", "error_estandar", "z", "p", "odds_ratio",
               "or_inferior", "or_superior", "significativo"))

escribir_csv(if (is.null(logistica)) list() else list(logistica$clasificacion),
             "salidas/clasificacion.csv",
             c("corte", "verdaderos_positivos", "falsos_positivos", "verdaderos_negativos",
               "falsos_negativos", "sensibilidad", "especificidad", "exactitud",
               "exactitud_trivial", "auc"))

avisos <- c(diagnostico$avisos, if (is.null(logistica)) list() else logistica$avisos)
escribir_csv(avisos, "salidas/avisos.csv", c("donde", "aviso"))

escribir_texto(redactar(parametros, modelo, diagnostico, logistica, length(datos)),
               "salidas/regresion.md")

cambian <- if (is.null(reajuste)) 0L else reajuste$cuantos_cambian
significativos <- sum(vapply(modelo$coeficientes,
                             function(f) f$termino != "(ordenada)" && isTRUE(f$significativo),
                             logical(1)))
resumen <- list(
  list(clave = "casos", valor = as.integer(length(datos))),
  list(clave = "usados_en_el_ajuste", valor = modelo$n),
  list(clave = "predictores", valor = as.integer(modelo$k - 1)),
  list(clave = "r2", valor = modelo$r2),
  list(clave = "coeficientes_significativos", valor = as.integer(significativos)),
  list(clave = "caso_mas_influyente", valor = if (is.null(reajuste)) 0L else reajuste$caso),
  list(clave = "cook_maximo", valor = max(cooks)),
  list(clave = "coeficientes_que_cambian_sin_el", valor = as.integer(cambian)),
  list(clave = "vueltas_del_irls",
       valor = if (is.null(logistica)) 0L else logistica$modelo$vueltas),
  list(clave = "auc", valor = if (is.null(logistica)) NULL else logistica$clasificacion$auc),
  list(clave = "avisos", valor = as.integer(length(avisos)))
)
escribir_csv(resumen, "salidas/resumen.csv", c("clave", "valor"))

cat("Listo. Salidas en salidas/:\n")
cat("  coeficientes.csv, ajuste.csv, diagnostico.csv, influencia.csv,\n")
cat("  sin-el-influyente.csv, logistica.csv, clasificacion.csv,\n")
cat("  avisos.csv, resumen.csv y regresion.md\n")
if (cambian > 0) {
  cuantos <- if (cambian == 1) "1 coeficiente" else paste0(cambian, " coeficientes")
  cat(sprintf("  Ojo: sacar el caso %d cambia la conclusión de %s.\n", reajuste$caso, cuantos))
}

# Corre las pruebas no paramétricas y el bootstrap, y escribe el informe.
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
source("R/azar.R")
source("R/01-apareadas.R")
source("R/02-independientes.R")
source("R/03-bootstrap.R")
source("R/04-redaccion.R")

datos <- leer_csv(DATOS)
parametros <- leer_parametros(PARAMETROS)

apareadas <- NULL
if (parametros$antes != "" && parametros$despues != "") {
  pares <- pares_completos(datos, parametros$antes, parametros$despues)
  apareadas <- calcular_apareadas(datos, parametros, pares)
}

grupos <- list()
if (parametros$respuesta != "" && parametros$grupo != "") {
  grupos <- por_grupo(datos, parametros$respuesta, parametros$grupo)$grupos
}
por_factor_ <- list()
if (parametros$respuesta != "" && parametros$factor != "") {
  por_factor_ <- por_grupo(datos, parametros$respuesta, parametros$factor)$grupos
}

independientes <- calcular_independientes(datos, parametros, grupos, por_factor_)

valores <- unlist(grupos, use.names = FALSE)
if (is.null(valores)) valores <- numeric(0)
bootstrap <- calcular_bootstrap(parametros, valores, grupos)

# ------------------------------------------------------------------ salidas
w <- if (is.null(apareadas)) NULL else apareadas$wilcoxon
s <- if (is.null(apareadas)) NULL else apareadas$signos

# Las dos pruebas apareadas y las dos que NO corresponden, en la misma tabla:
# el punto del paso es que se puedan mirar juntas.
filas_apareadas <- list()
if (!is.null(w)) {
  filas_apareadas[[length(filas_apareadas) + 1]] <- list(
    prueba = "Wilcoxon de rangos con signo", n = w$n, estadistico = w$w, z = w$z, p = w$p,
    significativa = w$significativa, desplazamiento = w$hodges_lehmann,
    detalle = paste0(w$sin_cambio, " pares sin cambio"))
}
if (!is.null(s)) {
  filas_apareadas[[length(filas_apareadas) + 1]] <- list(
    prueba = "Prueba de los signos", n = s$n, estadistico = s$subieron, z = NULL, p = s$p,
    significativa = s$significativa, desplazamiento = NULL,
    detalle = paste0(s$subieron, " suben y ", s$bajaron, " bajan"))
}
if (!is.null(apareadas)) {
  mal <- apareadas$como_independientes
  filas_apareadas[[length(filas_apareadas) + 1]] <- list(
    prueba = "Mann-Whitney, tirando el apareamiento", n = apareadas$n_pares,
    estadistico = NULL, z = NULL, p = mal$mann_whitney_p,
    significativa = if (is.null(mal$mann_whitney_p)) NULL else
      mal$mann_whitney_p < 1 - parametros$confianza,
    desplazamiento = NULL, detalle = "No corresponde: está para comparar")
  filas_apareadas[[length(filas_apareadas) + 1]] <- list(
    prueba = "t de Welch, tirando el apareamiento", n = apareadas$n_pares,
    estadistico = NULL, z = NULL, p = mal$t_de_welch_p,
    significativa = mal$t_de_welch_p < 1 - parametros$confianza,
    desplazamiento = NULL, detalle = "No corresponde: está para comparar")
}
escribir_csv(filas_apareadas, "salidas/apareadas.csv",
             c("prueba", "n", "estadistico", "z", "p", "significativa", "desplazamiento",
               "detalle"))

escribir_csv(if (!is.null(apareadas) && !is.null(w)) list(list(
  pares = apareadas$n_pares, descartados = apareadas$descartados,
  mediana_del_cambio = w$mediana_del_cambio, media_del_cambio = w$media_del_cambio,
  desvio_del_cambio = w$desvio_del_cambio, sin_cambio = w$sin_cambio,
  proporcion_que_sube = if (is.null(s)) NULL else s$proporcion_que_sube,
  cambia_la_conclusion = apareadas$cambia_la_conclusion)) else list(),
  "salidas/el-cambio.csv",
  c("pares", "descartados", "mediana_del_cambio", "media_del_cambio", "desvio_del_cambio",
    "sin_cambio", "proporcion_que_sube", "cambia_la_conclusion"))

u <- independientes$mann_whitney
t <- independientes$t_de_welch
escribir_csv(if (!is.null(u)) list(list(
  n_a = u$n_a, n_b = u$n_b, u = u$u, z = u$z, p = u$p, significativa = u$significativa,
  probabilidad_de_superar = u$probabilidad_de_superar, hodges_lehmann = u$hodges_lehmann,
  mediana_a = u$mediana_a, mediana_b = u$mediana_b,
  t_de_welch = if (is.null(t)) NULL else t$t,
  p_de_welch = if (is.null(t)) NULL else t$p,
  coinciden = if (is.null(t)) NULL else u$significativa == t$significativa)) else list(),
  "salidas/mann-whitney.csv",
  c("n_a", "n_b", "u", "z", "p", "significativa", "probabilidad_de_superar",
    "hodges_lehmann", "mediana_a", "mediana_b", "t_de_welch", "p_de_welch", "coinciden"))

filas_kw <- list()
for (par in list(list("grupo", independientes$kruskal),
                 list("factor", independientes$kruskal_factor))) {
  kw <- par[[2]]
  if (is.null(kw)) next
  for (g in kw$grupos) {
    filas_kw[[length(filas_kw) + 1]] <- c(list(sobre = par[[1]]), g)
  }
}
escribir_csv(filas_kw, "salidas/kruskal-grupos.csv",
             c("sobre", "grupo", "n", "mediana", "suma_de_rangos", "rango_promedio"))

filas_h <- list()
for (par in list(list("grupo", independientes$kruskal),
                 list("factor", independientes$kruskal_factor))) {
  kw <- par[[2]]
  if (is.null(kw)) next
  filas_h[[length(filas_h) + 1]] <- list(
    sobre = par[[1]], h = kw$h, h_sin_corregir = kw$h_sin_corregir, gl = kw$gl, p = kw$p,
    significativa = kw$significativa, epsilon_cuadrado = kw$epsilon_cuadrado,
    n = kw$n, grupos = kw$k)
}
escribir_csv(filas_h, "salidas/kruskal-wallis.csv",
             c("sobre", "h", "h_sin_corregir", "gl", "p", "significativa",
               "epsilon_cuadrado", "n", "grupos"))

escribir_csv(bootstrap$intervalos, "salidas/bootstrap.csv",
             c("estadistico", "observado", "error_estandar", "sesgo",
               "percentil_inferior", "percentil_superior", "basico_inferior",
               "basico_superior", "bca_inferior", "bca_superior", "z0", "aceleracion",
               "excluye_el_cero"))

p <- bootstrap$permutacion
escribir_csv(if (!is.null(p)) list(list(
  estadistico = "diferencia de medianas", observada = p$observada, replicas = p$replicas,
  mas_extremas = p$extremas, p = p$p, significativa = p$significativa)) else list(),
  "salidas/permutacion.csv",
  c("estadistico", "observada", "replicas", "mas_extremas", "p", "significativa"))

avisos <- c(if (is.null(apareadas)) list() else apareadas$avisos,
            independientes$avisos, bootstrap$avisos)
escribir_csv(avisos, "salidas/avisos.csv", c("donde", "aviso"))

escribir_texto(redactar(parametros, apareadas, independientes, bootstrap, length(datos)),
               "salidas/no-parametricas.md")

escribir_csv(list(
  list(clave = "casos", valor = as.integer(length(datos))),
  list(clave = "pares_completos",
       valor = if (is.null(apareadas)) 0L else apareadas$n_pares),
  list(clave = "p_wilcoxon", valor = if (is.null(w)) NULL else w$p),
  list(clave = "p_signos", valor = if (is.null(s)) NULL else s$p),
  list(clave = "p_sin_aparear",
       valor = if (is.null(apareadas)) NULL else apareadas$como_independientes$mann_whitney_p),
  list(clave = "el_apareamiento_cambia_la_conclusion",
       valor = if (is.null(apareadas)) NULL else apareadas$cambia_la_conclusion),
  list(clave = "p_mann_whitney", valor = if (is.null(u)) NULL else u$p),
  list(clave = "probabilidad_de_superar",
       valor = if (is.null(u)) NULL else u$probabilidad_de_superar),
  list(clave = "p_t_de_welch", valor = if (is.null(t)) NULL else t$p),
  list(clave = "replicas", valor = bootstrap$replicas),
  list(clave = "p_permutacion", valor = if (is.null(p)) NULL else p$p),
  list(clave = "avisos", valor = as.integer(length(avisos)))
), "salidas/resumen.csv", c("clave", "valor"))

cat("Listo. Salidas en salidas/:\n")
cat("  apareadas.csv, el-cambio.csv, mann-whitney.csv, kruskal-wallis.csv,\n")
cat("  kruskal-grupos.csv, bootstrap.csv, permutacion.csv, avisos.csv,\n")
cat("  resumen.csv y no-parametricas.md\n")
if (!is.null(apareadas) && isTRUE(apareadas$cambia_la_conclusion)) {
  cat("  Ojo: tirar el apareamiento cambia la conclusión.\n")
}
if (!is.null(u) && !is.null(t) && u$significativa != t$significativa) {
  cat("  Ojo: Mann-Whitney y la t de Welch no coinciden.\n")
}

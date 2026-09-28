# Selecciona la muestra, arma los ponderadores, estima y escribe el informe.
#
#     source("R/correr.R")
#
# Desde la carpeta del proyecto, no desde R/.

DATOS <- "datos/marco.csv"
VARIABLES <- "datos/variables.csv"
PARAMETROS <- "datos/parametros.csv"

for (archivo in c(DATOS, VARIABLES, PARAMETROS)) {
  if (!file.exists(archivo)) {
    stop(paste0("No encuentro ", archivo, ". ¿Estás parado en la carpeta del proyecto?"))
  }
}

source("R/comun.R")
source("R/01-seleccion.R")
source("R/02-ponderadores.R")
source("R/03-estimacion.R")
source("R/04-redaccion.R")

datos <- leer_csv(DATOS)
parametros <- leer_parametros(PARAMETROS)
poblacion <- length(datos)
valores <- suppressWarnings(as.numeric(limpiar_texto(columna(datos, parametros$variable))))

seleccion <- calcular_seleccion(datos, parametros, valores)

etiquetas_estrato <- limpiar_texto(columna(datos, parametros$estrato))
etiquetas_cong <- limpiar_texto(columna(datos, parametros$conglomerado))
por_estrato_marco <- indices_por(datos, parametros$estrato)

# La fracción de primera etapa, por estrato.
#
# Sin estratos todo entra en una sola celda, porque es lo que corresponde a un
# diseño que no estratificó: la corrección por población finita es entonces n/N
# sobre el marco entero.
fracciones_de <- function(sel, con_conglomerados, estratificado = TRUE) {
  filas <- vapply(sel, function(s) s$fila, numeric(1))
  if (!estratificado) {
    if (con_conglomerados) {
      en_el_marco <- length(unique(etiquetas_cong))
      elegidos <- length(unique(vapply(sel, function(s) s$conglomerado, character(1))))
    } else {
      en_el_marco <- length(datos)
      elegidos <- length(sel)
    }
    salida <- list()
    salida[["—"]] <- if (en_el_marco > 0) elegidos / en_el_marco else 0
    return(salida)
  }
  salida <- list()
  for (h in names(por_estrato_marco)) {
    indices <- por_estrato_marco[[h]]
    cuales <- which(etiquetas_estrato[filas] == h)
    if (con_conglomerados) {
      en_el_marco <- length(unique(etiquetas_cong[indices]))
      elegidos <- length(unique(vapply(sel[cuales], function(s) s$conglomerado,
                                       character(1))))
    } else {
      en_el_marco <- length(indices)
      elegidos <- length(cuales)
    }
    salida[[h]] <- if (en_el_marco > 0) elegidos / en_el_marco else 0
  }
  salida
}

CON_CONGLOMERADOS <- c("bietápico")
# Los diseños que usaron los estratos al SELECCIONAR. Un aleatorio simple y un
# sistemático no los usaron, y estimarles la varianza como si lo hubieran hecho
# les regalaría una precisión que no tienen.
ESTRATIFICADOS <- c("estratificado proporcional", "estratificado de Neyman", "bietápico")

filas_disenos <- list()
estimaciones <- list()
for (nombre in names(seleccion$disenos)) {
  sel <- seleccion$disenos[[nombre]]
  con_cong <- nombre %in% CON_CONGLOMERADOS
  estratificado <- nombre %in% ESTRATIFICADOS
  fracciones <- fracciones_de(sel, con_cong, estratificado)
  pesos <- pesos_de_diseno(sel)
  w <- vapply(pesos, function(p) p$peso, numeric(1))
  filas_disenos[[length(filas_disenos) + 1]] <- list(
    diseno = nombre, n = as.integer(length(sel)),
    unidades_primarias = as.integer(
      if (con_cong) length(unique(vapply(sel, function(s) s$conglomerado, character(1))))
      else length(sel)),
    suma_de_pesos = sum(w), peso_minimo = min(w), peso_maximo = max(w),
    sin_reemplazo = "Sí")
  estimaciones <- c(estimaciones,
                    calcular_estimacion(datos, parametros, pesos, fracciones, nombre,
                                        estratificado))
}

# El diseño principal —el bietápico— es el que lleva el resto del proyecto:
# ponderadores ajustados, estimación por estrato y simulación de cobertura.
principal <- seleccion$disenos[["bietápico"]]
fracciones_principal <- fracciones_de(principal, TRUE, TRUE)

# Quién contestó. Se sortea con el generador de R y una semilla derivada, así
# la no respuesta también es reproducible.
tasa <- parametros$tasa_de_no_respuesta
respondieron <- NULL
if (tasa > 0) {
  set.seed(parametros$semilla + 1000)
  respondieron <- runif(length(principal)) >= tasa
}
ponderadores <- calcular_ponderadores(datos, parametros, principal, respondieron)

por_estrato <- estimar_por_estrato(datos, parametros, ponderadores$pesos,
                                   fracciones_principal)

seleccionar_otra_vez <- function(semilla) {
  r <- bietapico(datos, semilla, parametros$estrato, parametros$conglomerado,
                 parametros$conglomerados_por_estrato,
                 parametros$hogares_por_conglomerado)
  list(muestra = r$muestra, fracciones = fracciones_de(r$muestra, TRUE, TRUE))
}

cobertura <- calcular_cobertura(datos, parametros, seleccionar_otra_vez,
                                parametros$replicas_de_cobertura)

# ------------------------------------------------------------------ salidas
escribir_csv(filas_disenos, "salidas/disenos.csv",
             c("diseno", "n", "unidades_primarias", "suma_de_pesos", "peso_minimo",
               "peso_maximo", "sin_reemplazo"))

identificadores <- columna(datos, "hogar")
escribir_csv(lapply(ponderadores$pesos, function(p) {
  list(hogar = identificadores[p$fila],
       estrato = etiquetas_estrato[p$fila],
       conglomerado = p$conglomerado,
       probabilidad = p$probabilidad, peso = p$peso)
}), "salidas/muestra.csv",
  c("hogar", "estrato", "conglomerado", "probabilidad", "peso"))

escribir_csv(list(
  c(list(cuando = "pesos de diseño"), ponderadores$antes),
  c(list(cuando = "ajustados por no respuesta"), ponderadores$tras_no_respuesta),
  c(list(cuando = "post-estratificados"), ponderadores$despues)),
  "salidas/ponderadores.csv",
  c("cuando", "n", "suma", "poblacion", "diferencia_con_la_poblacion", "minimo",
    "maximo", "media", "coeficiente_de_variacion", "razon_maximo_minimo",
    "deff_de_kish", "n_efectivo_de_kish"))

escribir_csv(ponderadores$calibracion, "salidas/calibracion.csv",
             c("celda", "en_el_marco", "estimado_antes", "factor"))

escribir_csv(estimaciones, "salidas/estimaciones.csv",
             c("diseno", "variable", "que", "verdadero", "estimacion", "error_estandar",
               "inferior", "superior", "gl", "contiene_al_verdadero", "ee_ingenuo",
               "inferior_ingenuo", "superior_ingenuo", "contiene_ingenuo", "deff",
               "n_efectivo", "error_relativo"))

escribir_csv(por_estrato, "salidas/por-estrato.csv",
             c("estrato", "n", "unidades_primarias", "verdadero", "estimacion",
               "error_estandar", "inferior", "superior", "contiene_al_verdadero",
               "error_relativo_del_ee"))

escribir_csv(if (is.null(cobertura)) list() else list(cobertura), "salidas/cobertura.csv",
             c("replicas", "verdadero", "nominal", "cobertura_del_diseno",
               "cobertura_ingenua", "ancho_medio_del_diseno", "ancho_medio_ingenuo"))

avisos <- ponderadores$avisos
del_principal <- Filter(function(e) e$diseno == "bietápico", estimaciones)
enganosas <- Filter(function(e) !isTRUE(e$contiene_ingenuo) && isTRUE(e$contiene_al_verdadero),
                    del_principal)
if (length(enganosas) > 0) {
  cuales <- paste(vapply(enganosas, function(e) paste0("«", e$variable, "»"), character(1)),
                  collapse = ", ")
  avisos[[length(avisos) + 1]] <- list(
    donde = "estimación",
    aviso = paste0("En ", cuales, " el intervalo que ignora el diseño no contiene al valor ",
                   "verdadero y el que lo respeta sí. Es la misma muestra: lo único que ",
                   "cambia es la fórmula del error estándar."))
}
if (length(Filter(function(e) e$deff > 2, del_principal)) > 0) {
  avisos[[length(avisos) + 1]] <- list(
    donde = "estimación",
    aviso = paste0("Hay estimaciones con un efecto de diseño mayor que 2: la muestra vale ",
                   "menos de la mitad de lo que su tamaño sugiere. Con conglomerados eso es ",
                   "lo esperable, y es el precio de no tener que recorrer la provincia ",
                   "entera."))
}
if (length(Filter(function(e) e$diseno == "sistemático", estimaciones)) > 0) {
  avisos[[length(avisos) + 1]] <- list(
    donde = "estimación",
    aviso = paste0("El error estándar del sistemático está calculado como si fuera un ",
                   "aleatorio simple, porque para una muestra sistemática **no existe** un ",
                   "estimador insesgado de la varianza con una sola muestra. Es la ",
                   "convención habitual y suele ser conservadora, pero es una convención, ",
                   "no un cálculo."))
}
if (!is.null(cobertura) && cobertura$cobertura_ingenua < cobertura$nominal - 0.05) {
  avisos[[length(avisos) + 1]] <- list(
    donde = "cobertura",
    aviso = paste0("Sobre ", cobertura$replicas, " muestras, el intervalo que ignora el ",
                   "diseño cubrió el valor verdadero el ",
                   gsub(".", ",", sprintf("%.1f", cobertura$cobertura_ingenua * 100),
                        fixed = TRUE),
                   " % de las veces en vez del ",
                   gsub(".", ",", sprintf("%.0f", cobertura$nominal * 100), fixed = TRUE),
                   " % que promete. No es mala suerte de una muestra: es la fórmula."))
}
chicos <- Filter(function(e) e$unidades_primarias < 10, por_estrato)
if (length(chicos) > 0) {
  avisos[[length(avisos) + 1]] <- list(
    donde = "estimación",
    aviso = paste0("Hay ", length(chicos), " estratos con menos de diez conglomerados en la ",
                   "muestra. El error estándar de esas estimaciones está calculado con muy ",
                   "pocos grados de libertad y es poco confiable: una muestra que alcanza ",
                   "para el total puede no alcanzar para ninguna de sus partes."))
}
escribir_csv(avisos, "salidas/avisos.csv", c("donde", "aviso"))

escribir_texto(redactar(parametros, seleccion, ponderadores, estimaciones, por_estrato,
                        cobertura, poblacion), "salidas/muestreo.md")

principal_media <- NULL
for (e in del_principal) if (e$variable == parametros$variable) principal_media <- e
escribir_csv(list(
  list(clave = "poblacion", valor = as.integer(poblacion)),
  list(clave = "muestra", valor = seleccion$n),
  list(clave = "contestaron", valor = ponderadores$despues$n),
  list(clave = "conglomerados_en_la_muestra",
       valor = as.integer(length(unique(vapply(principal, function(s) s$conglomerado,
                                               character(1)))))),
  list(clave = "suma_de_pesos", valor = ponderadores$despues$suma),
  list(clave = "deff_de_kish", valor = ponderadores$despues$deff_de_kish),
  list(clave = "verdadero", valor = principal_media$verdadero),
  list(clave = "estimacion", valor = principal_media$estimacion),
  list(clave = "ee_del_diseno", valor = principal_media$error_estandar),
  list(clave = "ee_ingenuo", valor = principal_media$ee_ingenuo),
  list(clave = "deff", valor = principal_media$deff),
  list(clave = "n_efectivo", valor = principal_media$n_efectivo),
  list(clave = "el_ingenuo_contiene_al_verdadero", valor = principal_media$contiene_ingenuo),
  list(clave = "cobertura_del_diseno",
       valor = if (is.null(cobertura)) NULL else cobertura$cobertura_del_diseno),
  list(clave = "cobertura_ingenua",
       valor = if (is.null(cobertura)) NULL else cobertura$cobertura_ingenua),
  list(clave = "avisos", valor = as.integer(length(avisos)))
), "salidas/resumen.csv", c("clave", "valor"))

cat("Listo. Salidas en salidas/:\n")
cat("  disenos.csv, muestra.csv, ponderadores.csv, calibracion.csv,\n")
cat("  estimaciones.csv, por-estrato.csv, cobertura.csv, avisos.csv,\n")
cat("  resumen.csv y muestreo.md\n")
if (length(enganosas) > 0) {
  cat("  Ojo: el intervalo que ignora el diseño no contiene al valor verdadero.\n")
}
if (!is.null(cobertura)) {
  cat(sprintf("  Cobertura: %.1f %% con el diseño, %.1f %% ignorándolo.\n",
              cobertura$cobertura_del_diseno * 100, cobertura$cobertura_ingenua * 100))
}

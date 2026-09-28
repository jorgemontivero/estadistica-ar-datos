# Lee el archivo del INDEC, calcula las tasas y los ingresos, y escribe el informe.
#
#     source("R/correr.R")
#
# Desde la carpeta del proyecto, no desde R/.

PARAMETROS <- "datos/parametros.csv"
if (!file.exists(PARAMETROS)) {
  stop(paste0("No encuentro ", PARAMETROS,
              ". ¿Estás parado en la carpeta del proyecto?"), call. = FALSE)
}

source("R/comun.R")
source("R/01-leer.R")
source("R/02-tasas.R")
source("R/03-ingresos.R")
source("R/04-redaccion.R")

parametros <- leer_parametros(PARAMETROS)
crudo <- leer_microdatos(parametros$archivo, parametros$separador, parametros$codificacion)
base <- leer(crudo$columnas, crudo$datos, parametros)
registros <- base$registros

# Los cortes con los que se abre cada tabla. El orden de las etiquetas es el del
# corte y no el del alfabeto: los tramos de edad van de menor a mayor y las
# regiones en el orden en que el INDEC las numera.
CORTES <- list(
  list(corte = "Sexo", etiquetas = c("Varón", "Mujer"),
       de_cual = function(r) etiquetas_de(SEXO, r$sexo)),
  list(corte = "Tramo de edad",
       etiquetas = vapply(TRAMOS, function(t) t$etiqueta, character(1)),
       de_cual = function(r) {
         v <- tramo_de(r$edad)
         v[is.na(v)] <- "Sin dato"
         v
       }),
  list(corte = "Región",
       etiquetas = unname(REGIONES[c("1", "40", "41", "42", "43", "44")]),
       de_cual = function(r) etiquetas_de(REGIONES, r$region))
)

CORTES_DE_INGRESO <- c(CORTES, list(
  list(corte = "Nivel educativo",
       etiquetas = unname(NIVEL[c("7", "1", "2", "3", "4", "5", "6")]),
       de_cual = function(r) etiquetas_de(NIVEL, r$nivel_ed)),
  list(corte = "Categoría ocupacional",
       etiquetas = unname(CATEGORIA[c("1", "2", "3", "4")]),
       de_cual = function(r) etiquetas_de(CATEGORIA, r$cat_ocup))
))

# Los aglomerados son los estratos y los hogares las unidades primarias. Se
# agrupan una sola vez: todas las estimaciones del proyecto usan los mismos.
conglomerados <- preparar_conglomerados(registros$aglomerado, registros$hogar)

filas_tasas <- calcular(registros, conglomerados, parametros)
filas_grupo <- por_grupo(registros, conglomerados, parametros, CORTES)
identidad_ <- identidad(filas_tasas)

contraste_ <- contraste(registros, base$ponderador_de_ingreso, parametros$ponderador)
distribucion_ <- distribucion(registros, conglomerados, parametros)
resumen_ingresos <- distribucion_$resumen
deciles <- distribucion_$grupos
ingresos_grupo <- por_grupo_ingreso(registros, CORTES_DE_INGRESO)
informal <- informalidad(registros, conglomerados, parametros, CORTES)

avisos <- c(base$avisos,
            avisos_de(filas_tasas, identidad_, registros),
            avisos_de_ingresos(contraste_, deciles))

# ------------------------------------------------------------------ salidas
escribir_csv(base$poblacion, "salidas/poblacion.csv",
             c("condicion", "codigo", "n", "poblacion", "porcentaje"))

escribir_csv(filas_tasas, "salidas/tasas.csv",
             c("tasa", "numerador", "denominador", "poblacion_numerador",
               "poblacion_denominador", "n_denominador", "valor", "error_estandar",
               "inferior", "superior", "gl", "deff", "n_efectivo", "sin_ponderar",
               "diferencia_con_la_ponderada"))

escribir_csv(filas_grupo, "salidas/tasas-por-grupo.csv",
             c("corte", "grupo", "tasa", "n_denominador", "poblacion_denominador",
               "valor", "error_estandar", "inferior", "superior", "sin_ponderar"))

escribir_csv(resumen_ingresos, "salidas/ingresos.csv", c("estadistico", "valor"))

escribir_csv(deciles, "salidas/deciles.csv",
             c("decil", "corte_superior", "n", "poblacion", "ingreso_medio",
               "participacion"))

escribir_csv(contraste_, "salidas/ponderador-e-ingreso.csv",
             c("caso", "ponderador", "que_hace_con_el_menos_nueve",
               "que_hace_con_el_cero", "n", "poblacion", "media", "mediana",
               "diferencia", "diferencia_relativa"))

escribir_csv(ingresos_grupo, "salidas/ingresos-por-grupo.csv",
             c("corte", "grupo", "n", "poblacion", "media", "mediana",
               "razon_con_el_total"))

escribir_csv(informal, "salidas/informalidad.csv",
             c("corte", "grupo", "n_asalariados", "asalariados", "sin_descuento",
               "tasa", "error_estandar", "inferior", "superior"))

escribir_csv(avisos, "salidas/avisos.csv", c("donde", "aviso"))

escribir_texto(redactar(parametros, base, filas_tasas, identidad_, contraste_,
                        resumen_ingresos, deciles, ingresos_grupo, informal, avisos),
               "salidas/eph.md")

tasa_de <- function(nombre) {
  for (t in filas_tasas) if (t$tasa == nombre) return(t$valor)
  NA_real_
}

valor_ingreso <- list()
for (f in resumen_ingresos) valor_ingreso[[f$estadistico]] <- f$valor
correcto <- por_nombre(contraste_, "caso", "Lo correcto")
solo_peso <- por_nombre(contraste_, "caso", "Con el ponderador general")
los_dos <- por_nombre(contraste_, "caso",
                      "Con el ponderador general y los que no declaran adentro")
total_informal <- por_nombre(informal, "corte", "Total")
o_na <- function(x) if (is.null(x)) NA_real_ else x

escribir_csv(list(
  list(clave = "periodo", valor = base$periodo),
  list(clave = "registros", valor = base$n),
  list(clave = "hogares", valor = base$hogares),
  list(clave = "aglomerados", valor = base$aglomerados),
  list(clave = "columnas_del_archivo", valor = base$columnas_del_archivo),
  list(clave = "poblacion", valor = base$peso_total),
  list(clave = "tasa_de_actividad", valor = tasa_de("actividad")),
  list(clave = "tasa_de_empleo", valor = tasa_de("empleo")),
  list(clave = "tasa_de_desocupacion", valor = tasa_de("desocupación")),
  list(clave = "tasa_de_subocupacion", valor = tasa_de("subocupación")),
  list(clave = "residuo_de_la_identidad",
       valor = if (!is.null(identidad_)) identidad_$residuo else NA_real_),
  list(clave = "ponderador_de_ingreso", valor = base$ponderador_de_ingreso),
  list(clave = "el_archivo_trae_ponderador_de_ingreso",
       valor = base$hay_ponderador_de_ingreso),
  list(clave = "ingreso_medio", valor = o_na(valor_ingreso[["media"]])),
  list(clave = "ingreso_mediano", valor = o_na(valor_ingreso[["mediana"]])),
  list(clave = "ingreso_medio_con_el_ponderador_general",
       valor = if (!is.null(solo_peso)) solo_peso$media else NA_real_),
  list(clave = "ingreso_medio_con_los_dos_descuidos",
       valor = if (!is.null(los_dos)) los_dos$media else NA_real_),
  list(clave = "caida_por_los_dos_descuidos",
       valor = if (!is.null(los_dos)) los_dos$diferencia_relativa else NA_real_),
  list(clave = "razon_entre_deciles",
       valor = o_na(valor_ingreso[["razón entre el décimo y el primer decil"]])),
  list(clave = "informalidad",
       valor = if (!is.null(total_informal)) total_informal$tasa else NA_real_),
  list(clave = "avisos", valor = length(avisos))
), "salidas/resumen.csv", c("clave", "valor"))

cat("Listo. Salidas en salidas/:\n")
cat("  poblacion.csv, tasas.csv, tasas-por-grupo.csv, ingresos.csv,\n")
cat("  deciles.csv, ponderador-e-ingreso.csv, ingresos-por-grupo.csv,\n")
cat("  informalidad.csv, avisos.csv, resumen.csv y eph.md\n")
if (!is.null(correcto) && !is.null(los_dos)) {
  cat(paste0("  Ingreso medio: ", numero_texto(correcto$media, 0),
             " bien calculado, ", numero_texto(los_dos$media, 0),
             " con los dos descuidos (",
             numero_texto(100 * los_dos$diferencia_relativa, 1), " %).\n"))
}
if (!base$hay_ponderador_de_ingreso) {
  cat("  Ojo: el archivo no trae ponderador de ingreso. Mirá avisos.csv.\n")
}

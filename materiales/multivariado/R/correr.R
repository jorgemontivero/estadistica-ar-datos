# Componentes, conglomerados y correspondencias, y después el informe.
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
source("R/jacobi.R")
source("R/01-componentes.R")
source("R/02-conglomerados.R")
source("R/03-correspondencias.R")
source("R/04-redaccion.R")

parametros <- leer_parametros(PARAMETROS)
leido <- leer_matriz(parametros$datos, parametros$unidad)
unidades <- leido$unidades
columnas <- leido$columnas
datos <- leido$datos
if (length(unidades) < 3) {
  stop("Con menos de tres unidades no hay nada que agrupar.", call. = FALSE)
}

# ------------------------------------------------------------- componentes
con <- calcular_componentes(datos, columnas, TRUE)
sin_ <- calcular_componentes(datos, columnas, FALSE)
cuantos <- min(parametros$componentes, length(columnas))

filas_componentes <- tabla_de_componentes(con, columnas)
filas_cargas <- tabla_de_cargas(con, columnas, cuantos)
filas_puntajes <- tabla_de_puntajes(con, unidades, cuantos)
filas_contraste <- contraste(con, sin_, columnas)

# ------------------------------------------------------------ conglomerados
preparado <- tipificar(datos)
base <- preparado$base
agrupado <- calcular_conglomerados(base, unidades, parametros)
por_enlace <- agrupado$por_enlace
filas_grupos <- tabla_de_grupos(unidades, por_enlace, parametros)
filas_fusiones <- tabla_de_fusiones(por_enlace, unidades)
filas_siluetas <- tabla_de_siluetas(por_enlace, parametros)
filas_nulo <- contra_el_nulo(base, parametros)
nulo <- resumen_del_nulo(filas_nulo, por_enlace[[parametros$enlace]]$silueta)

# --------------------------------------------------------- correspondencias
leida <- leer_matriz(parametros$tabla, parametros$unidad)
filas_tabla <- leida$unidades
columnas_tabla <- leida$columnas
tabla <- leida$datos
ca <- calcular_correspondencias(tabla, filas_tabla, columnas_tabla, parametros)
filas_ejes <- tabla_de_ejes(ca)
filas_puntos <- tabla_de_puntos(ca, filas_tabla, columnas_tabla, parametros)

avisos <- c(avisos_de_componentes(con, sin_, columnas, parametros),
            avisos_de_conglomerados(por_enlace, nulo, parametros, unidades),
            avisos_de_correspondencias(ca, filas_tabla, columnas_tabla, parametros, tabla))

# ------------------------------------------------------------------ salidas
escribir_csv(filas_componentes, "salidas/componentes.csv",
             c("componente", "autovalor", "proporcion", "acumulado",
               "supera_el_promedio"))

escribir_csv(filas_cargas, "salidas/cargas.csv",
             c("variable", paste0("componente_", seq_len(cuantos)), "representada"))

escribir_csv(filas_puntajes, "salidas/puntajes.csv",
             c("unidad", paste0("componente_", seq_len(cuantos))))

escribir_csv(filas_contraste, "salidas/sin-estandarizar.csv",
             c("version", "autovalor_1", "proporcion_1", "proporcion_2",
               "variable_mas_pegada", "correlacion_con_esa", "variables_hasta_el_90"))

escribir_csv(filas_grupos, "salidas/conglomerados.csv",
             c("unidad", ENLACES, "silueta"))

escribir_csv(filas_fusiones, "salidas/fusiones.csv",
             c("enlace", "paso", "unidad_a", "unidad_b", "altura", "tamano"))

escribir_csv(filas_siluetas, "salidas/silueta.csv",
             c("enlace", "grupos", "mayor", "menor", "silueta", "negativas",
               "acuerdo_con_el_elegido"))

escribir_csv(filas_nulo, "salidas/nulo.csv", c("corrimiento", "silueta"))

escribir_csv(filas_ejes, "salidas/correspondencias.csv",
             c("eje", "valor_singular", "inercia", "proporcion", "acumulado",
               "chi2_del_eje"))

ejes <- min(parametros$ejes, ca$ejes_posibles)
columnas_puntos <- c("tipo", "punto", "masa", "inercia")
for (j in seq_len(ejes)) {
  columnas_puntos <- c(columnas_puntos, paste0("eje_", j), paste0("aporte_", j))
}
escribir_csv(filas_puntos, "salidas/puntos.csv", c(columnas_puntos, "calidad"))

escribir_csv(avisos, "salidas/avisos.csv", c("donde", "aviso"))

escribir_texto(redactar(parametros, unidades, columnas, filas_componentes, filas_cargas,
                        filas_contraste, filas_siluetas, filas_grupos, nulo, ca,
                        filas_ejes, filas_puntos, avisos, columnas_tabla),
               "salidas/multivariado.md")

# ------------------------------------------------------------------ resumen
tipificada <- filas_contraste[[1]]
cruda <- filas_contraste[[2]]
elegido <- parametros$enlace
del_elegido <- Filter(function(f) f$enlace == elegido, filas_siluetas)[[1]]
otros <- Filter(function(f) f$enlace != elegido, filas_siluetas)

escribir_csv(list(
  list(clave = "unidades", valor = length(unidades)),
  list(clave = "variables", valor = length(columnas)),
  list(clave = "componentes_pedidos", valor = as.integer(cuantos)),
  list(clave = "proporcion_del_primero", valor = tipificada$proporcion_1),
  list(clave = "proporcion_de_los_dos_primeros",
       valor = tipificada$proporcion_1 +
         (if (is.na(tipificada$proporcion_2)) 0 else tipificada$proporcion_2)),
  list(clave = "componentes_hasta_el_90", valor = tipificada$variables_hasta_el_90),
  list(clave = "proporcion_del_primero_sin_tipificar", valor = cruda$proporcion_1),
  list(clave = "variable_que_se_come_el_primero", valor = cruda$variable_mas_pegada),
  list(clave = "correlacion_con_esa_variable", valor = cruda$correlacion_con_esa),
  list(clave = "enlace", valor = elegido),
  list(clave = "conglomerados", valor = parametros$conglomerados),
  list(clave = "silueta", valor = del_elegido$silueta),
  list(clave = "siluetas_negativas", valor = del_elegido$negativas),
  list(clave = "nulos", valor = nulo$replicas),
  list(clave = "mejor_silueta_del_nulo", valor = nulo$mayor),
  list(clave = "mediana_del_nulo", valor = nulo$mediana),
  list(clave = "nulos_que_igualan_o_superan", valor = nulo$nulos_que_igualan_o_superan),
  list(clave = "peor_acuerdo_entre_enlaces",
       valor = min(vapply(otros, function(f) f$acuerdo_con_el_elegido, numeric(1)))),
  list(clave = "filas_de_la_tabla", valor = length(filas_tabla)),
  list(clave = "columnas_de_la_tabla", valor = length(columnas_tabla)),
  list(clave = "chi2", valor = ca$chi2),
  list(clave = "gl", valor = ca$gl),
  list(clave = "inercia_total", valor = ca$inercia_total),
  list(clave = "inercia_de_los_ejes_graficados",
       valor = suma(vapply(seq_len(ejes), function(j) ca$inercias[j], numeric(1))) /
         ca$inercia_total),
  list(clave = "avisos", valor = length(avisos))
), "salidas/resumen.csv", c("clave", "valor"))

cat("Listo. Salidas en salidas/:\n")
cat("  componentes.csv, cargas.csv, puntajes.csv, sin-estandarizar.csv,\n")
cat("  conglomerados.csv, fusiones.csv, silueta.csv, nulo.csv,\n")
cat("  correspondencias.csv, puntos.csv, avisos.csv, resumen.csv y multivariado.md\n")
cat(paste0("  Tipificado, el primer componente explica ",
           sprintf("%.1f", 100 * tipificada$proporcion_1), " %; sin tipificar, ",
           sprintf("%.1f", 100 * cruda$proporcion_1), " % y es «",
           cruda$variable_mas_pegada, "».\n"))
cat(paste0("  Silueta con ", elegido, ": ", sprintf("%.3f", del_elegido$silueta),
           "; el mejor de los ", nulo$replicas, " nulos llega a ",
           sprintf("%.3f", nulo$mayor), ".\n"))

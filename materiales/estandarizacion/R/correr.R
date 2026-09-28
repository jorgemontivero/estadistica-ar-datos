# Estandariza, compara y escribe el informe.
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
source("R/01-directa.R")
source("R/02-indirecta.R")
source("R/03-comparar.R")
source("R/04-redaccion.R")

parametros <- leer_parametros(PARAMETROS)

# La tabla de casos y expuestos, y los pesos de cada estándar.
#
# El **orden de los grupos de edad lo fija el archivo de estándares**, no el
# alfabeto: «10 a 14» va antes que «0 a 9» si uno los ordena como texto, y una
# tabla de edades ordenada así es ilegible.
leer_datos <- function(parametros) {
  columnas <- leer_csv(parametros$estandares)
  if (length(columnas) == 0) {
    stop(paste0(parametros$estandares, " está vacío."), call. = FALSE)
  }
  nombres <- setdiff(names(columnas[[1]]), "grupo_edad")
  if (length(nombres) == 0) {
    stop(paste0("El archivo de estándares no tiene ninguna columna de pesos además de ",
                "«grupo_edad»."), call. = FALSE)
  }
  grupos <- vapply(columnas, function(f) f$grupo_edad, character(1))
  if (length(unique(grupos)) != length(grupos)) {
    stop("El archivo de estándares repite algún grupo de edad.", call. = FALSE)
  }
  pesos <- list()
  for (nombre in nombres) {
    valores <- list()
    for (f in columnas) {
      v <- numero(f[[nombre]])
      if (is.null(v) || v < 0) {
        stop(paste0("El peso de «", f$grupo_edad, "» en el estándar «", nombre,
                    "» no es un número positivo."), call. = FALSE)
      }
      valores[[f$grupo_edad]] <- v
    }
    pesos[[nombre]] <- valores
  }

  filas <- leer_csv(parametros$datos)
  for (clave in c(parametros$poblacion, parametros$grupo, parametros$casos,
                  parametros$expuestos)) {
    if (length(filas) > 0 && !(clave %in% names(filas[[1]]))) {
      stop(paste0("A ", parametros$datos, " le falta la columna «", clave, "»."),
           call. = FALSE)
    }
  }

  poblaciones <- list()
  for (f in filas) {
    nombre <- f[[parametros$poblacion]]
    grupo <- f[[parametros$grupo]]
    if (!(grupo %in% grupos)) {
      stop(paste0("El grupo «", grupo, "» está en los datos y no en el archivo de ",
                  "estándares. Los dos tienen que usar los mismos."), call. = FALSE)
    }
    if (is.null(poblaciones[[nombre]])) poblaciones[[nombre]] <- list()
    if (!is.null(poblaciones[[nombre]][[grupo]])) {
      stop(paste0("«", nombre, "» tiene el grupo «", grupo, "» dos veces."),
           call. = FALSE)
    }
    casos <- numero(f[[parametros$casos]])
    expuestos <- numero(f[[parametros$expuestos]])
    if (is.null(casos) || is.null(expuestos) || casos < 0 || expuestos < 0) {
      stop(paste0("«", nombre, "», grupo «", grupo, "»: los casos y los expuestos ",
                  "tienen que ser números no negativos."), call. = FALSE)
    }
    poblaciones[[nombre]][[grupo]] <- list(casos = casos, expuestos = expuestos)
  }

  if (length(poblaciones) == 0) {
    stop(paste0(parametros$datos, " no tiene ninguna fila."), call. = FALSE)
  }
  incompletas <- names(poblaciones)[vapply(poblaciones, function(c)
    !setequal(names(c), grupos), logical(1))]
  if (length(incompletas) > 0) {
    stop(paste0("Estas poblaciones no tienen todos los grupos de edad: ",
                paste(head(ordenar(incompletas), 5), collapse = ", "),
                ". Una tasa ajustada con grupos faltantes no se puede comparar con otra ",
                "que los tenga."), call. = FALSE)
  }
  list(poblaciones = poblaciones, grupos = grupos, pesos = pesos)
}

leido <- leer_datos(parametros)
poblaciones <- leido$poblaciones
grupos <- leido$grupos
todos_los_pesos <- leido$pesos
if (is.null(todos_los_pesos[[parametros$estandar]])) {
  stop(paste0("El estándar «", parametros$estandar, "» no está en ",
              parametros$estandares, ". Hay: ",
              paste(ordenar(names(todos_los_pesos)), collapse = ", "), "."), call. = FALSE)
}
pesos <- todos_los_pesos[[parametros$estandar]]

# ------------------------------------------------------------------ cálculo
tasas <- calcular(poblaciones, grupos, pesos, parametros)
detalle <- por_edad(poblaciones, grupos, pesos, parametros)

cuales <- limpiar_texto(strsplit(parametros$referencia, "|", fixed = TRUE)[[1]])
cuales <- cuales[cuales != ""]
referencia <- tasas_de_referencia(poblaciones, grupos, cuales)
indirectas <- calcular_indirecta(poblaciones, grupos, referencia, tasas, parametros)

comparado <- por_estandar(poblaciones, grupos, todos_los_pesos, parametros, calcular)
filas_estandar <- comparado$filas
sensibles <- sensibilidad(comparado$cuadro, parametros)
niveles_ <- niveles(comparado$cuadro)
comparaciones <- comparar(poblaciones, grupos, tasas, parametros$pares, parametros)
descomposicion <- descomponer(poblaciones, grupos, parametros$pares, parametros)

avisos <- c(avisos_de_directa(tasas, detalle, parametros),
            avisos_de_indirecta(indirectas, referencia, parametros),
            avisos_de_comparar(sensibles, niveles_, comparaciones))

# ------------------------------------------------------------------ salidas
escribir_csv(tasas, "salidas/tasas.csv",
             c("poblacion", "casos", "expuestos", "proporcion_en_el_grupo_mayor",
               "cruda", "cruda_inferior", "cruda_superior", "estandarizada",
               "estandarizada_inferior", "estandarizada_superior", "cambio_relativo",
               "casos_con_la_estructura_estandar", "rango_crudo", "rango_estandarizado",
               "cambio_de_rango"))

escribir_csv(detalle, "salidas/por-edad.csv",
             c("poblacion", "grupo_edad", "casos", "expuestos", "proporcion_propia",
               "peso_estandar", "tasa_especifica", "aporte"))

escribir_csv(indirectas, "salidas/indirecta.csv",
             c("poblacion", "observados", "esperados", "razon", "razon_inferior",
               "razon_superior", "distinta_de_uno", "estandarizada_indirecta",
               "estandarizada_directa", "diferencia_con_la_directa", "cruda",
               "rango_indirecto", "rango_directo"))

escribir_csv(filas_estandar, "salidas/por-estandar.csv",
             c("estandar", "poblacion", "tasa", "inferior", "superior", "rango"))

escribir_csv(sensibles, "salidas/sensibilidad.csv",
             c("estandar_1", "estandar_2", "poblacion_a", "poblacion_b", "tasa_a_1",
               "tasa_b_1", "tasa_a_2", "tasa_b_2", "distancia_1", "distancia_2",
               "se_pisan_con_1", "se_pisan_con_2", "se_pisan_con_los_dos"))

escribir_csv(niveles_, "salidas/niveles.csv",
             c("poblacion", "menor", "mayor", "razon_entre_niveles",
               "estandar_del_menor", "estandar_del_mayor"))

escribir_csv(comparaciones, "salidas/comparaciones.csv",
             c("poblacion_a", "poblacion_b", "cruda_a", "cruda_b", "diferencia_cruda",
               "efecto_estructura", "efecto_tasas", "residuo_de_la_identidad",
               "parte_estructura", "estandarizada_a", "estandarizada_b",
               "diferencia_estandarizada", "razon", "razon_inferior", "razon_superior",
               "la_razon_excluye_al_uno", "se_dan_vuelta"))

escribir_csv(descomposicion, "salidas/descomposicion.csv",
             c("poblacion_a", "poblacion_b", "grupo_edad", "proporcion_a", "proporcion_b",
               "tasa_a", "tasa_b", "efecto_estructura", "efecto_tasas"))

escribir_csv(avisos, "salidas/avisos.csv", c("donde", "aviso"))

escribir_texto(redactar(parametros, tasas, indirectas, referencia, sensibles, niveles_,
                        comparaciones, avisos, grupos),
               "salidas/estandarizacion.md")

# ------------------------------------------------------------------ resumen
cambios <- vapply(tasas, function(f) abs(f$cambio_de_rango), numeric(1))
mayor_vuelco <- tasas[[which.max(cambios)]]
mas_alta <- tasas[[1]]
mas_baja <- tasas[[length(tasas)]]
razones <- vapply(niveles_, function(f) if (is.na(f$razon_entre_niveles)) 0
                  else f$razon_entre_niveles, numeric(1))
peor_nivel <- niveles_[[which.max(razones)]]

escribir_csv(list(
  list(clave = "poblaciones", valor = length(tasas)),
  list(clave = "grupos_de_edad", valor = length(grupos)),
  list(clave = "estandar", valor = parametros$estandar),
  list(clave = "estandares_disponibles", valor = length(todos_los_pesos)),
  list(clave = "casos", valor = as.integer(sum(vapply(tasas, function(f) f$casos,
                                                      numeric(1))))),
  list(clave = "expuestos", valor = as.integer(sum(vapply(tasas, function(f) f$expuestos,
                                                          numeric(1))))),
  list(clave = "tasa_cruda_del_conjunto", valor = referencia$cruda *
         parametros$multiplicador),
  list(clave = "mas_alta_ajustada", valor = mas_alta$poblacion),
  list(clave = "mas_alta_ajustada_valor", valor = mas_alta$estandarizada),
  list(clave = "mas_baja_ajustada", valor = mas_baja$poblacion),
  list(clave = "mas_baja_ajustada_valor", valor = mas_baja$estandarizada),
  list(clave = "mayor_vuelco", valor = mayor_vuelco$poblacion),
  list(clave = "mayor_vuelco_rango_crudo", valor = mayor_vuelco$rango_crudo),
  list(clave = "mayor_vuelco_rango_estandarizado",
       valor = mayor_vuelco$rango_estandarizado),
  list(clave = "mayor_vuelco_cruda", valor = mayor_vuelco$cruda),
  list(clave = "mayor_vuelco_estandarizada", valor = mayor_vuelco$estandarizada),
  list(clave = "pares_que_se_dan_vuelta_por_el_estandar", valor = length(sensibles)),
  list(clave = "de_esos_con_intervalos_pisados_con_los_dos",
       valor = as.integer(sum(vapply(sensibles, function(f) f$se_pisan_con_los_dos,
                                     logical(1))))),
  list(clave = "mayor_razon_entre_niveles", valor = peor_nivel$razon_entre_niveles),
  list(clave = "referencia_de_la_indirecta", valor = referencia$nombre),
  list(clave = "razones_que_no_contienen_al_uno",
       valor = as.integer(sum(vapply(indirectas, function(f) f$distinta_de_uno,
                                     logical(1))))),
  list(clave = "pares_comparados", valor = length(comparaciones)),
  list(clave = "avisos", valor = length(avisos))
), "salidas/resumen.csv", c("clave", "valor"))

cat("Listo. Salidas en salidas/:\n")
cat("  tasas.csv, por-edad.csv, indirecta.csv, por-estandar.csv,\n")
cat("  sensibilidad.csv, niveles.csv, comparaciones.csv, descomposicion.csv,\n")
cat("  avisos.csv, resumen.csv y estandarizacion.md\n")
cat(paste0("  ", mayor_vuelco$poblacion, ": puesto ", mayor_vuelco$rango_crudo,
           " por la tasa cruda y ", mayor_vuelco$rango_estandarizado,
           " por la ajustada.\n"))
if (length(sensibles) > 0) {
  cat(paste0("  ", length(sensibles), " pares cambian de orden según el estándar.\n"))
}

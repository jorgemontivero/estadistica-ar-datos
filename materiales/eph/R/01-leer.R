# Paso 1: abrir el archivo del INDEC y entender qué dice.
#
# Leer la EPH es la mitad del trabajo, y es la mitad que no se publica. Este
# paso hace tres cosas, en este orden:
#
# 1. **Abre el archivo con el formato correcto.** Punto y coma, latin-1, textos
#    entre comillas. Está en `leer_microdatos`, en comun.R.
# 2. **Traduce los códigos.** `ESTADO = 1` es «ocupado» y `CAT_OCUP = 3` es
#    «obrero o empleado». Sin el diccionario, las tablas que salen son
#    ilegibles y las decisiones que se toman con ellas, también.
# 3. **Revisa lo que puede estar mal** y lo escribe en `avisos.csv`. No corrige
#    nada por su cuenta: avisa. Un programa que arregla los datos en silencio
#    es un programa que produce un número del que nadie puede responder.
#
# Las revisiones no son genéricas: son las cosas que efectivamente pasan con
# los archivos de la EPH, y cada una está comentada donde se hace.

# ------------------------------------------------------------ los códigos
#
# Salen del diseño de registro que el INDEC publica junto con la base. No están
# acá para adornar: una tabla que dice «3» en vez de «Obrero o empleado» es una
# tabla que nadie puede revisar.
CONDICION <- c("0" = "Entrevista individual no realizada",
               "1" = "Ocupado",
               "2" = "Desocupado",
               "3" = "Inactivo",
               "4" = "Menor de 10 años")

CATEGORIA <- c("1" = "Patrón",
               "2" = "Cuenta propia",
               "3" = "Obrero o empleado",
               "4" = "Trabajador familiar sin remuneración",
               "9" = "Sin especificar")

NIVEL <- c("1" = "Primaria incompleta",
           "2" = "Primaria completa",
           "3" = "Secundaria incompleta",
           "4" = "Secundaria completa",
           "5" = "Superior incompleta",
           "6" = "Superior completa",
           "7" = "Sin instrucción",
           "9" = "Sin especificar")

SEXO <- c("1" = "Varón", "2" = "Mujer")

INTENSIDAD <- c("1" = "Subocupado",
                "2" = "Ocupado pleno",
                "3" = "Sobreocupado",
                "4" = "Ocupado que no trabajó en la semana")

DESCUENTO <- c("1" = "Con descuento jubilatorio", "2" = "Sin descuento jubilatorio")

REGIONES <- c("1" = "Gran Buenos Aires",
              "40" = "Noroeste",
              "41" = "Nordeste",
              "42" = "Cuyo",
              "43" = "Pampeana",
              "44" = "Patagonia")

# Los tramos con los que la EPH suele publicar. El orden es este y no el
# alfabético: «10 a 13» antes que «65 y más» no sale de ordenar textos.
TRAMOS <- list(
  list(etiqueta = "10 a 13", desde = 10, hasta = 13),
  list(etiqueta = "14 a 24", desde = 14, hasta = 24),
  list(etiqueta = "25 a 34", desde = 25, hasta = 34),
  list(etiqueta = "35 a 49", desde = 35, hasta = 49),
  list(etiqueta = "50 a 64", desde = 50, hasta = 64),
  list(etiqueta = "65 y más", desde = 65, hasta = 200)
)

ORDEN_CONDICION <- c(1, 2, 3, 4, 0)

# Sin estas no hay proyecto. El resto se puede no tener.
IMPRESCINDIBLES <- c("ESTADO", "CH04", "CH06")

# El trimestre a partir del cual el INDEC publica los ponderadores de ingreso.
# Antes de este, `PONDIIO`, `PONDII` y `PONDIH` **no existen en el archivo**, y
# el que reusa un script hecho para un trimestre reciente sobre una base vieja
# se queda sin ellos sin enterarse.
ANO_CON_PONDERADOR_DE_INGRESO <- 2016
TRIMESTRE_CON_PONDERADOR_DE_INGRESO <- 2

# Comparar contra un código sin que un dato faltante se cuele. En R, `NA == 1`
# no es FALSO: es NA, y un NA dentro de un `if` o de un `[` hace estragos.
es <- function(v, k) !is.na(v) & v == k

tramo_de <- function(edad) {
  salida <- rep(NA_character_, length(edad))
  for (t in TRAMOS) {
    dentro <- !is.na(edad) & edad >= t$desde & edad <= t$hasta
    salida[dentro & is.na(salida)] <- t$etiqueta
  }
  salida
}

etiqueta <- function(tabla, codigo, sin_dato = "Sin dato") {
  if (is.null(codigo) || is.na(codigo)) return(sin_dato)
  clave <- as.character(codigo)
  if (clave %in% names(tabla)) unname(tabla[[clave]]) else paste0("Código ", clave)
}

etiquetas_de <- function(tabla, codigos, sin_dato = "Sin dato") {
  salida <- unname(tabla[as.character(codigos)])
  salida[is.na(salida)] <- sin_dato
  salida
}

# Los registros ya interpretados, más la lista de lo que hay que mirar.
leer <- function(columnas, crudas, parametros) {
  avisos <- list()
  presentes <- columnas
  crudas_n <- length(crudas[[columnas[1]]])
  col <- function(nombre) {
    if (nombre %in% presentes) crudas[[nombre]] else rep("", crudas_n)
  }

  faltan <- IMPRESCINDIBLES[!(IMPRESCINDIBLES %in% presentes)]
  if (length(faltan) > 0) {
    stop(paste0("Al archivo le faltan columnas que el proyecto necesita: ",
                paste(faltan, collapse = ", "),
                ". ¿Es el archivo de individual y no el de hogar?"), call. = FALSE)
  }

  ponderador <- parametros$ponderador
  if (!(ponderador %in% presentes)) {
    stop(paste0("El archivo no tiene la columna «", ponderador, "». Sin ",
                "ponderador no hay nada que estimar: la EPH es una muestra, y sus ",
                "casos no valen uno."), call. = FALSE)
  }

  # ------------------------------------------------ el período del archivo
  anos <- if ("ANO4" %in% presentes) ordenar(crudas[["ANO4"]]) else character(0)
  trimestres <- if ("TRIMESTRE" %in% presentes) ordenar(crudas[["TRIMESTRE"]]) else character(0)
  periodo <- ""
  ano_num <- NA_real_
  trimestre_num <- NA_real_
  if (length(anos) == 1 && length(trimestres) == 1) {
    ano_num <- numeros_de(anos[1])
    trimestre_num <- numeros_de(trimestres[1])
    periodo <- paste0(anos[1], "T", trimestres[1])
  } else if (length(anos) > 0 && length(trimestres) > 0) {
    periodo <- paste0(length(anos), " años y ", length(trimestres), " trimestres")
    avisos[[length(avisos) + 1]] <- list(
      donde = "archivo",
      aviso = paste0(
        "El archivo tiene más de un trimestre adentro. Las tasas que salen de ",
        "acá son un promedio de trimestres distintos, que no es lo mismo que la ",
        "tasa de ninguno de ellos. Si es a propósito, está bien; si es porque se ",
        "concatenaron bases, no."))
  }

  # ------------------------------ el ponderador del ingreso, o su falta
  #
  # Esta es la trampa que más caro sale. Antes de 2016T2 las bases de la EPH
  # **no traen** PONDIIO, PONDII ni PONDIH. Un script escrito contra un
  # trimestre reciente y corrido sobre uno viejo se queda sin el ponderador de
  # ingreso; si además no se filtra el −9, el ingreso medio se hunde un veinte
  # por ciento y no hay ningún error en pantalla.
  nombre_ingreso_pond <- parametros$ponderador_ingreso
  hay_ponderador_ingreso <- nombre_ingreso_pond %in% presentes
  if (!hay_ponderador_ingreso) {
    viejo <- (!is.na(ano_num) && !is.na(trimestre_num) &&
                (ano_num < ANO_CON_PONDERADOR_DE_INGRESO ||
                   (ano_num == ANO_CON_PONDERADOR_DE_INGRESO &&
                      trimestre_num < TRIMESTRE_CON_PONDERADOR_DE_INGRESO)))
    porque <- if (viejo) " Es lo esperable: el INDEC lo publica recién desde 2016T2." else ""
    avisos[[length(avisos) + 1]] <- list(
      donde = "ponderadores",
      aviso = paste0(
        "El archivo no tiene «", nombre_ingreso_pond, "».", porque,
        " Los ingresos se estiman con «", ponderador, "», que **no corrige la ",
        "no respuesta**: el que no declara ingresos no se parece al que sí, y con ",
        "el ponderador general su ausencia no se compensa. La tabla ",
        "«ponderador-e-ingreso.csv» muestra cuánto cambia."))
    nombre_ingreso_pond <- ponderador
  }

  nombre_ingreso <- parametros$ingreso
  hay_ingreso <- nombre_ingreso %in% presentes
  if (!hay_ingreso) {
    avisos[[length(avisos) + 1]] <- list(
      donde = "ingresos",
      aviso = paste0("El archivo no tiene la columna «", nombre_ingreso,
                     "». Las tablas de ingresos salen vacías."))
  }

  # ---------------------------------------------------------- los registros
  con_na_literal <- 0L
  for (c in c(ponderador, "ESTADO", "CH06", nombre_ingreso)) {
    if (c %in% presentes) {
      con_na_literal <- con_na_literal +
        sum(toupper(limpiar_texto(crudas[[c]])) %in% FALTANTES)
    }
  }

  peso <- numeros_de(crudas[[ponderador]])
  sirve <- !is.na(peso) & peso > 0
  peso_no_positivo <- sum(!sirve)

  estado <- numeros_de(col("ESTADO"))[sirve]
  estado_raro <- sum(is.na(estado) | !(as.character(estado) %in% names(CONDICION)))

  edad <- numeros_de(col("CH06"))[sirve]
  # CH06 = −1 quiere decir «menos de un año», no «falta el dato». Tratarlo como
  # un número sin mirarlo mete edades negativas en cualquier promedio de edad
  # que se calcule después.
  bebes <- sum(!is.na(edad) & edad < 0)
  edad[!is.na(edad) & edad < 0] <- 0

  con_cero <- function(nombre) {
    v <- numeros_de(col(nombre))[sirve]
    v[is.na(v)] <- 0
    v
  }

  peso_ingreso <- if (hay_ingreso) numeros_de(col(nombre_ingreso_pond))[sirve]
                  else rep(NA_real_, sum(sirve))
  peso_ingreso[is.na(peso_ingreso)] <- 0

  registros <- list(
    pondera = peso[sirve],
    pondera_ingreso = peso_ingreso,
    aglomerado = limpiar_texto(col("AGLOMERADO"))[sirve],
    region = numeros_de(col("REGION"))[sirve],
    # La unidad primaria disponible. Un hogar es CODUSU + NRO_HOGAR: una
    # vivienda puede tener más de un hogar adentro.
    hogar = paste0(limpiar_texto(col("CODUSU")), "|",
                   limpiar_texto(col("NRO_HOGAR")))[sirve],
    sexo = numeros_de(col("CH04"))[sirve],
    edad = edad,
    nivel_ed = numeros_de(col("NIVEL_ED"))[sirve],
    estado = estado,
    cat_ocup = con_cero("CAT_OCUP"),
    pp07h = con_cero("PP07H"),
    intensi = con_cero("INTENSI"),
    p21 = if (hay_ingreso) numeros_de(col(nombre_ingreso))[sirve]
          else rep(NA_real_, sum(sirve))
  )
  if (length(registros$pondera) == 0) {
    stop("No quedó ningún registro con ponderador positivo.", call. = FALSE)
  }

  # ------------------------------------------------------------- los filtros
  queda <- rep(TRUE, length(registros$pondera))
  if (nchar(parametros$region) > 0) {
    pedidas <- limpiar_texto(strsplit(parametros$region, " ", fixed = TRUE)[[1]])
    queda <- queda & (as.character(registros$region) %in% pedidas)
  }
  if (nchar(parametros$aglomerado) > 0) {
    pedidos <- limpiar_texto(strsplit(parametros$aglomerado, " ", fixed = TRUE)[[1]])
    queda <- queda & (registros$aglomerado %in% pedidos)
  }
  if (!any(queda)) {
    stop("El filtro de región o aglomerado no dejó ningún registro.", call. = FALSE)
  }
  filtrados <- sum(!queda)
  registros <- lapply(registros, function(v) v[queda])

  # --------------------------------------------------------- las revisiones
  agregar <- function(donde, aviso) {
    avisos[[length(avisos) + 1]] <<- list(donde = donde, aviso = aviso)
  }
  if (con_na_literal > 0) {
    agregar("archivo", paste0(
      "Hay ", con_na_literal, " celdas con «NA» escrito con letras en las ",
      "columnas que el proyecto usa. En algunos trimestres —2021T1, 2024T3 y ",
      "2024T4— el INDEC las escribe así, y eso convierte en texto a ciento ",
      "cincuenta columnas numéricas en cualquier lector que adivine el tipo. Acá ",
      "se leen como texto a propósito y se tratan como dato faltante."))
  }
  if (peso_no_positivo > 0) {
    agregar("ponderadores", paste0(
      "Se descartaron ", peso_no_positivo, " registros con «", ponderador,
      "» nulo o ausente. Un registro sin ponderador no representa a nadie."))
  }
  if (estado_raro > 0) {
    agregar("códigos", paste0(
      "Hay ", estado_raro, " registros con un valor de ESTADO que no está en el ",
      "diseño de registro. No entran en ninguna de las cinco condiciones y por lo ",
      "tanto no entran en el denominador de nada."))
  }
  if (bebes > 0) {
    agregar("códigos", paste0(
      "Hay ", bebes, " registros con CH06 negativo. En la EPH «−1» quiere decir ",
      "«menos de un año», no «falta el dato»: se los cuenta como cero. Promediar ",
      "la columna sin mirarla da una edad media más baja de la que corresponde."))
  }
  if (filtrados > 0) {
    agregar("filtros", paste0(
      "Se dejaron afuera ", filtrados, " registros por el filtro de región o ",
      "aglomerado declarado en parametros.csv. Todo lo que sigue es de la parte ",
      "filtrada, y no del total de los aglomerados relevados."))
  }

  # ----------------------- la coherencia entre el ingreso y su ponderador
  #
  # En las bases del INDEC el ponderador de ingreso vale **cero** justo para los
  # que no declararon. Comprobarlo es la manera de saber si el archivo es el que
  # uno cree que es: si no se cumple, o el archivo está tocado, o la columna que
  # se está usando no es la que se piensa.
  if (hay_ingreso && hay_ponderador_ingreso) {
    ocupados <- es(registros$estado, 1)
    sin_declarar <- ocupados & !is.na(registros$p21) & registros$p21 < 0
    mal <- sum(sin_declarar & registros$pondera_ingreso > 0)
    if (mal > 0) {
      agregar("ponderadores", paste0(
        "Hay ", mal, " ocupados que no declararon ingreso y sin embargo tienen «",
        nombre_ingreso_pond, "» mayor que cero. En una base del INDEC eso no pasa: ",
        "el ponderador de ingreso vale cero para el que no contestó. Conviene ",
        "revisar de dónde salió el archivo."))
    }
    if (any(sin_declarar)) {
      peso_total_oc <- sum(registros$pondera[ocupados])
      peso_sin <- sum(registros$pondera[sin_declarar])
      agregar("ingresos", paste0(
        sum(sin_declarar), " ocupados —el ",
        sub(".", ",", sprintf("%.1f", 100 * peso_sin / peso_total_oc), fixed = TRUE),
        " % ponderado— tienen «", nombre_ingreso, "» negativo, que en la EPH ",
        "quiere decir «no responde» y no «ingreso negativo». Promediar esa ",
        "columna sin sacarlos es el error más caro que se puede cometer con esta ",
        "base."))
    }
  }

  # ------------------------------------------------------------- la población
  peso_total <- sum(registros$pondera)
  vistos <- unique(registros$estado)
  # Primero las cinco condiciones en el orden en que se informan; después
  # cualquier código que el archivo traiga y el diseño de registro no
  # contemple; y al final, si los hay, los que directamente no tienen dato.
  otros <- sort(vistos[!is.na(vistos) & !(vistos %in% ORDEN_CONDICION)])
  codigos <- c(ORDEN_CONDICION, otros)
  poblacion <- list()
  for (codigo in codigos) {
    del_grupo <- es(registros$estado, codigo)
    if (!any(del_grupo)) next
    peso_grupo <- sum(registros$pondera[del_grupo])
    poblacion[[length(poblacion) + 1]] <- list(
      condicion = etiqueta(CONDICION, codigo), codigo = as.integer(codigo),
      n = sum(del_grupo), poblacion = peso_grupo,
      porcentaje = peso_grupo / peso_total)
  }
  if (any(is.na(registros$estado))) {
    sin_dato <- is.na(registros$estado)
    peso_grupo <- sum(registros$pondera[sin_dato])
    poblacion[[length(poblacion) + 1]] <- list(
      condicion = "Sin dato", codigo = NA_integer_, n = sum(sin_dato),
      poblacion = peso_grupo, porcentaje = peso_grupo / peso_total)
  }

  list(registros = registros, avisos = avisos, periodo = periodo,
       poblacion = poblacion, peso_total = peso_total,
       n = length(registros$pondera),
       hogares = length(unique(registros$hogar)),
       aglomerados = length(unique(registros$aglomerado)),
       ponderador_de_ingreso = nombre_ingreso_pond,
       hay_ponderador_de_ingreso = hay_ponderador_ingreso,
       hay_ingreso = hay_ingreso,
       columnas_del_archivo = length(columnas))
}

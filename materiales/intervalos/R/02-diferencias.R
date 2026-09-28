# Paso 2: los intervalos de la diferencia, y por qué no alcanza con mirar los
# dos por separado.
#
# Es el error más común con intervalos de confianza: publicar el intervalo de
# cada grupo y concluir, porque se pisan, que no hay diferencia. No se sigue.
# El intervalo de la diferencia usa el error estándar de la diferencia, que es
# √(EE₁² + EE₂²) y no EE₁ + EE₂: es más chico que la suma, así que hay un rango
# entero de diferencias donde los dos intervalos se pisan y sin embargo el de
# la diferencia no contiene al cero.
#
# Por eso cada fila trae las dos cosas al lado: si los intervalos de los dos
# grupos se pisan, y si el de la diferencia excluye al cero. Cuando las dos
# columnas dicen «Sí», mirar los intervalos por separado lleva a la conclusión
# contraria, y la columna `conclusion_distinta` lo marca.
#
# Con más de dos grupos se comparan todos los pares. Ahí conviene recordar que
# cada intervalo es del 95 % por separado: tres intervalos simultáneos no dan
# 95 % de confianza conjunta.

pares <- function(niveles) {
  salida <- list()
  if (length(niveles) < 2) return(salida)
  for (i in seq_len(length(niveles) - 1)) {
    for (j in seq(i + 1, length(niveles))) {
      salida[[length(salida) + 1]] <- c(niveles[i], niveles[j])
    }
  }
  salida
}

# ¿Los dos intervalos comparten algún valor?
se_pisan <- function(a, b) a$inferior <= b$superior && b$inferior <= a$superior

calcular_diferencias <- function(datos, variables, parametros, calculado) {
  confianza <- parametros$confianza
  cuales <- which(variables$tipo == "grupo")
  if (length(cuales) == 0) return(list(diferencias = list(), niveles = character(0),
                                       avisos = list()))
  grupo <- variables$nombre[cuales[1]]

  valores_grupo <- columna(datos, grupo)
  niveles <- ordenar(valores_grupo[valores_grupo != ""])
  por_nivel <- lapply(niveles, function(n) datos[valores_grupo == n])
  names(por_nivel) <- niveles

  # Los intervalos de una muestra, tal como quedaron publicados en el paso 1:
  # la pregunta es qué concluiría alguien que mira ESOS intervalos.
  buscar_media <- function(variable, ambito) {
    for (f in calculado$medias) {
      if (f$variable == variable && f$ambito == ambito) return(f)
    }
    NULL
  }
  buscar_proporcion <- function(variable, categoria, ambito) {
    for (f in calculado$proporciones) {
      if (f$metodo == "wilson" && f$variable == variable && f$categoria == categoria &&
          f$ambito == ambito) return(f)
    }
    NULL
  }

  filas <- list()
  avisos <- list()

  agregar <- function(base, ic, uno, dos, tipo) {
    for (aviso in ic$avisos) {
      avisos[[length(avisos) + 1]] <<- list(
        intervalo = tipo, variable = base$variable,
        ambito = paste0(base$grupo_1, " contra ", base$grupo_2),
        detalle = base$categoria, aviso = aviso)
    }
    pisan <- if (!is.null(uno) && !is.null(dos)) se_pisan(uno, dos) else NULL
    excluye <- ic$inferior > 0 || ic$superior < 0
    filas[[length(filas) + 1]] <<- c(base, list(
      diferencia = ic$estimacion, error_estandar = ic$error_estandar,
      gl = ic$gl, critico = ic$critico, inferior = ic$inferior, superior = ic$superior,
      excluye_cero = excluye, se_pisan_los_individuales = pisan,
      conclusion_distinta = isTRUE(pisan) && excluye))
  }

  for (i in seq_along(variables$nombre)) {
    if (variables$tipo[i] != "numerica") next
    for (par in pares(niveles)) {
      x1 <- numeros(por_nivel[[par[1]]], variables$nombre[i])
      x2 <- numeros(por_nivel[[par[2]]], variables$nombre[i])
      if (length(x1) < 2 || length(x2) < 2) next
      ic <- ic_diferencia_medias(mean(x1), desvio(x1), length(x1),
                                 mean(x2), desvio(x2), length(x2), confianza)
      if (is.null(ic)) next
      agregar(list(variable = variables$nombre[i], etiqueta = variables$etiqueta[i],
                   que = "media", categoria = "", grupo_1 = par[1], grupo_2 = par[2],
                   n_1 = as.integer(length(x1)), n_2 = as.integer(length(x2)),
                   estimacion_1 = mean(x1), estimacion_2 = mean(x2)),
              ic, buscar_media(variables$nombre[i], par[1]),
              buscar_media(variables$nombre[i], par[2]), "diferencia de medias")
    }
  }

  for (i in seq_along(variables$nombre)) {
    if (variables$tipo[i] != "categorica") next
    todos <- columna(datos, variables$nombre[i])
    categorias <- ordenar(todos[todos != ""])
    for (categoria in categorias) {
      for (par in pares(niveles)) {
        v1 <- columna(por_nivel[[par[1]]], variables$nombre[i])
        v2 <- columna(por_nivel[[par[2]]], variables$nombre[i])
        v1 <- v1[v1 != ""]
        v2 <- v2[v2 != ""]
        if (length(v1) == 0 || length(v2) == 0) next
        x1 <- sum(v1 == categoria)
        x2 <- sum(v2 == categoria)
        ic <- ic_diferencia_proporciones(x1, length(v1), x2, length(v2), confianza)
        if (is.null(ic)) next
        agregar(list(variable = variables$nombre[i], etiqueta = variables$etiqueta[i],
                     que = "proporción", categoria = categoria,
                     grupo_1 = par[1], grupo_2 = par[2],
                     n_1 = as.integer(length(v1)), n_2 = as.integer(length(v2)),
                     estimacion_1 = x1 / length(v1), estimacion_2 = x2 / length(v2)),
                ic, buscar_proporcion(variables$nombre[i], categoria, par[1]),
                buscar_proporcion(variables$nombre[i], categoria, par[2]),
                "diferencia de proporciones")
      }
    }
  }

  list(diferencias = filas, niveles = niveles, avisos = avisos)
}

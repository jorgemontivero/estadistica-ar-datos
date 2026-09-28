# Paso 1: los intervalos de una sola muestra.
#
# Para cada variable numérica, el intervalo de la media y el de la varianza y
# el desvío. Para cada categórica, el de la proporción de cada categoría, por
# los tres métodos a la vez.
#
# Todo se calcula dos veces: sobre el total y dentro de cada grupo. El «ámbito»
# es la columna que dice cuál de las dos cosas es cada fila.
#
# Los tres métodos para la proporción no están para que elijas el que más te
# guste: están para que veas cuánto se separan cuando la categoría es rara. Con
# 150 casos y 7 becados, Wald y Clopper-Pearson no dicen lo mismo, y el que hay
# que informar es el que no depende de la aproximación normal.

METODOS <- c("wilson", "wald", "clopper-pearson")
TOTAL <- "Total"

# El orden lo fija `method = "radix"`, que ordena por código de carácter y no
# por la configuración regional de la máquina: así R y Python escriben las
# filas en el mismo orden en cualquier computadora.
ordenar <- function(x) sort(unique(x), method = "radix")

# El total primero y después cada grupo, siempre en el mismo orden.
ambitos <- function(datos, grupo) {
  if (is.null(grupo)) return(list(list(nombre = TOTAL, filas = datos)))
  valores <- columna(datos, grupo)
  niveles <- ordenar(valores[valores != ""])
  c(list(list(nombre = TOTAL, filas = datos)),
    lapply(niveles, function(n) list(nombre = n, filas = datos[valores == n])))
}

calcular <- function(datos, variables, parametros) {
  confianza <- parametros$confianza
  poblacion <- parametros$poblacion
  cuales <- which(variables$tipo == "grupo")
  grupo <- if (length(cuales) == 0) NULL else variables$nombre[cuales[1]]

  medias <- list()
  varianzas <- list()
  proporciones <- list()
  avisos <- list()

  anotar <- function(intervalo, tipo, variable, ambito, detalle = "") {
    for (aviso in intervalo$avisos) {
      avisos[[length(avisos) + 1]] <<- list(intervalo = tipo, variable = variable,
                                            ambito = ambito, detalle = detalle, aviso = aviso)
    }
  }

  for (i in seq_along(variables$nombre)) {
    if (variables$tipo[i] != "numerica") next
    for (a in ambitos(datos, grupo)) {
      x <- numeros(a$filas, variables$nombre[i])
      if (length(x) < 2) next
      m <- mean(x)
      s <- desvio(x)
      ic <- ic_media(m, s, length(x), confianza, N = poblacion)
      if (is.null(ic)) next
      medias[[length(medias) + 1]] <- list(
        variable = variables$nombre[i], etiqueta = variables$etiqueta[i], ambito = a$nombre,
        n = as.integer(length(x)), media = m, desvio = s, error_estandar = ic$error_estandar,
        # Los grados de libertad de una media son n − 1: enteros. Los de Welch,
        # en el paso 2, no lo son.
        gl = as.integer(ic$gl), critico = ic$critico, margen = ic$margen,
        inferior = ic$inferior, superior = ic$superior)
      anotar(ic, "media", variables$nombre[i], a$nombre)

      # La varianza no admite corrección por población finita: el intervalo
      # sale de la chi-cuadrado, que no la contempla.
      iv <- ic_varianza(s, length(x), confianza)
      if (is.null(iv)) next
      varianzas[[length(varianzas) + 1]] <- list(
        variable = variables$nombre[i], etiqueta = variables$etiqueta[i], ambito = a$nombre,
        n = as.integer(length(x)), gl = as.integer(iv$gl), varianza = iv$estimacion, desvio = s,
        var_inferior = iv$inferior, var_superior = iv$superior,
        desvio_inferior = sqrt(iv$inferior), desvio_superior = sqrt(iv$superior))
      anotar(iv, "varianza", variables$nombre[i], a$nombre)
    }
  }

  for (i in seq_along(variables$nombre)) {
    if (variables$tipo[i] != "categorica") next
    todos <- columna(datos, variables$nombre[i])
    categorias <- ordenar(todos[todos != ""])
    for (a in ambitos(datos, grupo)) {
      valores <- columna(a$filas, variables$nombre[i])
      valores <- valores[valores != ""]
      if (length(valores) == 0) next
      for (categoria in categorias) {
        exitos <- sum(valores == categoria)
        for (metodo in METODOS) {
          ic <- ic_proporcion(exitos, length(valores), confianza, metodo = metodo, N = poblacion)
          if (is.null(ic)) next
          proporciones[[length(proporciones) + 1]] <- list(
            variable = variables$nombre[i], etiqueta = variables$etiqueta[i],
            categoria = categoria, ambito = a$nombre, n = as.integer(length(valores)),
            exitos = as.integer(exitos), proporcion = ic$estimacion, metodo = metodo,
            inferior = ic$inferior, superior = ic$superior,
            ancho = ic$superior - ic$inferior)
          anotar(ic, paste0("proporción (", metodo, ")"), variables$nombre[i], a$nombre,
                 categoria)
        }
      }
    }
  }

  list(medias = medias, varianzas = varianzas, proporciones = proporciones, avisos = avisos)
}

# Paso 3: el informe en Markdown, listo para pegar.
#
# Cada prueba se informa como se debe informar: el estadístico con sus grados
# de libertad, el valor p exacto y el tamaño del efecto. Nunca «p < 0,05» a
# secas, que no dice ni cuánto ni en qué dirección.
#
# Arriba de todo va lo único que hay que leer antes que nada: en qué
# comparaciones el supuesto decidió la conclusión y no solo la prueba.

SIN_POTENCIA <- "sin-potencia"

# «p = 0,032» o «p < 0,001»: con el «< 0,001» no va el signo igual.
valor_p <- function(nombre, p) {
  texto <- p_texto(p)
  if (startsWith(texto, "<")) paste0(nombre, " ", texto) else paste0(nombre, " = ", texto)
}

# «a», «a y b», «a, b y c»: como se enumera en castellano.
enumerar <- function(cosas) {
  if (length(cosas) == 1) return(cosas[1])
  paste0(paste(cosas[-length(cosas)], collapse = ", "), " y ", cosas[length(cosas)])
}

redactar <- function(supuestos, pruebas, parametros, variables, casos) {
  alfa <- parametros$alfa
  etiqueta_de <- function(nombre) {
    i <- which(variables$nombre == nombre)
    if (length(i) == 0) nombre else variables$etiqueta[i[1]]
  }
  lineas <- c("# Pruebas de hipótesis", "")
  lineas <- c(lineas, paste0("Nivel de significación: α = ", numero_texto(alfa, 2),
                             ". Casos en la base: ", casos, "."))
  lineas <- c(lineas, "",
              paste0("Cada prueba se eligió mirando los supuestos, no al revés. Al lado de ",
                     "cada una está la que se habría corrido con el otro supuesto, para que ",
                     "se vea cuándo la decisión importó."),
              "")

  cambian <- character(0)
  for (f in pruebas$pruebas) {
    if (isTRUE(f$cambia_la_conclusion)) {
      cambian <- c(cambian, paste0(f$etiqueta, " según ", tolower(etiqueta_de(f$factor))))
    }
  }
  if (length(cambian) > 0) {
    lineas <- c(lineas,
                paste0("> **Acá el supuesto decide la conclusión.** En ", enumerar(cambian),
                       " la prueba que corresponde y la alternativa no coinciden en rechazar. ",
                       "En el resto de las comparaciones, discutir el supuesto no cambia lo ",
                       "que hay que escribir."),
                "")
  }

  lineas <- c(lineas, "## Las pruebas", "")
  for (f in pruebas$pruebas) {
    factor <- tolower(etiqueta_de(f$factor))
    partes <- paste0("**", f$etiqueta, " según ", factor, ".** ", f$prueba)
    if (!is.null(f$estadistico) && nzchar(f$simbolo)) {
      gl <- ""
      if (!is.null(f$gl) && !is.null(f$gl2)) {
        gl <- paste0("(", numero_limpio(f$gl, 0), "; ",
                     numero_limpio(f$gl2, decimales_de(f$gl2)), ")")
      } else if (!is.null(f$gl)) {
        gl <- paste0("(", numero_limpio(f$gl, decimales_de(f$gl)), ")")
      }
      partes <- c(partes, paste0(f$simbolo, gl, " = ", numero_limpio(f$estadistico, 3)))
    }
    partes <- c(partes, valor_p("p", f$p))
    if (!is.null(f$efecto)) {
      partes <- c(partes, paste0(f$medida, " = ", numero_texto(f$efecto, 3),
                                 " (", f$calificacion, ")"))
    }
    lineas <- c(lineas, paste0("- ", paste(partes, collapse = ", "), "."))
    lineas <- c(lineas,
                if (!is.null(f$p_alternativa)) {
                  paste0("  Se eligió porque ", f$motivo, ". La alternativa daba ",
                         valor_p("p", f$p_alternativa), ".")
                } else {
                  paste0("  Se eligió porque ", f$motivo, ".")
                })
  }

  sin_potencia <- character(0)
  for (f in supuestos$supuestos) {
    if (identical(f$veredicto, SIN_POTENCIA)) {
      sin_potencia <- c(sin_potencia, paste0(f$etiqueta, " en «", f$grupo, "»"))
    }
  }
  if (length(sin_potencia) > 0) {
    cuales <- enumerar(ordenar(sin_potencia))
    lineas <- c(lineas, "", "## Dónde el supuesto no se pudo probar", "",
                paste0("En ", cuales, " hay menos de quince datos. Con tan pocos, ",
                       "Shapiro-Wilk no tiene potencia para detectar nada: que no rechace no ",
                       "es evidencia de normalidad. Ahí la decisión hay que tomarla por lo ",
                       "que se sabe de cómo se generan los datos."))
  }

  lineas
}

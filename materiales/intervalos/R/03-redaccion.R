# Paso 3: el informe en Markdown, listo para pegar.
#
# Un intervalo no se informa como dos números sueltos. Se informa con la
# estimación adelante, el nivel de confianza dicho, y la unidad puesta: «media
# de 41,0 años (IC 95 % [39,1; 43,0])». Este paso escribe eso, una línea por
# variable, para que copiar y pegar sea más rápido que escribirlo a mano y para
# que nadie se olvide de aclarar el nivel de confianza.
#
# Las proporciones se informan con el método de Wilson, que es el que hay que
# usar salvo que haya una razón para otro. Los otros dos quedan en el CSV.

WILSON <- "wilson"

# «a», «a y b», «a, b y c»: como se enumera en castellano.
enumerar <- function(cosas) {
  if (length(cosas) == 1) return(cosas[1])
  paste0(paste(cosas[-length(cosas)], collapse = ", "), " y ", cosas[length(cosas)])
}

confianza_texto <- function(confianza) {
  pct <- confianza * 100
  decimales <- if (abs(pct - round(pct)) < 1e-9) 0 else 1
  paste0(numero_texto(pct, decimales), " %")
}

redactar <- function(calculado, diferencias, parametros, casos) {
  conf <- confianza_texto(parametros$confianza)
  lineas <- c("# Intervalos de confianza", "")
  lineas <- c(lineas, paste0("Nivel de confianza: ", conf, ". Casos en la base: ", casos, "."))
  if (!is.null(parametros$poblacion)) {
    lineas <- c(lineas, paste0("Población: ", numero_texto(parametros$poblacion, 0),
                               ". Los intervalos de una muestra llevan corrección por ",
                               "población finita."))
  }
  lineas <- c(lineas, "",
              paste0("Un intervalo del ", conf, " no dice que el parámetro esté ahí adentro con ",
                     "probabilidad ", conf, ". Dice que, si se repitiera el muestreo muchas ",
                     "veces, ", conf, " de los intervalos construidos así contendrían al ",
                     "parámetro. El que tenés en la mano lo contiene o no lo contiene."),
              "", "## Medias", "")

  for (f in calculado$medias) {
    if (f$ambito != "Total") next
    d <- decimales_de(f$media)
    lineas <- c(lineas, paste0("- **", f$etiqueta, ".** Media de ", numero_texto(f$media, d),
                               " (IC ", conf, " ", intervalo_texto(f$inferior, f$superior, d),
                               "), n = ", f$n, "."))
  }

  lineas <- c(lineas, "", "## Proporciones", "")
  for (f in calculado$proporciones) {
    if (f$ambito != "Total" || f$metodo != WILSON) next
    lineas <- c(lineas, paste0("- **", f$etiqueta, " — ", f$categoria, ".** ",
                               numero_texto(f$proporcion * 100, 1), " % (IC ", conf, " [",
                               numero_texto(f$inferior * 100, 1), " %; ",
                               numero_texto(f$superior * 100, 1), " %]), ",
                               f$exitos, " de ", f$n, "."))
  }

  if (length(diferencias$diferencias) > 0) {
    lineas <- c(lineas, "", "## Diferencias entre grupos", "")
    # El aviso va una sola vez y arriba, no repetido debajo de cada fila: es la
    # misma advertencia y se lee mejor junta.
    enganosas <- character(0)
    for (f in diferencias$diferencias) {
      if (isTRUE(f$conclusion_distinta)) {
        enganosas <- c(enganosas,
                       if (f$categoria == "") f$etiqueta
                       else paste0(f$etiqueta, " — ", f$categoria))
      }
    }
    if (length(enganosas) > 0) {
      lineas <- c(lineas,
                  paste0("> **Acá no alcanza con mirar los intervalos por separado.** En ",
                         enumerar(enganosas), " los intervalos de los dos grupos se pisan y, ",
                         "sin embargo, el de la diferencia no contiene al cero: mirarlos por ",
                         "separado llevaría a la conclusión contraria. Lo que hay que informar ",
                         "es el intervalo de la diferencia."),
                  "")
    }
    for (f in diferencias$diferencias) {
      que <- if (f$categoria == "") f$etiqueta else paste0(f$etiqueta, " — ", f$categoria)
      if (f$que == "media") {
        d <- decimales_de(f$diferencia)
        valor <- numero_texto(f$diferencia, d)
        rango <- intervalo_texto(f$inferior, f$superior, d)
      } else {
        valor <- paste0(numero_texto(f$diferencia * 100, 1), " puntos")
        rango <- paste0("[", numero_texto(f$inferior * 100, 1), "; ",
                        numero_texto(f$superior * 100, 1), "]")
      }
      marca <- if (isTRUE(f$conclusion_distinta)) " ←" else ""
      lineas <- c(lineas, paste0("- **", que, ".** ", f$grupo_1, " menos ", f$grupo_2, ": ",
                                 valor, " (IC ", conf, " ", rango, ").", marca))
    }

    if (length(diferencias$niveles) > 2) {
      lineas <- c(lineas, "",
                  paste0("Hay ", length(diferencias$niveles), " grupos, así que cada variable se ",
                         "compara de a pares. Cada uno de esos intervalos es del ", conf,
                         " por separado: mirados en conjunto, la confianza es menor. Si la ",
                         "conclusión depende de compararlos todos, corresponde un método que lo ",
                         "tenga en cuenta."))
    }
  }

  lineas
}

# Paso 4: el informe, escrito en castellano.
#
# Lo mismo que hacen los otros descargables de la serie: lo que el proyecto
# calculó, redactado para pegar. Ningún número aparece acá si no está también
# en un CSV, y ninguna conclusión se escribe más fuerte de lo que la tabla la
# sostiene.

mayuscula <- function(x) paste0(toupper(substring(x, 1, 1)), substring(x, 2))

con_signo <- function(x) paste0(if (x >= 0) "+" else "-", abs(x))

redactar <- function(parametros, tasas, indirectas, referencia, sensibles, niveles_,
                     comparaciones, avisos, grupos) {
  conf <- paste0(numero_texto(parametros$confianza * 100, 0), " %")
  por <- numero_texto(parametros$multiplicador, 0)
  lineas <- c("# Tasas estandarizadas por edad", "")

  casos <- sum(vapply(tasas, function(f) f$casos, numeric(1)))
  expuestos <- sum(vapply(tasas, function(f) f$expuestos, numeric(1)))
  lineas <- c(lineas, paste0(
    length(tasas), " poblaciones, ", length(grupos), " grupos de edad, ",
    numero_texto(casos, 0), " casos sobre ", numero_texto(expuestos, 0),
    " personas. Estándar: «", parametros$estandar, "». Las tasas van por ", por, "."), "")

  # Lo primero que hay que leer: el vuelco.
  cambios <- vapply(tasas, function(f) abs(f$cambio_de_rango), numeric(1))
  vuelco <- tasas[[which.max(cambios)]]
  if (abs(vuelco$cambio_de_rango) >= 3) {
    promedio <- sum(vapply(tasas, function(f) f$proporcion_en_el_grupo_mayor,
                           numeric(1))) / length(tasas)
    lineas <- c(lineas, paste0(
      "> **La tasa cruda y la ajustada no ordenan igual.** «", vuelco$poblacion,
      "» está en el puesto ", vuelco$rango_crudo, " de ", length(tasas),
      " por su tasa cruda —", tasa_texto(vuelco$cruda), " por ", por, "— y en el ",
      vuelco$rango_estandarizado, " por la ajustada, que es ",
      tasa_texto(vuelco$estandarizada), ". No cambió ningún dato: cambió la estructura ",
      "de edad con la que se los pesa. El ",
      porcentaje(vuelco$proporcion_en_el_grupo_mayor), " de su población está en el ",
      "grupo de «", grupos[length(grupos)], "», contra el ", porcentaje(promedio),
      " del promedio de las poblaciones."), "")
  }

  # ------------------------------------------------------------ el ranking
  lineas <- c(lineas, "## Las tasas ajustadas, de mayor a menor", "",
              paste0("| Población | Cruda | Ajustada | IC ", conf,
                     " | Puesto crudo → ajustado |"),
              "| --- | --- | --- | --- | --- |")
  for (f in tasas) {
    flecha <- paste0(f$rango_crudo, " → ", f$rango_estandarizado)
    if (f$cambio_de_rango != 0) {
      flecha <- paste0(flecha, " (", con_signo(f$cambio_de_rango), ")")
    }
    lineas <- c(lineas, paste0(
      "| ", f$poblacion, " | ", tasa_texto(f$cruda), " | ", tasa_texto(f$estandarizada),
      " | ", tasa_texto(f$estandarizada_inferior), " a ",
      tasa_texto(f$estandarizada_superior), " | ", flecha, " |"))
  }
  lineas <- c(lineas, "")

  mas_alta <- tasas[[1]]
  mas_baja <- tasas[[length(tasas)]]
  lineas <- c(lineas, paste0(
    "De ", tasa_texto(mas_alta$estandarizada), " en «", mas_alta$poblacion, "» a ",
    tasa_texto(mas_baja$estandarizada), " en «", mas_baja$poblacion, "»: ",
    numero_texto(mas_alta$estandarizada / mas_baja$estandarizada, 2),
    " veces. Con las tasas crudas la distancia entre esas dos es de ",
    numero_texto(mas_alta$cruda / mas_baja$cruda, 2), " veces."), "")

  # ------------------------------------------------------ el estándar
  if (length(sensibles) > 0 || length(niveles_) > 0) {
    lineas <- c(lineas, "## Cuánto depende del estándar elegido", "")
    razones <- vapply(niveles_, function(f) if (is.na(f$razon_entre_niveles)) 0
                      else f$razon_entre_niveles, numeric(1))
    peor <- niveles_[[which.max(razones)]]
    lineas <- c(lineas, paste0(
      "Mucho, en el nivel. La tasa de «", peor$poblacion, "» va de ",
      tasa_texto(peor$menor), " con el estándar «", peor$estandar_del_menor, "» a ",
      tasa_texto(peor$mayor), " con «", peor$estandar_del_mayor, "»: ",
      numero_texto(peor$razon_entre_niveles, 2),
      " veces, con los mismos datos y el mismo método. **Una tasa ajustada sin el nombre ",
      "de su estándar al lado no quiere decir nada.**"), "")
    if (length(sensibles) > 0) {
      pisados <- sum(vapply(sensibles, function(f) f$se_pisan_con_los_dos, logical(1)))
      lineas <- c(lineas, paste0(
        "Y algo, en el orden. Se dan vuelta ", length(sensibles), " pares de poblaciones ",
        "según con qué estándar se los mire, y en ", pisados, " de esos ",
        length(sensibles), " los intervalos se pisan con los dos estándares: ahí el ",
        "estándar decide un orden que no estaba decidido, y no se pierde nada. Los otros ",
        length(sensibles) - pisados, " son el caso incómodo: con uno de los dos ",
        "estándares los intervalos **no** se pisan, así que la diferencia parecía ",
        "establecida y con el otro estándar se da vuelta. Están par por par en ",
        "`sensibilidad.csv`."))
    } else {
      lineas <- c(lineas, paste0(
        "Y nada, en el orden: con estos datos ningún par se da vuelta al cambiar de ",
        "estándar. No es una garantía —puede pasar, y pasa cuando las curvas de tasas ",
        "por edad se cruzan— pero acá no pasó."))
    }
    lineas <- c(lineas, "")
  }

  # ------------------------------------------------------------ la indirecta
  lineas <- c(lineas, "## La razón estandarizada", "", paste0(
    "Referencia: ", referencia$nombre, ", con una tasa cruda de ",
    tasa_texto(referencia$cruda * parametros$multiplicador), " por ", por,
    ". La razón compara los casos observados con los que habría si esta población ",
    "tuviera las tasas de la referencia a cada edad."), "")
  distintas <- Filter(function(f) f$distinta_de_uno, indirectas)
  lineas <- c(lineas, paste0(
    "En ", length(distintas), " de ", length(indirectas), " poblaciones el intervalo de ",
    "la razón no contiene al uno. En las otras ", length(indirectas) - length(distintas),
    ", la mortalidad no se distingue de la que la estructura de edad hacía esperar."), "")
  if (length(indirectas) > 0) {
    arriba <- indirectas[[1]]
    abajo <- indirectas[[length(indirectas)]]
    lineas <- c(lineas, paste0(
      "La más alta es «", arriba$poblacion, "», con ", numero_texto(arriba$razon, 3),
      " [", numero_texto(arriba$razon_inferior, 3), "; ",
      numero_texto(arriba$razon_superior, 3), "]: ", numero_texto(arriba$observados, 0),
      " casos contra ", numero_texto(arriba$esperados, 0), " esperados. La más baja es «",
      abajo$poblacion, "», con ", numero_texto(abajo$razon, 3), "."), "")
  }

  # ------------------------------------------------------- las comparaciones
  if (length(comparaciones) > 0) {
    lineas <- c(lineas, "## Los pares comparados", "")
    for (c_ in comparaciones) {
      lineas <- c(lineas, paste0("### ", c_$poblacion_a, " contra ", c_$poblacion_b), "")
      lineas <- c(lineas, paste0(
        "Tasas crudas: ", tasa_texto(c_$cruda_a), " y ", tasa_texto(c_$cruda_b),
        ", una diferencia de ", tasa_texto(c_$diferencia_cruda), ". Ajustadas: ",
        tasa_texto(c_$estandarizada_a), " y ", tasa_texto(c_$estandarizada_b),
        if (isTRUE(c_$se_dan_vuelta)) ", que van para el lado contrario."
        else ", que van para el mismo lado."), "")
      lineas <- c(lineas, paste0(
        "De esa diferencia cruda, ", tasa_texto(c_$efecto_estructura), " (",
        porcentaje(c_$parte_estructura), ") es **estructura** —las dos poblaciones ",
        "tienen edades distintas— y ", tasa_texto(c_$efecto_tasas),
        " es **riesgo**: lo que cambia a cada edad. Los dos sumandos suman exactamente ",
        "la diferencia, y ese es el control de la cuenta."), "")
      if (!is.na(c_$razon)) {
        lineas <- c(lineas, paste0(
          "La razón entre las dos tasas ajustadas es ", numero_texto(c_$razon, 3),
          ", IC ", conf, " [", numero_texto(c_$razon_inferior, 3), "; ",
          numero_texto(c_$razon_superior, 3), "]",
          if (isTRUE(c_$la_razon_excluye_al_uno)) "."
          else ", que contiene al uno: la diferencia no está establecida."), "")
      }
    }
  }

  # --------------------------------------------------------------- avisos
  if (length(avisos) > 0) {
    lineas <- c(lineas, "## Qué revisar antes de publicar esto", "")
    for (a in avisos) {
      lineas <- c(lineas, paste0("- **", mayuscula(a$donde), ".** ", a$aviso))
    }
    lineas <- c(lineas, "")
  }

  lineas
}

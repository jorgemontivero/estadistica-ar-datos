# Paso 1: mirar el archivo antes de tocarlo.
#
# Escribe salidas/perfil.csv: una fila por columna del archivo crudo, con lo
# que hay y con lo que conviene sospechar. Este paso no cambia ningún dato.

COLUMNAS_PERFIL <- c("columna", "en_diccionario", "tipo_declarado", "tipo_detectado", "n",
                     "faltantes", "pct_faltantes", "distintos", "ejemplo", "sospecha")

# Qué parece la columna, mirando todos sus valores no vacíos.
tipo_detectado <- function(valores, decimal) {
  llenos <- valores[valores != ""]
  if (length(llenos) == 0) return("vacía")
  numeros <- lapply(llenos, function(v) a_numero(v, decimal)$numero)
  if (all(!vapply(numeros, is.null, logical(1)))) {
    enteros <- all(vapply(numeros, function(n) n == as.integer(n), logical(1)))
    return(if (enteros) "entero" else "decimal")
  }
  if (all(!vapply(llenos, function(v) is.null(a_fecha(v)), logical(1)))) return("fecha")
  "texto"
}

# Lo que conviene mirar antes de confiar en la columna.
sospecha <- function(valores, tipo, en_diccionario, decimal) {
  llenos <- valores[valores != ""]
  if (!en_diccionario) return("No está en el diccionario: no pasa a la base limpia")
  if (length(llenos) == 0) return("No tiene un solo dato")
  if (length(valores) - length(llenos) > length(valores) / 2) return("Más de la mitad está vacía")
  if (length(unique(llenos)) == 1) return("Toda la columna tiene el mismo valor")
  if (tipo %in% c("entero", "decimal") &&
      any(vapply(llenos, function(v) a_numero(v, decimal)$convertido, logical(1)))) {
    return("Números guardados como texto: traen comas o separadores de miles")
  }
  if (length(unique(tolower(llenos))) < length(unique(llenos))) {
    return("La misma categoría escrita con mayúsculas y con minúsculas")
  }
  ""
}

perfilar <- function(crudo, diccionario) {
  declarado <- setNames(diccionario$tipo, diccionario$nombre)
  filas <- lapply(crudo$columnas, function(columna) {
    valores <- limpiar_texto(vapply(crudo$filas, function(f) f[[columna]], character(1)))
    llenos <- valores[valores != ""]
    tipo <- tipo_detectado(valores, crudo$decimal)
    en_dic <- columna %in% diccionario$nombre
    data.frame(
      columna = columna,
      en_diccionario = en_dic,
      tipo_declarado = if (en_dic) unname(declarado[[columna]]) else "",
      tipo_detectado = tipo,
      n = length(valores),
      faltantes = length(valores) - length(llenos),
      pct_faltantes = if (length(valores) > 0) (length(valores) - length(llenos)) / length(valores) * 100 else 0,
      distintos = length(unique(llenos)),
      ejemplo = if (length(llenos) > 0) llenos[1] else "",
      sospecha = sospecha(valores, tipo, en_dic, crudo$decimal),
      stringsAsFactors = FALSE
    )
  })
  perfil <- do.call(rbind, filas)
  perfil$n <- as.integer(perfil$n)
  perfil$faltantes <- as.integer(perfil$faltantes)
  perfil$distintos <- as.integer(perfil$distintos)
  escribir_csv(perfil, "salidas/perfil.csv", COLUMNAS_PERFIL)
  perfil
}

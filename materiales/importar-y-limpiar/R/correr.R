# Mira el archivo crudo, lo perfila y lo limpia.
#
#     source("R/correr.R")
#
# Desde la carpeta del proyecto, no desde R/.

CRUDO <- "datos/crudos/encuesta.csv"
DICCIONARIO <- "datos/crudos/diccionario.csv"

for (archivo in c(CRUDO, DICCIONARIO)) {
  if (!file.exists(archivo)) {
    stop(paste0("No encuentro ", archivo, ". ¿Estás parado en la carpeta del proyecto?"))
  }
}

source("R/comun.R")
source("R/01-perfilar.R")
source("R/02-limpiar.R")

crudo <- leer_crudo(CRUDO)

claves <- c("nombre", "tipo", "minimo", "maximo", "codigos", "faltante", "id")
filas_dic <- leer_crudo(DICCIONARIO)$filas
diccionario <- as.data.frame(
  setNames(lapply(claves, function(clave) {
    vapply(filas_dic, function(f) if (is.null(f[[clave]])) "" else f[[clave]], character(1))
  }), claves),
  stringsAsFactors = FALSE
)
diccionario <- diccionario[diccionario$nombre != "", ]

perfil <- perfilar(crudo, diccionario)
limpio <- limpiar(crudo, diccionario)

nombre_separador <- c("," = "coma", ";" = "punto y coma", "\t" = "tabulador")[[crudo$separador]]
resumen <- data.frame(
  clave = c("separador_detectado", "decimal_detectado", "filas_crudas", "columnas_crudas",
            "columnas_sin_declarar", "variables_del_diccionario", "filas_repetidas",
            "filas_limpias", "valores_modificados", "valores_vacios"),
  valor = c(nombre_separador,
            if (crudo$decimal == ",") "coma" else "punto",
            as.character(length(crudo$filas)),
            as.character(length(crudo$columnas)),
            as.character(sum(!perfil$en_diccionario)),
            as.character(nrow(diccionario)),
            as.character(limpio$duplicadas),
            as.character(limpio$filas),
            as.character(limpio$modificados),
            as.character(limpio$vacios)),
  stringsAsFactors = FALSE
)
escribir_csv(resumen, "salidas/resumen.csv", c("clave", "valor"))

cat("Listo. Salidas en salidas/:\n")
cat("  perfil.csv, cambios.csv, resumen.csv · base limpia en datos/limpios/base.csv\n")
cat(sprintf("  %d filas crudas → %d limpias, %d valores modificados\n",
            length(crudo$filas), limpio$filas, limpio$modificados))

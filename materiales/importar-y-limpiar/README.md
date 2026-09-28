# Importar, revisar y limpiar

Un CSV que llegó de cualquier lado y un diccionario que dice qué tiene que
haber en cada variable. El script mira el archivo, informa lo que encuentra y
después lo limpia dejando anotado cada cambio.

Está en R y en Python, y las dos versiones escriben exactamente los mismos
archivos. No usa ningún paquete.

## Cómo se corre

```r
source("R/correr.R")      # en R, desde la carpeta del proyecto
```

```bash
python python/correr.py   # en Python
```

## Qué escribe

| Archivo | Qué es |
|---|---|
| `salidas/perfil.csv` | Una fila por columna del archivo crudo: qué tipo parece, cuántos faltantes tiene, cuántos valores distintos, un ejemplo y qué sospechar |
| `datos/limpios/base.csv` | La base ya limpia, con las variables del diccionario y en su orden |
| `salidas/cambios.csv` | Una fila por variable y regla aplicada, con cuántos valores tocó |
| `salidas/resumen.csv` | Los números del proceso: filas, columnas, duplicados, valores modificados |

## El diccionario

`datos/crudos/diccionario.csv` es lo que decide todo. Una fila por variable:

| Columna | Qué va |
|---|---|
| `nombre` | El nombre de la columna en el archivo crudo |
| `tipo` | `entero`, `decimal`, `categoria`, `fecha` o `texto` |
| `minimo`, `maximo` | Para `entero` y `decimal`. Se pueden dejar vacíos |
| `codigos` | Para `categoria`: los valores válidos, separados por punto y coma |
| `faltante` | El código que significa «no contestó»: 99, 999, `NS`. Se pasa a vacío |
| `id` | `Sí` en la variable que identifica el caso. Las filas repetidas se descartan |

Es el mismo diccionario que la [planilla de carga con
validaciones](https://estadistica.ar/herramientas/plantilla-carga-datos/) del
sitio: si cargaste los datos con esa planilla, ya lo tenés escrito.

## Las reglas, en orden

Están acá para que se puedan discutir. Cambiarlas es editar dos funciones.

**Al leer el archivo:**

1. Se saca la marca de orden de bytes (el BOM) que dejan algunos programas.
2. **El separador se detecta:** se prueban la coma, el punto y coma y el
   tabulador, y gana el que parte el encabezado en más columnas.
3. **El decimal se detecta:** si hay más valores con forma de `1.234,56` que
   de `1,234.56`, el decimal es la coma. Con la coma decimal, el punto es
   separador de miles, y al revés.
4. A cada valor se le sacan los espacios de las puntas y se le colapsan los
   de adentro.

**Al limpiar cada variable, en este orden:**

1. Si el valor es igual al **código de faltante**, queda vacío.
2. `entero` y `decimal`: se saca el separador de miles y se pasa la coma
   decimal a punto; si no es un número, queda vacío; si `entero` tiene
   decimales, queda vacío; si cae fuera de `minimo`–`maximo`, queda vacío.
3. `categoria`: se compara con la lista de `codigos` sin distinguir
   mayúsculas; si no está, queda vacío; si está, se escribe como figura en el
   diccionario.
4. `fecha`: se aceptan `dd/mm/aaaa` y `aaaa-mm-dd`, y se escribe siempre
   `aaaa-mm-dd`; si no se puede leer, queda vacío.
5. `texto`: queda el texto sin espacios de más.

Las filas repetidas según la variable marcada como `id` se descartan: se queda
la primera.

**Nada se corrige en silencio.** Cada valor que cambia queda contado en
`cambios.csv`, por variable y por regla. Si una variable tiene 40 valores
«fuera de rango», eso no es un detalle de limpieza: es un problema del
relevamiento y hay que mirarlo antes de seguir.

## Lo que el perfil sospecha

- **Números guardados como texto**: la columna es numérica pero venía con
  comas, espacios o separadores de miles.
- **Mayúsculas y minúsculas mezcladas**: «Control» y «CONTROL» conviviendo.
- **Constante**: un solo valor en toda la columna.
- **Casi todo faltante**: más de la mitad vacía.
- **No está en el diccionario**: la columna existe en el archivo pero nadie la
  declaró. No pasa a la base limpia.

## Los datos de ejemplo

Un CSV exportado como lo exporta Excel en español: separado por punto y coma,
con coma decimal, con BOM, con espacios de más, con una categoría escrita de
tres maneras, con códigos de faltante, con fechas en dos formatos, con una fila
repetida y con una columna que nadie declaró.

Plantilla de estadistica.ar · CC BY-NC-SA 4.0

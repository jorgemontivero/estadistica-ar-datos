# De dónde salió cada número

Los datos de este proyecto **son reales**. No hay nada simulado: son ocho
indicadores de las 24 jurisdicciones argentinas y una tabla de nivel educativo,
calculados sobre las bases del Censo 2022. Esta ficha dice de qué variable salió
cada columna y con qué criterio se agregó, que es lo único que hace auditable a
una tabla que ya viene sumada.

## Fuente

Censo Nacional de Población, Hogares y Viviendas 2022 (INDEC), bases de personas
y de hogares por provincia.

El universo es **población y hogares en viviendas particulares**: la base de
viviendas colectivas no trae ni edades ni condiciones habitacionales, así que no
se puede repartir. Son unas cuatro personas de cada mil y quedan afuera de todas
las jurisdicciones por igual.

## `indicadores.csv`

24 filas y 8 columnas, en tres unidades de medida distintas. **Esa mezcla es a
propósito**: es la situación en la que un PCA sin tipificar deja de significar
nada, y el proyecto la usa para mostrarlo.

| Columna | Qué es | Unidad | De dónde sale |
| --- | --- | --- | --- |
| `poblacion` | Personas en viviendas particulares | personas | filas de la base de personas |
| `nbi` | Hogares con al menos una necesidad básica insatisfecha | % | `nbi_tot` = 1 |
| `hacinamiento` | Hogares con NBI de hacinamiento | % | `nbi_hac` = 1 |
| `sin_saneamiento` | Hogares con NBI sanitaria | % | `nbi_san` = 1 |
| `escolaridad` | Años de escolaridad de las personas de 25 y más | años | media de `aesc` |
| `tamano_del_hogar` | Personas por hogar | personas | personas ÷ hogares |
| `mayores` | Personas de 65 y más | % | `edad` ≥ 65 |
| `desocupacion` | Desocupados sobre población económicamente activa | % | `condact` |

Las cinco necesidades básicas insatisfechas vienen **ya calculadas** en la base
de hogares, con 1 para «la tiene» y 2 para «no la tiene». No se recalcula nada:
se cuenta.

### Criterios

- **Los años de escolaridad** se promedian sobre las personas de 25 años y más
  con dato válido. El 99 es «ignorado» y no entra; tampoco los nulos.
- **La condición de actividad** solo existe para las personas de 14 y más, que es
  el universo con el que se define. La desocupación va sobre la población
  económicamente activa —ocupados más desocupados— y no sobre el total.

## `educacion.csv`

24 filas y 5 columnas: la cantidad de personas de 25 y más con dato válido de
escolaridad, en cada tramo de años aprobados. Suma 26.711.969 personas.

Es una **partición**: cada persona cae en un tramo y solo en uno. Eso importa
porque el análisis de correspondencias está definido para tablas de contingencia,
y una tabla de respuestas múltiples —por ejemplo, los cinco tipos de NBI, que un
mismo hogar puede tener a la vez— no lo es.

Los cortes están donde están los títulos: el secundario completo son doce años y
el universitario, diecisiete.

| Tramo | Qué agrupa |
| --- | --- |
| Hasta 6 años | Primaria incompleta o menos |
| De 7 a 11 | Primaria completa, secundaria incompleta |
| 12 años | Secundaria completa |
| De 13 a 16 | Superior incompleta o completa corta |
| 17 y más | Universitario completo y posgrado |

## Cómo volver a armarlos

Está en `descargables/extraer_multivariado.py`, en el repositorio del sitio. Lee
el espejo local del Censo y deja escritos estos dos archivos. No hace falta para
usar el proyecto: los archivos ya están acá.

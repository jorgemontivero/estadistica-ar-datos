# De dónde salió cada número

Los datos de este proyecto **son reales**. No hay nada simulado: son las
defunciones y la población de las 24 jurisdicciones argentinas en 2022, tal
como las publican la DEIS y el INDEC. Esta ficha dice de qué archivo salió cada
columna y con qué criterio se agregó, que es lo único que hace auditable a una
tabla que ya viene sumada.

## `mortalidad-2022.csv`

384 filas: 24 jurisdicciones × 16 grupos de edad.

### `defunciones`

**Fuente.** Dirección de Estadísticas e Información de la Salud (DEIS),
Ministerio de Salud de la Nación. «Defunciones ocurridas en la República
Argentina en el año 2022», archivo `defweb22_0.csv`.

Es un tabulado y no un microdato: cada fila del original es una celda
—jurisdicción de residencia × sexo × causa × grupo de edad— con su conteo. Suma
**397.115** defunciones, que es el total publicado para 2022.

**Qué se descartó.**

| Motivo | Defunciones |
| --- | --- |
| Residencia en otro país (código 98) o sin especificar (99) | 1.460 |
| Edad sin especificar | 715 |
| **Quedan** | **394.940** |

### `poblacion`

**Fuente.** Censo Nacional de Población, Hogares y Viviendas 2022 (INDEC), base
de personas por provincia.

**El universo es la población en viviendas particulares**: 45.618.787 personas,
el 99,1 % del total censado. La base de viviendas colectivas trae el total de
cada vivienda pero no las edades de sus habitantes, así que no se puede repartir
por grupo. Quedan afuera cuatro personas de cada mil, y quedan afuera de todas
las jurisdicciones por igual.

**El numerador cubre a todos y el denominador no**, así que las tasas salen muy
levemente altas. Es uniforme entre jurisdicciones, que es lo que importa para
comparar, pero conviene saberlo antes de citar un nivel.

### El desfasaje de fechas

El denominador es la población censada al **18 de mayo de 2022** y el numerador
son las defunciones del **año entero**. Es la práctica habitual —la población
censal se toma como población a mitad de año— y es una de las razones por las
que un año censal es el más cómodo para este tipo de cuenta: en cualquier otro
año habría que usar una proyección, que es una estimación más.

### Los grupos de edad

Son los del archivo de defunciones, que es el más grueso de los dos y por lo
tanto el que manda.

El primero es **0 a 9** y no «0 a 4». El archivo trae «menor de 1 año» y «1 a
9», y no hay forma de partir el segundo, así que hay que juntarlos. Es una
pérdida real: adentro de ese grupo la mortalidad infantil convive con la más
baja de toda la vida, y esa mezcla no la arregla ninguna estandarización. Es el
ejemplo más claro de que **el ajuste no puede corregir lo que el agrupamiento
ya perdió**.

El último es **80 y más**, que también es el que trae el archivo.

## `estandares.csv`

Tres poblaciones estándar, con los mismos 16 grupos.

| Columna | Qué es | Suma |
| --- | --- | --- |
| `oms` | Población estándar mundial de la OMS (2000-2025), versión SEER | 1.000.000 |
| `europea` | Población estándar europea 2013 (ESP2013) | 100.000 |
| `argentina` | La estructura del país, de los mismos datos del censo | 45.618.787 |

Las dos primeras están publicadas por grupos quinquenales hasta 85+ o 95+; acá
vienen con los grupos de arriba y de abajo **sumados** para que calcen con los
16 del archivo de defunciones. Sumar grupos de una estándar es legítimo y no
cambia nada: lo único que importa de una población estándar es la proporción
que representa cada grupo.

La tercera sale de sumar la columna `poblacion` de `mortalidad-2022.csv` sobre
las 24 jurisdicciones. Es la que usa la DEIS cuando compara provincias contra el
total del país, y la que hay que usar para comparar adentro de Argentina; las
otras dos sirven para comparar Argentina contra otros países.

## Cómo volver a armarlos

Está en `descargables/extraer_estandarizacion.py`, en el repositorio del sitio.
Lee el espejo local de la DEIS y del Censo y deja escritos estos dos archivos.
No hace falta para usar el proyecto: los archivos ya están acá.

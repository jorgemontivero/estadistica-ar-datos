# Pruebas de hipótesis con verificación de supuestos

Para cada variable y cada agrupamiento: se miran los supuestos, se elige la
prueba que corresponde, se corre también la que no corresponde, y se escribe
cuándo esa decisión cambió la conclusión. En R y en Python.

## Cómo se corre

```r
source("R/correr.R")      # en R, desde la carpeta del proyecto
```

```bash
python python/correr.py   # en Python
```

## Qué deja

| Archivo | Qué trae |
|---|---|
| `normalidad.csv` | Shapiro-Wilk dentro de cada grupo, con el veredicto |
| `homogeneidad.csv` | Levene con centro en la mediana, y si decide algo o no |
| `esperadas.csv` | La frecuencia esperada más chica de cada tabla |
| `pruebas.csv` | La prueba elegida, por qué, el tamaño del efecto y la alternativa |
| `avisos.csv` | Cada supuesto que no se cumple, con la variable que lo disparó |
| `pruebas.md` | El informe redactado, listo para pegar |
| `resumen.csv` | Cuántas comparaciones, cuántas significativas, cuántas dudosas |

## El orden importa: primero el supuesto, después la prueba

El árbol de decisión de [estadistica.ar](https://estadistica.ar/herramientas/selector-de-prueba)
da un par para cada situación: una prueba y una alternativa. El árbol no mira
los datos —no puede, son seis preguntas—, así que quién de las dos corresponde
lo deciden los supuestos:

| Situación | Prueba | Si el supuesto falla |
|---|---|---|
| Dos grupos, los dos normales | t de Welch | Mann-Whitney |
| Tres o más, todos normales, varianzas homogéneas | ANOVA | ANOVA de Welch |
| Tres o más, alguno no normal | — | Kruskal-Wallis |
| Categórica, todas las esperadas ≥ 5 | Chi-cuadrado | Fisher (solo 2×2) |

**Shapiro-Wilk se corre dentro de cada grupo, no sobre la variable entera.**
El supuesto es sobre la distribución dentro de cada grupo; mezclarlos, cuando
tienen medias distintas, es probar otra cosa y casi siempre rechazar.

**Levene se informa siempre, pero con dos grupos no decide nada.** La prueba
que corresponde ahí es la de Welch, que no supone varianzas iguales. La
columna `decide` lo dice explícitamente.

## Lo que este proyecto quiere que no te pase

**Que elijas la prueba después de ver el resultado.** Por eso las dos se
corren siempre y las dos quedan escritas: la que corresponde y la alternativa.
La columna `cambia_la_conclusion` dice «Sí» cuando las dos no coinciden en
rechazar.

Es la única situación en la que discutir el supuesto cambia el informe. En
todas las demás, la discusión es académica: las dos pruebas dicen lo mismo y
el resultado no depende de cuál se eligió.

En los datos de ejemplo pasa con el gasto en materiales, y pasa por algo
concreto: unos pocos gastos enormes inflan la varianza del grupo control. La
prueba t, que compara medias, no encuentra diferencia; Mann-Whitney, que
compara rangos, la encuentra con claridad. La que corresponde es la segunda,
porque el supuesto de normalidad no se cumple.

## Lo que sí o sí sale escrito

**El tamaño del efecto, siempre.** Un valor p dice que algo pasa; no dice
cuánto. Cada fila lleva la medida que corresponde a su prueba —d de Hedges,
r de rangos, eta², épsilon² o V de Cramér— con la etiqueta de Cohen al lado.

Esa etiqueta conviene usarla con pinzas: Cohen publicó esos cortes
advirtiendo que eran provisorios. Una d de 0,2 puede ser enorme si se trata de
mortalidad y despreciable si se trata de un puntaje de satisfacción.

**El estadístico con sus grados de libertad y el valor p exacto.** Nunca
«p < 0,05» a secas.

## Lo que no hace

**No corrige por comparaciones múltiples.** Cada prueba es de a una. Si el
informe depende de mirarlas todas, corresponde una corrección.

**No hace post hoc.** Un ANOVA significativo dice que algún grupo difiere, no
cuál.

**No trae la prueba exacta de Fisher para tablas de más de 2×2.** R y SciPy no
la resuelven igual, y este proyecto no publica nada que dé distinto en cada
idioma. Con esperadas muy chicas en una tabla grande, conviene juntar
categorías.

**No cubre datos apareados ni relacionados.** Todas las comparaciones son
entre grupos independientes.

## Los parámetros

`datos/parametros.csv` tiene uno solo: `alfa`. Cambiarlo cambia los veredictos
de normalidad, de homogeneidad y de significación, todos a la vez, que es como
tiene que ser.

## Los dos idiomas

Las dos versiones escriben los siete archivos, byte a byte iguales. Las
opciones están puestas a mano y no por omisión —Welch sí, corrección de
continuidad no, corrección de Yates no, Mann-Whitney por la aproximación
normal— porque los valores por omisión de R y de SciPy no son los mismos.

La ANOVA de Welch y Levene están escritas a mano en los dos idiomas: R trae la
primera y no la segunda, SciPy trae la segunda y no la primera, y escribirlas
una vez en cada lado es lo único que garantiza que calculen lo mismo.

Plantilla de estadistica.ar · CC BY-NC-SA 4.0

# Descriptivos y tabla 1

Los descriptivos de cada variable y la tabla que abre todo informe: una fila
por variable, una columna por grupo, con la comparación al lado.

Está en R y en Python, y las dos versiones escriben exactamente los mismos
archivos. En R alcanza con lo que ya trae; en Python hace falta SciPy, y solo
para los valores p.

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
| `salidas/tabla1.md` | La tabla 1 en Markdown, para pegar en el informe |
| `salidas/tabla1.csv` | La misma tabla, para seguir trabajándola |
| `salidas/descriptivos.csv` | Las numéricas completas: n, media, desvío, mínimo, cuartiles, máximo, asimetría |
| `salidas/frecuencias.csv` | Las categóricas: n y porcentaje de cada categoría |
| `salidas/resumen.csv` | Cuántos casos, variables, grupos y cuántas resultaron asimétricas |

## Qué se configura

`datos/variables.csv`, una fila por variable:

| Columna | Qué va |
|---|---|
| `nombre` | El nombre de la columna en `datos/base.csv` |
| `etiqueta` | Cómo se llama en la tabla. Si está vacía, se usa el nombre |
| `tipo` | `numerica`, `categorica` o `grupo` |

La variable marcada como `grupo` es la que abre las columnas de la tabla. Si no
hay ninguna, sale la tabla con la columna total sola y sin comparaciones.

## Las decisiones que toma sola

**Media o mediana.** Con |asimetría| > 1 la variable se informa como
`mediana [Q1–Q3]`; si no, como `media (DE)`. Es la misma regla que usa la
calculadora de descriptivos del sitio, y evita lo de siempre: informar media en
una tabla y mediana en otra para la misma variable.

**Qué prueba.** Sale del tipo de variable, de cuántos grupos hay y de la forma:

| | 2 grupos | 3 o más |
|---|---|---|
| Numérica simétrica | t de Welch | ANOVA |
| Numérica asimétrica | Mann-Whitney | Kruskal-Wallis |
| Categórica | Chi-cuadrado | Chi-cuadrado |

Las opciones están puestas a mano y no por omisión —Welch sí, corrección de
continuidad no, corrección de Yates no—, porque los valores por omisión de R y
de SciPy no son los mismos y, sin fijarlas, los dos idiomas darían números
distintos. Cuando alguna frecuencia esperada del chi-cuadrado es menor que 5,
la tabla lo dice en una nota.

**Cuántos decimales.** Uno si el valor llega a 10, dos si es menor. Una media
de 41,3 con dos decimales finge una precisión que no hay; una de 0,42 con uno
se queda corta.

## Sobre los valores p en la tabla 1

Están porque se piden, no porque sean buena idea en todos los casos. En un
estudio experimental con asignación al azar, comparar los grupos al inicio
prueba algo que ya se sabe —que la asignación fue al azar—, y lo que importa es
el tamaño de la diferencia, no si es significativa. En un estudio
observacional, en cambio, esa comparación sí informa sobre la comparabilidad de
los grupos.

Si la tabla no los necesita, borrar la columna `p` es una línea.

## Los datos de ejemplo

Una muestra ficticia de 150 casos con dos grupos, dos variables numéricas
—una simétrica y otra claramente asimétrica, para que se vea el cambio de
media a mediana—, dos categóricas y algunos faltantes.

Plantilla de estadistica.ar · CC BY-NC-SA 4.0

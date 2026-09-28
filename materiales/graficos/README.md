# Gráficos con la paleta del sitio

Cuatro tipos de figura armados a partir de la base y del archivo de variables,
en R con ggplot2 y en Python con matplotlib. El script mira el tipo de cada
variable y dibuja lo que corresponde; con la base de ejemplo salen nueve
figuras. Cada una se guarda con su tabla.

## Cómo se corre

```r
source("R/correr.R")      # en R, desde la carpeta del proyecto
```

```bash
python python/correr.py   # en Python
```

## Qué dibuja

| Figura | Qué muestra |
|---|---|
| `barras-<var>` | Una variable categórica, ordenada de mayor a menor |
| `histograma-<var>` | Una numérica, con las clases de la regla de Freedman y Diaconis |
| `caja-<var>` | Una numérica por grupo, con los atípicos a la vista |
| `dispersion-<x>-<y>` | Dos numéricas, con la recta de mínimos cuadrados |

Cada una deja dos archivos en `salidas/figuras/`: el `PNG` a 300 dpi, listo
para pegar en un documento o mandar a imprimir, y el `CSV` con los números que
dibuja.

**Una figura sin su tabla es una afirmación sin fuente.** Por eso el CSV no es
un extra: es lo que permite que alguien revise el número, que el pie de figura
se escriba con datos y no de memoria, y que la figura se pueda rehacer en otra
herramienta sin volver a calcular nada.

## Lo que no hace

**No hay tortas.** Con más de dos o tres categorías, comparar ángulos es más
difícil que comparar largos, y la torta obliga a leer las etiquetas para
entender lo que unas barras dicen de un vistazo.

**No hay colores decorativos.** El acento verde es el que lleva el dato; los
grises son andamiaje. El rojo aparece solo donde significa algo: los atípicos
de la caja y la recta ajustada de la dispersión.

**No hay ejes cortados** en las barras: empiezan en cero, porque el largo de la
barra es lo que se compara. En el histograma y la dispersión, en cambio, el eje
se ajusta a los datos, que es lo correcto ahí.

## Las decisiones que toma sola

**Cuántas clases tiene el histograma.** La regla de Freedman y Diaconis,
acotada entre 4 y 25, que es la misma que usa la [calculadora de
frecuencias](https://estadistica.ar/herramientas/calc-tabla-frecuencias/) del
sitio. Así la figura y la tabla del informe no se contradicen.

**Qué es un atípico.** Los que caen a más de 1,5 rangos intercuartílicos de los
cuartiles, el criterio de Tukey. Los bigotes llegan hasta el dato más extremo
que no es atípico, no hasta el mínimo y el máximo.

**Cómo se escriben los números de los ejes.** Miles con punto: 1.500.000, no
1.5e6. matplotlib abrevia los ejes grandes y R los escribe enteros; sin fijarlo,
la misma figura sale distinta en cada idioma.

## Los dos idiomas

Las dos versiones calculan lo mismo y escriben las mismas tablas, byte a byte.
Las imágenes no son idénticas —son dos motores de dibujo distintos, con
tipografías distintas—, pero muestran los mismos números con los mismos
colores y con la misma geometría.

Eso obliga a fijar cosas que cada motor resuelve por su cuenta. El ancho de las
cajas, por ejemplo: ggplot2 lo deja en la mitad de lo que le toca a cada grupo
y matplotlib lo calcula según cuántos grupos haya. Está en `ANCHO_CAJA`, al
lado de la paleta.

## Para cambiar los colores

Están todos en un solo lugar: `PALETA`, arriba de `comun.R` y de `comun.py`. Si
tu facultad pide otra identidad, se cambia ahí y las nueve figuras salen con la
paleta nueva.

Plantilla de estadistica.ar · CC BY-NC-SA 4.0

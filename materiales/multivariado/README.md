# Multivariado: componentes, conglomerados y correspondencias

Un proyecto que toma una matriz de unidades por variables y una tabla de
contingencia, y hace las tres cosas que se piden siempre: componentes
principales, agrupamiento jerárquico y análisis de correspondencias. Está en
**R y en Python**, y los dos escriben exactamente los mismos bytes.

Los datos del ejemplo **son reales**: ocho indicadores de las 24 jurisdicciones
argentinas y la tabla de nivel educativo, del Censo 2022. La ficha de
`datos/FUENTES.md` dice de qué variable salió cada columna.

## Cómo se corre

Desde la carpeta del proyecto:

```bash
python python/correr.py
```

```r
source("R/correr.R")
```

Las salidas quedan en `salidas/`: doce CSV y un `multivariado.md` con el informe
redactado.

Python necesita `scipy`, y solo para la cola de la chi cuadrado. R la trae de
fábrica. **Nada más**: los autovalores se calculan acá adentro.

## Tres cosas que el proyecto quiere que no te pasen

### 1. El PCA sin tipificar es un ranking de unidades de medida

Sin tipificar, cada variable pesa según el cuadrado de su unidad. En el ejemplo
hay una población en personas, cinco porcentajes y unos años de escolaridad:

| | Explica el primer componente | Pegado a | Correlación |
| --- | --- | --- | --- |
| Sin tipificar | 100,0 % | `poblacion` | 1,000 |
| Tipificada | 52,3 % | `hacinamiento` | 0,904 |

El de arriba no resume nada: **es la población con otro nombre**. Y como
«explica el 100 % de la varianza», que suena bárbaro, nadie lo mira dos veces.
El de abajo necesita cinco componentes para llegar al 90 %, que es la respuesta
honesta: estas ocho variables no se dejan resumir en dos.

### 2. El enlace cambia los grupos

«Agrupamiento jerárquico» no es un método, son cuatro. Sobre la misma matriz de
distancias:

| Enlace | Grupos | El mayor | Silueta | Acuerdo con Ward |
| --- | --- | --- | --- | --- |
| simple | 4 | 21 | 0,266 | 0,209 |
| completo | 4 | 13 | 0,292 | 0,369 |
| promedio | 4 | 21 | 0,266 | 0,209 |
| ward | 4 | 14 | 0,264 | 1,000 |

La última columna es el índice de Rand ajustado, que vale uno cuando las dos
particiones son la misma. Entre Ward y el simple da **0,209**: no son los mismos
grupos ni parecido. No hay un enlace correcto; hay uno elegido, y hay que decir
cuál.

El simple deja 21 de las 24 jurisdicciones en un solo grupo y el resto casi
sueltas. No está roto: encadena, que es lo que su fórmula dice.

### 3. Agrupar siempre devuelve grupos

Pedirle cuatro conglomerados a una nube sin ninguna estructura devuelve cuatro
conglomerados prolijos, con su dendrograma y todo. Para saber si los grupos
dicen algo hay que compararlos contra el caso en que no dicen nada.

El proyecto arma **23 versiones nulas** de la tabla: corre cada columna una
cantidad distinta de posiciones, con lo cual cada variable conserva exactamente
sus valores, su media y su desvío, y lo único que se pierde es con qué fila iba
cada uno. Después vuelve a agrupar y mira la silueta.

    datos de verdad   0,264
    desordenados      de 0,089 a 0,228, con mediana 0,137
    cuántos ganan     0 de 23

Ninguno lo alcanza, así que hay estructura. **Eso no dice que los grupos sean
los correctos ni que sean cuatro**: dice que no son un invento del método. Y el
margen es chico: el mejor nulo llega a 0,228 contra 0,264.

No hace falta ningún generador de números aleatorios para armar los nulos, y por
eso los dos idiomas arman exactamente los mismos.

## El signo de un componente es arbitrario

`eigen` de R y `numpy.linalg.eigh` usan los dos LAPACK y aun así no devuelven lo
mismo: eligen distinto el signo de cada autovector. Un componente con el signo
cambiado es el mismo componente —las cargas cambian todas de signo a la vez— y
es la causa número uno de que dos personas digan que «el PCA les dio distinto».

Este proyecto calcula los autovalores **a mano**, por el método de Jacobi, y fija
el signo con una regla escrita: el elemento de mayor valor absoluto de cada
vector queda positivo. Son cuarenta líneas de rotaciones de dos por dos en
`jacobi.py` y `jacobi.R`, y se leen.

Esa pieza no usa ninguna suma compensada: todo se acumula con sumas comunes en
un orden fijo. De hecho **todo el núcleo numérico del proyecto** hace lo mismo,
y no por precisión —con veinticuatro filas cualquier método alcanza y sobra—
sino porque `math.fsum` de Python y `sum` de R no dan el mismo último bit. Con
sumas comunes en el mismo orden, las dos versiones salen idénticas bit a bit.

## Las correspondencias

Es el PCA de una tabla de contingencia. En vez de varianza hay **inercia**, que
es exactamente el χ² dividido por el total de casos, y cada eje se lleva una
parte de ella.

En el ejemplo, el primer eje ordena los cinco tramos educativos de menos a más:
de «Hasta 6 años» en −0,311 a «17 y más» en +0,485. Los dos primeros ejes se
llevan el 95,8 % de la inercia.

**El χ² da 1.478.333 con 92 grados de libertad y eso no dice nada.** El χ² crece
con el total de casos, y acá hay 26,7 millones de personas: con esa cantidad,
cualquier desvío rechaza. Lo que mide la fuerza de la asociación es la inercia,
que es 0,0553 —una V de Cramér de 0,118—. La asociación existe y es débil; el
mapa muestra su forma, no su tamaño.

Dos cosas más que el proyecto calcula y que evitan leer mal un mapa. **El
aporte** dice cuánto de un eje lo construyó un solo punto: acá el primer eje lo
arma la Ciudad de Buenos Aires casi sola, con el 79,8 %. **La calidad** dice
cuánto de un punto se ve en los ejes graficados: hay siete que están en el mapa
y de los que se ve menos de la mitad, o sea que están lejos en una dirección que
nadie está mirando.

## Qué deja

| Archivo | Qué trae |
| --- | --- |
| `componentes.csv` | Autovalor, proporción y acumulado de cada componente |
| `cargas.csv` | La correlación de cada variable con cada componente, y cuánto queda representada |
| `puntajes.csv` | Cada unidad proyectada sobre los componentes |
| `sin-estandarizar.csv` | Las dos versiones al lado: la tipificada y la que no |
| `conglomerados.csv` | El grupo de cada unidad con los cuatro enlaces, y su silueta |
| `fusiones.csv` | El árbol completo: qué se fusionó con qué y a qué altura |
| `silueta.csv` | Por enlace: tamaños, silueta y acuerdo con el elegido |
| `nulo.csv` | La silueta de cada una de las versiones desordenadas |
| `correspondencias.csv` | Los ejes con su inercia |
| `puntos.csv` | Filas y columnas con su masa, su aporte a cada eje y su calidad |
| `avisos.csv` | Cada cosa que hay que mirar antes de publicar un número |
| `resumen.csv` | Las veinticinco cifras del informe, en dos columnas |
| `multivariado.md` | El informe redactado |

## Correrlo con otros datos

Dos archivos y una línea de `datos/parametros.csv`.

El primero es la matriz: una fila por unidad, una columna por variable, y la
primera columna con el nombre. El segundo es la tabla de contingencia, con la
misma forma. Los dos pueden tener cualquier cantidad de filas y columnas, y el
nombre de la columna de etiquetas se declara en `parametros.csv`.

**El orden de las filas del archivo es el orden del proyecto.** No se reordena
por nombre: las distancias y las fusiones se identifican por posición, y
reordenar cambiaría cómo se rompen los empates.

El proyecto **no imputa faltantes**. Una celda que no sea un número lo detiene,
con el nombre de la fila y de la columna: una unidad incompleta no se puede
proyectar ni agrupar, y rellenarla con la media sería inventar una unidad que no
existe.

## Lo que no hace

- **No hace k-medias.** El jerárquico no depende de una inicialización al azar,
  que es lo que hace que dos corridas de k-medias den distinto. Con datos más
  grandes k-medias es la opción, y merece su propio proyecto.
- **No rota los componentes** —ni varimax ni nada—. La rotación es de análisis
  factorial, que no es lo mismo que PCA aunque los programas los pongan juntos.
- **No hace análisis factorial** ni estima comunalidades.
- **No elige la cantidad de componentes ni de grupos.** Deja el gráfico de
  sedimentación en una tabla, el criterio del autovalor promedio y la silueta;
  la decisión es de quien escribe.
- **No dibuja.** Deja las coordenadas en un CSV, que es lo que cualquier
  graficador necesita.

## Los dos idiomas

Las salidas son idénticas byte a byte, y acá eso es más fuerte que en el resto
de la serie: no es que coincidan al redondear a diez dígitos, es que **las dos
versiones hacen exactamente las mismas operaciones de punto flotante**. Está
comprobado en el verificador, que compara la descomposición de Jacobi entre los
dos motores sin redondear nada.

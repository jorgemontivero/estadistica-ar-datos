# Análisis multivariado

24 unidades y 8 variables. Enlace: «ward», 4 conglomerados.

> **Tipificar o no tipificar no es un detalle del preprocesamiento: es el análisis.** Sin tipificar, el primer componente explica el 100,0 % de la varianza y su correlación con «poblacion» es de 1,000: no resume nada, es esa variable con otro nombre. Tipificando, el primero explica el 52,3 % y hacen falta 5 componentes para llegar al 90 %.

## Los componentes

| Componente | Autovalor | Explica | Acumulado |
| --- | --- | --- | --- |
| 1 | 4,187 | 52,3 % | 52,3 % |
| 2 | 1,326 | 16,6 % | 68,9 % |
| 3 | 0,982 | 12,3 % | 81,2 % |
| 4 | 0,652 | 8,2 % | 89,3 % |
| 5 | 0,489 | 6,1 % | 95,4 % |
| 6 | 0,177 | 2,2 % | 97,7 % |
| 7 | 0,129 | 1,6 % | 99,3 % |
| 8 | 0,058 | 0,7 % | 100,0 % |

Con el criterio de quedarse con los que superan el autovalor promedio —que con datos tipificados es uno— quedan 2. Es una regla, no un resultado: no hay nada en los datos que diga que 2 es el número.

Lo que pesa en el primer componente, de mayor a menor:

- **hacinamiento:** 0,904
- **tamano_del_hogar:** 0,904
- **sin_saneamiento:** 0,891
- **nbi:** 0,834
- **escolaridad:** -0,701
- **mayores:** -0,700
- **poblacion:** -0,270
- **desocupacion:** 0,100

## Los conglomerados

| Enlace | Grupos | El mayor | Silueta | Negativas | Acuerdo |
| --- | --- | --- | --- | --- | --- |
| simple | 4 | 21 | 0,266 | 0 | 0,209 |
| completo | 4 | 13 | 0,292 | 1 | 0,369 |
| promedio | 4 | 21 | 0,266 | 0 | 0,209 |
| ward | 4 | 14 | 0,264 | 4 | 1,000 |

La última columna es el índice de Rand ajustado contra «ward», que es el enlace elegido: vale uno cuando las dos particiones son la misma. Los cuatro árboles salen de la misma matriz de distancias, y lo único que cambia entre ellos es cómo se mide la distancia entre dos grupos ya armados.

### Contra el azar

Agrupar siempre devuelve grupos. Para saber si estos dicen algo, el proyecto desordena cada variable por separado —cada columna conserva exactamente sus valores y se rompe la relación entre ellas—, vuelve a agrupar y mira la silueta. Con 23 corrimientos:

- **Datos de verdad:** 0,264
- **Desordenados:** de 0,089 a 0,228, con mediana 0,137
- **Cuántos igualan o superan al real:** 0 de 23

Ninguno lo alcanza, así que hay estructura. Eso **no** dice que los grupos sean los correctos ni que sean los que hay: dice que no son un invento del método.

Los 4 grupos con «ward»:

- **Grupo 1** (1): Buenos Aires
- **Grupo 2** (14): Catamarca, Chaco, Corrientes, Formosa, Jujuy, La Rioja, Mendoza, Misiones, Salta, San Juan, San Luis, Santiago del Estero, Tierra del Fuego, Tucumán
- **Grupo 3** (8): Chubut, Córdoba, Entre Ríos, La Pampa, Neuquén, Río Negro, Santa Cruz, Santa Fe
- **Grupo 4** (1): Ciudad de Buenos Aires

## Las correspondencias

La tabla cruza 24 filas con 5 columnas y suma 26.711.969 casos. El χ² de independencia es 1.478.333,1 con 92 grados de libertad, p < 0,001, y la inercia total —que es ese χ² dividido por el total— es 0,0553.

| Eje | Inercia | Explica | Acumulado |
| --- | --- | --- | --- |
| 1 | 0,0448 | 81,0 % | 81,0 % |
| 2 | 0,0082 | 14,8 % | 95,8 % |
| 3 | 0,0016 | 2,9 % | 98,7 % |
| 4 | 0,0007 | 1,3 % | 100,0 % |

Sobre el primer eje, las columnas se ordenan de «Hasta 6 años» (-0,311) a «17 y más» (0,485). Un punto lejos del centro no es «mucho»: es **distinto del perfil promedio**, y una fila con el reparto exactamente igual al del total cae en el origen por grande que sea.

Del lado de «Hasta 6 años» queda «Santiago del Estero» (-0,335); del otro, «Ciudad de Buenos Aires» (0,671).

## Qué revisar antes de publicar esto

- **Componentes.** Sin tipificar, el primer componente explica el 100,0 % de la varianza y su correlación con «poblacion» es de 1,000. No es un resumen de las variables: es esa variable con otro nombre, porque su unidad de medida es la más grande de la tabla.
- **Conglomerados.** La silueta de los datos de verdad es 0,264 y ninguno de los 23 desordenados la alcanza: el mejor llega a 0,228. Hay estructura. Eso no dice que los grupos sean los correctos ni que sean cuatro: dice que no son un invento del método.
- **Conglomerados.** Cambiar de enlace cambia los grupos. Entre «ward» y «simple» el índice de Rand ajustado es 0,209. Los cuatro árboles salen de la misma matriz de distancias: lo único que cambia es cómo se mide la distancia entre dos grupos ya armados.
- **Conglomerados.** El enlace simple deja 21 de las 24 unidades en un solo grupo y el resto casi sueltas. Es lo que hace: encadena. No está roto, está haciendo lo que la fórmula dice, y por eso casi nunca se usa para armar tipologías.
- **Conglomerados.** Hay 4 unidad(es) con silueta negativa: están más cerca del grupo de al lado que del propio. Un dendrograma no las muestra, y en un mapa de los dos primeros componentes tampoco se ven.
- **Correspondencias.** Los 2 ejes que se grafican se llevan el 95,8 % de la inercia. El resto está en las otras 2 dimensiones, que el mapa no muestra.
- **Correspondencias.** El χ² da 1.478.333 y el p es diminuto, pero eso no dice nada: el χ² crece con el total de casos y acá hay 26.711.969. Lo que mide la fuerza de la asociación es la inercia, que es 0,0553; puesta en escala de cero a uno —la V de Cramér— da 0,118. La asociación existe y es débil. El mapa muestra su forma, no su tamaño.
- **Correspondencias.** Hay 7 punto(s) con menos de la mitad de su inercia representada en los ejes que se grafican —«Catamarca», «Jujuy», «La Pampa», «La Rioja»—. Están en el mapa, se ven igual que los demás, y su posición es una sombra: están lejos en una dirección que no se está mirando.
- **Correspondencias.** El eje 1 lo construye casi solo «Ciudad de Buenos Aires», que aporta el 79,8 % de su inercia. Un eje definido por un punto describe a ese punto, no a la tabla.
- **Correspondencias.** El eje 2 lo construye casi solo «Hasta 6 años», que aporta el 65,6 % de su inercia. Un eje definido por un punto describe a ese punto, no a la tabla.


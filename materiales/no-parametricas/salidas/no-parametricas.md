# Pruebas no paramétricas

Casos en la base: 150.

> **El apareamiento decide el resultado.** Tomando los datos como lo que son —148 personas medidas dos veces— Wilcoxon da p < 0,001. Tratándolos como dos muestras independientes, Mann-Whitney da p = 0,206. Es la misma tabla: lo único que cambia es si se usa la información de quién es quién.

## Antes y después: `previo` contra `desempeno`

148 pares completos, 2 descartados por falta de alguna de las dos mediciones.

- **Wilcoxon de rangos con signo.** W = 3.664,0, z = -3,539, p < 0,001. El desplazamiento estimado (Hodges-Lehmann) es 1,65.
- **Prueba de los signos.** Subieron 97 y bajaron 51 de 148, p < 0,001.
- **Lo mismo sin aparear.** Mann-Whitney p = 0,206, t de Welch p = 0,220.

El cambio típico es de 1,70 y su desvío es 5,74. Esa es la razón aritmética de todo lo anterior: lo que separa a una persona de otra es mucho más grande que lo que cada una cambió, así que la comparación sin aparear tiene que buscar el efecto adentro de un ruido que la apareada ni ve.

## Dos muestras: `gasto` por `grupo`

- **Mann-Whitney.** U = 1.695,0, p < 0,001.
- **P(X > Y) = 0,301**: esa es la probabilidad de que un caso de «Control» supere a uno de «Tratamiento» tomados al azar. Es lo que la prueba contrasta, y no la igualdad de medianas.
- Medianas: 29.469,4 y 41.095,7. Desplazamiento de Hodges-Lehmann: 10.230,4.
- **t de Welch**, para comparar: t = 0,491, p = 0,625.

## Intervalos por bootstrap (2000 réplicas)

- **La mediana**: 35.817,9, percentil [31.991,8; 39.030,1], BCa [31.991,8; 39.029,9].
- **La media**: 44.480,4, percentil [36.723,3; 54.955,8], BCa [37.783,3; 58.968,0].
- **El rango intercuartílico**: 20.763,5, percentil [16.808,7; 23.802,3], BCa [17.569,2; 25.288,8].
- **El desvío estándar**: 58.332,6, percentil [14.178,7; 86.443,9], BCa [30.825,2; 99.442,8].
- **La diferencia de medianas**: 11.626,2, percentil [5.169,9; 16.454,0].
- **La diferencia de medias**: -4.692,6, percentil [-25.151,1; 12.034,3].

Prueba de permutación sobre la diferencia de medianas: observada 11.626,2, p < 0,001 con 2000 reordenamientos.


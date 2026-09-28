# ANOVA

Diseño: `desempeno ~ nivel * grupo`. Casos en la base: 150; usados: 148.
Se descartaron 2 casos sin respuesta o sin factor.

> **La interacción manda.** nivel × grupo da F(2; 142) = 15,69, p < 0,001. Con la interacción significativa, el efecto principal de grupo —p = 0,384— es el promedio de efectos que apuntan para lados distintos: no describe a ningún grupo. Lo que hay que leer son los efectos simples.

## Las celdas

- **Primario / Control.** n = 23, media 54,5, DE 8,4.
- **Primario / Tratamiento.** n = 14, media 66,4, DE 10,9.
- **Secundario / Control.** n = 25, media 60,3, DE 6,8.
- **Secundario / Tratamiento.** n = 24, media 62,7, DE 9,0.
- **Superior / Control.** n = 27, media 70,1, DE 11,3.
- **Superior / Tratamiento.** n = 35, media 60,0, DE 10,3.

## Los supuestos

- **Normalidad por celda.** Shapiro-Wilk rechaza en 0 de 6 celdas.
- **Igualdad de varianzas.** Levene con centro en la mediana: F(5; 142) = 1,281, p = 0,275.

## ANOVA de un factor: nivel

F(2; 145) = 3,257, p = 0,041. η² = 0,043, ω² = 0,030.

El factor explica el 4,3 % de la variación. El ω², que descuenta el sesgo del η², da 3,0 %: esa es la cifra que conviene informar.

Sin suponer varianzas iguales, la versión de Welch da F(2; 86,0) = 2,770, p = 0,068.

## ANOVA de dos factores

Sumas de cuadrados de tipo III, que no dependen del orden:

- **nivel.** SC = 590,30, F(2; 142) = 3,238, p = 0,042.
- **grupo.** SC = 69,56, F(1; 142) = 0,763, p = 0,384.
- **nivel × grupo.** SC = 2.859,34, F(2; 142) = 15,685, p < 0,001.

Con celdas desbalanceadas el tipo I y el tipo III no dan lo mismo. En este caso ninguna conclusión cambia, aunque las sumas de cuadrados difieran; está todo en `tipos-de-suma.csv`.

## Efectos simples: grupo dentro de cada nivel

- **Primario.** F(1; 142) = 13,688, p < 0,001, Tratamiento − Control = 11,97 (IC 95 % [5,58; 18,37]).
- **Secundario.** F(1; 142) = 0,769, p = 0,382, Tratamiento − Control = 2,39 (IC 95 % [-3,00; 7,79]).
- **Superior.** F(1; 142) = 17,040, p < 0,001, Tratamiento − Control = -10,09 (IC 95 % [-14,93; -5,26]).

Los efectos simples significativos **apuntan para lados distintos**. Por eso el efecto principal da chico: los dos se cancelan al promediarlos. Informar solo el promedio sería esconder el resultado.

## Comparaciones de a pares (nivel × grupo)

15 comparaciones, con los cuatro métodos. Con Tukey:

- **Primario / Control vs Primario / Tratamiento.** Diferencia -11,97 (IC 95 % [-21,32; -2,62]), p = 0,004.
- **Primario / Control vs Secundario / Tratamiento.** Diferencia -8,23 (IC 95 % [-16,27; -0,18]), p = 0,042.
- **Primario / Control vs Superior / Control.** Diferencia -15,66 (IC 95 % [-23,48; -7,83]), p < 0,001.
- **Secundario / Control vs Superior / Control.** Diferencia -9,82 (IC 95 % [-17,48; -2,17]), p = 0,004.
- **Superior / Control vs Superior / Tratamiento.** Diferencia 10,09 (IC 95 % [3,03; 17,16]), p < 0,001.

**Ojo:** en Primario / Control vs Secundario / Tratamiento los cuatro métodos no coinciden. Ahí la conclusión la decide la corrección elegida, no los datos.


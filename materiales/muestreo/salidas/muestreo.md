# Muestreo

Marco: 4.000 unidades. Muestra: 320 en cada uno de los 5 diseños. Semilla 2026.

## Cómo se sacó la muestra

El diseño principal es bietápico: 8 conglomerados por estrato y 10 unidades por conglomerado.

- **Centro.** 8 de 80 conglomerados.
- **Este.** 8 de 45 conglomerados.
- **Norte.** 8 de 30 conglomerados.
- **Sur.** 8 de 45 conglomerados.

El sistemático usó un intervalo de 12,5000 con arranque en 8,7334.

## Los ponderadores

Suman 4.000 sobre una población de 4.000. Van de 6,94 a 36,8, con un coeficiente de variación de 0,384.

El efecto de Kish —lo que cuestan los pesos desiguales por sí solos— es 1,148, o sea que la muestra de 276 vale como una de 241 antes de contar lo que cuesta el conglomerado.

## Las estimaciones, diseño por diseño

**La media de `ingreso`** (verdadera: 581.312,4)

- **aleatorio simple.** 584.276,0, IC 95 % [535.490,7; 633.061,2], deff 1,00, n efectivo 320.
- **sistemático.** 578.497,6, IC 95 % [534.203,4; 622.791,8], deff 1,00, n efectivo 320.
- **estratificado proporcional.** 602.536,3, IC 95 % [554.095,9; 650.976,7], deff 0,96, n efectivo 332.
- **estratificado de Neyman.** 589.230,7, IC 95 % [543.381,2; 635.080,2], deff 0,90, n efectivo 355.
- **bietápico.** 616.931,9, IC 95 % [518.044,9; 715.818,8], deff 3,62, n efectivo 89.

**El total de `personas`** (verdadera: 13.349,0)

- **aleatorio simple.** 13.562,5, IC 95 % [12.863,2; 14.261,8], deff 1,00, n efectivo 320.
- **sistemático.** 13.637,5, IC 95 % [12.969,5; 14.305,5], deff 1,00, n efectivo 320.
- **estratificado proporcional.** 13.375,0, IC 95 % [12.710,5; 14.039,5], deff 0,97, n efectivo 329.
- **estratificado de Neyman.** 13.277,8, IC 95 % [12.606,3; 13.949,2], deff 1,01, n efectivo 316.
- **bietápico.** 13.333,8, IC 95 % [12.727,8; 13.939,7], deff 0,80, n efectivo 402.

**La proporción de `agua`** (verdadera: 0,83)

- **aleatorio simple.** 0,83, IC 95 % [0,80; 0,87], deff 1,00, n efectivo 320.
- **sistemático.** 0,81, IC 95 % [0,77; 0,85], deff 1,00, n efectivo 320.
- **estratificado proporcional.** 0,84, IC 95 % [0,80; 0,88], deff 0,98, n efectivo 328.
- **estratificado de Neyman.** 0,82, IC 95 % [0,78; 0,86], deff 1,05, n efectivo 305.
- **bietápico.** 0,89, IC 95 % [0,85; 0,93], deff 1,17, n efectivo 275.

## La media de `ingreso` dentro de cada estrato

- **Centro.** n = 71 en 8 conglomerados. 812.130,2, IC 95 % [575.649,6; 1.048.610,8]. Verdadera: 695.051,8.
- **Este.** n = 71 en 8 conglomerados. 522.052,2, IC 95 % [351.435,6; 692.668,8]. Verdadera: 524.709,6.
- **Norte.** n = 66 en 8 conglomerados. 527.772,8, IC 95 % [285.194,2; 770.351,3]. Verdadera: 551.810,8.
- **Sur.** n = 68 en 8 conglomerados. 465.003,3, IC 95 % [243.526,6; 686.480,0]. Verdadera: 455.379,5.

## Cuántas veces le acierta cada intervalo

Sacando la muestra 500 veces y armando los dos intervalos cada vez:

- **Con el diseño:** cubre el valor verdadero el 92,0 % de las veces, contra el 95,0 % que promete.
- **Ignorando el diseño:** cubre el 61,0 %.

El intervalo ingenuo es en promedio 2,0 veces más angosto, y esa es exactamente la precisión que no tiene.


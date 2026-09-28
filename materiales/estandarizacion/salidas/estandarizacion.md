# Tasas estandarizadas por edad

24 poblaciones, 16 grupos de edad, 394.940 casos sobre 45.618.787 personas. Estándar: «oms». Las tasas van por 100.000.

> **La tasa cruda y la ajustada no ordenan igual.** «Ciudad de Buenos Aires» está en el puesto 1 de 24 por su tasa cruda —1.076,4 por 100.000— y en el 23 por la ajustada, que es 496,4. No cambió ningún dato: cambió la estructura de edad con la que se los pesa. El 4,8 % de su población está en el grupo de «80 y más», contra el 2,2 % del promedio de las poblaciones.

## Las tasas ajustadas, de mayor a menor

| Población | Cruda | Ajustada | IC 95 % | Puesto crudo → ajustado |
| --- | --- | --- | --- | --- |
| Chaco | 879,9 | 844,1 | 827,5 a 860,9 | 6 → 1 (+5) |
| Misiones | 742,5 | 752,1 | 737,0 a 767,4 | 14 → 2 (+12) |
| Formosa | 776,5 | 723,0 | 702,4 a 744,1 | 10 → 3 (+7) |
| La Rioja | 724,5 | 674,0 | 649,0 a 699,7 | 17 → 4 (+13) |
| Santa Fe | 990,1 | 660,4 | 653,2 a 667,6 | 2 → 5 (-3) |
| Tucumán | 789,8 | 660,0 | 648,9 a 671,3 | 9 → 6 (+3) |
| Entre Ríos | 904,7 | 649,2 | 637,8 a 660,9 | 4 → 7 (-3) |
| Corrientes | 742,6 | 638,8 | 625,5 a 652,3 | 13 → 8 (+5) |
| Córdoba | 939,4 | 637,2 | 630,4 a 644,0 | 3 → 9 (-6) |
| Santiago del Estero | 677,1 | 634,1 | 619,4 a 649,1 | 19 → 10 (+9) |
| Santa Cruz | 584,5 | 632,9 | 605,1 a 661,7 | 23 → 11 (+12) |
| Buenos Aires | 903,7 | 630,4 | 627,2 a 633,6 | 5 → 12 (-7) |
| Catamarca | 744,1 | 625,4 | 603,7 a 647,7 | 12 → 13 (-1) |
| Salta | 664,7 | 611,4 | 599,1 a 623,8 | 21 → 14 (+7) |
| San Juan | 755,4 | 610,4 | 595,2 a 626,1 | 11 → 15 (-4) |
| San Luis | 736,7 | 599,6 | 581,0 a 618,7 | 15 → 16 (-1) |
| Chubut | 699,5 | 585,5 | 567,7 a 603,9 | 18 → 17 (+1) |
| Jujuy | 673,6 | 578,4 | 563,0 a 594,1 | 20 → 18 (+2) |
| Mendoza | 810,8 | 567,4 | 558,6 a 576,4 | 8 → 19 (-11) |
| Río Negro | 729,8 | 564,0 | 549,0 a 579,5 | 16 → 20 (-4) |
| La Pampa | 817,1 | 542,8 | 522,8 a 563,6 | 7 → 21 (-14) |
| Neuquén | 590,6 | 534,4 | 518,3 a 550,9 | 22 → 22 |
| Ciudad de Buenos Aires | 1.076,4 | 496,4 | 490,5 a 502,3 | 1 → 23 (-22) |
| Tierra del Fuego | 409,8 | 496,2 | 460,7 a 533,9 | 24 → 24 |

De 844,1 en «Chaco» a 496,2 en «Tierra del Fuego»: 1,70 veces. Con las tasas crudas la distancia entre esas dos es de 2,15 veces.

## Cuánto depende del estándar elegido

Mucho, en el nivel. La tasa de «Ciudad de Buenos Aires» va de 496,4 con el estándar «oms» a 1.162,2 con «europea»: 2,34 veces, con los mismos datos y el mismo método. **Una tasa ajustada sin el nombre de su estándar al lado no quiere decir nada.**

Y algo, en el orden. Se dan vuelta 32 pares de poblaciones según con qué estándar se los mire, y en 29 de esos 32 los intervalos se pisan con los dos estándares: ahí el estándar decide un orden que no estaba decidido, y no se pierde nada. Los otros 3 son el caso incómodo: con uno de los dos estándares los intervalos **no** se pisan, así que la diferencia parecía establecida y con el otro estándar se da vuelta. Están par por par en `sensibilidad.csv`.

## La razón estandarizada

Referencia: el total de las poblaciones, con una tasa cruda de 865,7 por 100.000. La razón compara los casos observados con los que habría si esta población tuviera las tasas de la referencia a cada edad.

En 19 de 24 poblaciones el intervalo de la razón no contiene al uno. En las otras 5, la mortalidad no se distingue de la que la estructura de edad hacía esperar.

La más alta es «Chaco», con 1,347 [1,321; 1,374]: 9.895 casos contra 7.346 esperados. La más baja es «Tierra del Fuego», con 0,783.

## Los pares comparados

### Ciudad de Buenos Aires contra Chaco

Tasas crudas: 1.076,4 y 879,9, una diferencia de 196,5. Ajustadas: 496,4 y 844,1, que van para el lado contrario.

De esa diferencia cruda, 681,4 (346,8 %) es **estructura** —las dos poblaciones tienen edades distintas— y -484,9 es **riesgo**: lo que cambia a cada edad. Los dos sumandos suman exactamente la diferencia, y ese es el control de la cuenta.

La razón entre las dos tasas ajustadas es 0,588, IC 95 % [0,575; 0,602].

### Ciudad de Buenos Aires contra Tierra del Fuego

Tasas crudas: 1.076,4 y 409,8, una diferencia de 666,5. Ajustadas: 496,4 y 496,2, que van para el mismo lado.

De esa diferencia cruda, 657,6 (98,7 %) es **estructura** —las dos poblaciones tienen edades distintas— y 8,9 es **riesgo**: lo que cambia a cada edad. Los dos sumandos suman exactamente la diferencia, y ese es el control de la cuenta.

La razón entre las dos tasas ajustadas es 1,000, IC 95 % [0,928; 1,078], que contiene al uno: la diferencia no está establecida.

### Catamarca contra Santiago del Estero

Tasas crudas: 744,1 y 677,1, una diferencia de 67,0. Ajustadas: 625,4 y 634,1, que van para el lado contrario.

De esa diferencia cruda, 69,5 (103,7 %) es **estructura** —las dos poblaciones tienen edades distintas— y -2,5 es **riesgo**: lo que cambia a cada edad. Los dos sumandos suman exactamente la diferencia, y ese es el control de la cuenta.

La razón entre las dos tasas ajustadas es 0,986, IC 95 % [0,945; 1,029], que contiene al uno: la diferencia no está establecida.

## Qué revisar antes de publicar esto

- **Estandarización.** «Ciudad de Buenos Aires» pasa del puesto 1 al 23 al ajustar por edad. La tasa cruda y la ajustada no dicen lo mismo: dicen cosas distintas, y comparar poblaciones con la cruda es comparar estructuras de edad.
- **Estandarización.** Hay 2 población(es) con algún grupo de edad de menos de cinco casos —«Tierra del Fuego» tiene 2—. Una tasa específica calculada con cuatro muertes es muy inestable y la ajustada la arrastra: ahí conviene mirar también la indirecta, que no necesita estimar una tasa por grupo.
- **Estandarización.** En 20 de los 23 escalones del ranking el intervalo de una población se pisa con el de la siguiente. Un ranking se lee como si cada puesto estuviera decidido, y la mayoría de estos no lo están.
- **Indirecta.** En 5 de las 24 poblaciones el intervalo de la razón contiene al uno: su mortalidad no se distingue de la que la estructura de edad hacía esperar.
- **Indirecta.** El orden por razón indirecta y el orden por tasa directa no son el mismo: «Santiago del Estero» está 2 puesto(s) más arriba en uno que en el otro. Son dos preguntas distintas y no tienen por qué coincidir; cuando coinciden es porque las tasas específicas van casi todas para el mismo lado.
- **Estándar.** Hay 32 par(es) de poblaciones cuyo orden se da vuelta según con qué estándar se las mire, y en 29 de ellos los intervalos se pisan con los dos estándares. Es la respuesta a la frase de que el estándar cambia el nivel pero no el orden: cambia el orden, y casi siempre lo cambia donde no estaba establecido. Casi siempre, pero no siempre: en 3 par(es) los intervalos NO se pisan con alguno de los dos estándares, así que con ese estándar la diferencia parecía establecida y con el otro se da vuelta. Están marcados en sensibilidad.csv.
- **Estándar.** La tasa de «Ciudad de Buenos Aires» va de 496,4 con el estándar «oms» a 1162,2 con «europea». Son los mismos datos y el mismo método. Una tasa ajustada sin el nombre de su estándar al lado no quiere decir nada, y dos tasas ajustadas con estándares distintos no se comparan.
- **Comparación.** Entre «Ciudad de Buenos Aires» y «Chaco» la tasa cruda y la ajustada van para lados contrarios. La descomposición dice por qué: el efecto de la estructura es 681,4 y el de las tasas -484,9, y el primero es más grande que la brecha entera.
- **Comparación.** Entre «Catamarca» y «Santiago del Estero» la tasa cruda y la ajustada van para lados contrarios. La descomposición dice por qué: el efecto de la estructura es 69,5 y el de las tasas -2,5, y el primero es más grande que la brecha entera.


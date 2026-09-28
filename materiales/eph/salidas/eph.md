# Mercado de trabajo, 2025T4

Fuente: `datos/usu_individual_T425.txt`, 22 columnas. Quedaron 5.507 personas en 1.871 hogares de 32 aglomerados, que representan a 3.754.094 habitantes.

> **El mismo ingreso medio, tres veces.** Con `PONDIIO` y sacando a los que no declaran da $ 715.067. Cambiando nada más que el ponderador da $ 700.544, un 2,0 % menos. Cambiando además el filtro —dejando adentro al −9, que en la EPH quiere decir «no responde» y no «menos nueve pesos»— da $ 565.082, un 21,0 % menos. Son los mismos datos y las mismas personas.

## Las cuatro tasas

Cada una tiene su propio denominador, y no es un detalle de presentación: la desocupación se calcula sobre la población económicamente activa y no sobre la población.

- **Tasa de actividad:** 48,65 %, IC 95 % [46,35 %; 50,95 %]. Población económicamente activa sobre población total, 5.507 casos.
- **Tasa de empleo:** 45,02 %, IC 95 % [42,75 %; 47,30 %]. Ocupados sobre población total, 5.507 casos.
- **Tasa de desocupación:** 7,46 %, IC 95 % [5,69 %; 9,22 %]. Desocupados sobre población económicamente activa, 2.628 casos.
- **Tasa de subocupación:** 10,42 %, IC 95 % [8,57 %; 12,28 %]. Subocupados sobre población económicamente activa, 2.628 casos.

Las tres primeras tienen que cerrar entre sí: empleo = actividad × (1 − desocupación). Da 45,0237 % contra el 45,0237 % calculado aparte. Es la única comprobación que no depende de tener razón sobre nada más.

Contar casos en vez de ponderar cambia las tasas. Donde más cambia es en la de empleo: 44,03 % sin ponderar contra 45,02 % ponderando. La EPH no es una muestra autoponderada, y un caso de un aglomerado chico no vale lo mismo que uno del conurbano.

El efecto de diseño más alto es el de la tasa de desocupación: 3,09. Los 2.628 casos de su denominador valen como 851. Y está calculado con el hogar como unidad primaria, que es lo más fino que trae el archivo público: el conglomerado de verdad es el radio censal, así que el efecto real es todavía mayor y estos intervalos son una cota optimista.

## Los ingresos de la ocupación principal

Sobre 1.803 ocupados con ingreso declarado, que representan a 1.658.412 personas. La media es $ 715.067, IC 95 % [$ 662.471; $ 767.664]. La mediana es $ 497.000.

El décimo decil gana 20,8 veces lo que el primero. El primer decil corta en $ 156.000 y el noveno en $ 1.418.000.

| Decil | Corte superior | Ingreso medio | Participación |
| --- | --- | --- | --- |
| 1 | $ 156.000 | $ 118.901 | 1,7 % |
| 2 | $ 239.000 | $ 195.999 | 2,7 % |
| 3 | $ 317.000 | $ 282.974 | 3,9 % |
| 4 | $ 403.000 | $ 360.543 | 5,1 % |
| 5 | $ 497.000 | $ 451.634 | 6,3 % |
| 6 | $ 615.000 | $ 554.170 | 7,8 % |
| 7 | $ 756.000 | $ 685.979 | 9,5 % |
| 8 | $ 984.000 | $ 864.804 | 12,2 % |
| 9 | $ 1.418.000 | $ 1.185.824 | 16,7 % |
| 10 | — | $ 2.468.823 | 34,2 % |

## El mismo promedio, de cinco maneras

| Cómo se calculó | Ponderador | El −9 | El 0 | Media | Diferencia |
| --- | --- | --- | --- | --- | --- |
| Lo correcto | `PONDIIO` | lo saca | lo saca | $ 715.067 | referencia |
| Con los que no declaran adentro | `PONDIIO` | lo deja | lo saca | $ 715.067 | **exactamente la misma** |
| Con el ponderador general | `PONDERA` | lo saca | lo saca | $ 700.544 | -2,0 % |
| Con el ponderador general y los que no declaran adentro | `PONDERA` | lo deja | lo saca | $ 565.082 | -21,0 % |
| Con los ocupados sin ingreso adentro | `PONDIIO` | lo saca | lo deja | $ 701.595 | -1,9 % |

Las dos primeras filas dan lo mismo, y eso es lo importante: con el ponderador de ingreso, el −9 ya está sacado, porque el INDEC le pone el peso en cero. El filtro que nunca se escribió no hace falta… hasta que el ponderador no está.

### Por sexo

Los varones ocupados declaran en promedio $ 771.239 y las mujeres $ 642.764: ellas ganan el 83,3 % de lo que ganan ellos. Es una diferencia de ingresos entre ocupados, no una diferencia de salario a igual tarea: la EPH no alcanza para lo segundo.

## Informalidad

El 36,87 % de los asalariados no tiene descuento jubilatorio, IC 95 % [33,52 %; 40,23 %]. Son 440.983 personas sobre 1.195.894 asalariados.

El grupo con más informalidad es «25 a 34» (tramo de edad), con 39,7 %; el que menos, «50 a 64» (tramo de edad), con 32,7 %.

## Qué revisar antes de publicar esto

- **Códigos.** Hay 35 registros con CH06 negativo. En la EPH «−1» quiere decir «menos de un año», no «falta el dato»: se los cuenta como cero. Promediar la columna sin mirarla da una edad media más baja de la que corresponde.
- **Ingresos.** 589 ocupados —el 19,0 % ponderado— tienen «P21» negativo, que en la EPH quiere decir «no responde» y no «ingreso negativo». Promediar esa columna sin sacarlos es el error más caro que se puede cometer con esta base.
- **Tasas.** El efecto de diseño de «actividad», «empleo», «desocupación», «subocupación» pasa de 2. El efecto de diseño es un cociente de varianzas, así que un 2 no duplica el intervalo: lo ensancha un 41 %, que es la raíz de 2. Un programa al que se le pasa la columna sin contarle del diseño informa el error de la raíz de abajo, y el intervalo le sale así de corto.
- **Ingresos.** Con «PONDIIO», dejar adentro a los que no declaran ingreso **no cambia nada**: el promedio da igual hasta el último decimal, porque ese ponderador les vale cero. Por eso el filtro del −9 se puede no escribir nunca sin que nadie lo note.
- **Ingresos.** Cambiar de ponderador corre el promedio 2,0 %; dejar adentro al −9 con el ponderador general lo corre 21,0 %. Los dos descuidos por separado se disimulan y juntos no. Y van juntos justo cuando el script se reusa sobre un trimestre anterior a 2016T2, que es donde el ponderador de ingreso no existe.


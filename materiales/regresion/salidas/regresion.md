# Regresión

Modelo: `nota ~ horas + gasto + edad`. Casos en la base: 150; usados en el ajuste: 149.
Se descartó 1 caso al que le faltaba alguna variable del modelo.

> **Un solo caso decide parte de este modelo.** Sacar el caso 96 —el de mayor distancia de Cook, 0,948— cambia la conclusión de **gasto**. Un resultado que depende de una observación entre 149 no es un resultado sobre la población: es un resultado sobre esa observación.

## El modelo lineal

- **horas.** b = 0,06480, IC 95 % [0,01527; 0,114], t(145) = 2,59, p = 0,011, VIF = 1,00.
- **gasto.** b = 0,000002464, IC 95 % [-0,000001330; 0,000006259], t(145) = 1,28, p = 0,201, VIF = 1,00.
- **edad.** b = 0,00235, IC 95 % [-0,01641; 0,02111], t(145) = 0,25, p = 0,805, VIF = 1,00.

El modelo explica el 5,4 % de la variación (3,4 % ajustado por la cantidad de predictores), con un error estándar residual de 1,366.
La prueba F del modelo completo da F(3; 145) = 2,76, p = 0,045.

## El diagnóstico

- **Normalidad de los residuos.** Shapiro-Wilk W = 0,9770, p = 0,013.
- **Homocedasticidad.** Breusch-Pagan LM = 6,369 con 3 gl, p = 0,095.
- **Independencia.** Durbin-Watson = 1,853. Solo significa algo si las filas tienen un orden.
- **Influencia.** 7 casos con palanca alta y 4 con residuo estandarizado mayor que 2 en valor absoluto.

## Qué pasa sin el caso más influyente

El caso 96 tiene una distancia de Cook de 0,948 y una palanca de 0,509. Sacándolo:

- **horas.** b pasa de 0,06480 (p = 0,011) a 0,06911 (p = 0,006).
- **gasto.** b pasa de 0,000002464 (p = 0,201) a 0,000006153 (p = 0,024). ←
- **edad.** b pasa de 0,00235 (p = 0,805) a -0,000021547 (p = 0,998).

## La regresión logística

Respuesta: `aprueba`, con «Sí» como resultado de interés (79 casos de 149).

- **horas.** OR = 1,432 (IC 95 % [1,257; 1,630]), p < 0,001.
- **puntaje.** OR = 1,691 (IC 95 % [1,297; 2,204]), p < 0,001.

Clasificando al corte de 0,5: exactitud 74,5 %, sensibilidad 74,7 %, especificidad 74,3 %. El AUC es 0,851.

Conviene comparar la exactitud contra la del modelo que siempre contesta la clase más frecuente, que acá sería 53,0 %. Una exactitud alta con clases desbalanceadas no dice nada por sí sola.

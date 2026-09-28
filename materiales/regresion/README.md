# Regresión lineal y logística, con diagnóstico

Un ajuste lineal múltiple y uno logístico, los dos con el diagnóstico que
decide si hay que creerles. En R y en Python, sin usar `lm` ni `glm`.

## Cómo se corre

```r
source("R/correr.R")      # en R, desde la carpeta del proyecto
```

```bash
python python/correr.py   # en Python
```

El modelo se declara en `datos/parametros.csv`, no en el código:

```text
respuesta_numerica,nota
predictores,horas;gasto;edad
respuesta_binaria,aprueba
predictores_binaria,horas;puntaje
exito,Sí
```

Cambiar de respuesta o agregar un predictor es editar esa línea.

## Qué deja

| Archivo | Qué trae |
|---|---|
| `coeficientes.csv` | Los coeficientes del modelo lineal, con error estándar, t, p, intervalo y VIF |
| `ajuste.csv` | n, R², R² ajustado, error residual y la prueba F del modelo |
| `diagnostico.csv` | Shapiro-Wilk, Breusch-Pagan, Durbin-Watson y los recuentos de influencia |
| `influencia.csv` | Una fila por caso: ajustado, residuo, palanca y distancia de Cook |
| `sin-el-influyente.csv` | El modelo recalculado sin el caso de mayor Cook, comparado con el original |
| `logistica.csv` | Los coeficientes logísticos, con el odds ratio y su intervalo |
| `clasificacion.csv` | Matriz de confusión, sensibilidad, especificidad, exactitud y AUC |
| `avisos.csv` | Cada supuesto que no se cumple |
| `regresion.md` | El informe redactado |

## Lo que este proyecto quiere que no te pase

**Que publiques un coeficiente que en realidad lo decide un solo caso.**

Por eso el paso 2 no termina en el diagnóstico: **vuelve a ajustar el modelo
sin el caso de mayor distancia de Cook** y compara los dos, coeficiente por
coeficiente. La columna `cambia_la_conclusion` dice «Sí» cuando uno de ellos
cruza el umbral de significación al sacar esa observación.

En los datos de ejemplo pasa, y pasa con un caso que estaba ahí desde el
principio: uno de los tres gastos enormes que el descargable de gráficos deja
a la vista en su diagrama de caja. En una regresión, un valor así no es un
punto más lejos: es un punto con **palanca**, que tira del plano de ajuste
mucho más que los otros.

```text
gasto    con el caso 96   b = 0,0000025   p = 0,201
         sin el caso 96   b = 0,0000062   p = 0,024
```

El coeficiente se multiplica por dos y medio, y la conclusión se da vuelta.

**Y el caso no llega al umbral clásico.** Su distancia de Cook es 0,948, por
debajo del 1 que se suele citar como línea de corte. Es el mejor argumento
contra los umbrales mecánicos: el único modo de saber cuánto pesa un caso es
sacarlo y volver a mirar.

## Por qué no usa `lm` ni `glm`

Porque el proyecto promete que las dos versiones escriben **los mismos
archivos, byte a byte**, y las bibliotecas no lo permiten:

- `lm` de R resuelve por QR y numpy por SVD. Los coeficientes empiezan a
  diferir alrededor del décimo dígito.
- `glm` de R y `Logit` de statsmodels **paran de iterar con criterios
  distintos**, y ahí la diferencia llega al octavo dígito.

La salida es la misma que en los otros descargables de la serie: escribir el
cálculo una vez de cada lado. `algebra.R` y `algebra.py` resuelven los
sistemas por eliminación de Gauss con pivoteo parcial, y el ajuste logístico
es un IRLS de veinte líneas con la misma tolerancia en los dos idiomas.

El precio está declarado: las ecuaciones normales son menos estables que una
QR. Por eso el VIF sale en la tabla de coeficientes y hay un aviso cuando pasa
de 10, que es la señal de que el problema está mal condicionado.

## Un detalle que vas a notar si comparás con `summary(glm)`

Los coeficientes de la logística coinciden con los de `glm` hasta el décimo
decimal, y la devianza coincide exacta. **Los errores estándar no**: difieren
en el sexto decimal.

No es un error de este proyecto. `glm` corta de iterar cuando la devianza deja
de moverse —su criterio es relativo y vale 10⁻⁸— y calcula los errores
estándar con **los pesos que tenía guardados en ese momento**, que no están
evaluados en los coeficientes finales. Se ve sin salir de R:

```r
X <- model.matrix(m); mu <- m$fitted.values
sqrt(diag(solve(t(X) %*% (m$weights * X))))   # 1,397354108440  ← summary(m)
sqrt(diag(solve(t(X) %*% (mu * (1 - mu) * X))))  # 1,397358594094
```

El segundo es el que informa este proyecto, que itera hasta que los
coeficientes dejan de moverse en 10⁻¹⁰ y ahí evalúa la información. La
diferencia es de tres partes por millón y no cambia ninguna conclusión.

Vale aclarar una cosa, porque es fácil sacar la conclusión de más: **con esta
tolerancia, recalcular la información al final o dejar la de la última vuelta
da lo mismo hasta el duodécimo decimal.** Lo que abre la brecha con `glm` no
es dónde se evalúan los pesos, es que `glm` para antes. El recálculo está
igual, porque es lo que hace que el número sea el correcto por construcción y
no por suerte.

## Lo que sí o sí sale escrito

**El intervalo de confianza de cada coeficiente**, no solo el valor p. Un
coeficiente de 0,065 con intervalo [0,015; 0,114] dice algo que «p = 0,011»
no dice: que el efecto podría ser siete veces más chico o casi el doble.

**El VIF de cada predictor.** No es un supuesto que se verifica después: es
una propiedad de los predictores que elegiste. Con VIF alto, el coeficiente y
su signo dejan de ser interpretables por separado.

**El odds ratio, no el riesgo relativo.** No son lo mismo, y con un resultado
frecuente el odds ratio exagera bastante.

**La exactitud del modelo trivial**, al lado de la del modelo logístico. Un
clasificador que siempre contesta la clase mayoritaria acierta tanto como
desbalanceadas estén las clases, y esa es la vara contra la que hay que medir.

## Lo que no hace

**No elige el modelo.** No hay selección de variables, ni paso a paso, ni
criterios de información. Elegir predictores mirando valores p es la receta
más rápida para un modelo que no replica.

**No hay interacciones ni términos no lineales.** Los predictores entran como
están.

**No hay variables categóricas como predictores.** Entran solo numéricas; para
una categórica hay que construir las variables indicadoras a mano.

**No hay errores estándar robustos.** Cuando Breusch-Pagan rechaza, el aviso
lo dice y recomienda; el cálculo no está.

## Los dos idiomas

Las dos versiones escriben los diez archivos byte a byte iguales, incluido el
informe. Lo único que necesita SciPy son las distribuciones —t, F, chi² y
normal— para los valores p; en R vienen de fábrica.

Plantilla de estadistica.ar · CC BY-NC-SA 4.0

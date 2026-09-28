# Estandarización de tasas por edad

Un proyecto que toma casos y población por grupo de edad, calcula las tasas
ajustadas con sus intervalos, las compara y escribe el informe. Está en **R y en
Python**, y los dos escriben exactamente los mismos bytes.

Los datos del ejemplo **son reales**: las defunciones de 2022 de las 24
jurisdicciones argentinas (DEIS) sobre la población del Censo 2022 (INDEC). No
hay nada simulado. La ficha de `datos/FUENTES.md` dice de qué archivo salió cada
columna y qué se descartó.

## Cómo se corre

Desde la carpeta del proyecto:

```bash
python python/correr.py
```

```r
source("R/correr.R")
```

Las salidas quedan en `salidas/`: diez CSV y un `estandarizacion.md` con el
informe redactado.

Python necesita `scipy`, y solo para los cuantiles de la chi cuadrado y la
normal. R los tiene de fábrica.

## La tasa cruda ordena al revés

**La jurisdicción con la tasa de mortalidad más alta del país es la que tiene la
segunda más baja.** No es un error de nadie: es la misma cifra contestando dos
preguntas distintas.

| | Cruda | Ajustada | Puesto |
| --- | --- | --- | --- |
| Ciudad de Buenos Aires | 1.076,4 | 496,4 | 1 → 23 |
| Chaco | 879,9 | 844,1 | 6 → 1 |
| Misiones | 742,5 | 752,1 | 14 → 2 |
| Tierra del Fuego | 409,8 | 496,2 | 24 → 24 |

Por 100.000, estándar de la OMS. La razón es la edad: el **4,8 %** de la
población porteña tiene 80 años o más, contra el **2,2 %** del promedio de las
jurisdicciones. Una población más vieja tiene más muertes aunque se muera menos
a cada edad.

El caso de abajo de la tabla es el mismo argumento por el otro lado: la Ciudad
de Buenos Aires y Tierra del Fuego tienen tasas crudas que difieren en **2,6
veces** y tasas ajustadas que difieren en **un 0,03 %** —496,4 contra 496,2, con
un intervalo que contiene al uno—. El 98,7 % de esa brecha enorme es estructura
de edad y nada más.

## Las dos estandarizaciones, y para qué sirve cada una

**Directa.** Las tasas propias sobre una estructura ajena:

    tasa ajustada = Σ (wᵢ / W) · (dᵢ / nᵢ)

Es la que se usa cuando cada grupo de edad tiene casos suficientes. Da un número
comparable entre poblaciones y con cualquier otra tasa ajustada **al mismo
estándar**.

**Indirecta.** Las tasas de una referencia sobre la estructura propia:

    esperados = Σ nᵢ · mᵢ(referencia)
    razón     = observados / esperados

Solo necesita el **total** de casos observados, no el detalle por edad. Sirve
donde la directa se rompe: poblaciones chicas, causas poco frecuentes, o casos
por edad que no están publicados. La contracara es que dos razones indirectas
no son estrictamente comparables entre sí, porque cada una está ajustada a su
propia estructura.

El proyecto calcula las dos y las deja al lado para que se vea cuánto se
parecen. Con estos datos el orden que dan no es el mismo, y el aviso lo dice.

## Los intervalos no son los de siempre

**Una tasa ajustada no es una proporción y su intervalo no sale de la normal.**
Es una suma ponderada de conteos de Poisson, que no es un Poisson. El proyecto
usa el método de **Fay-Feuer** (1997), que aproxima esa suma por una gamma con
los mismos dos primeros momentos: es el que usan los registros de cáncer y el
programa SEER. Con pocos casos el intervalo sale asimétrico, que es lo correcto;
la aproximación normal daría límites inferiores negativos.

Para la razón estandarizada va el intervalo **exacto de Poisson**, por la chi
cuadrado, dividido por los esperados. Los esperados se tratan como conocidos,
que es la convención.

Y para la razón entre dos tasas ajustadas, el intervalo se arma en escala
logarítmica, recuperando el error estándar de cada una del ancho de su propio
intervalo.

## El estándar cambia el nivel, y a veces el orden

Se dice mucho que el estándar cambia el nivel de una tasa ajustada pero no el
orden entre poblaciones. **Lo primero es cierto y lo segundo no.**

El nivel cambia muchísimo. La tasa de la Ciudad de Buenos Aires es 496,4 con el
estándar de la OMS y 1.162,2 con el europeo: **2,34 veces**, con los mismos
datos y el mismo método. Una tasa ajustada sin el nombre de su estándar al lado
no quiere decir nada, y dos tasas ajustadas con estándares distintos no se
comparan.

El orden también cambia, aunque menos. Con estos datos se dan vuelta **32 pares**
de jurisdicciones según con qué estándar se los mire. En **29 de esos 32** los
intervalos se pisan con los dos estándares: ahí el estándar decide un orden que
no estaba decidido, y no se pierde nada. Los otros **3** son el caso incómodo,
y están marcados en `sensibilidad.csv`: con uno de los estándares los intervalos
no se pisan —la diferencia parecía establecida— y con el otro se da vuelta.

## Cuánto de la brecha es estructura y cuánto es riesgo

La descomposición de **Kitagawa** parte la diferencia entre dos tasas crudas en
dos sumandos:

    C_a − C_b = Σ (p_ai − p_bi)·(m_ai + m_bi)/2   ← estructura
              + Σ (m_ai − m_bi)·(p_ai + p_bi)/2   ← tasas

La identidad es **exacta**, no una aproximación, y por eso sirve de control: el
proyecto escribe el residuo de la resta en `comparaciones.csv` y tiene que dar
cero.

Entre la Ciudad de Buenos Aires y Chaco, la brecha cruda es de +196,5 a favor de
la Ciudad. La estructura aporta **+681,4** y las tasas **−484,9**: la estructura
explica el 347 % de la brecha y el riesgo tira para el otro lado. Por eso la
cruda y la ajustada se dan vuelta.

## Qué deja

| Archivo | Qué trae |
| --- | --- |
| `tasas.csv` | Cruda y ajustada con intervalos, el cambio porcentual y el puesto en los dos ordenamientos |
| `por-edad.csv` | El detalle: tasa específica, peso estándar y aporte de cada grupo |
| `indirecta.csv` | Observados, esperados, la razón con su intervalo y la tasa indirecta |
| `por-estandar.csv` | La misma tasa con cada estándar disponible, con su puesto |
| `sensibilidad.csv` | Los pares que se dan vuelta según el estándar, y si sus intervalos se pisan |
| `niveles.csv` | Cuánto se mueve el nivel de cada población entre estándares |
| `comparaciones.csv` | Por par: la brecha cruda partida en dos y la razón entre ajustadas |
| `descomposicion.csv` | La descomposición de Kitagawa, grupo por grupo |
| `avisos.csv` | Cada cosa que hay que mirar antes de publicar un número |
| `resumen.csv` | Las veintitrés cifras del informe, en dos columnas |
| `estandarizacion.md` | El informe redactado |

## Correrlo con otros datos

Alcanza con dos archivos y una línea de `datos/parametros.csv`.

Los datos son una tabla larga: una fila por población y grupo de edad, con los
casos y los expuestos. Los nombres de las columnas se declaran en
`parametros.csv`, así que no hace falta renombrar nada. Sirve para mortalidad,
pero también para incidencia, para accidentes o para cualquier cosa que sea
«casos sobre expuestos» y dependa de la edad.

El archivo de estándares es otra tabla: un grupo de edad por fila y una columna
por estándar. **El orden de sus filas es el orden de los grupos de edad en todo
el proyecto**, que es la única manera de que «0 a 9» salga antes que «10 a 14»
sin hacer suposiciones sobre cómo están escritas las etiquetas.

Los dos tienen que usar exactamente los mismos grupos. Si no, el proyecto para y
lo dice: una tasa ajustada con grupos faltantes no se puede comparar con otra
que los tenga.

## Lo que no hace

- **No estandariza por nada que no sea una variable categórica de agrupamiento.**
  Es edad porque es el caso normal, pero cualquier columna sirve. Lo que no hace
  es ajustar por varias a la vez.
- **No calcula esperanza de vida** ni construye tablas de mortalidad.
- **No hace series de tiempo** ni prueba tendencias.
- **No suaviza las tasas específicas.** Con poblaciones muy chicas eso ayuda, y
  es un método bayesiano que merece su propio proyecto; acá la recomendación es
  usar la indirecta.
- **No corrige el subregistro.** Si al registro de defunciones le faltan casos,
  la tasa ajustada va a estar igual de baja que la cruda.

## Los dos idiomas

Las salidas son idénticas byte a byte, y eso es a propósito: si las dos
versiones dan lo mismo, el resultado no depende del programa.

Las dos usan el cuantil de la chi cuadrado que trae cada motor —`qchisq` en R,
`scipy.stats.chi2.ppf` en Python—. Las dos implementaciones coinciden hasta la
decimosexta cifra significativa, cinco órdenes de magnitud más allá de las diez
que este proyecto escribe; está comprobado en el verificador sobre el rango de
grados de libertad que la fórmula de Fay-Feuer produce, que llega al millón.

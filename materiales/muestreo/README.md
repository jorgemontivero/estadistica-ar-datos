# Muestreo: selección, ponderadores y estimación

Cinco diseños sacados del mismo marco, los ponderadores que les corresponden,
y la estimación con **el error estándar del diseño** al lado del que sale de
ignorarlo. En R y en Python, con la misma muestra.

## Cómo se corre

```r
source("R/correr.R")      # en R, desde la carpeta del proyecto
```

```bash
python python/correr.py   # en Python
```

El diseño se declara en `datos/parametros.csv`:

```text
semilla,2026
estrato,region
conglomerado,radio
calibrar_por,tamano
conglomerados_por_estrato,8
hogares_por_conglomerado,10
tasa_de_no_respuesta,0.12
replicas_de_cobertura,500
```

## Los datos no son una muestra: son la población

`datos/marco.csv` tiene los **4.000 hogares** de una ciudad inventada,
repartidos en 4 regiones y 200 radios censales de 20 hogares cada uno. Eso
permite hacer lo único que en la vida real nunca se puede hacer: **mirar si el
intervalo le acertó**.

El ingreso se armó en dos capas —un efecto de radio y un ruido de hogar—,
porque es lo que pasa en cualquier ciudad: los vecinos se parecen. Toda la
lección del proyecto sale de ahí.

## Lo que este proyecto quiere que no te pase

**Que calcules el promedio con los ponderadores y el error estándar sin
ellos.**

Es el error más común en el análisis de encuestas y el más difícil de ver,
porque el número que sale es perfectamente plausible. Sobre la muestra
bietápica del ejemplo, para el ingreso medio:

```text
estimación                       616.932
error estándar del diseño         48.275
error estándar ignorándolo        25.390
```

El segundo es **la mitad** del primero. El intervalo que sale de él es la mitad
de ancho, y es el que aparece en la mayoría de los informes.

**Y no es mala suerte de una muestra.** El proyecto vuelve a sacar la muestra
500 veces y cuenta cuántas veces cada intervalo del 95 % contiene al valor
verdadero, que acá se conoce:

```text
con el diseño          cubre el 92,0 %
ignorando el diseño    cubre el 61,0 %
```

Un intervalo que promete 95 y entrega 61. Esa es la diferencia entre las dos
fórmulas, medida y no discutida.

## El efecto de diseño no siempre es un castigo

Los cinco diseños salen del mismo marco, con el mismo n y la misma semilla:

| Diseño | deff | n efectivo |
|---|---:|---:|
| Aleatorio simple | 1,000 | 320 |
| Sistemático | 1,000 | 320 |
| Estratificado proporcional | 0,965 | 332 |
| Estratificado de Neyman | 0,902 | 355 |
| Bietápico | 3,615 | 89 |

La estratificación **gana** precisión: saca de la varianza las diferencias
entre regiones, y con la afijación de Neyman —más muestra donde hay más
dispersión— la muestra de 320 rinde como una de 355. El conglomerado la
**paga**: 320 hogares en 32 radios rinden como 89 hogares sueltos, porque los
vecinos se parecen y el décimo hogar de un radio agrega mucho menos
información que el primero.

Eso no significa que conglomerar esté mal. Significa que se paga, y que el
tamaño de muestra hay que decidirlo sabiendo cuánto. Visitar 32 radios cuesta
una fracción de lo que cuesta visitar 320 direcciones dispersas.

## Una sola fórmula para los cinco diseños

La varianza se calcula siempre por el método de la **última etapa**: dentro de
cada estrato, la variabilidad entre los totales ponderados de cada unidad
primaria.

```text
v = Σ_h (1 − f_h) · a_h/(a_h − 1) · Σ_i (z_hi − z̄_h)²
```

Con conglomerados, la unidad primaria es el conglomerado. Sin conglomerados,
cada unidad es su propia unidad primaria y la fórmula **se reduce exactamente**
a la del estratificado; con un solo estrato, a la del aleatorio simple con
corrección por población finita. No hay cinco fórmulas: hay una, mirada desde
cinco diseños.

Dos detalles que están adentro y casi nunca se ven:

**La linealización.** Una media ponderada es una razón, y su denominador
también es aleatorio. Hay que restarle la estimación a cada valor antes de
acumular por conglomerado; saltear ese paso infla la varianza de una media
hasta el absurdo.

**Los grados de libertad.** Son (unidades primarias − estratos), no (n − 1).
Acá son 28 y no 319. Usar n − 1 angosta el intervalo de más, encima de todo lo
demás.

## Por qué la selección se hace con el generador de R

Una muestra hay que poder volver a sacarla. Si alguien pregunta cómo se
eligieron esos 320 hogares, la respuesta tiene que ser un par de líneas que
cualquiera pueda correr.

El estándar de hecho para eso es R. Por eso **la versión en R usa `set.seed` y
`sample.int` tal cual** y la de Python reimplementa ese generador bit por bit,
en `python/azar.py`. Es el único archivo de toda la serie que no tiene
equivalente del otro lado, y la asimetría es a propósito: al revés no
serviría, porque nadie audita una selección corriendo el `random` de Python.

Lo que hay que copiar y no es obvio: el sembrado pasa la semilla cincuenta
veces por una congruencial antes de tocar el estado; la primera posición del
vector es el índice y se descarta; y desde la versión 3.6 R sortea enteros por
rechazo, con un bucle de bits que va de 0 a `bits` **inclusive**, así que con
16 bits justos hace dos tandas y no una. Parece un descuido de R y es lo que R
hace: copiarlo «corregido» daría otra muestra.

La calculadora `calc-muestreo` del sitio hace lo mismo en TypeScript, así que
la página, este proyecto y R coinciden en la muestra.

## Los ponderadores, en tres momentos

| Momento | Qué tiene que cumplir |
|---|---|
| De diseño | Sumar exactamente la población. Si no, hay un error en las probabilidades de inclusión |
| Ajustados por no respuesta | Volver a sumarla, después de repartir el peso de los que no contestaron |
| Post-estratificados | Dar los totales conocidos por celda |

En el ejemplo contestaron **276 de 320**. El ajuste reparte el peso de los que
faltan entre sus vecinos del mismo radio —lo que supone que se parecen, y eso
es un supuesto, no un dato— y los pesos vuelven a sumar 4.000 exacto.

La post-estratificación se hace sobre el **tamaño del hogar**, que es un dato
que un censo conoce y que el diseño no controló:

```text
1 a 2 personas     en el marco 1.299    estimado 1.246    factor 1,043
3 a 4 personas     en el marco 1.754    estimado 1.895    factor 0,925
5 o más            en el marco   947    estimado   859    factor 1,103
```

La muestra se había quedado corta de hogares chicos y grandes y larga de
medianos. La calibración lo corrige, y esa es la parte del sesgo de no
respuesta que sí se puede arreglar.

**Ojo con qué variable se calibra.** Si se calibra sobre la misma que
estratificó el diseño, todos los factores dan uno y no se corrige nada —el
proyecto lo avisa cuando pasa—. Calibrar sobre algo que el diseño ya controla
da la sensación de haber hecho algo sin haberlo hecho.

## Lo que no hace

**No hay selección con probabilidad proporcional al tamaño (PPS).** Es lo que
usa cualquier encuesta de hogares grande y merece su propio proyecto.

**No hay remuestreo para la varianza** —ni jackknife por grupos ni bootstrap
de conglomerados—. La linealización alcanza para medias, totales y
proporciones, que es lo que este proyecto estima.

**No hay calibración con varias variables a la vez.** Con una sola es una
cuenta de una línea; con varias hay que iterar, que es el «raking».

**No hay tamaño de muestra.** Para eso están `calc-tamano-muestra` y
`plantilla-tamano-muestra` en el sitio.

## Los dos idiomas

Las dos versiones escriben los diez archivos byte a byte iguales, la
simulación de cobertura incluida. Lo único que necesita SciPy es la t de
Student para los valores críticos; en R viene de fábrica.

Plantilla de estadistica.ar · CC BY-NC-SA 4.0

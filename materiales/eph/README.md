# EPH: leer los microdatos del INDEC sin arruinarlos

Un proyecto que abre un archivo de la Encuesta Permanente de Hogares, calcula
las cuatro tasas del mercado de trabajo y el ingreso de la ocupación principal,
y escribe el informe. Está en **R y en Python**, y los dos escriben exactamente
los mismos bytes.

No es una biblioteca ni un paquete: son seis archivos por idioma que se leen de
arriba abajo. El que quiera cambiar un criterio va a poder encontrar dónde.

## Cómo se corre

Desde la carpeta del proyecto:

```bash
python python/correr.py
```

```r
source("R/correr.R")
```

Las salidas quedan en `salidas/`: diez CSV y un `eph.md` con el informe
redactado. Los dos idiomas los escriben idénticos.

Python necesita `scipy`, y solo para el cuantil de la t de Student.

## El archivo de ejemplo no es la EPH

`datos/usu_individual_T425_simulado.txt` está **simulado**. Tiene el formato exacto de
un `usu_individual_Tnnaa.txt` del INDEC —punto y coma, latin-1, los mismos
nombres de columna y los mismos códigos— y copia el **diseño** de la encuesta:
los 32 aglomerados relevados, con su región y con su peso relativo en la
muestra y en la población. Lo que no copia es ningún dato de ninguna persona.

La muestra está a la octava parte de la real, y la población con ella. Es a
propósito: así ningún número que salga de este proyecto se puede confundir con
una cifra publicada por el INDEC. Las tasas quedan cerca de las reales porque
el modelo está calibrado contra ellas, pero **son de un archivo inventado**.

Para correrlo sobre datos de verdad:

1. Bajá el trimestre de
   [las bases del INDEC](https://www.indec.gob.ar/indec/web/Institucional-Indec-BasesDeDatos).
2. Descomprimilo en `datos/`.
3. Cambiá `archivo` en `datos/parametros.csv` al `usu_individual_Tnnaa.txt` que
   salió.

No hace falta tocar nada más. El archivo real de 2025T4 tiene **235 columnas**
—el de 2016T2 tenía 177, y el número cambia de trimestre en trimestre— y el de
ejemplo tiene 22. El código elige por nombre, así que las dos cosas andan.

## Lo que este proyecto quiere que no te pase

**El ingreso medio de la EPH se calcula mal casi siempre, y de una manera muy
particular: hacen falta dos descuidos juntos, y cada uno por separado es
invisible.**

En `P21` —ingreso de la ocupación principal— el `-9` no es un ingreso negativo:
quiere decir «no responde». Y el ponderador que corresponde no es `PONDERA`
sino `PONDIIO`, que reparte la población **de los que declararon**.

Corrido sobre el archivo de ejemplo, el mismo promedio da:

| Cómo se calculó | Media | Diferencia |
| --- | --- | --- |
| `PONDIIO`, sacando el −9 | $ 715.067 | — |
| `PONDIIO`, dejando el −9 | $ 715.067 | **exactamente la misma** |
| `PONDERA`, sacando el −9 | $ 700.544 | −2,0 % |
| `PONDERA`, dejando el −9 | $ 565.082 | −21,0 % |

Las dos primeras filas dan **lo mismo hasta el último decimal**, y ahí está
todo el asunto: el INDEC le pone `PONDIIO = 0` al que no contestó, así que el
−9 ya viene sacado. El filtro que uno nunca escribió no hace falta.

Hasta que hace falta. **Antes de 2016T2 las bases de la EPH no traen
`PONDIIO`** —ni `PONDII`, ni `PONDIH`—. El día que el mismo script se corre
sobre un trimestre viejo, el ponderador no está, el filtro nunca se escribió, y
el promedio se cae un quinto sin que nada aparezca en pantalla.

Por eso el paso 1 revisa que el ponderador de ingreso exista y lo escribe en
`avisos.csv` cuando no está, en vez de seguir de largo.

## Las cuatro tasas y sus cuatro denominadores

El otro error caro es más simple y se ve más seguido:

    actividad      PEA / población total
    empleo         ocupados / población total
    desocupación   desocupados / PEA
    subocupación   subocupados / PEA

**La desocupación no se divide por la población.** Un 7 % no quiere decir que
siete de cada cien personas no tengan trabajo: quiere decir que siete de cada
cien que lo buscan no lo consiguen. Dividido por la población total da menos de
la mitad, y da un número que no se compara con nada.

Las tres primeras tienen que cerrar entre sí:

    empleo = actividad × (1 − desocupación)

El proyecto calcula las tres por separado y después escribe el residuo de esa
resta en `resumen.csv`. Es la única comprobación que no depende de tener razón
sobre ninguna otra cosa.

## El error estándar, y por qué el que sale de acá es optimista

La EPH es una muestra por conglomerados, y eso cambia el error estándar, no la
estimación. Todo lo que el proyecto estima —las tasas, el ingreso medio, la
informalidad— es una razón entre dos totales ponderados, y las tres se calculan
con la misma función, linealizando:

    z_i = w_i · (y_i − p·x_i)

y sumando los z por unidad primaria dentro de cada estrato.

**El estrato es el aglomerado y la unidad primaria es el hogar.** No es lo
ideal. El conglomerado de verdad es el radio censal, y el archivo público no lo
trae. Con el hogar se captura que los miembros de un hogar se parecen y se
pierde que los vecinos se parecen, así que **el error estándar que sale de acá
es una cota inferior**: el verdadero es más grande. Con el archivo publicado no
se puede hacer mejor, y decirlo es parte de hacerlo bien.

Aun así, el efecto de diseño de las cuatro tasas va de 2,5 a 3,1: los 5.507
casos de la tasa de actividad valen como 1.816. Cualquier programa al que se le
pase la columna sin contarle del diseño va a informar un intervalo bastante más
corto del que corresponde.

Los grados de libertad son **unidades primarias menos estratos**, no n − 1: con
1.871 hogares y 32 aglomerados son 1.839.

## Las otras trampas, y dónde están contempladas

- **`NA` escrito con letras.** En algunos trimestres —2021T1, 2024T3 y 2024T4
  entre ellos— el INDEC escribe los faltantes como `NA`. Cualquier lector que
  adivine tipos convierte ahí mismo unas ciento cincuenta columnas numéricas en
  texto. Este proyecto lee **todo como texto** y decide después, columna por
  columna.
- **`CH06 = -1`.** Quiere decir «menos de un año», no «falta el dato».
  Promediar la columna sin mirarla baja la edad media.
- **El ponderador es del hogar, no de la persona.** Todos los miembros de un
  hogar comparten `PONDERA`. Por eso el hogar sirve como unidad primaria.
- **Un archivo con más de un trimestre adentro.** Pasa cuando alguien concatena
  bases. Las tasas que salen son un promedio de trimestres y no son la tasa de
  ninguno; el paso 1 lo detecta y avisa.
- **La coherencia entre `P21` y `PONDIIO`.** En una base del INDEC, el
  ponderador de ingreso vale cero justo para los que no declararon. El paso 1 lo
  comprueba: si no se cumple, el archivo no es el que uno cree.

## Cómo se lee el archivo

Tres detalles que no son detalles, y que están en `leer_microdatos`:

- **El separador es el punto y coma.** Con la coma sale una sola columna, y
  algunos programas no avisan.
- **La codificación es latin-1**, no UTF-8.
- **Los textos vienen entre comillas** y los números no.

## Los deciles no salen del mismo tamaño

Los ingresos declarados se amontonan en cifras redondas —medio millón,
setecientos mil— y un corte que cae sobre un montón se lleva el montón entero
para un lado. El proyecto usa una definición explícita del cuantil ponderado
—el primer valor cuyo peso acumulado llega a p·W— y no interpola, justamente
para que los dos motores den lo mismo. Los deciles desparejos que salen de ahí
no son un error de cálculo: son la distribución.

## Lo que no hace

- No lee el archivo de **hogar** ni lo cruza con el de individual. Todo lo que
  calcula es de personas.
- No arma **series** de varios trimestres.
- No calcula **pobreza**: eso necesita la canasta y el archivo de hogar.
- No ajusta por **inflación**. Los ingresos son del trimestre y en pesos de ese
  trimestre.
- No calcula el **Gini** ni la curva de Lorenz. Para eso está la calculadora del
  sitio.
- No corrige nada en silencio. Lo que está raro va a `avisos.csv`.

## Los dos idiomas

Las salidas son idénticas byte a byte, y eso es a propósito: si las dos
versiones dan lo mismo, el resultado no depende del programa.

Hay una diferencia de forma. **La versión de R trabaja por columnas y la de
Python por filas.** Recorrer cinco mil quinientos registros de a uno es natural
en Python y es la manera equivocada de escribir R. Las dos hacen las mismas
cuentas en el mismo orden; lo que cambia es de qué lado se paran.

Donde sí se hizo un esfuerzo por coincidir es en el orden de las sumas: los
estratos y los hogares se recorren ordenados, siempre igual, porque de eso
depende el último bit de la varianza.

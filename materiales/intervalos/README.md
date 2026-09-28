# Intervalos de confianza

Los cinco intervalos que hacen falta en un informe —media, varianza y desvío,
proporción, diferencia de medias y diferencia de proporciones— calculados
sobre el total y dentro de cada grupo, en R y en Python.

## Cómo se corre

```r
source("R/correr.R")      # en R, desde la carpeta del proyecto
```

```bash
python python/correr.py   # en Python
```

## Qué deja

| Archivo | Qué trae |
|---|---|
| `ic-medias.csv` | La media de cada variable numérica, con su error estándar, sus grados de libertad y su intervalo |
| `ic-varianzas.csv` | La varianza y el desvío, por chi-cuadrado |
| `ic-proporciones.csv` | Cada categoría, por los tres métodos: Wilson, Wald y Clopper-Pearson |
| `ic-diferencias.csv` | La diferencia entre cada par de grupos, con las dos columnas que dicen si mirar los intervalos por separado engaña |
| `avisos.csv` | Cada supuesto que no se cumple, con el intervalo que lo disparó |
| `intervalos.md` | El informe redactado, listo para pegar |
| `resumen.csv` | Cuántos intervalos salieron de cada tipo |

Cada fila lleva un **ámbito**: `Total` para la muestra entera, y el nombre del
grupo para los de adentro de cada grupo.

## Lo que este proyecto quiere que no te pase

**Que publiques los intervalos de los dos grupos y concluyas, porque se pisan,
que no hay diferencia.** No se sigue, y es el error más común con intervalos.

El intervalo de la diferencia usa el error estándar de la diferencia, que es
√(EE₁² + EE₂²) y no EE₁ + EE₂. Como la raíz de la suma de cuadrados es menor
que la suma, hay un rango entero de diferencias donde los dos intervalos se
pisan y sin embargo el de la diferencia no contiene al cero.

Por eso `ic-diferencias.csv` trae las dos cosas al lado —`se_pisan_los_individuales`
y `excluye_cero`— y una tercera columna, `conclusion_distinta`, que dice «Sí»
cuando mirar los intervalos por separado lleva a la conclusión contraria. En
los datos de ejemplo pasa con las horas de estudio: los intervalos de los dos
grupos se pisan y el de la diferencia va de 0,38 a 3,24.

**Lo que hay que informar es el intervalo de la diferencia.** Los otros dos
sirven para describir cada grupo, no para compararlos.

## Las decisiones que toma sola

**Wilson para las proporciones.** Es el que se informa en `intervalos.md`.
Wald —la fórmula clásica p ± z·√(p(1−p)/n)— tiene mala cobertura con n chico o
con proporciones cerca de 0 o de 1, y en el extremo da un intervalo de ancho
cero, que es absurdo. Los tres métodos quedan igual en el CSV: con la beca,
que la tienen 7 de 150, se ve cuánto se separan.

**t y no z para la media.** Salvo que declares que conocés σ, que casi nunca
pasa: si el desvío lo calculaste con estos mismos datos, σ no es conocida.

**Welch para la diferencia de medias.** Sin suponer varianzas iguales, que es
lo que corre R por omisión. Los grados de libertad salen con decimales, y eso
no es un error.

**La confianza y la población están en `datos/parametros.csv`**, no en el
código: son los dos parámetros que más se tocan. Si dejás la población en
blanco no hay corrección por población finita, que es el caso habitual. Si la
completás, los intervalos de una muestra se achican y el aviso lo dice.

## Lo que no hace

**No calcula intervalos por bootstrap.** Todos los de acá son paramétricos.

**No corrige por comparaciones múltiples.** Con más de dos grupos compara
todos los pares, y avisa: cada intervalo es del 95 % por separado, no en
conjunto.

**No aplica la corrección por población finita a la diferencia ni a la
varianza.** A la diferencia porque la calculadora del sitio tampoco lo hace; a
la varianza porque el intervalo sale de la chi-cuadrado, que no la contempla.

## Los avisos

`avisos.csv` es lo que dicen las funciones de la calculadora de estadistica.ar,
palabra por palabra. No son decorativos: cada uno marca un supuesto que estos
datos no cumplen. Los que más aparecen son el de la categoría con menos de
cinco casos, el del grupo con menos de treinta y el del intervalo de la
varianza, que es el menos robusto de todos.

## Los dos idiomas

Las dos versiones escriben los mismos archivos, byte a byte. Lo único que
necesita SciPy son los cuantiles —qt, qnorm, qchisq y qbeta—; en R vienen de
fábrica.

Plantilla de estadistica.ar · CC BY-NC-SA 4.0

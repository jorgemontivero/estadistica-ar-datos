# No paramétricas y bootstrap

Las pruebas que no suponen normalidad —apareadas y de muestras
independientes—, intervalos por bootstrap para cualquier estadístico, y una
prueba de permutación. En R y en Python, sin `wilcox.test`, sin `boot` y sin
`sample()`.

## Cómo se corre

```r
source("R/correr.R")      # en R, desde la carpeta del proyecto
```

```bash
python python/correr.py   # en Python
```

Qué se compara con qué se declara en `datos/parametros.csv`:

```text
antes,previo            # la misma unidad, medida dos veces
despues,desempeno
respuesta,gasto         # dos muestras independientes
grupo,grupo
factor,nivel            # tres o más muestras
replicas,2000
semilla,20260930
```

Cualquiera de los bloques puede quedar vacío.

## Qué deja

| Archivo | Qué trae |
|---|---|
| `apareadas.csv` | Wilcoxon y la prueba de los signos, y las dos pruebas que **no** corresponden, para comparar |
| `el-cambio.csv` | La mediana, la media y el desvío del cambio, y si tirar el apareamiento cambia la conclusión |
| `mann-whitney.csv` | U, el valor p, **P(X > Y)**, el desplazamiento de Hodges-Lehmann y la t de Welch al lado |
| `kruskal-wallis.csv` | H con corrección por empates, ε² y los grados de libertad |
| `kruskal-grupos.csv` | n, mediana y rango promedio de cada grupo |
| `bootstrap.csv` | Percentil, básico y BCa para cada estadístico, con z₀ y la aceleración |
| `permutacion.csv` | La prueba de permutación sobre la diferencia de medianas |
| `avisos.csv` | Cada supuesto que no se cumple y cada conclusión que depende de una decisión |
| `no-parametricas.md` | El informe redactado |

## Lo que este proyecto quiere que no te pase

**Que tires el apareamiento.**

En los datos de ejemplo hay 148 personas evaluadas dos veces: al entrar y al
salir. Analizado como lo que es —una muestra de cambios— da esto:

```text
Wilcoxon de rangos con signo      p = 0,0004
Prueba de los signos              p = 0,0002
```

Analizado como si fueran dos muestras distintas, que es lo que pasa cuando
alguien pega las dos columnas una debajo de la otra:

```text
Mann-Whitney                      p = 0,206
t de Welch                        p = 0,220
```

La misma tabla, la conclusión al revés. Y la razón es aritmética, no
doctrinaria: **el cambio típico es de 1,7 puntos con un desvío de 5,7, y lo
que separa a una persona de otra son 12,5 puntos al entrar y 10,6 al salir.**
La comparación apareada mide el efecto contra la variabilidad de los cambios;
la otra tiene que buscarlo adentro de la variabilidad entre personas, que es
casi el doble de grande. El apareamiento es información que está en los
datos, y tirarla no es una decisión conservadora: es perder el resultado.

## Dos cosas más que el ejemplo deja ver

### Mann-Whitney no contrasta la igualdad de medianas

Es la afirmación más repetida sobre esta prueba y es falsa. Lo que contrasta
es **P(X > Y) = ½**: la probabilidad de que un caso tomado al azar de un grupo
supere a uno del otro. Solo cuando las dos distribuciones tienen la misma
forma esa hipótesis equivale a la de medianas iguales.

Por eso el proyecto escribe P(X > Y) al lado del valor p —en el ejemplo vale
**0,301**, la probabilidad de que un caso de Control supere a uno de
Tratamiento— y el desplazamiento de **Hodges-Lehmann**, que es la mediana de
todas las diferencias entre un caso de un grupo y uno del otro. Ese último es
el número que corresponde informar como «de cuánto es la diferencia».

### Un promedio y una mediana que apuntan para lados opuestos

El gasto en materiales del ejemplo trae tres valores enormes —los mismos que
el descargable de gráficos deja a la vista en su diagrama de caja—, y los tres
cayeron del lado de Control. El resultado:

```text
diferencia de medianas    +11.626    IC 95 % [ 5.170;  16.454]
diferencia de medias       −4.693    IC 95 % [−25.151; 12.034]
```

Signos opuestos. Y las pruebas dicen lo mismo:

```text
Mann-Whitney    p = 0,00003
t de Welch      p = 0,625
```

La t no ve nada porque los tres casos le inflaron la varianza; la de rangos no
los ve como valores enormes, los ve como tres puestos más arriba en el orden.
**Con datos asimétricos, la prueba de rangos suele tener más potencia que la
paramétrica**, que es lo contrario de lo que se suele creer.

## Los tres intervalos de bootstrap, y por qué son tres

| Intervalo | Qué corrige |
|---|---|
| Percentil | Nada. Es el que todo el mundo usa |
| Básico | El sesgo de traslación, reflejando alrededor del valor observado |
| BCa | El sesgo y la asimetría, con z₀ y una aceleración que sale de un jackknife |

Con un estadístico simétrico dan lo mismo. Con uno asimétrico se separan, y el
percentil empieza a mentir. En el ejemplo, sobre el gasto:

```text
                       percentil                    BCa
mediana       [31.992;  39.030]          [31.992;  39.030]
media         [36.723;  54.956]          [37.783;  58.968]
desvío        [14.179;  86.444]          [30.825;  99.443]
```

Para la mediana los dos coinciden hasta el redondeo. Para el desvío, el límite
inferior del percentil es 14.179 y el del BCa es 30.825: **más del doble**. El
proyecto avisa cuando el corrimiento pasa del 10 % del ancho.

## Por qué el generador de azar está escrito a mano

Porque `sample()` de R y `random` de Python **no sortean lo mismo**. Los dos
usan Mersenne Twister, pero siembran el estado distinto y convierten el número
de 32 bits en un índice distinto. Con la misma semilla y el mismo n, la
primera fila remuestreada ya sale diferente.

En un bootstrap eso no es un detalle de formato: cada límite de cada intervalo
sale de qué filas tocaron. `azar.R` y `azar.py` implementan el generador de
Lehmer de Park y Miller —x ← 48271·x mod 2³¹−1— porque el producto más grande
entra exacto en un número de doble precisión, que es lo único que R tiene. El
barajado de la permutación es un Fisher-Yates escrito también a mano, por la
misma razón.

Sus límites están declarados adentro: período de 2.100 millones, del que un
bootstrap de 2.000 réplicas usa la siete milésima parte, y pares consecutivos
sobre un retículo, que es la debilidad conocida de todos los congruenciales.
Para remuestrear una tabla alcanza y sobra; para criptografía, no.

## Lo que apareció al hacer que los dos idiomas coincidan

El bootstrap obligó a resolver dos cosas que en los otros descargables de la
serie no hicieron falta, y las dos son del mismo tipo: **el número está bien,
el que está mal es el supuesto de que dos motores hacen lo mismo.**

La primera es el generador, que está arriba. La segunda apareció después, y
es más sutil: las réplicas se **ordenan** para sacar los cuantiles, y dos
réplicas que difieren en el último bit pueden intercambiar su lugar en ese
orden. Ahí el cuantil interpola entre otro par de vecinos y el intervalo
cambia en el sexto decimal. La solución es redondear cada réplica a diez
dígitos significativos antes de ordenarla.

Pero redondear trajo lo suyo. **`round()` de Python y `round()` de R no
desempatan igual.** Sobre exactamente el mismo número de doble precisión:

```text
round(54955.843065, 5)      Python → 54955,84307
                            R      → 54955,84306
```

No es un error de ninguno de los dos: es un valor que cae justo en la mitad, y
cada lenguaje eligió una regla distinta. Con dos mil réplicas y un cuantil
interpolado, caer en la mitad deja de ser raro —al ejemplo le pasó—. Por eso
el redondeo también está escrito a mano, con la regla «medio para arriba en
valor absoluto», que es aritmética pura.

## Otras dos decisiones que conviene conocer

**La aproximación normal, siempre.** Ni Wilcoxon ni Mann-Whitney usan el valor
p exacto. El exacto solo es viable con muestras chicas, y tener dos regímenes
según el n hace que dos corridas parecidas den números que no se pueden
comparar. Con menos de diez pares el proyecto avisa que el número es apenas
orientativo.

**La prueba de los signos sí es exacta**, hasta mil pares, y por una
recurrencia y no por coeficientes binomiales: C(148, 51) tiene cuarenta y una
cifras, Python lo representa exacto y R no. Arriba de mil pares se pasa a la
normal y la salida lo dice.

**El valor p de permutación lleva la corrección de Davison y Hinkley**:
(extremas + 1) / (réplicas + 1). La permutación observada es una de las
posibles, y contarla evita informar p = 0, que diría que ninguna reordenación
del azar podría dar lo que se vio.

## Lo que no hace

**No hay Friedman** ni ninguna prueba para más de dos medidas repetidas.

**No hay post hoc después de Kruskal-Wallis.** Las comparaciones de a pares
con corrección están en el descargable de ANOVA.

**No hay bootstrap para datos apareados ni para diseños con estratos.** El
remuestreo es simple, o por grupo en el caso de la diferencia.

**No hay intervalos bootstrap-t.** Requieren estimar el error estándar dentro
de cada réplica, que multiplica el costo por el tamaño de la muestra.

## Los dos idiomas

Las dos versiones escriben los diez archivos byte a byte iguales, bootstrap y
permutación incluidos. Lo único que necesita SciPy es la normal, la chi
cuadrado y la t de Welch; en R vienen de fábrica.

Plantilla de estadistica.ar · CC BY-NC-SA 4.0

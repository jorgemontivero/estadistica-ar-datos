# ANOVA, con supuestos, interacción y post hoc

Un ANOVA de uno y de dos factores, con las comparaciones de a pares por los
cuatro métodos y los efectos simples cuando la interacción manda. En R y en
Python, sin `aov` ni `TukeyHSD`.

## Cómo se corre

```r
source("R/correr.R")      # en R, desde la carpeta del proyecto
```

```bash
python python/correr.py   # en Python
```

El diseño se declara en `datos/parametros.csv`, no en el código:

```text
confianza,0.95
respuesta,desempeno
factor,nivel
factor_2,grupo
```

Con `factor_2` vacío el proyecto hace un ANOVA de un factor y nada más.

## Qué deja

| Archivo | Qué trae |
|---|---|
| `celdas.csv` | n, media, desvío, mediana, mínimo y máximo de cada celda |
| `supuestos.csv` | Shapiro-Wilk dentro de cada celda, con el veredicto |
| `anova-un-factor.csv` | La tabla clásica: entre, dentro y total |
| `efecto-y-welch.csv` | η², ω², la versión de Welch y Levene, en una línea |
| `anova-dos-factores.csv` | El modelo completo por sumas de cuadrados de tipo III |
| `tipos-de-suma.csv` | Tipo I en los dos órdenes contra tipo III, con la marca de si cambia alguna conclusión |
| `efectos-simples.csv` | El efecto del segundo factor dentro de cada nivel del primero |
| `post-hoc.csv` | Cada par por los cuatro métodos y también sin corregir |
| `avisos.csv` | Cada supuesto que no se cumple y cada conclusión que depende de una decisión |
| `anova.md` | El informe redactado |

## Lo que este proyecto quiere que no te pase

**Que informes un efecto principal cuando hay interacción.**

En los datos de ejemplo hay un programa de apoyo (`grupo`: Control o
Tratamiento) y el nivel educativo con el que cada persona llegó (`nivel`). La
respuesta es el desempeño en la evaluación final. El efecto principal del
programa da esto:

```text
grupo      SC = 69,56    F(1; 142) = 0,763    p = 0,384
```

No significativo. La conclusión inmediata —«el programa no sirve»— es falsa, y
la tabla de efectos simples dice por qué:

```text
Primario     Tratamiento − Control = +11,97   p < 0,001
Secundario   Tratamiento − Control =  +2,39   p = 0,382
Superior     Tratamiento − Control = −10,09   p < 0,001
```

El programa levanta doce puntos a quien llega con primario y hunde diez puntos
a quien llega con superior. **Los dos efectos se cancelan al promediarlos**, y
lo que queda es un efecto principal de cero con un valor p tranquilizador.

La interacción es la que avisa: F(2; 142) = 15,69, p < 0,001. Por eso, cuando
la interacción sale significativa, este proyecto calcula los efectos simples
solo y pone la advertencia arriba de todo en el informe.

## Dos decisiones que casi nadie declara

### El tipo de suma de cuadrados

Con las celdas balanceadas los tipos de suma de cuadrados dan lo mismo y la
discusión no existe. Con celdas de tamaños distintos —o sea, casi siempre—
dan distinto. El ejemplo tiene celdas de 14 a 35 casos, y el efecto del
programa sale así:

```text
tipo I, con nivel primero      SC =  11,47    p = 0,723
tipo I, con grupo primero      SC =   0,28    p = 0,956
tipo III                       SC =  69,56    p = 0,384
```

La suma de cuadrados se multiplica por doscientos cincuenta según cuál se
elija. Acá las tres conclusiones coinciden —ninguna es significativa—, pero no
tiene por qué ser así, y por eso `tipos-de-suma.csv` trae la columna
`cambia_la_conclusion`.

`anova()` de R devuelve tipo I. SPSS devuelve tipo III. Dos personas con los
mismos datos y distinto programa pueden publicar números distintos sin haberse
equivocado en nada.

### Cuál corrección por comparaciones múltiples

Se corren los cuatro siempre, y también la prueba sin corregir, porque elegir
el método después de ver cuál da significativo es exactamente la maniobra que
las correcciones existen para impedir.

En el ejemplo son quince comparaciones entre las seis celdas:

```text
sin corregir     9 pares significativos
con Tukey        5 pares significativos
```

Esos cuatro pares son el precio de haber hecho quince comparaciones. Y hay un
par donde los cuatro métodos **no coinciden**:

```text
Primario / Control vs Secundario / Tratamiento
    sin corregir   p = 0,004
    Tukey          p = 0,042   ← significativo
    Holm           p = 0,041   ← significativo
    Bonferroni     p = 0,055
    Scheffé        p = 0,128
```

Ahí la conclusión no la deciden los datos: la decide el método. Lo honesto es
decir que está en el borde.

## Por qué no usa `aov`, `TukeyHSD` ni `ptukey`

Porque el proyecto promete que las dos versiones escriben **los mismos
archivos, byte a byte**, y Python no tiene equivalentes exactos de ninguna de
las tres. Lo mismo que en el descargable de regresión: el cálculo se escribe
una vez de cada lado.

Con `ptukey` hay además una razón que no es de comodidad. La distribución del
rango studentizado se integra numéricamente, y la implementación de R usa
dieciséis puntos fijos. Medido contra `scipy.stats.studentized_range`, que es
una implementación independiente:

```text
confianza 0,95  k = 4  ν = 20     valor crítico
esto                              3,958293560921
scipy                             3,958293560945
qtukey de R                       3,958293461450
```

Las dos cuadraturas finas coinciden en once dígitos y la de R se despega en el
octavo. Para decidir si un valor p es mayor o menor que 0,05 da exactamente
igual, pero quien compare este proyecto contra R va a ver la diferencia y
merece saber de dónde sale.

## Lo que sí o sí sale escrito

**El tamaño del efecto, y el ω² al lado del η².** El η² siempre sobreestima,
porque un factor explica algo de variabilidad aunque no haya ningún efecto
real. En el ejemplo el η² da 4,3 % y el ω² 3,0 %: el segundo es el que conviene
informar.

**La versión de Welch al lado de la clásica**, siempre, aunque Levene no
rechace. Es más honesto que decidir cuál mostrar después de ver el resultado.

**El intervalo de confianza de cada comparación**, no solo el valor p.

**La normalidad, por celda y no sobre todo junto.** Si los grupos tienen medias
distintas, la respuesta apilada sale bimodal y Shapiro-Wilk rechaza aunque cada
celda sea perfectamente normal. Lo que el ANOVA supone normal es el residuo.

## Lo que no hace

**No hay medidas repetidas.** Todas las comparaciones son entre sujetos
distintos.

**No hay más de dos factores**, ni covariables (ANCOVA), ni efectos aleatorios.

**No hay alternativa no paramétrica.** Cuando la normalidad no se cumple, el
aviso recomienda Kruskal-Wallis; el cálculo no está.

**No elige por vos qué post hoc informar.** Los cuatro salen en la misma tabla,
y cuál declarar es una decisión que tiene que tomar quien firma el informe.

## Los dos idiomas

Las dos versiones escriben los once archivos byte a byte iguales, incluido el
informe. Lo único que necesita SciPy son las distribuciones —t, F y la normal—
y Shapiro-Wilk; en R vienen de fábrica. El rango studentizado está escrito a
mano de los dos lados.

Plantilla de estadistica.ar · CC BY-NC-SA 4.0

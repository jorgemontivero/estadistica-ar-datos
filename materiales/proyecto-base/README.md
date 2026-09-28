# Proyecto base

El esqueleto de un análisis reproducible, en R y en Python. Copialo, poné tus
datos en `datos/crudos/` y escribí adentro de los dos pasos que ya están.

No usa ningún paquete: corre con R recién instalado y con Python recién
instalado. Los scripts que siguen en estadistica.ar —importar y limpiar,
descriptivos, gráficos— sí usan paquetes, y se apoyan en esta estructura.

## Qué hay adentro

```
datos/crudos/      los datos como llegaron. Acá no se toca nada.
datos/limpios/     lo que produce el paso 1. Se puede borrar y rehacer.
salidas/           tablas y figuras. También se puede borrar y rehacer.
R/                 el análisis en R
python/            el mismo análisis en Python
```

La regla que hace reproducible a un proyecto es esa: **los datos crudos no se
tocan nunca y todo lo demás se puede borrar y volver a generar con un comando**.
Si para rehacer un resultado hace falta acordarse de algo que se hizo a mano,
el proyecto no es reproducible.

## Cómo se corre

En R, desde la carpeta del proyecto:

```r
source("R/correr.R")
```

En Python:

```bash
python python/correr.py
```

Cualquiera de los dos hace lo mismo y escribe lo mismo:

| Archivo | Qué es |
|---|---|
| `datos/limpios/encuesta.csv` | Los datos ya limpios, que es sobre lo que se analiza |
| `salidas/descriptivos.csv` | Una fila por variable: n, media, desvío, mínimo, mediana, máximo |
| `salidas/por-grupo.csv` | Lo mismo, abierto por grupo |
| `salidas/resumen.csv` | Los números sueltos que cita el informe, con su nombre |

Los dos idiomas tienen que dar **exactamente los mismos números**. Si no, hay
un error en alguno de los dos: es la comprobación más barata que existe y casi
nadie la hace.

## Los dos pasos

1. **Importar y limpiar** (`R/01-importar.R`, `python/01_importar.py`): lee el
   crudo, saca los espacios de más, convierte los números, marca lo que está
   fuera de rango, descarta las filas repetidas y guarda el limpio. Deja
   escrito cuántas filas entraron y cuántas salieron, y por qué.

2. **Analizar** (`R/02-analizar.R`, `python/02_analizar.py`): lee el limpio
   —nunca el crudo— y escribe las tablas.

Están separados a propósito: limpiar es lento y se hace una vez; analizar se
repite veinte veces mientras se escribe la tesis.

## Los datos de ejemplo

`datos/crudos/encuesta.csv` es una encuesta ficticia de 120 casos con los
problemas que traen los datos de verdad: espacios de más, una edad imposible,
un ingreso vacío, una fila cargada dos veces y una categoría escrita de dos
maneras. La limpieza los resuelve y deja anotado cuántos eran.

## Qué conviene agregarle

- **Control de versiones.** `git init` en esta carpeta, y un commit cada vez
  que algo funcione. El `.gitignore` ya excluye `datos/limpios/` y `salidas/`,
  que se regeneran.
- **Un registro de sesión.** En R, `sessionInfo()`; en Python,
  `pip freeze`. Guardarlo al lado de los resultados: dentro de dos años va a
  ser la única forma de saber con qué se calculó esto.

Plantilla de estadistica.ar · CC BY-NC-SA 4.0

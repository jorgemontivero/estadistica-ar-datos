# estadistica-ar-datos

Los scripts, los resultados y las comprobaciones detrás de los números de
**[estadistica.ar](https://estadistica.ar)**.

El sitio es una enciclopedia de Estadística en castellano con datos argentinos.
Sostiene, en su página [cómo se hace](https://estadistica.ar/acerca-de/como-se-hace),
que **ningún número se copia de otro lado**: todos se recalculan de archivos
públicos o de simulaciones con semilla fija, y se verifican de forma automática
antes de publicarse.

Este repositorio existe para que eso se pueda comprobar en vez de creerlo.

---

## Qué hay adentro

| Carpeta | Qué es |
|---|---|
| **`generadores/`** | Los scripts que leen los microdatos y producen cada número, con el JSON de resultados al lado. |
| **`verificacion/`** | El verificador que comprueba esos JSON, y el saboteador que comprueba al verificador. |
| **`materiales/`** | Trece paquetes de trabajo en R y en Python, con datos de ejemplo. Son los mismos que se descargan del sitio. |
| **`FUENTES.md`** | De dónde se baja cada fuente pública. |

## Los datos no están acá

Los microdatos —la EPH, las estadísticas vitales de la DEIS, el Censo— los
publica cada organismo con su propia licencia. Copiarlos a este repositorio
crearía una versión paralela que queda vieja y de la que nadie se hace cargo,
así que lo que hay es **el catálogo de dónde bajarlos**: [`FUENTES.md`](FUENTES.md).

Los scripts los buscan en la carpeta que indique la variable de entorno
`DATOS_AR`, y si no está, en `datos-fuente/`:

```bash
export DATOS_AR="/donde/tengas/los/microdatos"    # Linux y macOS
$env:DATOS_AR = "D:\Datos"                        # PowerShell
```

La excepción son los `materiales/`, que **sí traen sus datos**: son archivos
chicos, simulados o recortados a propósito para poder trabajar sin bajar nada.

## Cómo correr un generador

```bash
pip install pandas numpy scipy
python generadores/eph/preparar-ingresos-eph.py
```

Cada script escribe su JSON al lado y también imprime lo que calculó, así que
se puede leer la salida sin abrir el archivo. Todo lo que tiene azar lleva
**semilla fija**: correrlo dos veces da lo mismo, y por eso una diferencia
contra lo publicado es siempre una señal y no ruido.

Arriba de todo, cada generador declara la ruta exacta del archivo que necesita,
el filtro que aplica y el ponderador que usa.

## Cómo se verifica

```bash
python verificacion/verificar-datos.py
```

Comprueba los JSON en cuatro frentes:

1. **La forma.** Que cada archivo tenga los campos que dice tener y que las
   listas midan lo que corresponde.
2. **La aritmética interna.** Que los porcentajes sumen, que un desvío sea la
   raíz de su varianza, que un intervalo contenga a su estimación, que un
   tamaño efectivo sea el que implica el efecto de diseño. Está escrito solo
   con la biblioteca estándar de Python: si el número lo produjo NumPy, no
   tiene sentido comprobarlo con NumPy.
3. **La coherencia entre archivos.** Dos resultados que describen la misma
   población tienen que informar el mismo total.
4. **El recuento contra los microdatos.** El frente que existe porque los otros
   tres no alcanzan: un número puede cerrar contra todos los demás números y
   aun así no ser el que sale del archivo. Este paso necesita los microdatos;
   sin ellos, los otros tres corren igual.

### Quién verifica al verificador

Un verificador que no detecta nada y uno que funciona se parecen mucho: los dos
terminan sin errores.

```bash
python verificacion/sabotear-datos.py
```

Rompe los datos a propósito —cambia un decimal, aplica el ponderador
equivocado, mueve un filtro— y comprueba que el verificador se dé cuenta. Los
primeros sabotajes no son inventados: **reproducen errores que de verdad
estuvieron publicados** en el sitio, y están puestos primero porque son los que
justifican que el verificador exista.

## Los materiales

Trece paquetes autocontenidos, cada uno con su `README.md`, los mismos
análisis resueltos **en R y en Python**, y datos para correrlos:

```
materiales/
├── proyecto-base/        cómo se organiza un proyecto de datos
├── importar-y-limpiar/   leer un archivo sin romperlo
├── descriptivos/         resumen de una variable y tabla 1
├── graficos/             qué gráfico usar y cómo no arruinarlo
├── intervalos/           estimación por intervalo
├── pruebas/              pruebas de hipótesis
├── anova/                análisis de la varianza
├── no-parametricas/      cuando no se cumplen los supuestos
├── regresion/            modelo lineal y diagnóstico
├── multivariado/         componentes principales y conglomerados
├── muestreo/             diseños y cálculo de tamaño
├── estandarizacion/      tasas comparables entre poblaciones
└── eph/                  un análisis completo de la EPH, de punta a punta
```

Los datos de `materiales/eph/` son una base **simulada** con la estructura de
la EPH, no los microdatos reales: sirve para aprender el procedimiento sin
tener que bajar nada y sin problemas de redistribución.

## Qué falla igual

- **Ya se publicaron errores.** Los sabotajes existen porque hubo números mal
  publicados que ningún control atrapó hasta que alguien los miró de nuevo.
- **Los verificadores comprueban consistencia, no verdad.** Pueden decir que
  una cuenta cierra; no pueden decir que la cuenta correspondía.
- **Las interpretaciones no se verifican solas.** Los números se comprueban; lo
  que se dice sobre ellos, no.

Si encontrás algo mal: [jorge@m3s.pro](mailto:jorge@m3s.pro), o abrí un issue.

## Licencia

El código es **MIT** —ver [`LICENSE`](LICENSE)—. Los textos explicativos siguen
la licencia del sitio, **CC BY-NC-SA 4.0**. Los datos de cada fuente pública
mantienen la licencia de su organismo, que figura en su ficha.

---

**Jorge Luis Montivero** · Licenciado en Estadística (UNCa) ·
[m3s.pro](https://m3s.pro) · un proyecto de Mu3Sigma

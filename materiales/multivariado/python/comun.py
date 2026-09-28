"""Lo que comparten los cuatro pasos: leer, tipificar, escribir.

Los números se escriben con seis decimales, redondeados a diez dígitos
significativos, así los archivos de R y los de Python salen idénticos byte a
byte.

Una advertencia sobre las sumas. Todo el núcleo numérico de este proyecto suma
con `suma`, que es un bucle en orden fijo, y no con `math.fsum`. No es por
precisión —con veinticuatro filas cualquiera de las dos alcanza y sobra— sino
por igualdad: `fsum` no tiene equivalente en R, cuyo `sum` acumula en long
double, y de ese último bit dependen los signos que devuelve la
descomposición. Con sumas comunes en el mismo orden, los dos idiomas hacen
exactamente las mismas operaciones de punto flotante y el proyecto entero sale
**idéntico bit a bit**, no solo redondeado a diez dígitos.
"""

import math
from pathlib import Path

from scipy import stats


def limpiar_texto(x: str) -> str:
    return " ".join((x or "").split())


# ------------------------------------------------------------------ leer
def leer_csv(ruta: str | Path) -> list[dict]:
    texto = Path(ruta).read_text(encoding="utf-8-sig")
    lineas = [l for l in texto.replace("\r\n", "\n").split("\n") if l.strip() != ""]
    columnas = [limpiar_texto(c) for c in lineas[0].split(",")]
    filas = []
    for linea in lineas[1:]:
        partes = (linea.split(",") + [""] * len(columnas))[:len(columnas)]
        filas.append({c: limpiar_texto(p) for c, p in zip(columnas, partes)})
    return filas


def numero(x: str):
    x = limpiar_texto(x)
    if x == "":
        return None
    try:
        return float(x)
    except ValueError:
        return None


def leer_parametros(ruta: str | Path) -> dict:
    """Qué archivo, cuántos componentes y cuántos grupos, declarado en un archivo."""
    filas = {f["clave"]: f["valor"] for f in leer_csv(ruta)}

    def texto(clave, por_omision=""):
        v = limpiar_texto(filas.get(clave, ""))
        return v if v else por_omision

    def entero(clave, por_omision):
        v = numero(filas.get(clave, ""))
        return por_omision if v is None else int(v)

    parametros = {
        "datos": texto("datos", "datos/indicadores.csv"),
        "tabla": texto("tabla", "datos/educacion.csv"),
        "unidad": texto("unidad", "jurisdiccion"),
        "componentes": entero("componentes", 3),
        "conglomerados": entero("conglomerados", 4),
        "enlace": texto("enlace", "ward"),
        "ejes": entero("ejes", 2),
        "confianza": numero(filas.get("confianza", "")) or 0.95,
    }
    if parametros["componentes"] < 1:
        raise SystemExit("«componentes» tiene que ser al menos 1.")
    if parametros["conglomerados"] < 2:
        raise SystemExit("«conglomerados» tiene que ser al menos 2.")
    if parametros["ejes"] < 1:
        raise SystemExit("«ejes» tiene que ser al menos 1.")
    return parametros


def leer_matriz(ruta, clave_unidad):
    """Una tabla de «etiqueta + números» en una matriz, con sus nombres.

    Devuelve las filas como lista de listas, en el orden del archivo. **El orden
    del archivo es el orden del proyecto**: no se reordena por nombre, porque
    las distancias y las fusiones se identifican por posición y reordenar
    cambiaría los empates.
    """
    filas = leer_csv(ruta)
    if not filas:
        raise SystemExit(f"{ruta} no tiene ninguna fila.")
    if clave_unidad not in filas[0]:
        raise SystemExit(f"A {ruta} le falta la columna «{clave_unidad}».")
    columnas = [c for c in filas[0] if c != clave_unidad]
    if not columnas:
        raise SystemExit(f"{ruta} no tiene ninguna columna de números.")
    unidades = []
    datos = []
    for f in filas:
        nombre = f[clave_unidad]
        if nombre in unidades:
            raise SystemExit(f"«{nombre}» aparece dos veces en {ruta}.")
        unidades.append(nombre)
        fila = []
        for c in columnas:
            v = numero(f[c])
            if v is None:
                raise SystemExit(f"«{nombre}», columna «{c}»: «{f[c]}» no es un número. "
                                 f"Este proyecto no imputa faltantes: una fila incompleta "
                                 f"no se puede proyectar ni agrupar.")
            fila.append(v)
        datos.append(fila)
    return unidades, columnas, datos


def ordenar(x) -> list[str]:
    return sorted(set(x))


# ------------------------------------------------------------ estadística
def suma(x) -> float:
    """La suma en el orden en que viene, sin compensar.

    No es `math.fsum` a propósito. `fsum` suma sin error acumulado, y R no
    tiene nada equivalente: su `sum` acumula en long double. Cualquiera de las
    dos alcanza y sobra para veinticuatro filas, pero **no dan el mismo último
    bit**, y de ese bit dependen los signos que devuelve Jacobi. Con una suma
    común en un orden fijo, los dos idiomas hacen exactamente las mismas
    operaciones de punto flotante.
    """
    total = 0.0
    for v in x:
        total += v
    return total


def media(x) -> float:
    return suma(x) / len(x)


def desvio(x) -> float:
    """Desvío estándar muestral, con n − 1."""
    if len(x) < 2:
        return float("nan")
    m = media(x)
    return math.sqrt(suma([(v - m) ** 2 for v in x]) / (len(x) - 1))


def tipificar(datos):
    """La matriz centrada y escalada, más las medias y los desvíos que se usaron.

    Es **la** decisión del análisis multivariado y casi nunca se declara. Sin
    tipificar, cada variable pesa según el cuadrado de su unidad de medida: una
    población en personas y un porcentaje en la misma matriz dan un primer
    componente que es la población y nada más. El proyecto calcula las dos
    versiones y las pone al lado.
    """
    n = len(datos)
    p = len(datos[0])
    medias = [media([datos[i][j] for i in range(n)]) for j in range(p)]
    desvios = [desvio([datos[i][j] for i in range(n)]) for j in range(p)]
    for j, d in enumerate(desvios):
        if not d > 0:
            raise SystemExit(f"La columna {j + 1} no varía: todas sus filas valen lo "
                             f"mismo. Una variable constante no aporta nada y rompe la "
                             f"tipificación.")
    return ([[(datos[i][j] - medias[j]) / desvios[j] for j in range(p)]
             for i in range(n)], medias, desvios)


def centrar(datos):
    """Solo centrada, sin escalar: es lo que come el PCA sobre covarianzas."""
    n = len(datos)
    p = len(datos[0])
    medias = [media([datos[i][j] for i in range(n)]) for j in range(p)]
    return ([[datos[i][j] - medias[j] for j in range(p)] for i in range(n)], medias)


def cruzada(datos):
    """La matriz de covarianzas de una matriz ya centrada, con n − 1."""
    n = len(datos)
    p = len(datos[0])
    salida = [[0.0] * p for _ in range(p)]
    for a in range(p):
        for b in range(a, p):
            v = suma([datos[i][a] * datos[i][b] for i in range(n)]) / (n - 1)
            salida[a][b] = v
            salida[b][a] = v
    return salida


def correlacion(x, y) -> float:
    n = len(x)
    mx, my = media(x), media(y)
    sx = math.sqrt(suma([(v - mx) ** 2 for v in x]))
    sy = math.sqrt(suma([(v - my) ** 2 for v in y]))
    if not (sx > 0 and sy > 0):
        return float("nan")
    return suma([(x[i] - mx) * (y[i] - my) for i in range(n)]) / (sx * sy)


def chi2_cola(x: float, gl: int) -> float:
    """La cola derecha de la chi cuadrado. En R es `pchisq(x, gl, lower = FALSE)`."""
    return float(stats.chi2.sf(x, gl))


# ------------------------------------------------------------------ escribir
SIGNIFICATIVOS = 10


def redondear(valor: float) -> float:
    if valor == 0 or not math.isfinite(valor):
        return valor
    decimales = SIGNIFICATIVOS - 1 - math.floor(math.log10(abs(valor)))
    return valor if decimales >= 6 else round(valor, decimales)


def formatear(valor) -> str:
    if valor is None:
        return ""
    if isinstance(valor, bool):
        return "Sí" if valor else "No"
    if isinstance(valor, int):
        return str(valor)
    if isinstance(valor, float):
        if math.isnan(valor):
            return ""
        if math.isinf(valor):
            return "Inf" if valor > 0 else "-Inf"
        texto = f"{redondear(valor):.6f}"
        return "0.000000" if texto == "-0.000000" else texto
    return str(valor)


def entrecomillar(valor: str) -> str:
    if any(c in valor for c in [",", '"', "\n"]):
        return '"' + valor.replace('"', '""') + '"'
    return valor


def escribir_csv(filas: list[dict], ruta: str | Path, columnas: list[str]) -> None:
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    lineas = [",".join(entrecomillar(c) for c in columnas)]
    lineas += [",".join(entrecomillar(formatear(fila.get(c))) for c in columnas)
               for fila in filas]
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")


def escribir_texto(lineas: list[str], ruta: str | Path) -> None:
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")


# ------------------------------------------- cómo se escriben los números
def numero_texto(valor: float, decimales: int) -> str:
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return ""
    if math.isinf(valor):
        return "-infinito" if valor < 0 else "infinito"
    entero, _, decimal = f"{abs(valor):.{decimales}f}".partition(".")
    grupos = []
    while len(entero) > 3:
        grupos.insert(0, entero[-3:])
        entero = entero[:-3]
    texto = ".".join([entero] + grupos)
    if decimales > 0:
        texto += "," + decimal
    return ("-" if valor < 0 else "") + texto


def porcentaje(valor: float, decimales: int = 1) -> str:
    if valor is None:
        return ""
    return numero_texto(valor * 100, decimales) + " %"


def p_texto(p) -> str:
    if p is None or (isinstance(p, float) and math.isnan(p)):
        return ""
    return "< 0,001" if p < 0.001 else numero_texto(p, 3)

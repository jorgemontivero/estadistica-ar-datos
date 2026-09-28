"""Lo que comparten los tres pasos: leer, resumir y escribir.

La media, el desvío y la asimetría están escritos acá con las mismas
definiciones que usa el sitio: el desvío es el muestral, con n − 1, y la
asimetría lleva la corrección por tamaño de muestra que usan SKEW de Excel y
`e1071::skewness` con `type = 2`.

Los números se escriben con seis decimales, redondeados a diez dígitos
significativos, así los archivos de R y los de Python salen idénticos byte a
byte. Diez dígitos son muchos más de los que cualquier dato justifica, y son
los que las dos implementaciones comparten: más abajo cada motor tiene su
propio último bit.
"""

import math
from pathlib import Path


def limpiar_texto(x: str) -> str:
    return " ".join((x or "").split())


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


def numeros(datos: list[dict], variable: str) -> list[float]:
    valores = [numero(f.get(variable, "")) for f in datos]
    return [v for v in valores if v is not None]


def leer_parametros(ruta: str | Path) -> dict:
    """El nivel de significación, que es el único parámetro que hay que elegir."""
    filas = {f["clave"]: f["valor"] for f in leer_csv(ruta)}
    alfa = numero(filas.get("alfa", "")) or 0.05
    if not (0 < alfa < 1):
        raise SystemExit(f"El alfa tiene que estar entre 0 y 1, y es {alfa}.")
    return {"alfa": alfa}


# ------------------------------------------------------------ estadísticas
def media(x: list[float]) -> float:
    return math.fsum(x) / len(x)


def desvio(x: list[float]) -> float:
    """Desvío estándar muestral, con n − 1."""
    if len(x) < 2:
        return float("nan")
    m = media(x)
    return math.sqrt(math.fsum((v - m) ** 2 for v in x) / (len(x) - 1))


def mediana(x: list[float]) -> float:
    orden = sorted(x)
    n = len(orden)
    mitad = n // 2
    return orden[mitad] if n % 2 else (orden[mitad - 1] + orden[mitad]) / 2


def asimetria(x: list[float]):
    """La asimetría corregida por tamaño de muestra, como SKEW de Excel."""
    n = len(x)
    if n < 3:
        return None
    m, s = media(x), desvio(x)
    if not s > 0:
        return None
    return n / ((n - 1) * (n - 2)) * math.fsum(((v - m) / s) ** 3 for v in x)


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
        return "" if math.isnan(valor) else f"{redondear(valor):.6f}"
    return str(valor)


def entrecomillar(valor: str) -> str:
    if any(c in valor for c in [",", '"', "\n"]):
        return '"' + valor.replace('"', '""') + '"'
    return valor


def escribir_csv(filas: list[dict], ruta: str | Path, columnas: list[str]) -> None:
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    lineas = [",".join(entrecomillar(c) for c in columnas)]
    lineas += [",".join(entrecomillar(formatear(fila.get(c))) for c in columnas) for fila in filas]
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")


def escribir_texto(lineas: list[str], ruta: str | Path) -> None:
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")


# ------------------------------------------- cómo se escriben los números
def decimales_de(valor: float) -> int:
    """Uno o dos decimales según la escala. Una media de 41,3 con dos decimales
    finge una precisión que no hay; una de 0,42 con uno se queda corta."""
    return 1 if abs(valor) >= 10 else 2


def numero_texto(valor: float, decimales: int) -> str:
    """El número como se escribe en un informe en castellano: miles con punto y
    decimales con coma."""
    entero, _, decimal = f"{abs(valor):.{decimales}f}".partition(".")
    grupos = []
    while len(entero) > 3:
        grupos.insert(0, entero[-3:])
        entero = entero[:-3]
    texto = ".".join([entero] + grupos)
    if decimales > 0:
        texto += "," + decimal
    return ("-" if valor < 0 else "") + texto


def numero_limpio(valor: float, decimales: int) -> str:
    """Como `numero_texto`, pero sin decimales cuando el número es entero.

    Unos grados de libertad de 2 se escriben «2» y no «2,00»; los de Welch,
    que salen con decimales de verdad, se escriben con ellos.
    """
    if valor == round(valor):
        return numero_texto(valor, 0)
    return numero_texto(valor, decimales)


def p_texto(p) -> str:
    """El valor p como se informa: «< 0,001» o con tres decimales."""
    if p is None or (isinstance(p, float) and math.isnan(p)):
        return ""
    return "< 0,001" if p < 0.001 else numero_texto(p, 3)

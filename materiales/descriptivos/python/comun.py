"""Lo que comparten los dos pasos: leer, calcular y escribir.

Las estadísticas están escritas acá, con la misma definición que usa el sitio:
los cuartiles por interpolación lineal (el tipo 7, el que trae R por omisión y
el que usa Excel), y la asimetría con la corrección por tamaño de muestra que
usan SKEW de Excel y `e1071::skewness` de R con `type = 2`.

Los números se escriben con seis decimales y los conteos como enteros, así los
archivos de R y los de Python salen idénticos byte a byte.
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


# ------------------------------------------------------------ estadísticas
def media(x: list[float]) -> float:
    return math.fsum(x) / len(x)


def desvio(x: list[float]) -> float:
    """Desvío estándar muestral, con n − 1."""
    if len(x) < 2:
        return float("nan")
    m = media(x)
    return math.sqrt(math.fsum((v - m) ** 2 for v in x) / (len(x) - 1))


def cuantil(x: list[float], p: float) -> float:
    """El cuantil por interpolación lineal: el tipo 7, el de R y el de Excel."""
    orden = sorted(x)
    if len(orden) == 1:
        return orden[0]
    h = (len(orden) - 1) * p
    bajo = math.floor(h)
    alto = min(bajo + 1, len(orden) - 1)
    return orden[bajo] + (h - bajo) * (orden[alto] - orden[bajo])


def asimetria(x: list[float]):
    """La asimetría corregida por tamaño de muestra, como SKEW de Excel."""
    n = len(x)
    if n < 3:
        return None
    m, s = media(x), desvio(x)
    if not s > 0:
        return None
    suma = math.fsum(((v - m) / s) ** 3 for v in x)
    return n / ((n - 1) * (n - 2)) * suma


def descriptivos(x: list[float]) -> dict:
    n = len(x)
    if n == 0:
        return {"n": 0}
    asim = asimetria(x)
    return {
        "n": n, "media": media(x), "desvio": desvio(x) if n >= 2 else None,
        "minimo": min(x), "q1": cuantil(x, 0.25), "mediana": cuantil(x, 0.5),
        "q3": cuantil(x, 0.75), "maximo": max(x), "asimetria": asim,
        # La regla del sitio: con |asimetría| > 1 se informa la mediana.
        "forma": "asimétrica" if asim is not None and abs(asim) > 1 else "simétrica",
    }


# ------------------------------------------------------------------ escribir
def formatear(valor) -> str:
    if valor is None:
        return ""
    if isinstance(valor, bool):
        return "Sí" if valor else "No"
    if isinstance(valor, int):
        return str(valor)
    if isinstance(valor, float):
        return "" if math.isnan(valor) else f"{valor:.6f}"
    return str(valor)


def entrecomillar(valor: str) -> str:
    if any(c in valor for c in [",", '"', "\n"]):
        return '"' + valor.replace('"', '""') + '"'
    return valor


def escribir_csv(filas: list[dict], ruta: str | Path, columnas: list[str] | None = None) -> None:
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    columnas = columnas or (list(filas[0]) if filas else [])
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


def coma(texto: str) -> str:
    return texto.replace(".", ",")


def numero_texto(valor: float, decimales: int) -> str:
    """El número como se escribe en un informe en castellano: miles con punto y
    decimales con coma. Un ingreso de 425282,9 se lee mal; 425.282,9 no."""
    entero, _, decimal = f"{abs(valor):.{decimales}f}".partition(".")
    grupos = []
    while len(entero) > 3:
        grupos.insert(0, entero[-3:])
        entero = entero[:-3]
    texto = ".".join([entero] + grupos)
    if decimales > 0:
        texto += "," + decimal
    return ("-" if valor < 0 else "") + texto


def p_texto(p) -> str:
    """El valor p como se informa: «< 0,001» o con tres decimales."""
    if p is None or (isinstance(p, float) and math.isnan(p)):
        return ""
    return "< 0,001" if p < 0.001 else coma(f"{p:.3f}")

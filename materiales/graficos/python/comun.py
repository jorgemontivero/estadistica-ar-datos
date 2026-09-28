"""Los colores, el estilo y las cuentas que hay detrás de cada figura.

Dos decisiones que valen para todo el proyecto:

  · Cada figura se guarda con su tabla. El PNG es para pegar; el CSV de al lado
    es para que cualquiera pueda revisar el número que la figura dibuja. Una
    figura sin su tabla es una afirmación sin fuente.

  · Las clases del histograma salen de la regla de Freedman y Diaconis, acotada
    entre 4 y 25, que es la misma que usa la calculadora de frecuencias del
    sitio. Así la figura y la tabla del informe no se contradicen.
"""

import math
from pathlib import Path

# Los colores del sitio. El acento es el que lleva el dato; el resto es
# andamiaje y va en grises, para que el ojo no compita con la información.
PALETA = {
    "acento": "#0e6b60",
    "acento_fuerte": "#0a4f47",
    "aviso": "#8a5a06",
    "alerta": "#9e382b",
    "gris": "#5b626a",
    "papel": "#fbfaf7",
    "tinta": "#191c1f",
    "borde": "#cbc5b9",
}
# Para una variable con categorías, en este orden.
SERIES = [PALETA["acento"], PALETA["aviso"], PALETA["alerta"], PALETA["gris"],
          PALETA["acento_fuerte"]]
ANCHO, ALTO, DPI = 7.2, 4.0, 300  # 2160 × 1200 píxeles
ANCHO_CAJA = 0.4  # de lo que le toca a cada grupo, igual en los dos idiomas


def estilo():
    """El estilo del sitio, aplicado a matplotlib."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "figure.figsize": (ANCHO, ALTO),
        "figure.dpi": DPI,
        "savefig.dpi": DPI,
        "figure.facecolor": PALETA["papel"],
        "axes.facecolor": PALETA["papel"],
        "axes.edgecolor": PALETA["borde"],
        "axes.labelcolor": PALETA["tinta"],
        "axes.titlecolor": PALETA["tinta"],
        "axes.titlesize": 12,
        "axes.titlelocation": "left",
        "axes.labelsize": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "text.color": PALETA["tinta"],
        "xtick.color": PALETA["gris"],
        "ytick.color": PALETA["gris"],
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "grid.color": PALETA["borde"],
        "grid.linewidth": 0.6,
        "font.size": 10,
    })
    return plt


def eje_castellano(ax, cual: str = "y"):
    """Los números del eje como se escriben acá: 1.500.000 y no 1.5e6.

    matplotlib abrevia los ejes grandes con notación científica y R los escribe
    enteros: sin esto, la misma figura sale distinta en cada idioma."""
    from matplotlib.ticker import FuncFormatter

    def formato(valor, _pos):
        if valor == int(valor):
            entero, decimales = f"{abs(int(valor))}", ""
        else:
            entero, _, resto = f"{abs(valor):.2f}".partition(".")
            decimales = "," + resto.rstrip("0")
        grupos = []
        while len(entero) > 3:
            grupos.insert(0, entero[-3:])
            entero = entero[:-3]
        return ("-" if valor < 0 else "") + ".".join([entero] + grupos) + decimales

    getattr(ax, f"{cual}axis").set_major_formatter(FuncFormatter(formato))


def guardar(fig, nombre: str):
    """Guarda la figura y deja el archivo cerrado."""
    ruta = Path("salidas/figuras") / f"{nombre}.png"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(ruta, facecolor=PALETA["papel"], bbox_inches=None)
    import matplotlib.pyplot as plt
    plt.close(fig)


# ------------------------------------------------------------------ lectura
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


def numeros(datos: list[dict], variable: str) -> list[float]:
    salida = []
    for fila in datos:
        v = limpiar_texto(fila.get(variable, ""))
        if v:
            try:
                salida.append(float(v))
            except ValueError:
                pass
    return salida


# --------------------------------------------------------------- las cuentas
def cuantil(x: list[float], p: float) -> float:
    orden = sorted(x)
    if len(orden) == 1:
        return orden[0]
    h = (len(orden) - 1) * p
    bajo = math.floor(h)
    alto = min(bajo + 1, len(orden) - 1)
    return orden[bajo] + (h - bajo) * (orden[alto] - orden[bajo])


def clases_sugeridas(x: list[float]) -> int:
    """La regla de Freedman y Diaconis, entre 4 y 25, como en el sitio."""
    n = len(x)
    rango = max(x) - min(x)
    ric = cuantil(x, 0.75) - cuantil(x, 0.25)
    if ric > 0 and rango > 0:
        h = 2 * ric / (n ** (1 / 3))
        if h > 0:
            return min(25, max(4, math.ceil(rango / h)))
    return min(25, max(4, math.ceil(math.sqrt(n))))


def agrupar(x: list[float], k: int) -> list[dict]:
    """Las clases, como las arma la calculadora del sitio: todas del mismo
    ancho, cada una incluye su límite inferior y no el superior, salvo la
    última, que incluye el máximo."""
    minimo, maximo = min(x), max(x)
    ancho = (maximo - minimo) / k if maximo > minimo else 1
    clases = []
    for i in range(k):
        desde = minimo + i * ancho
        hasta = maximo if i == k - 1 else desde + ancho
        if i == k - 1:
            ni = sum(1 for v in x if desde <= v <= hasta)
        else:
            ni = sum(1 for v in x if desde <= v < hasta)
        clases.append({"clase": i + 1, "desde": desde, "hasta": hasta,
                       "marca": (desde + hasta) / 2, "n": ni, "pct": ni / len(x) * 100})
    return clases


def caja(x: list[float]) -> dict:
    """Los cinco números de Tukey y los atípicos, con el criterio de 1,5 RIC."""
    q1, mediana, q3 = cuantil(x, 0.25), cuantil(x, 0.5), cuantil(x, 0.75)
    ric = q3 - q1
    tope, piso = q3 + 1.5 * ric, q1 - 1.5 * ric
    dentro = [v for v in x if piso <= v <= tope]
    atipicos = sorted(v for v in x if v < piso or v > tope)
    return {"n": len(x), "minimo": min(dentro) if dentro else min(x), "q1": q1,
            "mediana": mediana, "q3": q3, "maximo": max(dentro) if dentro else max(x),
            "atipicos": atipicos}


def recta(x: list[float], y: list[float]) -> dict:
    """La recta de mínimos cuadrados y el coeficiente de correlación."""
    n = len(x)
    mx, my = math.fsum(x) / n, math.fsum(y) / n
    sxy = math.fsum((a - mx) * (b - my) for a, b in zip(x, y))
    sxx = math.fsum((a - mx) ** 2 for a in x)
    syy = math.fsum((b - my) ** 2 for b in y)
    pendiente = sxy / sxx if sxx > 0 else 0.0
    return {"n": n, "pendiente": pendiente, "ordenada": my - pendiente * mx,
            "r": sxy / math.sqrt(sxx * syy) if sxx > 0 and syy > 0 else float("nan")}


# ------------------------------------------------------------------ escribir
def formatear(valor) -> str:
    if valor is None:
        return ""
    if isinstance(valor, int):
        return str(valor)
    if isinstance(valor, float):
        return "" if math.isnan(valor) else f"{valor:.6f}"
    return str(valor)


def escribir_csv(filas: list[dict], nombre: str, columnas: list[str]) -> None:
    ruta = Path("salidas/figuras") / f"{nombre}.csv"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    lineas = [",".join(columnas)]
    lineas += [",".join(formatear(fila.get(c)) for c in columnas) for fila in filas]
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")

"""Lo que comparten los tres pasos: leer, resumir y escribir.

La media y el desvío están escritos acá con la misma definición que usa el
sitio: el desvío es el muestral, con n − 1, que es el que corresponde cuando
los datos son una muestra y no la población entera.

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


def leer_parametros(ruta: str | Path) -> dict:
    """La confianza y, si se conoce, el tamaño de la población.

    Se leen de un archivo y no del código para que cambiar el nivel de
    confianza no sea editar un script: es el parámetro que más se toca.
    """
    filas = {f["clave"]: f["valor"] for f in leer_csv(ruta)}
    confianza = numero(filas.get("confianza", "")) or 0.95
    if not (0 < confianza < 1):
        raise SystemExit(f"La confianza tiene que estar entre 0 y 1, y es {confianza}.")
    poblacion = numero(filas.get("poblacion", ""))
    if poblacion is not None and poblacion <= 0:
        raise SystemExit(f"La población tiene que ser mayor que cero, y es {poblacion}.")
    return {"confianza": confianza, "poblacion": poblacion}


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


# ------------------------------------------------------------ estadísticas
def media(x: list[float]) -> float:
    return math.fsum(x) / len(x)


def desvio(x: list[float]) -> float:
    """Desvío estándar muestral, con n − 1."""
    if len(x) < 2:
        return float("nan")
    m = media(x)
    return math.sqrt(math.fsum((v - m) ** 2 for v in x) / (len(x) - 1))


# ------------------------------------------------------------------ escribir
SIGNIFICATIVOS = 10


def redondear(valor: float) -> float:
    """Diez dígitos significativos, y ni uno más.

    Los seis decimales de siempre alcanzan mientras los números sean chicos,
    pero la varianza de un ingreso en pesos anda por 10¹¹: ahí seis decimales
    piden dieciocho dígitos significativos, más de los que un `double` tiene.
    Y el último bit de `qchisq` no es el mismo en R que en SciPy —son dos
    implementaciones distintas de la misma función—, así que el archivo salía
    distinto en cada idioma por un dígito que no significaba nada.

    Diez dígitos significativos son muchos más de los que cualquier dato de
    una encuesta justifica, y los dos idiomas coinciden en todos.
    """
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


def intervalo_texto(inferior: float, superior: float, decimales=None) -> str:
    """El intervalo como se informa: «[10,60; 12,69]».

    El separador es punto y coma y no coma, porque los números ya llevan coma
    decimal. «[10,60, 12,69]» tiene cuatro comas y ninguna dice lo mismo.
    """
    if decimales is None:
        decimales = decimales_de(max(abs(inferior), abs(superior)))
    return f"[{numero_texto(inferior, decimales)}; {numero_texto(superior, decimales)}]"


def porcentaje_texto(valor: float, decimales: int = 1) -> str:
    return numero_texto(valor * 100, decimales) + " %"

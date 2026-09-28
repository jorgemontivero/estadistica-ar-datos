"""Lo que comparten los cuatro pasos: leer, agrupar y escribir.

El desvío es el muestral, con n − 1, la misma definición que usa el sitio.

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
    """La confianza y el diseño.

    Qué se compara y según qué vive en un archivo, no en el código: cambiar de
    respuesta o agregar el segundo factor no tiene que obligar a editar un
    script. Con `factor_2` vacío el proyecto hace un ANOVA de un factor y nada
    más.
    """
    filas = {f["clave"]: f["valor"] for f in leer_csv(ruta)}
    confianza = numero(filas.get("confianza", "")) or 0.95
    if not (0 < confianza < 1):
        raise SystemExit(f"La confianza tiene que estar entre 0 y 1, y es {confianza}.")

    parametros = {
        "confianza": confianza,
        "respuesta": limpiar_texto(filas.get("respuesta", "")),
        "factor": limpiar_texto(filas.get("factor", "")),
        "factor_2": limpiar_texto(filas.get("factor_2", "")),
    }
    if not parametros["respuesta"] or not parametros["factor"]:
        raise SystemExit("Faltan «respuesta» o «factor» en parametros.csv.")
    if parametros["factor_2"] == parametros["factor"]:
        raise SystemExit("«factor_2» no puede ser el mismo que «factor».")
    return parametros


# ------------------------------------------------------------------- grupos
def agrupar(datos: list[dict], factores: list[str], respuesta: str):
    """Los valores de la respuesta, partidos por la combinación de factores.

    Devuelve una lista de (etiqueta, tupla de niveles, valores) en el orden que
    fija `ordenar`, y aparte cuántas filas se descartaron. Una fila entra solo
    si tiene la respuesta y **todos** los factores: descartarla en un paso y no
    en otro haría que las tablas no cierren entre sí.
    """
    grupos: dict[tuple, list[float]] = {}
    descartados = 0
    for fila in datos:
        niveles = tuple(limpiar_texto(fila.get(f, "")) for f in factores)
        valor = numero(fila.get(respuesta, ""))
        if valor is None or any(n == "" for n in niveles):
            descartados += 1
            continue
        grupos.setdefault(niveles, []).append(valor)
    orden = ordenar([" / ".join(k) for k in grupos])
    por_etiqueta = {" / ".join(k): (k, v) for k, v in grupos.items()}
    return [(e, por_etiqueta[e][0], por_etiqueta[e][1]) for e in orden], descartados


def ordenar(x) -> list[str]:
    """El orden de las etiquetas, por código de carácter y no por el idioma de
    la máquina: así R y Python escriben las filas en el mismo orden en
    cualquier computadora."""
    return sorted(set(x))


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
        # Un ANOVA con un grupo de varianza cero da F infinito, y el eta²
        # de un factor que explica todo da 1 exacto. El infinito no es un
        # error: es un resultado, y se escribe. R lo llama «Inf» y acá se lo
        # llama igual, porque si no los dos archivos dejarían de ser
        # idénticos.
        if math.isinf(valor):
            return "Inf" if valor > 0 else "-Inf"
        return f"{redondear(valor):.6f}"
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
    # En un informe en castellano un valor que se fue al infinito se escribe
    # con la palabra. «inf» es como lo llama el motor, no como se lee.
    if math.isnan(valor):
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

"""Lo que comparten los cuatro pasos: leer, agrupar y escribir.

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
    """El diseño de la muestra, declarado en un archivo y no en el código.

    Cambiar de estrato, de conglomerado o de tamaño no tiene que obligar a
    editar un script: eso es lo que hace que una selección se pueda repetir y
    documentar.
    """
    filas = {f["clave"]: f["valor"] for f in leer_csv(ruta)}
    confianza = numero(filas.get("confianza", "")) or 0.95
    if not (0 < confianza < 1):
        raise SystemExit(f"La confianza tiene que estar entre 0 y 1, y es {confianza}.")

    def entero(clave, por_omision):
        v = numero(filas.get(clave, ""))
        return por_omision if v is None else int(v)

    parametros = {
        "confianza": confianza,
        "semilla": entero("semilla", 1),
        "estrato": limpiar_texto(filas.get("estrato", "")),
        "conglomerado": limpiar_texto(filas.get("conglomerado", "")),
        "calibrar_por": limpiar_texto(filas.get("calibrar_por", "")),
        "variable": limpiar_texto(filas.get("variable", "")),
        "variable_total": limpiar_texto(filas.get("variable_total", "")),
        "variable_binaria": limpiar_texto(filas.get("variable_binaria", "")),
        "exito": limpiar_texto(filas.get("exito", "")),
        "conglomerados_por_estrato": entero("conglomerados_por_estrato", 8),
        "hogares_por_conglomerado": entero("hogares_por_conglomerado", 10),
        "replicas_de_cobertura": entero("replicas_de_cobertura", 0),
        "tasa_de_no_respuesta": numero(filas.get("tasa_de_no_respuesta", "")) or 0.0,
    }
    if not (0 <= parametros["tasa_de_no_respuesta"] < 1):
        raise SystemExit("«tasa_de_no_respuesta» tiene que estar entre 0 y 1.")
    if not parametros["variable"]:
        raise SystemExit("Falta «variable» en parametros.csv.")
    for clave in ("conglomerados_por_estrato", "hogares_por_conglomerado"):
        if parametros[clave] < 2:
            raise SystemExit(f"«{clave}» tiene que ser al menos 2, y es {parametros[clave]}.")
    return parametros


def ordenar(x) -> list[str]:
    """El orden de las etiquetas, por código de carácter y no por el idioma de
    la máquina: así R y Python escriben las filas en el mismo orden en
    cualquier computadora."""
    return sorted(set(x))


def indices_por(datos: list[dict], columna: str) -> dict:
    """Las posiciones de cada valor de una columna, en orden de aparición.

    Se trabaja con posiciones y no con copias de las filas porque el marco
    tiene miles de registros y cada diseño lo recorre varias veces.
    """
    salida: dict[str, list[int]] = {}
    for i, fila in enumerate(datos):
        salida.setdefault(limpiar_texto(fila.get(columna, "")), []).append(i)
    return {k: salida[k] for k in ordenar(list(salida))}


def cuantil(orden: list[float], p: float) -> float:
    """El cuantil por interpolación lineal, que es el tipo 7 de R y el que usa
    numpy por omisión. `orden` ya tiene que venir ordenado."""
    n = len(orden)
    if n == 0:
        return float("nan")
    if n == 1:
        return orden[0]
    h = (n - 1) * p
    bajo = int(h)
    alto = min(bajo + 1, n - 1)
    return orden[bajo] + (h - bajo) * (orden[alto] - orden[bajo])


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
        texto = f"{redondear(valor):.6f}"
        # Un cero con signo. Pasa con la aceleración del BCa, que a veces da
        # un negativo tan chico que se escribe como cero: ahí el signo no
        # significa nada y además sale distinto en cada motor, porque depende
        # del último bit de una suma. «-0,000000» en una tabla es ruido.
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

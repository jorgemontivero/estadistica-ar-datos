"""Leer el archivo crudo, entender sus valores y escribir los resultados.

Acá están las dos decisiones que se toman antes de mirar un solo dato: con qué
separador viene el archivo y cuál es el separador decimal. Las dos se detectan
y las dos quedan informadas en el resumen, porque adivinar mal cualquiera de
las dos arruina todo lo que venga después.

Los números se escriben con seis decimales fijos y los conteos como enteros:
así los archivos de R y los de Python salen idénticos byte a byte.
"""

from pathlib import Path

SEPARADORES = [",", ";", "\t"]


def limpiar_texto(x: str) -> str:
    """Sin espacios en las puntas ni repetidos adentro."""
    return " ".join((x or "").split())


def detectar_separador(encabezado: str) -> str:
    """El que parte el encabezado en más columnas; si empatan, la coma."""
    mejor, cuantas = ",", 0
    for sep in SEPARADORES:
        n = len(encabezado.split(sep))
        if n > cuantas:
            mejor, cuantas = sep, n
    return mejor


def es_decimal_coma(valores: list[str]) -> bool:
    """Compara cuántos valores tienen forma de 1.234,56 y cuántos de 1,234.56."""
    coma = punto = 0
    for v in valores:
        v = limpiar_texto(v).lstrip("-")
        if not v or not v[0].isdigit():
            continue
        if "," in v and v.rfind(",") > v.rfind("."):
            coma += 1
        elif "." in v and v.rfind(".") > v.rfind(","):
            punto += 1
    return coma > punto


def leer_crudo(ruta: str | Path) -> dict:
    """Devuelve las columnas, las filas y lo que se detectó del archivo."""
    texto = Path(ruta).read_text(encoding="utf-8-sig")
    lineas = [l for l in texto.replace("\r\n", "\n").split("\n") if l.strip() != ""]
    if not lineas:
        raise SystemExit(f"{ruta} está vacío")
    separador = detectar_separador(lineas[0])
    columnas = [limpiar_texto(c) for c in lineas[0].split(separador)]
    filas = []
    for linea in lineas[1:]:
        partes = linea.split(separador)
        # Si a una fila le faltan o le sobran campos, se completa o se corta:
        # es preferible a perder la fila entera sin avisar.
        partes = (partes + [""] * len(columnas))[:len(columnas)]
        filas.append({c: limpiar_texto(p) for c, p in zip(columnas, partes)})
    valores = [f[c] for f in filas for c in columnas]
    return {"columnas": columnas, "filas": filas, "separador": separador,
            "decimal": "," if es_decimal_coma(valores) else "."}


# --------------------------------------------------- entender un valor suelto
def a_numero(texto: str, decimal: str):
    """El texto como número, o None. Dice también si hubo que convertirlo.

    Con coma decimal, el punto es separador de miles; con punto decimal, lo es
    la coma. Sacarlo primero es lo que permite leer «1.234,56» y «1,234.56»."""
    original = texto
    miles = "." if decimal == "," else ","
    texto = texto.replace(miles, "")
    if decimal == ",":
        texto = texto.replace(",", ".")
    convertido = texto != original
    cuerpo = texto[1:] if texto[:1] in "+-" else texto
    if cuerpo == "" or cuerpo.count(".") > 1 or not cuerpo.replace(".", "").isdigit():
        return None, convertido
    return float(texto), convertido


def dias_del_mes(anio: int, mes: int) -> int:
    largos = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    bisiesto = anio % 4 == 0 and (anio % 100 != 0 or anio % 400 == 0)
    return 29 if mes == 2 and bisiesto else largos[mes - 1]


def a_fecha(texto: str):
    """La fecha en aaaa-mm-dd, o None.

    Se aceptan dd/mm/aaaa y aaaa-mm-dd, y se rechaza una fecha que no existe:
    el 31 de febrero no es una fecha, por más que se parezca a una."""
    for sep, orden in [("/", (2, 1, 0)), ("-", (0, 1, 2))]:
        partes = texto.split(sep)
        if len(partes) != 3 or not all(p.isdigit() for p in partes):
            continue
        anio, mes, dia = int(partes[orden[0]]), int(partes[orden[1]]), int(partes[orden[2]])
        if len(partes[orden[0]]) != 4 or not (1 <= mes <= 12):
            continue
        if not (1 <= dia <= dias_del_mes(anio, mes)):
            continue
        return f"{anio:04d}-{mes:02d}-{dia:02d}"
    return None


def codigos(texto: str) -> list[str]:
    return [limpiar_texto(c) for c in texto.split(";") if limpiar_texto(c) != ""]


# ------------------------------------------------------------------ escribir
def formatear(valor) -> str:
    if valor is None:
        return ""
    if isinstance(valor, bool):
        return "Sí" if valor else "No"
    if isinstance(valor, int):
        return str(valor)
    if isinstance(valor, float):
        return f"{valor:.6f}"
    return str(valor)


def entrecomillar(valor: str) -> str:
    """Un valor de CSV: si trae una coma, va entre comillas, y las comillas de
    adentro se duplican. Sin esto, un ejemplo como «529.991,44» corre una
    columna entera del archivo."""
    if any(c in valor for c in [",", '"', "\n"]):
        return '"' + valor.replace('"', '""') + '"'
    return valor


def escribir_csv(filas: list[dict], ruta: str | Path, columnas: list[str] | None = None) -> None:
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    columnas = columnas or (list(filas[0]) if filas else [])
    lineas = [",".join(columnas)]
    lineas += [",".join(entrecomillar(formatear(fila.get(c))) for c in columnas) for fila in filas]
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")

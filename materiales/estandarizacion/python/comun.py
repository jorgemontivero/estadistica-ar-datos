"""Lo que comparten los cuatro pasos: leer, ordenar, estimar y escribir.

Los números se escriben con seis decimales, redondeados a diez dígitos
significativos, así los archivos de R y los de Python salen idénticos byte a
byte. Diez dígitos son muchos más de los que cualquier dato justifica, y son
los que las dos implementaciones comparten: más abajo cada motor tiene su
propio último bit.
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
    """Qué archivo, qué estándar y contra qué comparar, declarado en un archivo.

    Cambiar de estándar o de par a comparar no tiene que obligar a editar un
    script: es lo que hace que un resultado se pueda repetir y discutir.
    """
    filas = {f["clave"]: f["valor"] for f in leer_csv(ruta)}

    def texto(clave, por_omision=""):
        v = limpiar_texto(filas.get(clave, ""))
        return v if v else por_omision

    confianza = numero(filas.get("confianza", "")) or 0.95
    if not (0 < confianza < 1):
        raise SystemExit(f"La confianza tiene que estar entre 0 y 1, y es {confianza}.")

    multiplicador = numero(filas.get("multiplicador", "")) or 100000
    if multiplicador not in (1000, 10000, 100000):
        raise SystemExit("«multiplicador» tiene que ser 1000, 10000 o 100000.")

    # Los pares van separados por punto y coma, y los dos miembros por una
    # barra: «Chaco | Ciudad de Buenos Aires; Catamarca | La Rioja».
    pares = []
    for trozo in texto("pares").split(";"):
        partes = [limpiar_texto(p) for p in trozo.split("|") if limpiar_texto(p)]
        if len(partes) == 2:
            pares.append((partes[0], partes[1]))
        elif partes:
            raise SystemExit(f"«{trozo.strip()}» no es un par: hacen falta dos nombres "
                             f"separados por una barra.")

    return {
        "datos": texto("datos", "datos/mortalidad-2022.csv"),
        "estandares": texto("estandares", "datos/estandares.csv"),
        "estandar": texto("estandar", "oms"),
        "multiplicador": int(multiplicador),
        "confianza": confianza,
        "poblacion": texto("poblacion", "jurisdiccion"),
        "grupo": texto("grupo", "grupo_edad"),
        "casos": texto("casos", "defunciones"),
        "expuestos": texto("expuestos", "poblacion"),
        # Contra qué se compara la indirecta. Vacío quiere decir «contra el
        # total de las poblaciones del archivo», que es lo que hace la DEIS
        # cuando compara provincias contra el país.
        "referencia": texto("referencia"),
        "pares": pares,
    }


def ordenar(x) -> list[str]:
    """El orden de las etiquetas, por código de carácter y no por el idioma de
    la máquina: así R y Python escriben las filas en el mismo orden en
    cualquier computadora. Con «Córdoba» y «Chaco» en la misma tabla, el idioma
    de la máquina decide distinto según dónde esté."""
    return sorted(set(x))


# ------------------------------------------------------------ estadística
def chi2(p: float, gl: float) -> float:
    """El cuantil de la chi cuadrado. En R es `qchisq`.

    Las dos implementaciones coinciden mucho más allá del décimo dígito
    significativo, que es hasta donde este proyecto escribe.
    """
    return float(stats.chi2.ppf(p, gl))


def ic_poisson(casos: float, confianza: float):
    """El intervalo exacto de un conteo de Poisson, por la chi cuadrado.

    No es la aproximación normal. Con pocos casos la normal da límites
    inferiores negativos, que para un conteo no quieren decir nada; este es
    exacto y asimétrico, que es lo que corresponde.
    """
    alfa = 1 - confianza
    return {
        "inferior": 0.0 if casos == 0 else chi2(alfa / 2, 2 * casos) / 2,
        "superior": chi2(1 - alfa / 2, 2 * (casos + 1)) / 2,
    }


def ic_fay_feuer(tasa: float, varianza: float, mayor_peso: float, confianza: float):
    """El intervalo de una tasa estandarizada, por el método de Fay-Feuer (1997).

    Una tasa ajustada es una **suma ponderada** de conteos de Poisson, y eso no
    es un Poisson: no se le puede aplicar el intervalo de un conteo. Fay y
    Feuer la aproximan por una gamma con los mismos dos primeros momentos, y
    esa gamma se evalúa con la chi cuadrado.

    Es el que usan los registros de cáncer y el programa SEER, y el que hay que
    usar cuando algún grupo de edad tiene pocos casos: ahí el intervalo sale
    asimétrico, que es lo correcto. La aproximación normal, en cambio, da
    límites inferiores negativos.

    El `mayor_peso` —el mayor de los wᵢ/nᵢ— entra solo en el límite superior:
    es el ajuste que Fay y Feuer agregan para que el intervalo cubra bien
    cuando la tasa es cero o casi.
    """
    alfa = 1 - confianza
    if tasa > 0 and varianza > 0:
        inferior = (varianza / (2 * tasa)) * chi2(alfa / 2, 2 * tasa * tasa / varianza)
        varianza_sup = varianza + mayor_peso * mayor_peso
        tasa_sup = tasa + mayor_peso
        superior = (varianza_sup / (2 * tasa_sup)) * chi2(
            1 - alfa / 2, 2 * tasa_sup * tasa_sup / varianza_sup)
        return {"inferior": inferior, "superior": superior}
    if tasa == 0:
        # Sin ningún caso el límite inferior es cero y el superior sale del peso.
        superior = mayor_peso * chi2(1 - alfa / 2, 2) / 2 if mayor_peso > 0 else 0.0
        return {"inferior": 0.0, "superior": superior}
    return {"inferior": float("nan"), "superior": float("nan")}


def normal_inv(p: float) -> float:
    """El cuantil de la normal estándar. En R es `qnorm`."""
    return float(stats.norm.ppf(p))


def razon_de_tasas(a: dict, b: dict, confianza: float):
    """La razón entre dos tasas estandarizadas, con su intervalo.

    El intervalo se arma en escala logarítmica, como el de toda razón, y el
    error estándar de cada tasa se recupera del ancho de su propio intervalo:
    el de Fay-Feuer no tiene una fórmula cerrada para la varianza en escala
    log, y deducirla del intervalo es la manera habitual de combinarlos.
    """
    if not (a["valor"] > 0 and b["valor"] > 0):
        return None
    if not all(v > 0 for v in (a["inferior"], a["superior"], b["inferior"], b["superior"])):
        return None
    z = normal_inv(1 - (1 - confianza) / 2)
    ee_a = (math.log(a["superior"]) - math.log(a["inferior"])) / (2 * z)
    ee_b = (math.log(b["superior"]) - math.log(b["inferior"])) / (2 * z)
    ee = math.sqrt(ee_a * ee_a + ee_b * ee_b)
    log = math.log(a["valor"] / b["valor"])
    return {"valor": a["valor"] / b["valor"],
            "inferior": math.exp(log - z * ee),
            "superior": math.exp(log + z * ee),
            "error_estandar_log": ee}


def se_pisan(a: dict, b: dict) -> bool:
    """Si dos intervalos se tocan. Que no se pisen no es una prueba de
    hipótesis —es más exigente que una—, pero que sí se pisen alcanza para
    decir que la diferencia no está establecida."""
    return a["inferior"] <= b["superior"] and b["inferior"] <= a["superior"]


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
        # Un cero con signo no significa nada y además sale distinto en cada
        # motor, porque depende del último bit de una suma.
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
    """El número como se escribe en un informe en castellano: miles con punto y
    decimales con coma."""
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


def tasa_texto(valor: float, decimales: int = 1) -> str:
    """Una tasa, con un decimal. Escribir tres decimales en una tasa por cien
    mil finge una precisión que los conteos no tienen."""
    if valor is None:
        return ""
    return numero_texto(valor, decimales)

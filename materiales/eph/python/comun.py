"""Lo que comparten los cuatro pasos: leer los microdatos, estimar y escribir.

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
# Lo que en un archivo del INDEC quiere decir «no hay dato».
#
# El `NA` escrito con letras no es un invento: aparece tal cual en los
# archivos de algunos trimestres —2021T1, 2024T3 y 2024T4 entre ellos— y es lo
# que hace que un lector distraído reciba ciento cincuenta columnas numéricas
# convertidas en texto. Leer todo como texto y decidir acá qué es un número
# evita el problema de raíz.
FALTANTES = {"", "NA", "N/A", "NULL", ".", "-"}


def leer_csv(ruta: str | Path) -> list[dict]:
    """Un CSV común y corriente: coma, UTF-8. Para los archivos del proyecto."""
    texto = Path(ruta).read_text(encoding="utf-8-sig")
    lineas = [l for l in texto.replace("\r\n", "\n").split("\n") if l.strip() != ""]
    columnas = [limpiar_texto(c) for c in lineas[0].split(",")]
    filas = []
    for linea in lineas[1:]:
        partes = (linea.split(",") + [""] * len(columnas))[:len(columnas)]
        filas.append({c: limpiar_texto(p) for c, p in zip(columnas, partes)})
    return filas


def leer_microdatos(ruta: str | Path, separador: str, codificacion: str):
    """El `usu_individual_Tnnaa.txt` del INDEC, tal como viene.

    Tres detalles que no son detalles:

    - **El separador es el punto y coma**, no la coma. Abrirlo con la coma da
      una sola columna, y algunos programas no avisan.
    - **La codificación es latin-1**, no UTF-8. Con UTF-8 el archivo de hogar
      directamente no abre, y el de individual abre con la ñ rota.
    - **Los textos vienen entre comillas** y los números no. Las comillas se
      sacan acá, una sola vez, y no en cada paso.

    Se devuelve todo como texto. Convertir a número es una decisión que toma
    el paso 1 columna por columna, con los códigos de la EPH a la vista.
    """
    ruta = Path(ruta)
    if not ruta.exists():
        raise SystemExit(
            f"No encuentro {ruta}.\n"
            f"Si querés correrlo sobre datos del INDEC, bajá el trimestre de\n"
            f"https://www.indec.gob.ar/indec/web/Institucional-Indec-BasesDeDatos,\n"
            f"descomprimilo en datos/ y apuntá «archivo» en datos/parametros.csv\n"
            f"al usu_individual_Tnnaa.txt que salga.")
    texto = ruta.read_bytes().decode(codificacion)
    lineas = [l for l in texto.replace("\r\n", "\n").split("\n") if l.strip() != ""]
    if not lineas:
        raise SystemExit(f"{ruta} está vacío.")

    def partir(linea: str) -> list[str]:
        return [limpiar_texto(p).strip('"') for p in linea.split(separador)]

    columnas = [c.upper() for c in partir(lineas[0])]
    if len(columnas) < 2:
        raise SystemExit(
            f"La primera línea de {ruta} tiene una sola columna con el separador "
            f"«{separador}». Si el archivo es del INDEC, el separador es «;».")
    filas = []
    for linea in lineas[1:]:
        partes = (partir(linea) + [""] * len(columnas))[:len(columnas)]
        filas.append(dict(zip(columnas, partes)))
    return columnas, filas


def numero(x: str):
    x = limpiar_texto(x)
    if x.upper() in FALTANTES:
        return None
    try:
        return float(x)
    except ValueError:
        return None


def entero(x: str, por_omision=None):
    v = numero(x)
    return por_omision if v is None else int(v)


def leer_parametros(ruta: str | Path) -> dict:
    """Qué archivo leer y con qué columnas trabajar, declarado en un archivo.

    Correr el proyecto sobre otro trimestre, sobre otro aglomerado o con otro
    ponderador no tiene que obligar a editar un script.
    """
    filas = {f["clave"]: f["valor"] for f in leer_csv(ruta)}

    def texto(clave, por_omision=""):
        v = limpiar_texto(filas.get(clave, ""))
        return v if v else por_omision

    confianza = numero(filas.get("confianza", "")) or 0.95
    if not (0 < confianza < 1):
        raise SystemExit(f"La confianza tiene que estar entre 0 y 1, y es {confianza}.")

    parametros = {
        "archivo": texto("archivo", "datos/usu_individual_T425_simulado.txt"),
        "separador": texto("separador", ";"),
        "codificacion": texto("codificacion", "latin1"),
        "ponderador": texto("ponderador", "PONDERA").upper(),
        "ponderador_ingreso": texto("ponderador_ingreso", "PONDIIO").upper(),
        "ingreso": texto("ingreso", "P21").upper(),
        "confianza": confianza,
        "region": texto("region"),
        "aglomerado": texto("aglomerado"),
    }
    if len(parametros["separador"]) != 1:
        raise SystemExit("«separador» tiene que ser un solo carácter.")
    return parametros


def ordenar(x) -> list[str]:
    """El orden de las etiquetas, por código de carácter y no por el idioma de
    la máquina: así R y Python escriben las filas en el mismo orden en
    cualquier computadora."""
    return sorted(set(x))


# ------------------------------------------------------------ estadísticas
def cuantil_ponderado(valores, pesos, p: float):
    """El cuantil de una distribución con pesos.

    `valores` y `pesos` vienen en paralelo y **ya ordenados por valor**. Se
    devuelve el primer valor cuyo peso acumulado llega a p·W.

    Es la definición más simple de las varias que hay, y la única que no
    depende de una convención de interpolación: con pesos de encuesta, dos
    programas que interpolan distinto dan medianas distintas sobre los mismos
    datos. Acá se elige una, se la escribe, y los dos motores dan lo mismo.
    """
    total = math.fsum(pesos)
    if total <= 0 or not valores:
        return None
    objetivo = p * total
    acumulado = 0.0
    for valor, peso in zip(valores, pesos):
        acumulado += peso
        if acumulado >= objetivo:
            return valor
    return valores[-1]


def preparar_conglomerados(estratos, unidades):
    """Las posiciones de cada hogar dentro de cada aglomerado, en orden fijo.

    Se calcula una sola vez y se reusa en las setenta y pico de estimaciones
    que hace el proyecto: los estratos y las unidades son siempre los mismos, y
    reagruparlos en cada una es lo que hace que la versión de R tarde minutos
    en vez de segundos.

    El orden —estratos ordenados, y hogares ordenados dentro de cada uno— no es
    por prolijidad: fija en qué orden se suman los aportes, y con eso el último
    bit de la varianza. Los dos motores tienen que recorrerlos igual.
    """
    por: dict = {}
    for i, (h, u) in enumerate(zip(estratos, unidades)):
        por.setdefault(h, {}).setdefault(u, []).append(i)
    return [[por[h][u] for u in ordenar(list(por[h]))] for h in ordenar(list(por))]


def estimar_razon(w, y, x, conglomerados, confianza):
    """Una razón Y/X y su error estándar, respetando el diseño de la EPH.

    Casi todo lo que se calcula con la EPH es una razón entre dos totales
    ponderados: la tasa de empleo es ocupados sobre población, la de
    desocupación es desocupados sobre PEA, y un ingreso medio es la suma de
    ingresos sobre la suma de pesos. Las tres salen de la misma cuenta.

    El error estándar **no** es el de una muestra aleatoria simple. La EPH
    selecciona conglomerados dentro de cada aglomerado, y la gente que vive
    cerca se parece: dos vecinos aportan menos información que dos personas
    sorteadas de todo el país. La varianza se calcula por el método de los
    conglomerados últimos, linealizando la razón:

        z_i = w_i · (y_i − p·x_i)

    y después se trata a los z como si fueran un total, sumándolos por unidad
    primaria dentro de cada estrato.

    **Acá el estrato es el aglomerado y la unidad primaria es el hogar.** No
    es lo ideal: el conglomerado de verdad es el radio censal, y el archivo
    público no lo trae. Con el hogar como unidad se captura la parte del
    efecto de diseño que viene de que los miembros de un hogar se parecen, y
    se pierde la que viene de que los vecinos se parecen. **El error estándar
    que sale de acá es, entonces, una cota inferior**: el verdadero es más
    grande. Es lo mejor que se puede hacer con el archivo publicado, y decirlo
    es parte de hacerlo bien.
    """
    n = len(w)
    total_y = math.fsum(w[i] * y[i] for i in range(n))
    total_x = math.fsum(w[i] * x[i] for i in range(n))
    if total_x <= 0:
        return None
    p = total_y / total_x

    varianza = 0.0
    grados = 0
    unidades_primarias = 0
    estratos_solitarios = 0
    for estrato in conglomerados:
        zs = [math.fsum(w[i] * (y[i] - p * x[i]) for i in hogar) for hogar in estrato]
        a = len(zs)
        unidades_primarias += a
        if a < 2:
            # Un estrato con una sola unidad primaria no aporta grados de
            # libertad y su varianza no se puede estimar. Se lo deja pasar y
            # se cuenta, que es mejor que devolver un cero silencioso.
            estratos_solitarios += 1
            continue
        media_z = math.fsum(zs) / a
        varianza += a / (a - 1) * math.fsum((z - media_z) ** 2 for z in zs)
        grados += a - 1

    varianza = varianza / (total_x ** 2)
    error = math.sqrt(varianza) if varianza > 0 else 0.0

    # Los grados de libertad de una encuesta compleja son (unidades primarias
    # − estratos), no (n − 1). Con 1.871 hogares y 32 aglomerados son 1.839.
    gl = max(1, grados)
    critico = float(stats.t.ppf(1 - (1 - confianza) / 2, gl))
    return {
        "estimacion": p, "error_estandar": error, "gl": gl,
        "inferior": p - critico * error, "superior": p + critico * error,
        "total_numerador": total_y, "total_denominador": total_x,
        "unidades_primarias": unidades_primarias,
        "estratos_solitarios": estratos_solitarios,
    }


def deff_de_proporcion(p: float, error: float, n: int):
    """Cuánto cuesta el diseño, para una proporción.

    Es la varianza que se obtuvo dividida por la que tendría una muestra
    aleatoria simple del mismo tamaño. Un deff de 1,8 quiere decir que los
    1.000 casos de la muestra valen como 555.
    """
    if n < 2 or p <= 0 or p >= 1:
        return None
    simple = p * (1 - p) / n
    return (error ** 2) / simple if simple > 0 else None


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
    entero_, _, decimal = f"{abs(valor):.{decimales}f}".partition(".")
    grupos = []
    while len(entero_) > 3:
        grupos.insert(0, entero_[-3:])
        entero_ = entero_[:-3]
    texto = ".".join([entero_] + grupos)
    if decimales > 0:
        texto += "," + decimal
    return ("-" if valor < 0 else "") + texto


def porcentaje(valor: float, decimales: int = 2) -> str:
    """Una proporción escrita como porcentaje. La EPH informa sus tasas con un
    decimal; acá se usan dos, porque las diferencias que el proyecto quiere
    mostrar viven en el segundo."""
    if valor is None:
        return ""
    return numero_texto(valor * 100, decimales) + " %"


def pesos_texto(valor: float) -> str:
    """Un monto en pesos, sin decimales. Escribir centavos en un ingreso medio
    de seiscientos mil finge una precisión que la muestra no tiene."""
    if valor is None:
        return ""
    return "$ " + numero_texto(valor, 0)

"""Genera public/descargas/eph.zip.

    python descargables/generar_eph.py

Los archivos del proyecto viven en `descargables/eph/`; este script arma el
archivo de ejemplo y empaqueta, con las mismas reglas que los otros
descargables: fecha fija, orden fijo, sin comprimir y declarando siempre el
mismo sistema.

El archivo de ejemplo es **simulado**, y tiene exactamente el formato del
`usu_individual_Tnnaa.txt` del INDEC: separado por punto y coma, en latin-1,
con los códigos de la EPH y con los mismos nombres de columna. Lo que copia de
la EPH real es el **diseño**: los 32 aglomerados con su región, su tamaño de
muestra relativo y su peso relativo en la población. Lo que no copia es ningún
dato de ninguna persona: los registros se simulan.

La muestra va a la octava parte de la real y la población, con ella. Es a
propósito y por dos razones. Una es que el archivo entre en un zip. La otra es
más importante: así ningún número que salga de este proyecto se puede confundir
con una cifra publicada por el INDEC. El archivo sirve para aprender a leer la
EPH; los datos de la EPH se bajan del INDEC.

Lo verifica `npm run script-eph`.
"""

import math
import random
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PROYECTO = Path(__file__).resolve().parent / "eph"
DESTINO = RAIZ / "public" / "descargas" / "eph.zip"
FECHA = (2026, 9, 24, 0, 0, 0)

ARCHIVOS = [
    "README.md",
    ".gitignore",
    "datos/usu_individual_T425_simulado.txt",
    "datos/aglomerados.csv",
    "datos/variables.csv",
    "datos/parametros.csv",
    "R/correr.R",
    "R/comun.R",
    "R/01-leer.R",
    "R/02-tasas.R",
    "R/03-ingresos.R",
    "R/04-redaccion.R",
    "python/correr.py",
    "python/comun.py",
    "python/01_leer.py",
    "python/02_tasas.py",
    "python/03_ingresos.py",
    "python/04_redaccion.py",
]

# El archivo de microdatos entra al zip byte por byte: sus fines de línea de
# Windows son los del INDEC, y son parte de lo que el proyecto enseña a leer.
TAL_CUAL = {"datos/usu_individual_T425_simulado.txt"}

GITIGNORE = """# Lo que se puede volver a generar no se versiona.
salidas/

# Los microdatos del INDEC tampoco: se bajan, no se versionan.
datos/usu_individual_*.txt
!datos/usu_individual_T425_simulado.txt
datos/*.zip

.Rhistory
.RData
.Rproj.user/
__pycache__/
.venv/
"""

# ---------------------------------------------------------------------------
# El diseño de la EPH continua: los 32 aglomerados relevados, con su región y
# su peso. Los tamaños de muestra y las poblaciones son los del cuarto
# trimestre de 2025 divididos por ocho.
#
#   codigo, nombre, region, mas_500, n, poblacion
AGLOMERADOS = [
    (2, "Gran La Plata", 43, "S", 1027, 946892),
    (3, "Bahía Blanca - Cerri", 43, "N", 881, 323483),
    (4, "Gran Rosario", 43, "S", 1677, 1364004),
    (5, "Gran Santa Fe", 43, "S", 1381, 556150),
    (6, "Gran Paraná", 43, "N", 1288, 288522),
    (7, "Posadas", 41, "N", 1125, 395265),
    (8, "Gran Resistencia", 41, "N", 1229, 428269),
    (9, "Comodoro Rivadavia - Rada Tilly", 44, "N", 704, 260446),
    (10, "Gran Mendoza", 42, "S", 1793, 1067048),
    (12, "Corrientes", 41, "N", 963, 395425),
    (13, "Gran Córdoba", 43, "S", 1910, 1613451),
    (14, "Concordia", 43, "N", 1405, 166725),
    (15, "Formosa", 41, "N", 834, 266546),
    (17, "Neuquén - Plottier", 44, "N", 1022, 327896),
    (18, "Santiago del Estero - La Banda", 40, "N", 1411, 420976),
    (19, "Jujuy - Palpalá", 40, "N", 1459, 363998),
    (20, "Río Gallegos", 44, "N", 730, 134293),
    (22, "Gran Catamarca", 40, "N", 1417, 235700),
    (23, "Gran Salta", 40, "S", 1930, 675692),
    (25, "La Rioja", 40, "N", 1215, 241217),
    (26, "Gran San Luis", 42, "N", 1192, 254332),
    (27, "Gran San Juan", 42, "S", 1360, 560835),
    (29, "Gran Tucumán - Tafí Viejo", 40, "S", 1996, 931273),
    (30, "Santa Rosa - Toay", 43, "N", 811, 134057),
    (31, "Ushuaia - Río Grande", 44, "N", 989, 182897),
    (32, "Ciudad Autónoma de Buenos Aires", 1, "S", 1370, 3005773),
    (33, "Partidos del GBA", 1, "S", 5722, 13194278),
    (34, "Mar del Plata", 43, "S", 853, 671215),
    (36, "Río Cuarto", 43, "N", 1102, 184661),
    (38, "San Nicolás - Villa Constitución", 43, "N", 1282, 200700),
    (91, "Rawson - Trelew", 44, "N", 791, 153720),
    (93, "Viedma - Carmen de Patagones", 44, "N", 834, 87006),
]

REGIONES = {
    1: "Gran Buenos Aires",
    40: "Noroeste",
    41: "Nordeste",
    42: "Cuyo",
    43: "Pampeana",
    44: "Patagonia",
}

DIVISOR = 8
ANO = 2025
TRIMESTRE = 4
SEMILLA = 55

COLUMNAS = [
    "CODUSU", "ANO4", "TRIMESTRE", "NRO_HOGAR", "COMPONENTE", "H15", "REGION",
    "MAS_500", "AGLOMERADO", "PONDERA", "CH03", "CH04", "CH06", "NIVEL_ED",
    "ESTADO", "CAT_OCUP", "PP07H", "INTENSI", "P21", "ITF", "IPCF", "PONDIIO",
]

LETRAS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

# Cuántos miembros tiene un hogar.
TAMANOS = [(1, 0.20), (2, 0.25), (3, 0.20), (4, 0.17), (5, 0.10), (6, 0.08)]

# La probabilidad de ser económicamente activo, por tramo de edad. El tramo es
# lo que más manda: el resto son ajustes.
ACTIVIDAD_POR_EDAD = [
    (13, 0.0049), (17, 0.0897), (24, 0.502), (34, 0.760), (49, 0.780),
    (59, 0.673), (64, 0.419), (200, 0.115),
]

# Y la de estar desocupado, entre los activos.
DESOCUPACION_POR_EDAD = [
    (17, 0.239), (24, 0.152), (34, 0.076), (49, 0.056), (59, 0.045), (200, 0.036),
]


def de_tabla(tabla, edad):
    for tope, valor in tabla:
        if edad <= tope:
            return valor
    return tabla[-1][1]


def elegir(azar, opciones):
    """Una categoría con su probabilidad, con el azar recorrido en orden fijo."""
    u = azar.random()
    acumulado = 0.0
    for valor, p in opciones:
        acumulado += p
        if u < acumulado:
            return valor
    return opciones[-1][0]


def codusu(azar) -> str:
    """El identificador de la vivienda: 20 caracteres, como el del INDEC."""
    return "".join(azar.choice(LETRAS) for _ in range(16)) + f"{azar.randrange(10000):04d}"


def nivel_educativo(azar, edad):
    if edad < 5:
        return 7
    if edad < 12:
        return elegir(azar, [(1, 0.90), (2, 0.08), (7, 0.02)])
    if edad < 18:
        return elegir(azar, [(2, 0.30), (3, 0.62), (1, 0.06), (7, 0.02)])
    if edad < 25:
        return elegir(azar, [(3, 0.22), (4, 0.36), (5, 0.32), (6, 0.05),
                             (2, 0.04), (1, 0.01)])
    return elegir(azar, [(1, 0.12), (2, 0.13), (3, 0.19), (4, 0.22), (5, 0.11),
                         (6, 0.20), (7, 0.03)])


# Cuánto multiplica al ingreso cada nivel educativo alcanzado.
PRIMA_EDUCATIVA = {1: 0.72, 2: 0.80, 3: 0.86, 4: 1.00, 5: 1.08, 6: 1.62, 7: 0.66}
PRIMA_CATEGORIA = {1: 1.85, 2: 0.86, 3: 1.00, 4: 0.42}


def generar_personas():
    """El archivo entero, hogar por hogar y aglomerado por aglomerado."""
    azar = random.Random(SEMILLA)
    filas = []
    for codigo, _nombre, region, mas_500, n_real, poblacion_real in AGLOMERADOS:
        objetivo = max(60, round(n_real / DIVISOR))
        poblacion = poblacion_real / DIVISOR

        # Cada aglomerado tiene su propio nivel de ingresos y su propia tasa de
        # no respuesta, y las dos van juntas: donde se gana más, se contesta
        # menos. Es la razón de ser de PONDIIO, y acá está puesta a mano para
        # que el proyecto la pueda mostrar.
        nivel = 0.72 + 0.62 * ((codigo * 37) % 23) / 22.0
        no_respuesta = 0.106 + 0.41 * (nivel - 0.72) / 0.62
        empuje = 0.94 + 0.12 * ((codigo * 19) % 17) / 16.0

        hogares = []
        personas_del_aglomerado = []
        while len(personas_del_aglomerado) < objetivo:
            vivienda = codusu(azar)
            nro_hogar = 1
            tamano = elegir(azar, TAMANOS)
            edad_jefe = azar.randint(22, 82)
            sexo_jefe = elegir(azar, [(1, 0.55), (2, 0.45)])
            miembros = []
            for componente in range(1, tamano + 1):
                if componente == 1:
                    ch03, edad, sexo = 1, edad_jefe, sexo_jefe
                elif componente == 2 and edad_jefe >= 25 and azar.random() < 0.68:
                    ch03 = 2
                    edad = max(18, edad_jefe + azar.randint(-6, 6))
                    sexo = 2 if sexo_jefe == 1 else 1
                else:
                    ch03 = elegir(azar, [(3, 0.86), (5, 0.08), (9, 0.06)])
                    # La edad del hijo se saca de los años adultos del jefe y no
                    # de una resta fija. Con una resta fija, todo jefe joven
                    # produce edades negativas, y al recortarlas en cero el
                    # archivo termina lleno de bebés.
                    edad = int(round((edad_jefe - 20) * azar.uniform(0.52, 1.00)))
                    edad = max(-1, min(edad_jefe - 16, edad))
                    # A los más chicos el INDEC los codifica como «menos de un
                    # año», que es -1 y no 0. El modelo no distingue entre un
                    # bebé y alguien de un año, así que el corte va acá. No
                    # consume azar, para no mover el resto del archivo.
                    if edad <= 1:
                        edad = -1
                    sexo = elegir(azar, [(1, 0.51), (2, 0.49)])
                miembros.append({
                    "COMPONENTE": componente, "CH03": ch03, "CH04": sexo,
                    "CH06": edad,
                })

            peso = azar.lognormvariate(0.0, 0.42)
            hogares.append({"CODUSU": vivienda, "NRO_HOGAR": nro_hogar,
                            "peso": peso, "miembros": miembros})
            personas_del_aglomerado.extend(miembros)

        # Una vivienda puede tener más de un hogar adentro, y en la EPH pasa:
        # por eso el hogar es CODUSU **más** NRO_HOGAR, y no CODUSU a secas.
        # Acá se reetiquetan hogares ya armados, sin tocar a nadie: no consume
        # azar y no mueve ningún número del archivo.
        for j in range(1, len(hogares)):
            if j % 29 == 0:
                hogares[j]["CODUSU"] = hogares[j - 1]["CODUSU"]
                hogares[j]["NRO_HOGAR"] = 2

        # Los pesos se escalan para que la suma dé la población del aglomerado.
        # En la EPH todos los miembros de un hogar comparten el ponderador, y
        # acá también: es lo que hace que la muestra esté conglomerada y que el
        # error estándar ingenuo se quede corto.
        suma = math.fsum(h["peso"] * len(h["miembros"]) for h in hogares)
        escala = poblacion / suma

        del_aglomerado = []
        for hogar in hogares:
            pondera = max(1, round(hogar["peso"] * escala))
            ingresos_del_hogar = []
            for m in hogar["miembros"]:
                edad = m["CH06"]
                sexo = m["CH04"]
                nivel_ed = nivel_educativo(azar, max(0, edad))

                if edad < 10:
                    estado = 4
                elif azar.random() < 0.0014:
                    # La entrevista individual que no se pudo hacer. Son pocas y
                    # existen, y no entran en ningún denominador: ni activas, ni
                    # inactivas. Por eso las tres condiciones de actividad no
                    # suman exactamente el total de la población.
                    estado = 0
                else:
                    p_act = de_tabla(ACTIVIDAD_POR_EDAD, edad) * empuje
                    p_act *= 1.14 if sexo == 1 else 0.84
                    if azar.random() < min(0.97, p_act):
                        p_des = de_tabla(DESOCUPACION_POR_EDAD, edad)
                        p_des *= 1.10 if sexo == 2 else 1.0
                        estado = 2 if azar.random() < p_des else 1
                    else:
                        estado = 3

                cat_ocup, pp07h, intensi, p21 = 0, 0, 0, 0
                if estado == 1:
                    cat_ocup = elegir(azar, [(3, 0.710), (2, 0.249), (1, 0.036),
                                             (4, 0.005)])
                    intensi = elegir(azar, [(2, 0.600), (3, 0.270), (1, 0.1225),
                                            (4, 0.0075)])

                    prima = PRIMA_EDUCATIVA[nivel_ed] * PRIMA_CATEGORIA[cat_ocup]
                    prima *= nivel * (0.82 if sexo == 2 else 1.0)
                    bruto = azar.lognormvariate(math.log(660000) + math.log(prima), 0.78)
                    p21 = int(round(bruto / 1000.0)) * 1000

                    if cat_ocup == 3:
                        # La informalidad no está repartida al azar: cae con el
                        # nivel educativo y con el ingreso.
                        p_informal = 0.598 - 0.055 * nivel_ed - 0.10 * math.log10(
                            max(1.0, p21 / 400000.0))
                        pp07h = 2 if azar.random() < max(0.05, p_informal) else 1
                    if cat_ocup == 4 or azar.random() < 0.014:
                        p21 = 0

                    # Y la no respuesta tampoco: el que gana más contesta menos,
                    # y hay aglomerados enteros donde se contesta menos.
                    if p21 > 0:
                        p_nr = no_respuesta * (0.70 + 0.55 * math.log10(
                            max(1.0, p21 / 300000.0)))
                        if azar.random() < min(0.60, p_nr):
                            p21 = -9

                    if p21 > 0:
                        ingresos_del_hogar.append(p21)

                del_aglomerado.append({
                    "CODUSU": hogar["CODUSU"], "ANO4": ANO, "TRIMESTRE": TRIMESTRE,
                    "NRO_HOGAR": hogar["NRO_HOGAR"], "COMPONENTE": m["COMPONENTE"],
                    "H15": 1, "REGION": region, "MAS_500": mas_500,
                    "AGLOMERADO": codigo, "PONDERA": pondera, "CH03": m["CH03"],
                    "CH04": sexo, "CH06": edad, "NIVEL_ED": nivel_ed,
                    "ESTADO": estado, "CAT_OCUP": cat_ocup, "PP07H": pp07h,
                    "INTENSI": intensi, "P21": p21,
                })

            itf = sum(ingresos_del_hogar)
            ipcf = int(round(itf / len(hogar["miembros"])))
            for fila in del_aglomerado[-len(hogar["miembros"]):]:
                fila["ITF"] = itf
                fila["IPCF"] = ipcf

        # PONDIIO: el ponderador del ingreso de la ocupación principal.
        #
        # Vale cero para el que no contestó, y el peso de los que no
        # contestaron se reparte entre los que sí, **dentro del aglomerado**.
        # Esa es toda la diferencia entre PONDIIO y PONDERA, y es la que hace
        # que las dos cuentas no den lo mismo.
        ocupados = [f for f in del_aglomerado if f["ESTADO"] == 1]
        peso_ocupados = sum(f["PONDERA"] for f in ocupados)
        peso_responden = sum(f["PONDERA"] for f in ocupados if f["P21"] != -9)
        factor = peso_ocupados / peso_responden if peso_responden > 0 else 0.0
        for f in del_aglomerado:
            if f["ESTADO"] == 1 and f["P21"] != -9:
                f["PONDIIO"] = max(1, round(f["PONDERA"] * factor))
            else:
                f["PONDIIO"] = 0

        filas.extend(del_aglomerado)
    return filas


def escribir_microdatos(filas, ruta: Path) -> None:
    """El archivo, en el formato del INDEC: punto y coma, latin-1 y CRLF.

    Los tres detalles importan. El separador porque no es la coma; la
    codificación porque no es UTF-8 y hay acentos en los archivos de hogar; el
    fin de línea porque los archivos vienen de Windows. Un lector que no
    declare los tres no abre el archivo real.
    """
    lineas = [";".join(COLUMNAS)]
    for f in filas:
        partes = []
        for c in COLUMNAS:
            v = f[c]
            partes.append(f'"{v}"' if isinstance(v, str) else str(v))
        lineas.append(";".join(partes))
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_bytes(("\r\n".join(lineas) + "\r\n").encode("latin-1"))


def escribir_aglomerados(ruta: Path) -> None:
    lineas = ["codigo,aglomerado,region,nombre_region,mas_500"]
    for codigo, nombre, region, mas_500, _n, _p in AGLOMERADOS:
        lineas.append(f"{codigo},{nombre},{region},{REGIONES[region]},{mas_500}")
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")


def resumir(filas) -> None:
    """Lo que el archivo terminó teniendo, para poder mirarlo al generarlo."""
    pob = sum(f["PONDERA"] for f in filas)
    def peso(cond):
        return sum(f["PONDERA"] for f in filas if cond(f))
    ocupados = peso(lambda f: f["ESTADO"] == 1)
    desocupados = peso(lambda f: f["ESTADO"] == 2)
    pea = ocupados + desocupados
    subocupados = peso(lambda f: f["ESTADO"] == 1 and f["INTENSI"] == 1)
    print(f"registros        {len(filas):>12,d}")
    print(f"población        {pob:>12,d}")
    print(f"actividad        {100 * pea / pob:>12.2f} %")
    print(f"empleo           {100 * ocupados / pob:>12.2f} %")
    print(f"desocupación     {100 * desocupados / pea:>12.2f} %")
    print(f"subocupación     {100 * subocupados / pea:>12.2f} %")

    oc = [f for f in filas if f["ESTADO"] == 1]
    sin_dato = sum(f["PONDERA"] for f in oc if f["P21"] == -9)
    print(f"P21 = -9         {100 * sin_dato / ocupados:>12.2f} % de los ocupados")
    conio = [f for f in oc if f["PONDIIO"] > 0 and f["P21"] > 0]
    correcto = (sum(f["P21"] * f["PONDIIO"] for f in conio)
                / sum(f["PONDIIO"] for f in conio))
    ingenuo = (sum(f["P21"] * f["PONDERA"] for f in conio)
               / sum(f["PONDERA"] for f in conio))
    con_menos_nueve = [f for f in oc if f["P21"] != 0]
    peor = (sum(f["P21"] * f["PONDERA"] for f in con_menos_nueve)
            / sum(f["PONDERA"] for f in con_menos_nueve))
    print(f"ingreso PONDIIO  {correcto:>12,.0f}")
    print(f"ingreso PONDERA  {ingenuo:>12,.0f}   ({100 * (ingenuo / correcto - 1):+.1f} %)")
    print(f"con el -9 adentro{peor:>12,.0f}   ({100 * (peor / correcto - 1):+.1f} %)")
    asal = [f for f in oc if f["CAT_OCUP"] == 3]
    informal = sum(f["PONDERA"] for f in asal if f["PP07H"] == 2)
    print(f"informalidad     {100 * informal / sum(f['PONDERA'] for f in asal):>12.2f} %")


def generar(destino: Path = DESTINO) -> Path:
    """El zip, igual en cualquier máquina.

    El código y la documentación se leen con `read_text`, que convierte los
    fines de línea de Windows en los de siempre: si no, el zip armado en una
    máquina y el armado en otra no serían el mismo archivo.

    **El de microdatos no.** Ese se copia byte por byte, porque sus CRLF son
    parte de lo que el proyecto enseña a leer: el archivo del INDEC viene de
    Windows y el lector tiene que contemplarlo. Por eso además está declarado
    en `.gitattributes` para que git tampoco se los toque.
    """
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)

    def entrada(nombre: str) -> zipfile.ZipInfo:
        info = zipfile.ZipInfo(f"eph/{nombre}", date_time=FECHA)
        info.compress_type = zipfile.ZIP_STORED
        info.external_attr = 0o644 << 16
        info.create_system = 3
        return info

    with zipfile.ZipFile(destino, "w", zipfile.ZIP_STORED) as z:
        for nombre in ARCHIVOS:
            origen = PROYECTO / nombre
            if not origen.exists():
                raise SystemExit(f"Falta {origen}")
            z.writestr(entrada(nombre),
                       origen.read_bytes() if nombre in TAL_CUAL
                       else origen.read_text(encoding="utf-8"))
        z.writestr(entrada("salidas/.gitkeep"), "")
    return destino


def main() -> None:
    (PROYECTO / ".gitignore").write_text(GITIGNORE, encoding="utf-8")
    filas = generar_personas()
    escribir_microdatos(filas, PROYECTO / "datos" / "usu_individual_T425_simulado.txt")
    escribir_aglomerados(PROYECTO / "datos" / "aglomerados.csv")
    resumir(filas)
    generar()
    print(f"\n{DESTINO}  ({DESTINO.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()

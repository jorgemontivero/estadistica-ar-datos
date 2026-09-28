"""Genera public/descargas/pruebas.zip.

    python descargables/generar_pruebas.py

Los archivos del proyecto viven en `descargables/pruebas/`; este script arma
los datos de ejemplo y empaqueta, con las mismas reglas que los otros
descargables: fecha fija, orden fijo, sin comprimir y declarando siempre el
mismo sistema.

Las ocho primeras columnas de la base son, carácter por carácter, las del
descargable de intervalos, y las seis primeras son además las de gráficos y
las de la tabla 1. Por eso cada columna nueva se sortea con un generador
propio: si compartieran uno, cada número que sacaran correría la serie y las
columnas viejas cambiarían.

Lo verifica `npm run script-pruebas`.
"""

import random
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PROYECTO = Path(__file__).resolve().parent / "pruebas"
DESTINO = RAIZ / "public" / "descargas" / "pruebas.zip"
FECHA = (2026, 9, 23, 0, 0, 0)
CASOS = 150

ARCHIVOS = [
    "README.md",
    ".gitignore",
    "datos/base.csv",
    "datos/variables.csv",
    "datos/parametros.csv",
    "R/correr.R",
    "R/comun.R",
    "R/01-supuestos.R",
    "R/02-pruebas.R",
    "R/03-redaccion.R",
    "python/correr.py",
    "python/comun.py",
    "python/01_supuestos.py",
    "python/02_pruebas.py",
    "python/03_redaccion.py",
]

GITIGNORE = """# Lo que se puede volver a generar no se versiona.
salidas/

.Rhistory
.RData
.Rproj.user/
__pycache__/
.venv/
"""

# Dos variables de agrupamiento: una de dos niveles y otra de tres. El árbol
# de decisión del sitio manda a pruebas distintas según cuántos haya, y así el
# ejemplo recorre las dos ramas.
VARIABLES = """nombre,etiqueta,tipo
grupo,Grupo,grupo
nivel,Nivel educativo,grupo
edad,Edad (años),numerica
ingreso,Ingreso mensual del hogar,numerica
puntaje,Puntaje de satisfacción,numerica
horas,Horas de estudio por semana,numerica
gasto,Gasto mensual en materiales,numerica
sexo,Sexo,categorica
beca,Tiene beca,categorica
"""

PARAMETROS = """clave,valor
alfa,0.05
"""


def datos_de_ejemplo() -> str:
    """Los 150 casos de siempre, con una columna más.

    El gasto está puesto para que pase lo que el proyecto quiere mostrar: unos
    pocos gastos enormes en el grupo control inflan la varianza, la prueba t
    no encuentra diferencia y Mann-Whitney sí. Cuál de las dos corresponde no
    es cuestión de gusto: lo decide el supuesto de normalidad, y el supuesto
    no se cumple.
    """
    azar = random.Random(20260923)
    otro = random.Random(20260924)
    tercero = random.Random(20260925)
    niveles = ["Primario", "Secundario", "Superior"]
    filas = []
    for i in range(1, CASOS + 1):
        grupo = "Control" if i % 2 else "Tratamiento"
        edad = min(85, max(18, round(azar.gauss(44 if grupo == "Control" else 41, 12))))
        ingreso = round(azar.lognormvariate(12.9 if grupo == "Control" else 13.05, 0.65), 2)
        puntaje = min(10, max(1, round(azar.gauss(6.4 if grupo == "Control" else 7.3, 1.9))))
        sexo = "Mujer" if azar.random() < (0.52 if grupo == "Control" else 0.49) else "Varón"
        nivel = niveles[min(2, int(azar.random() * 3 + (0.3 if grupo == "Tratamiento" else 0)))]
        horas = round(max(0, otro.gauss(11.6 if grupo == "Control" else 13.8, 4.6)), 1)
        beca = "Sí" if otro.random() < 0.035 else "No"
        gasto = round(tercero.lognormvariate(10.25 if grupo == "Control" else 10.7, 0.42), 2)
        filas.append([grupo, str(edad), f"{ingreso:.2f}", str(puntaje), sexo, nivel,
                      f"{horas:.1f}", beca, f"{gasto:.2f}"])

    # Los tres gastos enormes: un curso que alguien pagó de una vez. Van al
    # control, que es el grupo con el gasto más bajo, así que arrastran su
    # media hacia arriba y tapan la diferencia que los rangos sí ven.
    for i, factor in [(12, 14), (40, 17), (96, 12)]:
        filas[i][8] = f"{float(filas[i][8]) * factor:.2f}"

    for i, j in [(7, 1), (23, 2), (61, 3), (88, 2), (104, 4)]:
        filas[i][j] = ""

    lineas = ["grupo,edad,ingreso,puntaje,sexo,nivel,horas,beca,gasto"]
    lineas += [",".join(f) for f in filas]
    return "\n".join(lineas) + "\n"


def generar(destino: Path = DESTINO) -> Path:
    (PROYECTO / ".gitignore").write_text(GITIGNORE, encoding="utf-8")
    (PROYECTO / "datos" / "variables.csv").write_text(VARIABLES, encoding="utf-8")
    (PROYECTO / "datos" / "parametros.csv").write_text(PARAMETROS, encoding="utf-8")
    (PROYECTO / "datos" / "base.csv").write_text(datos_de_ejemplo(), encoding="utf-8")

    def entrada(nombre: str) -> zipfile.ZipInfo:
        info = zipfile.ZipInfo(f"pruebas/{nombre}", date_time=FECHA)
        info.compress_type = zipfile.ZIP_STORED
        info.external_attr = 0o644 << 16
        info.create_system = 3
        return info

    destino.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_STORED) as zip_:
        for nombre in ARCHIVOS:
            ruta = PROYECTO / nombre
            if not ruta.exists():
                raise SystemExit(f"falta {ruta}")
            zip_.writestr(entrada(nombre), ruta.read_text(encoding="utf-8"))
        zip_.writestr(entrada("salidas/.gitkeep"), "")
    return destino


if __name__ == "__main__":
    ruta = generar()
    print(f"public/descargas/{ruta.name} ({ruta.stat().st_size / 1024:.0f} KB)")

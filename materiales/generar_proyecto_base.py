"""Genera public/descargas/proyecto-base.zip.

    python descargables/generar_proyecto_base.py

El esqueleto de un análisis reproducible, en R y en Python. Los archivos del
proyecto viven en `descargables/proyecto-base/` —se leen y se corrigen como
cualquier código del repositorio—; este script arma los datos de ejemplo y los
empaqueta.

Dos decisiones:

  · Los datos de ejemplo se generan acá, con semilla fija, y quedan escritos en
    el proyecto. Así el archivo es reproducible y el verificador puede saber de
    antemano cuántas filas tienen que sobrevivir a la limpieza.

  · El zip se arma con fecha fija, orden fijo, sin comprimir y declarando
    siempre el mismo sistema de origen. Sin eso, dos corridas dan archivos
    distintos byte a byte: la fecha cambia, el encabezado guarda si lo hizo
    Windows o Linux, y la compresión puede variar entre versiones de zlib. Son
    diez KB de texto: comprimirlos no vale el riesgo de no poder compararlos.

Lo verifica `npm run script-proyecto`, que corre el proyecto entero con Python
y —si hay R— también con R, y exige que den lo mismo.
"""

import random
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PROYECTO = Path(__file__).resolve().parent / "proyecto-base"
DESTINO = RAIZ / "public" / "descargas" / "proyecto-base.zip"
FECHA = (2026, 9, 22, 0, 0, 0)  # la fecha que lleva cada archivo adentro del zip
CASOS = 120

# Los archivos del proyecto, en el orden en que entran al zip.
ARCHIVOS = [
    "README.md",
    ".gitignore",
    "datos/crudos/encuesta.csv",
    "R/correr.R",
    "R/comun.R",
    "R/01-importar.R",
    "R/02-analizar.R",
    "python/correr.py",
    "python/comun.py",
    "python/01_importar.py",
    "python/02_analizar.py",
]

GITIGNORE = """# Lo que se puede volver a generar no se versiona.
datos/limpios/
salidas/

# Lo que nunca se versiona.
.Rhistory
.RData
.Rproj.user/
__pycache__/
.venv/
"""


def datos_de_ejemplo() -> str:
    """Una encuesta ficticia con los problemas que traen los datos de verdad.

    Son cinco: espacios de más, un grupo escrito en mayúsculas, una edad
    imposible, un ingreso vacío y una fila cargada dos veces."""
    azar = random.Random(20260922)
    filas = []
    for i in range(1, CASOS + 1):
        grupo = "Control" if i % 2 else "Tratamiento"
        edad = min(85, max(18, round(azar.gauss(42, 14))))
        base = 380000 if grupo == "Control" else 460000
        ingreso = round(max(0, azar.gauss(base, 150000)), 2)
        puntaje = min(10, max(1, round(azar.gauss(6.5 if grupo == "Control" else 7.4, 1.8))))
        filas.append([f"c{i:03d}", grupo, str(edad), f"{ingreso:.2f}", str(puntaje)])

    filas[6][1] = "  CONTROL "       # el mismo grupo, escrito de otra manera
    filas[17][0] = f" {filas[17][0]} "  # espacios alrededor del id
    filas[31][2] = "150"             # una edad imposible: queda como faltante
    filas[44][3] = ""                # un ingreso sin cargar
    filas[58][4] = "s/d"             # un puntaje que no es un número
    filas.insert(60, list(filas[59]))  # la fila anterior, cargada dos veces

    lineas = ["id,grupo,edad,ingreso,puntaje"] + [",".join(f) for f in filas]
    return "\n".join(lineas) + "\n"


def generar(destino: Path = DESTINO) -> Path:
    (PROYECTO / ".gitignore").write_text(GITIGNORE, encoding="utf-8")
    (PROYECTO / "datos" / "crudos" / "encuesta.csv").write_text(datos_de_ejemplo(), encoding="utf-8")

    destino.parent.mkdir(parents=True, exist_ok=True)
    def entrada(nombre: str) -> zipfile.ZipInfo:
        info = zipfile.ZipInfo(f"proyecto-base/{nombre}", date_time=FECHA)
        info.compress_type = zipfile.ZIP_STORED
        info.external_attr = 0o644 << 16
        info.create_system = 3  # siempre Unix, lo haga Windows o Linux
        return info

    with zipfile.ZipFile(destino, "w", zipfile.ZIP_STORED) as zip_:
        for nombre in ARCHIVOS:
            ruta = PROYECTO / nombre
            if not ruta.exists():
                raise SystemExit(f"falta {ruta}")
            # read_text en modo texto: los saltos de línea de Windows quedan como
            # los de Linux, así que el zip sale igual en las dos máquinas.
            zip_.writestr(entrada(nombre), ruta.read_text(encoding="utf-8"))
        # Las dos carpetas que el proyecto necesita vacías.
        for carpeta in ["datos/limpios", "salidas"]:
            zip_.writestr(entrada(f"{carpeta}/.gitkeep"), "")
    return destino


if __name__ == "__main__":
    ruta = generar()
    print(f"public/descargas/{ruta.name} ({ruta.stat().st_size / 1024:.0f} KB)")

"""Genera public/descargas/descriptivos-y-tabla1.zip.

    python descargables/generar_descriptivos_tabla1.py

Los archivos del proyecto viven en `descargables/descriptivos/`; este script
arma los datos de ejemplo y empaqueta, con las mismas reglas que los otros
descargables: fecha fija, orden fijo, sin comprimir y declarando siempre el
mismo sistema.

El ejemplo tiene lo que hace falta para que la tabla muestre sus dos caras: una
variable simétrica que sale como media (DE) y una claramente asimétrica que
sale como mediana [Q1–Q3].

Lo verifica `npm run script-descriptivos`.
"""

import random
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PROYECTO = Path(__file__).resolve().parent / "descriptivos"
DESTINO = RAIZ / "public" / "descargas" / "descriptivos-y-tabla1.zip"
FECHA = (2026, 9, 23, 0, 0, 0)
CASOS = 150

ARCHIVOS = [
    "README.md",
    ".gitignore",
    "datos/base.csv",
    "datos/variables.csv",
    "R/correr.R",
    "R/comun.R",
    "R/pruebas.R",
    "R/01-descriptivos.R",
    "R/02-tabla1.R",
    "python/correr.py",
    "python/comun.py",
    "python/pruebas.py",
    "python/01_descriptivos.py",
    "python/02_tabla1.py",
]

GITIGNORE = """# Lo que se puede volver a generar no se versiona.
salidas/

.Rhistory
.RData
.Rproj.user/
__pycache__/
.venv/
"""

VARIABLES = """nombre,etiqueta,tipo
grupo,Grupo,grupo
edad,Edad (años),numerica
ingreso,Ingreso mensual del hogar,numerica
puntaje,Puntaje de satisfacción,numerica
sexo,Sexo,categorica
nivel,Nivel educativo,categorica
"""


def datos_de_ejemplo() -> str:
    """150 casos en dos grupos. La edad es simétrica; el ingreso, claramente
    asimétrico —una cola larga a la derecha, como todo ingreso—, así que la
    tabla lo informa con mediana."""
    azar = random.Random(20260923)
    niveles = ["Primario", "Secundario", "Superior"]
    filas = []
    for i in range(1, CASOS + 1):
        grupo = "Control" if i % 2 else "Tratamiento"
        edad = min(85, max(18, round(azar.gauss(44 if grupo == "Control" else 41, 12))))
        ingreso = round(azar.lognormvariate(12.9 if grupo == "Control" else 13.05, 0.65), 2)
        puntaje = min(10, max(1, round(azar.gauss(6.4 if grupo == "Control" else 7.3, 1.9))))
        sexo = "Mujer" if azar.random() < (0.52 if grupo == "Control" else 0.49) else "Varón"
        nivel = niveles[min(2, int(azar.random() * 3 + (0.3 if grupo == "Tratamiento" else 0)))]
        filas.append([grupo, str(edad), f"{ingreso:.2f}", str(puntaje), sexo, nivel])

    # Unos pocos faltantes, que es lo que siempre pasa.
    for i, j in [(7, 1), (23, 2), (61, 3), (88, 2), (104, 4)]:
        filas[i][j] = ""

    lineas = ["grupo,edad,ingreso,puntaje,sexo,nivel"] + [",".join(f) for f in filas]
    return "\n".join(lineas) + "\n"


def generar(destino: Path = DESTINO) -> Path:
    (PROYECTO / ".gitignore").write_text(GITIGNORE, encoding="utf-8")
    (PROYECTO / "datos" / "variables.csv").write_text(VARIABLES, encoding="utf-8")
    (PROYECTO / "datos" / "base.csv").write_text(datos_de_ejemplo(), encoding="utf-8")

    def entrada(nombre: str) -> zipfile.ZipInfo:
        info = zipfile.ZipInfo(f"descriptivos-y-tabla1/{nombre}", date_time=FECHA)
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

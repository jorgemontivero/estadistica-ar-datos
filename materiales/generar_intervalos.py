"""Genera public/descargas/intervalos.zip.

    python descargables/generar_intervalos.py

Los archivos del proyecto viven en `descargables/intervalos/`; este script
arma los datos de ejemplo y empaqueta, con las mismas reglas que los otros
descargables: fecha fija, orden fijo, sin comprimir y declarando siempre el
mismo sistema.

Las seis primeras columnas de la base son, carácter por carácter, las del
descargable de gráficos y las del de la tabla 1: la idea es que el informe
entero salga de la misma base. Por eso las dos columnas nuevas —las horas de
estudio y la beca— se sortean con un generador aparte: si compartieran el
mismo, cada número que sacaran correría la serie y las seis columnas viejas
cambiarían.

Lo verifica `npm run script-intervalos`.
"""

import random
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PROYECTO = Path(__file__).resolve().parent / "intervalos"
DESTINO = RAIZ / "public" / "descargas" / "intervalos.zip"
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
    "R/intervalos.R",
    "R/01-una-muestra.R",
    "R/02-diferencias.R",
    "R/03-redaccion.R",
    "python/correr.py",
    "python/comun.py",
    "python/intervalos.py",
    "python/01_una_muestra.py",
    "python/02_diferencias.py",
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

VARIABLES = """nombre,etiqueta,tipo
grupo,Grupo,grupo
edad,Edad (años),numerica
ingreso,Ingreso mensual del hogar,numerica
puntaje,Puntaje de satisfacción,numerica
horas,Horas de estudio por semana,numerica
sexo,Sexo,categorica
nivel,Nivel educativo,categorica
beca,Tiene beca,categorica
"""

# La confianza y, si se conoce, el tamaño de la población. Con la población en
# blanco no hay corrección por población finita, que es el caso habitual.
PARAMETROS = """clave,valor
confianza,0.95
poblacion,
"""


def datos_de_ejemplo() -> str:
    """Los 150 casos de siempre, con dos columnas más.

    Las horas de estudio están puestas para que pase lo que el proyecto quiere
    mostrar: los dos intervalos por separado se pisan, y sin embargo el
    intervalo de la diferencia no contiene al cero.

    La beca es rara a propósito —poco más de un caso cada treinta—, que es
    donde Wald deja de servir y se le nota.
    """
    azar = random.Random(20260923)
    otro = random.Random(20260924)
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
        filas.append([grupo, str(edad), f"{ingreso:.2f}", str(puntaje), sexo, nivel,
                      f"{horas:.1f}", beca])

    for i, j in [(7, 1), (23, 2), (61, 3), (88, 2), (104, 4)]:
        filas[i][j] = ""

    lineas = ["grupo,edad,ingreso,puntaje,sexo,nivel,horas,beca"] + [",".join(f) for f in filas]
    return "\n".join(lineas) + "\n"


def generar(destino: Path = DESTINO) -> Path:
    (PROYECTO / ".gitignore").write_text(GITIGNORE, encoding="utf-8")
    (PROYECTO / "datos" / "variables.csv").write_text(VARIABLES, encoding="utf-8")
    (PROYECTO / "datos" / "parametros.csv").write_text(PARAMETROS, encoding="utf-8")
    (PROYECTO / "datos" / "base.csv").write_text(datos_de_ejemplo(), encoding="utf-8")

    def entrada(nombre: str) -> zipfile.ZipInfo:
        info = zipfile.ZipInfo(f"intervalos/{nombre}", date_time=FECHA)
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

"""Genera public/descargas/importar-y-limpiar.zip.

    python descargables/generar_importar_y_limpiar.py

Los archivos del proyecto viven en `descargables/importar-y-limpiar/`; este
script arma los datos de ejemplo y empaqueta, con las mismas reglas que el
proyecto base: fecha fija, orden fijo, sin comprimir y declarando siempre el
mismo sistema, para que el zip sea idéntico en cualquier máquina.

El ejemplo es un CSV como los que exporta Excel en español —punto y coma, coma
decimal, BOM— con todo lo que este script sabe arreglar.

Lo verifica `npm run script-limpiar`.
"""

import random
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PROYECTO = Path(__file__).resolve().parent / "importar-y-limpiar"
DESTINO = RAIZ / "public" / "descargas" / "importar-y-limpiar.zip"
FECHA = (2026, 9, 23, 0, 0, 0)
CASOS = 80

ARCHIVOS = [
    "README.md",
    ".gitignore",
    "datos/crudos/encuesta.csv",
    "datos/crudos/diccionario.csv",
    "R/correr.R",
    "R/comun.R",
    "R/01-perfilar.R",
    "R/02-limpiar.R",
    "python/correr.py",
    "python/comun.py",
    "python/01_perfilar.py",
    "python/02_limpiar.py",
]

GITIGNORE = """# Lo que se puede volver a generar no se versiona.
datos/limpios/
salidas/

.Rhistory
.RData
.Rproj.user/
__pycache__/
.venv/
"""

DICCIONARIO = """nombre,tipo,minimo,maximo,codigos,faltante,id
id,texto,,,,,Sí
fecha,fecha,,,,,No
grupo,categoria,,,Control;Tratamiento,,No
edad,entero,18,99,,999,No
ingreso,decimal,0,,,,No
puntaje,entero,1,10,,99,No
comentario,texto,,,,,No
"""


def datos_de_ejemplo() -> str:
    """Un CSV exportado por Excel en español, con todos los problemas que el
    script sabe arreglar: coma decimal, separador de miles, una categoría
    escrita de tres maneras, códigos de faltante, dos formatos de fecha, una
    fila repetida y una columna que nadie declaró."""
    azar = random.Random(20260923)
    grupos = ["Control", "Tratamiento", "CONTROL", "tratamiento"]
    filas = []
    for i in range(1, CASOS + 1):
        grupo = grupos[i % 4] if i % 7 == 0 else ("Control" if i % 2 else "Tratamiento")
        edad = min(85, max(18, round(azar.gauss(41, 13))))
        ingreso = round(max(0, azar.gauss(420000, 160000)), 2)
        puntaje = min(10, max(1, round(azar.gauss(7, 2))))
        fecha = f"{azar.randint(1, 28):02d}/0{azar.randint(1, 9)}/2026"
        # El ingreso, como lo escribe Excel en español: 1.234.567,89
        entero, decimales = f"{int(ingreso):,}".replace(",", "."), f"{ingreso:.2f}".split(".")[1]
        filas.append([f"c{i:03d}", fecha, grupo, str(edad), f"{entero},{decimales}", str(puntaje),
                      "  sin comentarios " if i % 9 == 0 else ""])

    filas[3][1] = "2026-03-14"       # la misma fecha, en el otro formato
    filas[8][3] = "999"              # el código de «no responde» de la edad
    filas[12][5] = "99"              # el de puntaje
    filas[19][3] = "7"               # una edad fuera del rango declarado
    filas[26][5] = "11"              # un puntaje fuera de escala
    filas[33][2] = "Testigo"         # una categoría que no está en el diccionario
    filas[41][4] = "no contesta"     # un ingreso que no es un número
    filas[47][3] = "38,5"            # una edad con decimales
    filas[54][1] = "31/02/2026"      # una fecha que no existe en el calendario
    filas.insert(60, list(filas[59]))  # la fila anterior, cargada dos veces

    encabezado = "id;fecha;grupo;edad;ingreso;puntaje;comentario;observaciones"
    lineas = [encabezado]
    for i, f in enumerate(filas):
        # «observaciones» no está en el diccionario: el perfil la marca.
        lineas.append(";".join(f + ["ok" if i % 5 else ""]))
    return "﻿" + "\n".join(lineas) + "\n"


def generar(destino: Path = DESTINO) -> Path:
    (PROYECTO / ".gitignore").write_text(GITIGNORE, encoding="utf-8")
    (PROYECTO / "datos" / "crudos" / "diccionario.csv").write_text(DICCIONARIO, encoding="utf-8")
    (PROYECTO / "datos" / "crudos" / "encuesta.csv").write_text(datos_de_ejemplo(), encoding="utf-8")

    def entrada(nombre: str) -> zipfile.ZipInfo:
        info = zipfile.ZipInfo(f"importar-y-limpiar/{nombre}", date_time=FECHA)
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
        for carpeta in ["datos/limpios", "salidas"]:
            zip_.writestr(entrada(f"{carpeta}/.gitkeep"), "")
    return destino


if __name__ == "__main__":
    ruta = generar()
    print(f"public/descargas/{ruta.name} ({ruta.stat().st_size / 1024:.0f} KB)")

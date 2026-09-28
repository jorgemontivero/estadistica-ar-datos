"""Genera public/descargas/estandarizacion.zip.

    python descargables/generar_estandarizacion.py

Los archivos del proyecto viven en `descargables/estandarizacion/`; este script
los empaqueta, con las mismas reglas que los otros descargables: fecha fija,
orden fijo, sin comprimir y declarando siempre el mismo sistema.

A diferencia del resto de la serie, acá **no se genera ningún dato**. Los del
ejemplo son reales —las defunciones de 2022 de las 24 jurisdicciones argentinas
sobre la población del Censo 2022— y están versionados tal cual. Quien quiera
ver de dónde salieron tiene la ficha en `estandarizacion/datos/FUENTES.md` y el
extractor en `descargables/extraer_estandarizacion.py`, que lee el espejo local
de la DEIS y del Censo.

Lo verifica `npm run script-estandarizacion`.
"""

import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PROYECTO = Path(__file__).resolve().parent / "estandarizacion"
DESTINO = RAIZ / "public" / "descargas" / "estandarizacion.zip"
FECHA = (2026, 9, 24, 0, 0, 0)

ARCHIVOS = [
    "README.md",
    ".gitignore",
    "datos/mortalidad-2022.csv",
    "datos/estandares.csv",
    "datos/parametros.csv",
    "datos/FUENTES.md",
    "R/correr.R",
    "R/comun.R",
    "R/01-directa.R",
    "R/02-indirecta.R",
    "R/03-comparar.R",
    "R/04-redaccion.R",
    "python/correr.py",
    "python/comun.py",
    "python/01_directa.py",
    "python/02_indirecta.py",
    "python/03_comparar.py",
    "python/04_redaccion.py",
]

GITIGNORE = """# Lo que se puede volver a generar no se versiona.
salidas/

.Rhistory
.RData
.Rproj.user/
__pycache__/
.venv/
"""


def generar(destino: Path = DESTINO) -> Path:
    """El zip, igual en cualquier máquina.

    Los archivos se leen con `read_text`, que convierte los fines de línea de
    Windows en los de siempre: si no, el zip armado en una máquina y el armado
    en otra no serían el mismo archivo.
    """
    (PROYECTO / ".gitignore").write_text(GITIGNORE, encoding="utf-8")
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)

    def entrada(nombre: str) -> zipfile.ZipInfo:
        info = zipfile.ZipInfo(f"estandarizacion/{nombre}", date_time=FECHA)
        info.compress_type = zipfile.ZIP_STORED
        info.external_attr = 0o644 << 16
        info.create_system = 3
        return info

    with zipfile.ZipFile(destino, "w", zipfile.ZIP_STORED) as z:
        for nombre in ARCHIVOS:
            origen = PROYECTO / nombre
            if not origen.exists():
                raise SystemExit(f"Falta {origen}")
            z.writestr(entrada(nombre), origen.read_text(encoding="utf-8"))
        z.writestr(entrada("salidas/.gitkeep"), "")
    return destino


if __name__ == "__main__":
    ruta = generar()
    print(f"public/descargas/{ruta.name} ({ruta.stat().st_size / 1024:.0f} KB)")

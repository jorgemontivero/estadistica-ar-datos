"""Genera public/descargas/multivariado.zip.

    python descargables/generar_multivariado.py

Los archivos del proyecto viven en `descargables/multivariado/`; este script los
empaqueta, con las mismas reglas que los otros descargables: fecha fija, orden
fijo, sin comprimir y declarando siempre el mismo sistema.

Acá **no se genera ningún dato**. Los del ejemplo son reales —ocho indicadores
de las 24 jurisdicciones argentinas y la tabla de nivel educativo, del Censo
2022— y están versionados tal cual. La ficha está en
`multivariado/datos/FUENTES.md` y el extractor en
`descargables/extraer_multivariado.py`, que lee el espejo local del Censo.

Lo verifica `npm run script-multivariado`.
"""

import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PROYECTO = Path(__file__).resolve().parent / "multivariado"
DESTINO = RAIZ / "public" / "descargas" / "multivariado.zip"
FECHA = (2026, 9, 24, 0, 0, 0)

ARCHIVOS = [
    "README.md",
    ".gitignore",
    "datos/indicadores.csv",
    "datos/educacion.csv",
    "datos/parametros.csv",
    "datos/FUENTES.md",
    "R/correr.R",
    "R/comun.R",
    "R/jacobi.R",
    "R/01-componentes.R",
    "R/02-conglomerados.R",
    "R/03-correspondencias.R",
    "R/04-redaccion.R",
    "python/correr.py",
    "python/comun.py",
    "python/jacobi.py",
    "python/01_componentes.py",
    "python/02_conglomerados.py",
    "python/03_correspondencias.py",
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
        info = zipfile.ZipInfo(f"multivariado/{nombre}", date_time=FECHA)
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

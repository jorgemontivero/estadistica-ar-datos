"""Genera public/descargas/muestreo.zip.

    python descargables/generar_muestreo.py

Los archivos del proyecto viven en `descargables/muestreo/`; este script arma
el marco de ejemplo y empaqueta, con las mismas reglas que los otros
descargables: fecha fija, orden fijo, sin comprimir y declarando siempre el
mismo sistema.

A diferencia del resto de la serie, acá los datos **no** son una muestra: son
la población entera. Es lo que un proyecto de muestreo necesita para poder
mostrar la única cosa que en la vida real nunca se puede mirar, que es si el
intervalo le acertó al valor verdadero.

Lo verifica `npm run script-muestreo`.
"""

import math
import random
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PROYECTO = Path(__file__).resolve().parent / "muestreo"
DESTINO = RAIZ / "public" / "descargas" / "muestreo.zip"
FECHA = (2026, 9, 23, 0, 0, 0)

ARCHIVOS = [
    "README.md",
    ".gitignore",
    "datos/marco.csv",
    "datos/variables.csv",
    "datos/parametros.csv",
    "R/correr.R",
    "R/comun.R",
    "R/01-seleccion.R",
    "R/02-ponderadores.R",
    "R/03-estimacion.R",
    "R/04-redaccion.R",
    "python/correr.py",
    "python/comun.py",
    "python/azar.py",
    "python/01_seleccion.py",
    "python/02_ponderadores.py",
    "python/03_estimacion.py",
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

VARIABLES = """nombre,etiqueta,tipo
hogar,Identificador del hogar,identificador
region,Región,categorica
radio,Radio censal,categorica
ingreso,Ingreso mensual del hogar,numerica
personas,Personas en el hogar,numerica
agua,Tiene agua de red,binaria
tamano,Tamaño del hogar,categorica
"""

# El diseño se declara acá y no en el código.
PARAMETROS = """clave,valor
confianza,0.95
semilla,2026
estrato,region
conglomerado,radio
calibrar_por,tamano
variable,ingreso
variable_total,personas
variable_binaria,agua
exito,Sí
conglomerados_por_estrato,8
hogares_por_conglomerado,10
tasa_de_no_respuesta,0.12
replicas_de_cobertura,500
"""

# Cuatro regiones de tamaños distintos, con radios de veinte hogares.
REGIONES = [("Centro", 80), ("Este", 45), ("Norte", 30), ("Sur", 45)]
POR_RADIO = 20
NIVEL = {"Norte": 0.00, "Centro": 0.35, "Sur": -0.20, "Este": 0.10}
# El desvío entre radios es lo que hace que el efecto de diseño sea grande:
# los hogares de un mismo radio se parecen entre sí, que es lo que pasa en
# cualquier ciudad y lo que un muestreo por conglomerados paga.
DESVIO_ENTRE_RADIOS = 0.42
DESVIO_DENTRO = 0.55


def marco_de_ejemplo() -> str:
    """Los 4.000 hogares de la población, con su región y su radio.

    El ingreso se arma en dos capas: un efecto de radio y un ruido de hogar.
    Esa es toda la física del ejemplo —los vecinos se parecen— y es de donde
    sale el efecto de diseño que el proyecto quiere mostrar.
    """
    azar = random.Random(20261001)
    filas = []
    radio = 0
    for region, radios in REGIONES:
        for _ in range(radios):
            radio += 1
            efecto = azar.gauss(0, DESVIO_ENTRE_RADIOS)
            # La cobertura de agua también se parece dentro del radio: se
            # tiende una red por cuadra, no por hogar.
            prob_agua = min(0.99, max(0.35, 0.82 + NIVEL[region] * 0.3 + efecto * 0.35))
            for _ in range(POR_RADIO):
                log_ingreso = 12.9 + NIVEL[region] + efecto + azar.gauss(0, DESVIO_DENTRO)
                personas = max(1, min(12, round(azar.gauss(3.4 - NIVEL[region], 1.7))))
                # El tramo de tamaño del hogar es lo que se usa para calibrar:
                # un censo lo conoce y una encuesta no tiene por qué
                # reproducirlo sola.
                tamano = ("1 a 2" if personas <= 2 else
                          "3 a 4" if personas <= 4 else "5 o más")
                filas.append([
                    str(len(filas) + 1), region, str(radio),
                    f"{math.exp(log_ingreso):.2f}", str(personas),
                    "Sí" if azar.random() < prob_agua else "No", tamano,
                ])

    lineas = ["hogar,region,radio,ingreso,personas,agua,tamano"]
    lineas += [",".join(f) for f in filas]
    return "\n".join(lineas) + "\n"


def generar(destino: Path = DESTINO) -> Path:
    (PROYECTO / ".gitignore").write_text(GITIGNORE, encoding="utf-8")
    (PROYECTO / "datos" / "variables.csv").write_text(VARIABLES, encoding="utf-8")
    (PROYECTO / "datos" / "parametros.csv").write_text(PARAMETROS, encoding="utf-8")
    (PROYECTO / "datos" / "marco.csv").write_text(marco_de_ejemplo(), encoding="utf-8")

    def entrada(nombre: str) -> zipfile.ZipInfo:
        info = zipfile.ZipInfo(f"muestreo/{nombre}", date_time=FECHA)
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

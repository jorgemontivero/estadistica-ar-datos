"""Genera public/descargas/no-parametricas.zip.

    python descargables/generar_no_parametricas.py

Los archivos del proyecto viven en `descargables/no-parametricas/`; este
script arma los datos de ejemplo y empaqueta, con las mismas reglas que los
otros descargables: fecha fija, orden fijo, sin comprimir y declarando
siempre el mismo sistema.

Las doce primeras columnas de la base son, carácter por carácter, las del
descargable de ANOVA. La columna nueva se sortea con un generador propio para
no correr la serie de las viejas.

Lo verifica `npm run script-no-parametricas`.
"""

import random
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PROYECTO = Path(__file__).resolve().parent / "no-parametricas"
DESTINO = RAIZ / "public" / "descargas" / "no-parametricas.zip"
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
    "R/azar.R",
    "R/01-apareadas.R",
    "R/02-independientes.R",
    "R/03-bootstrap.R",
    "R/04-redaccion.R",
    "python/correr.py",
    "python/comun.py",
    "python/azar.py",
    "python/01_apareadas.py",
    "python/02_independientes.py",
    "python/03_bootstrap.py",
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
grupo,Grupo,categorica
edad,Edad (años),numerica
ingreso,Ingreso mensual del hogar,numerica
puntaje,Puntaje de satisfacción,numerica
horas,Horas de estudio por semana,numerica
gasto,Gasto mensual en materiales,numerica
sexo,Sexo,categorica
nivel,Nivel educativo,categorica
beca,Tiene beca,categorica
nota,Nota final de la cursada,numerica
aprueba,Aprobó la cursada,binaria
desempeno,Desempeño en la evaluación final,numerica
previo,Desempeño en la evaluación de ingreso,numerica
"""

# Qué se compara con qué. `antes` y `despues` son la misma unidad medida dos
# veces; `respuesta` y `grupo`, dos muestras independientes.
PARAMETROS = """clave,valor
confianza,0.95
antes,previo
despues,desempeno
respuesta,gasto
grupo,grupo
factor,nivel
replicas,2000
semilla,20260930
"""

# La mejora media entre la evaluación de ingreso y la final, y cuánto varía de
# persona a persona. Está elegido para que la mejora sea chica frente a la
# dispersión entre personas y grande frente a la dispersión de los cambios:
# ahí es donde tirar el apareamiento cuesta la conclusión entera.
MEJORA = 1.2
DESVIO_DEL_CAMBIO = 6.5


def datos_de_ejemplo() -> str:
    """Los 150 casos de siempre, con una columna más y ni una celda cambiada.

    El `previo` es la evaluación de ingreso de la misma persona. La mejora
    media es de poco más de un punto, con un desvío de seis y medio: chica al
    lado de los doce puntos que separan a una persona de otra. Esa relación
    es la que hace que la comparación apareada vea el efecto y la misma
    comparación hecha como si fueran dos muestras independientes no lo vea.

    Los dos casos sin evaluación final igual tienen ingreso: rindieron al
    entrar y no rindieron al salir, que es lo que pasa siempre.
    """
    azar = random.Random(20260923)
    otro = random.Random(20260924)
    tercero = random.Random(20260925)
    cuarto = random.Random(20260926)
    quinto = random.Random(20260927)
    sexto = random.Random(20260928)
    septimo = random.Random(20260929)
    niveles = ["Primario", "Secundario", "Superior"]
    medias = {
        ("Primario", "Control"): 55.0, ("Primario", "Tratamiento"): 68.0,
        ("Secundario", "Control"): 62.0, ("Secundario", "Tratamiento"): 63.5,
        ("Superior", "Control"): 70.0, ("Superior", "Tratamiento"): 62.0,
    }
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
        ruido = quinto.gauss(0, 1.6)
        lineal = -7.2 + 0.28 * horas + 0.55 * puntaje
        aprueba = "Sí" if cuarto.random() < 1 / (1 + pow(2.718281828459045, -lineal)) else "No"
        desempeno = max(0, min(100, sexto.gauss(medias[(nivel, grupo)], 9.0)))
        previo = max(0, min(100, desempeno - septimo.gauss(MEJORA, DESVIO_DEL_CAMBIO)))
        filas.append([grupo, str(edad), f"{ingreso:.2f}", str(puntaje), sexo, nivel,
                      f"{horas:.1f}", beca, f"{gasto:.2f}", ruido, aprueba,
                      f"{desempeno:.1f}", f"{previo:.1f}"])

    for i, factor in [(12, 14), (40, 17), (96, 12)]:
        filas[i][8] = f"{float(filas[i][8]) * factor:.2f}"

    for fila in filas:
        nota = 2.0 + 0.07 * float(fila[6]) + 0.000003 * float(fila[8]) + fila[9]
        fila[9] = f"{min(10, max(1, nota)):.2f}"

    for i, j in [(7, 1), (23, 2), (61, 3), (88, 2), (104, 4)]:
        filas[i][j] = ""
    for i in [33, 119]:
        filas[i][11] = ""

    lineas = ["grupo,edad,ingreso,puntaje,sexo,nivel,horas,beca,gasto,nota,aprueba,"
              "desempeno,previo"]
    lineas += [",".join(f) for f in filas]
    return "\n".join(lineas) + "\n"


def generar(destino: Path = DESTINO) -> Path:
    (PROYECTO / ".gitignore").write_text(GITIGNORE, encoding="utf-8")
    (PROYECTO / "datos" / "variables.csv").write_text(VARIABLES, encoding="utf-8")
    (PROYECTO / "datos" / "parametros.csv").write_text(PARAMETROS, encoding="utf-8")
    (PROYECTO / "datos" / "base.csv").write_text(datos_de_ejemplo(), encoding="utf-8")

    def entrada(nombre: str) -> zipfile.ZipInfo:
        info = zipfile.ZipInfo(f"no-parametricas/{nombre}", date_time=FECHA)
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

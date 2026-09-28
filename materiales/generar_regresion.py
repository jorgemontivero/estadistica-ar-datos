"""Genera public/descargas/regresion.zip.

    python descargables/generar_regresion.py

Los archivos del proyecto viven en `descargables/regresion/`; este script arma
los datos de ejemplo y empaqueta, con las mismas reglas que los otros
descargables: fecha fija, orden fijo, sin comprimir y declarando siempre el
mismo sistema.

Las nueve primeras columnas de la base son, carácter por carácter, las del
descargable de pruebas de hipótesis. Cada columna nueva se sortea con un
generador propio para no correr la serie de las viejas.

Lo verifica `npm run script-regresion`.
"""

import random
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PROYECTO = Path(__file__).resolve().parent / "regresion"
DESTINO = RAIZ / "public" / "descargas" / "regresion.zip"
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
    "R/algebra.R",
    "R/01-lineal.R",
    "R/02-diagnostico.R",
    "R/03-logistica.R",
    "R/04-redaccion.R",
    "python/correr.py",
    "python/comun.py",
    "python/algebra.py",
    "python/01_lineal.py",
    "python/02_diagnostico.py",
    "python/03_logistica.py",
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
"""

# El modelo se declara acá y no en el código: cambiar de respuesta o de
# predictores no tiene que obligar a editar un script.
PARAMETROS = """clave,valor
confianza,0.95
respuesta_numerica,nota
predictores,horas;gasto;edad
respuesta_binaria,aprueba
predictores_binaria,horas;puntaje
exito,Sí
"""


def datos_de_ejemplo() -> str:
    """Los 150 casos de siempre, con dos columnas más y ni una celda cambiada.

    La nota depende de las horas de estudio y, apenas, del gasto en
    materiales. Eso alcanza para que el proyecto muestre lo que quiere
    mostrar sin inventar nada: los tres gastos enormes que ya traía la base
    —los mismos que el descargable de gráficos deja a la vista en la caja y
    el de pruebas usa para Mann-Whitney— son, en una regresión, puntos de
    muchísima palanca. Uno de ellos decide solo si el coeficiente del gasto
    es significativo o no.
    """
    azar = random.Random(20260923)
    otro = random.Random(20260924)
    tercero = random.Random(20260925)
    cuarto = random.Random(20260926)
    quinto = random.Random(20260927)
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
        # La nota se calcula más abajo: necesita el gasto ya corregido por los
        # tres valores extremos, así que no puede salir de este bucle.
        ruido = quinto.gauss(0, 1.6)
        # La aprobación depende de las horas y del puntaje, con ruido.
        lineal = -7.2 + 0.28 * horas + 0.55 * puntaje
        aprueba = "Sí" if cuarto.random() < 1 / (1 + pow(2.718281828459045, -lineal)) else "No"
        filas.append([grupo, str(edad), f"{ingreso:.2f}", str(puntaje), sexo, nivel,
                      f"{horas:.1f}", beca, f"{gasto:.2f}", ruido, aprueba])

    for i, factor in [(12, 14), (40, 17), (96, 12)]:
        filas[i][8] = f"{float(filas[i][8]) * factor:.2f}"

    # Recién ahora se puede calcular la nota, con el gasto definitivo.
    for fila in filas:
        nota = 2.0 + 0.07 * float(fila[6]) + 0.000003 * float(fila[8]) + fila[9]
        fila[9] = f"{min(10, max(1, nota)):.2f}"

    for i, j in [(7, 1), (23, 2), (61, 3), (88, 2), (104, 4)]:
        filas[i][j] = ""

    lineas = ["grupo,edad,ingreso,puntaje,sexo,nivel,horas,beca,gasto,nota,aprueba"]
    lineas += [",".join(f) for f in filas]
    return "\n".join(lineas) + "\n"


def generar(destino: Path = DESTINO) -> Path:
    (PROYECTO / ".gitignore").write_text(GITIGNORE, encoding="utf-8")
    (PROYECTO / "datos" / "variables.csv").write_text(VARIABLES, encoding="utf-8")
    (PROYECTO / "datos" / "parametros.csv").write_text(PARAMETROS, encoding="utf-8")
    (PROYECTO / "datos" / "base.csv").write_text(datos_de_ejemplo(), encoding="utf-8")

    def entrada(nombre: str) -> zipfile.ZipInfo:
        info = zipfile.ZipInfo(f"regresion/{nombre}", date_time=FECHA)
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

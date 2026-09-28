"""Arma los datos reales del descargable de estandarización.

    python descargables/extraer_estandarizacion.py

**Esto no corre en integración continua y no hace falta para usar el
descargable.** Lee el espejo local de datos —el de la DEIS y el del Censo— y
deja escritos los dos CSV que sí se versionan:

    descargables/estandarizacion/datos/mortalidad-2022.csv
    descargables/estandarizacion/datos/estandares.csv

Está en el repositorio para que quede escrito de dónde salió cada número y con
qué criterio, que es lo único que hace auditable a una tabla ya agregada.

FUENTES
-------

**Defunciones.** DEIS, «Defunciones ocurridas en la República Argentina en el
año 2022», archivo `defweb22_0.csv`. Es un tabulado, no un microdato: cada
fila es una celda (provincia de residencia × sexo × causa × grupo de edad) con
su conteo. Suma 397.115 defunciones, que es el total publicado para 2022.

**Población.** Censo Nacional de Población, Hogares y Viviendas 2022, base de
personas por provincia. El universo es **población en viviendas particulares**:
la base de colectivas trae el total de cada vivienda pero no las edades, así
que no se puede repartir por grupo. Son unas cuatro personas de cada mil, y
quedan afuera de las dos puntas por igual.

CRITERIOS
---------

- **Los grupos de edad son los del archivo de defunciones**, que llega hasta
  «80 y más» y junta el primer año con el resto de la infancia. Por eso el
  primer grupo es **0 a 9**: el archivo trae «menor de 1 año» y «1 a 9», y no
  hay manera de partir el segundo. Es una pérdida real —adentro de ese grupo la
  mortalidad infantil convive con la más baja de toda la vida— y está avisada
  en el proyecto.
- **Se descartan** las defunciones con residencia en otro país (código 98),
  con residencia sin especificar (99) y con edad sin especificar. Son 1.460 y
  999 respectivamente, sobre 397.115.
- El denominador es la población censada al 18 de mayo de 2022 y el numerador
  son las defunciones del año entero. Es la práctica habitual —la población
  censal se toma como población a mitad de año— y conviene tenerlo presente.
"""

import os
import csv
import collections
from pathlib import Path

import pandas as pd


RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "descargables" / "estandarizacion" / "datos"

# La carpeta con los microdatos públicos. No se versionan: cada fuente se
# baja de su organismo. La variable de entorno DATOS_AR permite moverla.
DATOS = Path(os.environ.get("DATOS_AR", "datos-fuente"))
DEFUNCIONES = DATOS / "Salud" / "DEIS" / "microdatos" / "defunciones" / "defweb22_0.csv"
CENSO = DATOS / "INDEC" / "Censos" / "Censo_2022" / "microdatos" / "provincias"

# Los dieciséis grupos con los que se puede trabajar: los del archivo de
# defunciones, que es el que manda porque es el más grueso de los dos.
GRUPOS = [
    "0 a 9", "10 a 14", "15 a 19", "20 a 24", "25 a 29", "30 a 34", "35 a 39",
    "40 a 44", "45 a 49", "50 a 54", "55 a 59", "60 a 64", "65 a 69", "70 a 74",
    "75 a 79", "80 y más",
]

DE_DEFUNCIONES = {
    "01_Menor de 1 año": "0 a 9", "02_1 a 9": "0 a 9", "03_10 a 14": "10 a 14",
    "04_15 a 19": "15 a 19", "05_20 a 24": "20 a 24", "06_25 a 29": "25 a 29",
    "07_30 a 34": "30 a 34", "08_35 a 39": "35 a 39", "09_40 a 44": "40 a 44",
    "10_45 a 49": "45 a 49", "11_50 a 54": "50 a 54", "12_55 a 59": "55 a 59",
    "13_60 a 64": "60 a 64", "14_65 a 69": "65 a 69", "15_70 a 74": "70 a 74",
    "16_75 a 79": "75 a 79", "17_80 y más": "80 y más",
}

JURISDICCIONES = {
    "02": "Ciudad de Buenos Aires", "06": "Buenos Aires", "10": "Catamarca",
    "14": "Córdoba", "18": "Corrientes", "22": "Chaco", "26": "Chubut",
    "30": "Entre Ríos", "34": "Formosa", "38": "Jujuy", "42": "La Pampa",
    "46": "La Rioja", "50": "Mendoza", "54": "Misiones", "58": "Neuquén",
    "62": "Río Negro", "66": "Salta", "70": "San Juan", "74": "San Luis",
    "78": "Santa Cruz", "82": "Santa Fe", "86": "Santiago del Estero",
    "90": "Tucumán", "94": "Tierra del Fuego",
}

# Población estándar mundial de la OMS, versión SEER, por 1.000.000, con los
# grupos de arriba y de abajo sumados para que calcen con los dieciséis.
OMS = {
    "0 a 9": 88569 + 86870, "10 a 14": 85970, "15 a 19": 84670, "20 a 24": 82171,
    "25 a 29": 79272, "30 a 34": 76073, "35 a 39": 71475, "40 a 44": 65877,
    "45 a 49": 60379, "50 a 54": 53681, "55 a 59": 45484, "60 a 64": 37187,
    "65 a 69": 29590, "70 a 74": 22092, "75 a 79": 15195, "80 y más": 9097 + 6348,
}

# Población estándar europea 2013 (ESP2013), por 100.000, sumada igual.
EUROPEA = {
    "0 a 9": 5000 + 5500, "10 a 14": 5500, "15 a 19": 5500, "20 a 24": 6000,
    "25 a 29": 6000, "30 a 34": 6500, "35 a 39": 7000, "40 a 44": 7000,
    "45 a 49": 7000, "50 a 54": 7000, "55 a 59": 6500, "60 a 64": 6000,
    "65 a 69": 5500, "70 a 74": 5000, "75 a 79": 4000,
    "80 y más": 2500 + 1500 + 800 + 200,
}


def grupo_de(edad: int) -> str:
    if edad < 10:
        return "0 a 9"
    if edad >= 80:
        return "80 y más"
    desde = (edad // 5) * 5
    return f"{desde} a {desde + 4}"


def leer_defunciones():
    """Las defunciones de 2022, por jurisdicción de residencia y grupo de edad."""
    conteo: dict = collections.defaultdict(int)
    descartadas = collections.Counter()
    total = 0
    with open(DEFUNCIONES, encoding="utf-8-sig") as f:
        for fila in csv.DictReader(f, delimiter=";"):
            cuantas = int(fila["CUENTA"])
            total += cuantas
            provincia = fila["PROVRES"]
            grupo = DE_DEFUNCIONES.get(fila["GRUPEDAD"])
            if provincia not in JURISDICCIONES:
                descartadas["residencia fuera del país o sin especificar"] += cuantas
                continue
            if grupo is None:
                descartadas["edad sin especificar"] += cuantas
                continue
            conteo[(provincia, grupo)] += cuantas
    print(f"  defunciones 2022: {total:,}")
    for que, cuantas in descartadas.items():
        print(f"    descartadas por {que}: {cuantas:,}")
    print(f"    quedan: {sum(conteo.values()):,}")
    return conteo


def leer_poblacion():
    """La población censada en viviendas particulares, por provincia y grupo."""
    conteo: dict = collections.defaultdict(int)
    total = 0
    for carpeta in sorted(CENSO.iterdir()):
        if not carpeta.is_dir():
            continue
        codigo = carpeta.name.split("_")[0]
        if codigo not in JURISDICCIONES:
            raise SystemExit(f"No conozco la jurisdicción {codigo} ({carpeta.name})")
        archivos = list(carpeta.glob("*_Personas.parquet"))
        if len(archivos) != 1:
            raise SystemExit(f"En {carpeta} esperaba un solo archivo de personas")
        edades = pd.read_parquet(archivos[0], columns=["edad_1"])["edad_1"]
        for edad, cuantas in edades.value_counts().items():
            conteo[(codigo, grupo_de(int(edad)))] += int(cuantas)
        total += len(edades)
        print(f"  {JURISDICCIONES[codigo]:<24} {len(edades):>10,}")
    print(f"  población en viviendas particulares: {total:,}")
    return conteo


def main() -> None:
    DESTINO.mkdir(parents=True, exist_ok=True)

    print("Defunciones")
    defunciones = leer_defunciones()
    print("\nPoblación")
    poblacion = leer_poblacion()

    filas = []
    for codigo, nombre in sorted(JURISDICCIONES.items()):
        for grupo in GRUPOS:
            filas.append({
                "jurisdiccion": nombre,
                "codigo": codigo,
                "grupo_edad": grupo,
                "defunciones": defunciones.get((codigo, grupo), 0),
                "poblacion": poblacion.get((codigo, grupo), 0),
            })
    ruta = DESTINO / "mortalidad-2022.csv"
    with open(ruta, "w", encoding="utf-8", newline="\n") as f:
        escritor = csv.DictWriter(
            f, ["jurisdiccion", "codigo", "grupo_edad", "defunciones", "poblacion"],
            lineterminator="\n")
        escritor.writeheader()
        escritor.writerows(filas)
    print(f"\n{ruta.name}: {len(filas)} filas")

    # La estándar de Argentina sale de los mismos datos: es la estructura del
    # país entero. Es la que usa la DEIS para comparar provincias entre sí.
    argentina = {g: sum(poblacion.get((c, g), 0) for c in JURISDICCIONES) for g in GRUPOS}
    ruta = DESTINO / "estandares.csv"
    with open(ruta, "w", encoding="utf-8", newline="\n") as f:
        escritor = csv.writer(f, lineterminator="\n")
        escritor.writerow(["grupo_edad", "oms", "europea", "argentina"])
        for grupo in GRUPOS:
            escritor.writerow([grupo, OMS[grupo], EUROPEA[grupo], argentina[grupo]])
    print(f"{ruta.name}: OMS suma {sum(OMS.values()):,}, "
          f"europea {sum(EUROPEA.values()):,}, Argentina {sum(argentina.values()):,}")


if __name__ == "__main__":
    main()

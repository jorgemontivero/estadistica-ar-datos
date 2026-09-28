"""Arma los datos reales del descargable de multivariado.

    python descargables/extraer_multivariado.py

**Esto no corre en integración continua y no hace falta para usar el
descargable.** Lee el espejo local del Censo 2022 y deja escritos los dos CSV
que sí se versionan:

    descargables/multivariado/datos/indicadores.csv
    descargables/multivariado/datos/educacion.csv

Está en el repositorio para que quede escrito de dónde salió cada número y con
qué criterio, que es lo único que hace auditable a una tabla ya agregada.

FUENTE
------

Censo Nacional de Población, Hogares y Viviendas 2022 (INDEC), bases de
personas y de hogares por provincia. El universo es **población y hogares en
viviendas particulares**: la base de colectivas no trae ni edades ni
condiciones habitacionales.

Las cinco necesidades básicas insatisfechas vienen **ya calculadas** en la base
de hogares (`nbi_hac`, `nbi_viv`, `nbi_san`, `nbi_esc`, `nbi_sub` y el total),
con 1 para «la tiene» y 2 para «no la tiene». No se recalcula nada: se cuenta.

CRITERIOS
---------

- **Los años de escolaridad** se promedian sobre las personas de 25 años y más
  con dato válido. El 99 es «ignorado» y no entra; tampoco los nulos, que son
  los que no contestaron.
- **La condición de actividad** solo está para las personas de 14 y más, que es
  el universo con el que se define. La desocupación va sobre la población
  económicamente activa —ocupados más desocupados— y no sobre el total.
- **Los tramos de escolaridad** de la tabla de correspondencias son una
  partición: cada persona de 25 y más con dato válido cae en uno y solo uno.
"""

import os
import csv
from pathlib import Path

import pandas as pd


# La carpeta con los microdatos públicos. No se versionan: cada fuente se
# baja de su organismo. La variable de entorno DATOS_AR permite moverla.
DATOS = os.environ.get("DATOS_AR", "datos-fuente")

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "descargables" / "multivariado" / "datos"
CENSO = Path(DATOS + r"\INDEC\Censos\Censo_2022"
             r"\microdatos\provincias")

JURISDICCIONES = {
    "02": "Ciudad de Buenos Aires", "06": "Buenos Aires", "10": "Catamarca",
    "14": "Córdoba", "18": "Corrientes", "22": "Chaco", "26": "Chubut",
    "30": "Entre Ríos", "34": "Formosa", "38": "Jujuy", "42": "La Pampa",
    "46": "La Rioja", "50": "Mendoza", "54": "Misiones", "58": "Neuquén",
    "62": "Río Negro", "66": "Salta", "70": "San Juan", "74": "San Luis",
    "78": "Santa Cruz", "82": "Santa Fe", "86": "Santiago del Estero",
    "90": "Tucumán", "94": "Tierra del Fuego",
}

# Los tramos de la tabla de correspondencias. Son una partición de las personas
# de 25 y más con dato válido: los cortes están donde están los títulos —el
# secundario completo son doce años y el universitario, diecisiete—.
TRAMOS = [
    ("Hasta 6 años", 0, 6),
    ("De 7 a 11", 7, 11),
    ("12 años", 12, 12),
    ("De 13 a 16", 13, 16),
    ("17 y más", 17, 90),
]

# El orden en que salen las columnas de indicadores, y con qué unidad.
COLUMNAS = ["poblacion", "nbi", "hacinamiento", "sin_saneamiento", "escolaridad",
            "tamano_del_hogar", "mayores", "desocupacion"]


def de_una_provincia(carpeta: Path) -> dict:
    personas = pd.read_parquet(next(carpeta.glob("*_Personas.parquet")),
                               columns=["edad_1", "aesc_5", "condact_6"])
    hogares = pd.read_parquet(next(carpeta.glob("*_Hogares.parquet")),
                              columns=["nbi_tot_5", "nbi_hac_10", "nbi_san_12"])

    n_personas = len(personas)
    n_hogares = len(hogares)
    mayores = int((personas["edad_1"] >= 65).sum())

    de_25 = personas[personas["edad_1"] >= 25]["aesc_5"]
    validos = de_25[(de_25.notna()) & (de_25 < 90)]

    activos = personas[personas["edad_1"] >= 14]["condact_6"]
    ocupados = int((activos == 1).sum())
    desocupados = int((activos == 2).sum())

    tramos = {}
    for etiqueta, desde, hasta in TRAMOS:
        tramos[etiqueta] = int(((validos >= desde) & (validos <= hasta)).sum())

    return {
        "indicadores": {
            "poblacion": n_personas,
            "nbi": 100 * int((hogares["nbi_tot_5"] == 1).sum()) / n_hogares,
            "hacinamiento": 100 * int((hogares["nbi_hac_10"] == 1).sum()) / n_hogares,
            "sin_saneamiento": 100 * int((hogares["nbi_san_12"] == 1).sum()) / n_hogares,
            "escolaridad": float(validos.mean()),
            "tamano_del_hogar": n_personas / n_hogares,
            "mayores": 100 * mayores / n_personas,
            "desocupacion": 100 * desocupados / (ocupados + desocupados),
        },
        "educacion": tramos,
    }


def main() -> None:
    DESTINO.mkdir(parents=True, exist_ok=True)
    indicadores = {}
    educacion = {}
    for carpeta in sorted(CENSO.iterdir()):
        if not carpeta.is_dir():
            continue
        codigo = carpeta.name.split("_")[0]
        if codigo not in JURISDICCIONES:
            raise SystemExit(f"No conozco la jurisdicción {codigo} ({carpeta.name})")
        nombre = JURISDICCIONES[codigo]
        salida = de_una_provincia(carpeta)
        indicadores[nombre] = salida["indicadores"]
        educacion[nombre] = salida["educacion"]
        print(f"  {nombre:<24} {salida['indicadores']['poblacion']:>10,}  "
              f"NBI {salida['indicadores']['nbi']:5.2f} %  "
              f"escolaridad {salida['indicadores']['escolaridad']:5.2f}")

    ruta = DESTINO / "indicadores.csv"
    with open(ruta, "w", encoding="utf-8", newline="\n") as f:
        escritor = csv.writer(f, lineterminator="\n")
        escritor.writerow(["jurisdiccion"] + COLUMNAS)
        for nombre in sorted(JURISDICCIONES.values()):
            fila = indicadores[nombre]
            escritor.writerow([nombre] + [
                str(int(fila[c])) if c == "poblacion" else f"{fila[c]:.6f}"
                for c in COLUMNAS])
    print(f"\n{ruta.name}: {len(indicadores)} filas x {len(COLUMNAS)} columnas")

    ruta = DESTINO / "educacion.csv"
    etiquetas = [e for e, _d, _h in TRAMOS]
    with open(ruta, "w", encoding="utf-8", newline="\n") as f:
        escritor = csv.writer(f, lineterminator="\n")
        escritor.writerow(["jurisdiccion"] + etiquetas)
        for nombre in sorted(JURISDICCIONES.values()):
            escritor.writerow([nombre] + [educacion[nombre][e] for e in etiquetas])
    total = sum(sum(v.values()) for v in educacion.values())
    print(f"{ruta.name}: {len(educacion)} filas x {len(etiquetas)} tramos, "
          f"{total:,} personas de 25 y más con dato válido")


if __name__ == "__main__":
    main()

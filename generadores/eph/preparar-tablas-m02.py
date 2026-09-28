#!/usr/bin/env python
"""
Tablas de ejemplo del módulo M02 (Descriptiva), con datos reales de la EPH.

Genera las tres tablas que usan las entradas del módulo, para que ninguna
tenga que inventar números:

    distribucion-de-frecuencias  nivel educativo de los ocupados (nominal/ordinal)
    tabla-de-frecuencias         personas por hogar (cuantitativa discreta)
    intervalos-de-clase          edad de los ocupados (agrupada en clases)

Salida: datos/eph/tablas-m02.json

    python datos/eph/preparar-tablas-m02.py
"""

from __future__ import annotations

import os

import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd


# La carpeta con los microdatos públicos. No se versionan: cada fuente se
# baja de su organismo. La variable de entorno DATOS_AR permite moverla.
DATOS = os.environ.get("DATOS_AR", "datos-fuente")

ESPEJO = Path(
    DATOS + r"\INDEC\EPH\01_microdatos_eph"
    r"\2026\EPH_usu_1_Trim_2026_txt.zip"
)
SALIDA = Path(__file__).resolve().parent / "tablas-m02.json"

NIVEL_ED = {
    1: "Primario incompleto",
    2: "Primario completo",
    3: "Secundario incompleto",
    4: "Secundario completo",
    5: "Superior incompleto",
    6: "Superior completo",
    7: "Sin instrucción",
}


def leer(interno: str, columnas: list[str]) -> pd.DataFrame:
    with zipfile.ZipFile(ESPEJO) as z, z.open(interno) as f:
        return pd.read_csv(f, sep=";", decimal=",", usecols=columnas,
                           low_memory=False)


def fila(etiqueta, ni, W, acumulada=None):
    f = {"etiqueta": etiqueta, "ni": int(round(ni)),
         "fi": round(ni / W, 3), "pi": round(100 * ni / W, 1)}
    if acumulada is not None:
        f["Ni"] = int(round(acumulada))
        f["Pi"] = round(100 * acumulada / W, 1)
    return f


def nivel_educativo() -> dict:
    """Nominal ordenada: sin acumuladas, para no sugerir un orden que no importa."""
    d = leer("usu_individual_T126.txt", ["ESTADO", "NIVEL_ED", "PONDERA"])
    u = d[(d.ESTADO == 1) & (d.NIVEL_ED.isin(NIVEL_ED))]
    g = u.groupby("NIVEL_ED").PONDERA.sum()
    W = g.sum()
    orden = [7, 1, 2, 3, 4, 5, 6]
    return {
        "universo": "Personas ocupadas",
        "n": int(len(u)),
        "poblacion": int(round(W)),
        "filas": [fila(NIVEL_ED[k], g.get(k, 0), W) for k in orden if k in g.index],
    }


def personas_por_hogar() -> dict:
    """Cuantitativa discreta: acá las acumuladas sí significan algo."""
    d = leer("usu_hogar_T126.txt", ["IX_TOT", "PONDERA"])
    u = d[d.IX_TOT > 0].copy()
    # Agrupa la cola larga para que la tabla sea legible
    u["cat"] = np.where(u.IX_TOT >= 7, 7, u.IX_TOT)
    g = u.groupby("cat").PONDERA.sum().sort_index()
    W = g.sum()
    acum = 0
    filas = []
    for k, ni in g.items():
        acum += ni
        etiqueta = "7 o más" if k == 7 else str(int(k))
        filas.append(fila(etiqueta, ni, W, acum))
    return {
        "universo": "Hogares",
        "n": int(len(u)),
        "poblacion": int(round(W)),
        "filas": filas,
        "mediana_en": next(f["etiqueta"] for f in filas if f["Pi"] >= 50),
    }


def edades_agrupadas() -> dict:
    """Continua agrupada: clases de 10 años, cerradas por izquierda."""
    d = leer("usu_individual_T126.txt", ["ESTADO", "CH06", "PONDERA"])
    u = d[(d.ESTADO == 1) & (d.CH06 >= 15) & (d.CH06 < 75)]
    bordes = list(range(15, 76, 10))
    acum = 0
    filas = []
    W = u.PONDERA.sum()
    for a, b in zip(bordes[:-1], bordes[1:]):
        ni = u.loc[(u.CH06 >= a) & (u.CH06 < b), "PONDERA"].sum()
        acum += ni
        f = fila(f"[{a}, {b})", ni, W, acum)
        f["marca"] = (a + b) / 2
        filas.append(f)
    return {
        "universo": "Personas ocupadas de 15 a 74 años",
        "n": int(len(u)),
        "poblacion": int(round(W)),
        "minimo": int(u.CH06.min()),
        "maximo": int(u.CH06.max()),
        "filas": filas,
    }


def main() -> None:
    salida = {
        "fuente": "INDEC, Encuesta Permanente de Hogares, base usuario",
        "periodo": "1º trimestre de 2026",
        "nota": "Frecuencias expandidas con el ponderador PONDERA.",
        "nivel_educativo": nivel_educativo(),
        "personas_por_hogar": personas_por_hogar(),
        "edades_agrupadas": edades_agrupadas(),
    }
    SALIDA.write_text(json.dumps(salida, ensure_ascii=False, indent=2),
                      encoding="utf-8")

    for clave in ("nivel_educativo", "personas_por_hogar", "edades_agrupadas"):
        t = salida[clave]
        print(f"\n### {clave}  (n = {t['n']:,} · {t['poblacion']:,} expandidos)")
        for f in t["filas"]:
            acum = f" | {f['Pi']:>5} %" if "Pi" in f else ""
            print(f"  {f['etiqueta']:<24} {f['ni']:>10,}  {f['fi']:>6}  "
                  f"{f['pi']:>5} %{acum}")


if __name__ == "__main__":
    main()

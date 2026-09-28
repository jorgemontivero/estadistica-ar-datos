#!/usr/bin/env python
"""
La serie mensual completa del IPC, para la calculadora de deflactación.

El JSON de M04 (`indices-m04.json`) trae resúmenes —la última variación, el
cambio de base, un ejemplo de deflactación—, pero la calculadora necesita la
serie entera: cualquiera puede pedir pasar pesos de un mes cualquiera a otro.

Son unos 120 números, así que el archivo pesa nada y se sirve como estático.
El IPC nacional empieza en diciembre de 2016 (es su base), y para lo anterior
el INDEC no publica una serie nacional homogénea: hubo años sin IPC creíble.
Eso queda advertido en la página, no disimulado con un empalme inventado.

Salida: public/datos/ipc-mensual.json

    python datos/series/preparar-ipc-deflactor.py
"""

from __future__ import annotations

import os

import json
from pathlib import Path

import pandas as pd


# La carpeta con los microdatos públicos. No se versionan: cada fuente se
# baja de su organismo. La variable de entorno DATOS_AR permite moverla.
DATOS = os.environ.get("DATOS_AR", "datos-fuente")

MACRO = Path(DATOS + r"\Macro_fiscal")
ARCHIVO = (
    MACRO
    / "indice-de-precios-al-consumidor-nacional-ipc-base-diciembre-2016"
    / "Indice_de_Precios_al_Consumidor._Nivel_Gener__indice-precios-al-consumidor-nivel-general-bas.csv"
)
SALIDA = Path(__file__).resolve().parent.parent.parent / "public" / "datos" / "ipc-mensual.json"


def main() -> None:
    ipc = pd.read_csv(ARCHIVO, encoding="utf-8-sig")
    ipc["fecha"] = pd.to_datetime(ipc["indice_tiempo"])
    ipc = ipc.dropna(subset=["ipc_ng_nacional"]).sort_values("fecha")

    meses = [f"{d.year}-{d.month:02d}" for d in ipc["fecha"]]
    valores = [round(float(v), 4) for v in ipc["ipc_ng_nacional"]]

    # Control: la serie tiene que ser mensual y sin huecos.
    esperados = pd.date_range(ipc["fecha"].iloc[0], ipc["fecha"].iloc[-1], freq="MS")
    if len(esperados) != len(ipc):
        faltan = sorted(set(esperados) - set(ipc["fecha"]))
        raise SystemExit(
            f"La serie tiene huecos: faltan {len(faltan)} meses, "
            f"del {faltan[0]:%Y-%m} en adelante"
        )
    # Control: el IPC no baja nunca en este período, y si bajara habría que mirarlo.
    caidas = [(m, a, b) for m, a, b in zip(meses[1:], valores, valores[1:]) if b < a]
    if caidas:
        print(f"  Ojo: {len(caidas)} mes(es) con caída del índice: {caidas[:3]}")

    salida = {
        "fuente": "IPC nacional, nivel general, base diciembre 2016 = 100. INDEC",
        "url": "https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-5-31",
        "desde": meses[0],
        "hasta": meses[-1],
        "meses": meses,
        "valores": valores,
    }

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps(salida, ensure_ascii=False), encoding="utf-8")

    print(f"  {len(meses)} meses, de {meses[0]} a {meses[-1]}")
    print(f"  índice final: {valores[-1]:,.2f}".replace(",", "."))
    print(f"  acumulado desde la base: ×{valores[-1] / 100:,.1f}".replace(",", "."))
    print(f"  escrito en {SALIDA}")


if __name__ == "__main__":
    main()

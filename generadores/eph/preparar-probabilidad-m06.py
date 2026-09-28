#!/usr/bin/env python
"""
Probabilidades de referencia para las entradas del módulo M06.

Construye, con la EPH real, la tabla conjunta que M06 usa como hilo conductor:
nivel educativo x registración del empleo, entre los asalariados ocupados.
De ahí salen todas las probabilidades del módulo —conjuntas, marginales,
condicionales, la verificación de independencia y el ejemplo de Bayes—.

Además calcula la tabla de diagnóstico (sensibilidad, especificidad y VPP)
sobre esa misma base: "ser asalariado no registrado" hace de condición y
"no haber terminado el secundario" hace de señal, para que el ejemplo de
valor predictivo no sea un caso médico inventado.

Salida: datos/eph/probabilidad-m06.json

    python datos/eph/preparar-probabilidad-m06.py
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
SALIDA = Path(__file__).resolve().parent / "probabilidad-m06.json"


def leer(interno: str, columnas: list[str]) -> pd.DataFrame:
    with zipfile.ZipFile(ESPEJO) as z, z.open(interno) as f:
        return pd.read_csv(f, sep=";", decimal=",", usecols=columnas,
                           low_memory=False)


def main() -> None:
    ind = leer(
        "usu_individual_T126.txt",
        ["ESTADO", "CAT_OCUP", "NIVEL_ED", "PP07H", "CH06", "PONDERA"],
    )

    # Asalariados ocupados de 18 años o más, con registración declarada.
    # PP07H: 1 = le descuentan jubilación, 2 = no.
    d = ind[
        (ind["ESTADO"] == 1)
        & (ind["CAT_OCUP"] == 3)
        & (ind["CH06"] >= 18)
        & (ind["PP07H"].isin([1, 2]))
        & (ind["NIVEL_ED"].between(1, 6))
    ].copy()

    # NIVEL_ED: 1 primaria incompleta … 6 superior completa.
    # 1-3 = hasta secundario incompleto · 4-6 = secundario completo o más
    d["sec"] = np.where(d["NIVEL_ED"].isin([4, 5, 6]), 1, 0)
    d["reg"] = np.where(d["PP07H"] == 1, 1, 0)

    w = d["PONDERA"].to_numpy(float)
    W = w.sum()

    def p(sec: int, reg: int) -> float:
        m = (d["sec"] == sec) & (d["reg"] == reg)
        return float(w[m.to_numpy()].sum() / W)

    conj = {f"sec{s}_reg{r}": p(s, r) for s in (0, 1) for r in (0, 1)}

    p_sec = {"0": conj["sec0_reg0"] + conj["sec0_reg1"],
             "1": conj["sec1_reg0"] + conj["sec1_reg1"]}
    p_reg = {"0": conj["sec0_reg0"] + conj["sec1_reg0"],
             "1": conj["sec0_reg1"] + conj["sec1_reg1"]}

    # Condicionales P(registrado | nivel educativo)
    cond_reg_dado_sec = {
        "0": conj["sec0_reg1"] / p_sec["0"],
        "1": conj["sec1_reg1"] / p_sec["1"],
    }
    # Condicionales invertidas P(secundario | registración)
    cond_sec_dado_reg = {
        "0": conj["sec1_reg0"] / p_reg["0"],
        "1": conj["sec1_reg1"] / p_reg["1"],
    }

    # Qué valdría la celda (sec=0, reg=0) si fueran independientes
    esperado_si_indep = p_sec["0"] * p_reg["0"]

    # Diagnóstico: condición = no registrado, señal = sin secundario completo
    vp = conj["sec0_reg0"]           # sin secundario y no registrado
    fp = conj["sec0_reg1"]           # sin secundario pero registrado
    fn = conj["sec1_reg0"]           # con secundario y no registrado
    vn = conj["sec1_reg1"]           # con secundario y registrado

    diagnostico = {
        "prevalencia": p_reg["0"],
        "sensibilidad": vp / (vp + fn),
        "especificidad": vn / (vn + fp),
        "vpp": vp / (vp + fp),
        "vpn": vn / (vn + fn),
    }

    salida = {
        "fuente": "EPH continua, 1er trimestre de 2026, total aglomerados urbanos",
        "universo": "Asalariados ocupados de 18 años o más con registración declarada",
        "n": int(len(d)),
        "poblacion_expandida": float(W),
        "conjunta": conj,
        "marginal_secundario": p_sec,
        "marginal_registrado": p_reg,
        "cond_registrado_dado_secundario": cond_reg_dado_sec,
        "cond_secundario_dado_registrado": cond_sec_dado_reg,
        "esperado_si_independientes_sec0_reg0": esperado_si_indep,
        "diagnostico": diagnostico,
    }

    SALIDA.write_text(json.dumps(salida, indent=2, ensure_ascii=False),
                      encoding="utf-8")

    print(f"n = {len(d):,}  ·  poblacion = {W:,.0f}")
    print()
    print("Tabla conjunta (probabilidades)")
    print(f"{'':28} {'no reg.':>9} {'registrado':>11} {'marginal':>10}")
    for s, etiq in ((0, "hasta sec. incompleto"), (1, "secundario completo+")):
        print(f"  {etiq:26} {conj[f'sec{s}_reg0']:9.4f} "
              f"{conj[f'sec{s}_reg1']:11.4f} {p_sec[str(s)]:10.4f}")
    print(f"  {'marginal':26} {p_reg['0']:9.4f} {p_reg['1']:11.4f} "
          f"{1.0:10.4f}")
    print()
    print("P(registrado | hasta sec. incompleto) =",
          f"{cond_reg_dado_sec['0']:.4f}")
    print("P(registrado | secundario completo+)  =",
          f"{cond_reg_dado_sec['1']:.4f}")
    print("Celda (sin sec., no reg.) si fueran independientes:",
          f"{esperado_si_indep:.4f}  (observada {conj['sec0_reg0']:.4f})")
    print()
    print("Diagnóstico — condición: no registrado · señal: sin secundario")
    for k, v in diagnostico.items():
        print(f"  {k:14} {v:.4f}")
    print()
    print(f"→ {SALIDA}")


if __name__ == "__main__":
    main()

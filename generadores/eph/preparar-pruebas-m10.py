#!/usr/bin/env python
"""
Estadísticos de prueba de referencia para el módulo M10.

Calcula, sobre la EPH real, cada una de las pruebas que M10 explica: t para una
media, t para dos muestras, z para una y dos proporciones, chi-cuadrado de
bondad de ajuste y de independencia, F para varianzas, más los tamaños de
efecto que corresponden a cada una.

La tabla de independencia es la misma de M06 (nivel educativo x registración),
para que el módulo de hipótesis retome el caso que el de probabilidad ya
describió.

Salida: datos/eph/pruebas-m10.json

    python datos/eph/preparar-pruebas-m10.py

Nota sobre los ponderadores: las pruebas usan los casos SIN ponderar, tratando
la muestra como si fuera aleatoria simple. Es la convención del sitio para los
ejemplos de inferencia —lo que se enseña es el procedimiento—, y queda dicho en
cada entrada que el diseño real de la EPH es por conglomerados y exige errores
estándar de diseño complejo.
"""

from __future__ import annotations

import os

import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


# La carpeta con los microdatos públicos. No se versionan: cada fuente se
# baja de su organismo. La variable de entorno DATOS_AR permite moverla.
DATOS = os.environ.get("DATOS_AR", "datos-fuente")

ESPEJO = Path(
    DATOS + r"\INDEC\EPH\01_microdatos_eph"
    r"\2026\EPH_usu_1_Trim_2026_txt.zip"
)
SALIDA = Path(__file__).resolve().parent / "pruebas-m10.json"


def leer(interno: str, columnas: list[str]) -> pd.DataFrame:
    with zipfile.ZipFile(ESPEJO) as z, z.open(interno) as f:
        return pd.read_csv(f, sep=";", decimal=",", usecols=columnas,
                           low_memory=False)


def main() -> None:
    ind = leer(
        "usu_individual_T126.txt",
        ["ESTADO", "CAT_OCUP", "NIVEL_ED", "PP07H", "CH03", "CH04", "CH06",
         "P21", "PONDERA"],
    )

    out: dict = {
        "fuente": "EPH continua, 1er trimestre de 2026, total aglomerados urbanos",
        "advertencia": (
            "Pruebas calculadas sobre casos sin ponderar, tratando la muestra "
            "como aleatoria simple. El diseño real es por conglomerados."
        ),
    }

    # ---- Base de ingresos de ocupados -------------------------------------
    ocup = ind[(ind["ESTADO"] == 1) & (ind["P21"] > 0)].copy()
    x = ocup["P21"].to_numpy(float)
    n = len(x)
    media, s = x.mean(), x.std(ddof=1)
    ee = s / np.sqrt(n)

    # 1 · t para una media: ¿la media difiere de $1.000.000?
    mu0 = 1_000_000
    t1, p1 = stats.ttest_1samp(x, mu0)
    out["t_una_media"] = {
        "mu0": mu0, "n": n, "media": media, "s": s, "ee": ee,
        "t": float(t1), "gl": n - 1, "p": float(p1),
        "d_cohen": float((media - mu0) / s),
        "ic95": [float(media - stats.t.ppf(0.975, n - 1) * ee),
                 float(media + stats.t.ppf(0.975, n - 1) * ee)],
    }

    # 2 · t para dos muestras: ingreso por sexo (CH04: 1 varón, 2 mujer)
    v = ocup.loc[ocup["CH04"] == 1, "P21"].to_numpy(float)
    m = ocup.loc[ocup["CH04"] == 2, "P21"].to_numpy(float)
    tw, pw = stats.ttest_ind(v, m, equal_var=False)
    ts, ps = stats.ttest_ind(v, m, equal_var=True)
    glw = (v.var(ddof=1) / len(v) + m.var(ddof=1) / len(m)) ** 2 / (
        (v.var(ddof=1) / len(v)) ** 2 / (len(v) - 1)
        + (m.var(ddof=1) / len(m)) ** 2 / (len(m) - 1)
    )
    sp = np.sqrt(((len(v) - 1) * v.var(ddof=1) + (len(m) - 1) * m.var(ddof=1))
                 / (len(v) + len(m) - 2))
    out["t_dos_muestras"] = {
        "n_varones": len(v), "n_mujeres": len(m),
        "media_varones": v.mean(), "media_mujeres": m.mean(),
        "s_varones": v.std(ddof=1), "s_mujeres": m.std(ddof=1),
        "diferencia": v.mean() - m.mean(),
        "t_welch": float(tw), "gl_welch": float(glw), "p_welch": float(pw),
        "t_pooled": float(ts), "gl_pooled": len(v) + len(m) - 2,
        "p_pooled": float(ps),
        "d_cohen": float((v.mean() - m.mean()) / sp),
    }

    # 3 · F para dos varianzas (mismo par)
    F = v.var(ddof=1) / m.var(ddof=1)
    gl1, gl2 = len(v) - 1, len(m) - 1
    out["f_varianzas"] = {
        "F": float(F), "gl1": gl1, "gl2": gl2,
        "p": float(2 * min(stats.f.cdf(F, gl1, gl2),
                           stats.f.sf(F, gl1, gl2))),
        "levene_p": float(stats.levene(v, m, center="median").pvalue),
    }

    # ---- Base de asalariados: la tabla de M06 -----------------------------
    a = ind[
        (ind["ESTADO"] == 1) & (ind["CAT_OCUP"] == 3) & (ind["CH06"] >= 18)
        & (ind["PP07H"].isin([1, 2])) & (ind["NIVEL_ED"].between(1, 6))
    ].copy()
    a["sec"] = np.where(a["NIVEL_ED"].isin([4, 5, 6]), 1, 0)
    a["reg"] = np.where(a["PP07H"] == 1, 1, 0)

    tabla = pd.crosstab(a["sec"], a["reg"]).to_numpy()

    # 4 · Chi-cuadrado de independencia
    chi2, pchi, gl, esperado = stats.chi2_contingency(tabla, correction=False)
    chi2c, pchic, _, _ = stats.chi2_contingency(tabla, correction=True)
    N = tabla.sum()
    out["chi2_independencia"] = {
        "tabla": tabla.tolist(),
        "esperado": np.round(esperado, 1).tolist(),
        "n": int(N), "chi2": float(chi2), "gl": int(gl), "p": float(pchi),
        "chi2_yates": float(chi2c), "p_yates": float(pchic),
        "v_cramer": float(np.sqrt(chi2 / (N * (min(tabla.shape) - 1)))),
        "phi": float(np.sqrt(chi2 / N)),
        "odds_ratio": float((tabla[0, 0] * tabla[1, 1])
                            / (tabla[0, 1] * tabla[1, 0])),
    }

    # 5 · Proporción de registrados: una y dos proporciones
    p_reg = a["reg"].mean()
    n_a = len(a)
    p0 = 0.60
    z1 = (p_reg - p0) / np.sqrt(p0 * (1 - p0) / n_a)
    out["z_una_proporcion"] = {
        "n": n_a, "exitos": int(a["reg"].sum()), "p_muestral": float(p_reg),
        "p0": p0, "z": float(z1), "p": float(2 * stats.norm.sf(abs(z1))),
        "ic95": [float(p_reg - 1.96 * np.sqrt(p_reg * (1 - p_reg) / n_a)),
                 float(p_reg + 1.96 * np.sqrt(p_reg * (1 - p_reg) / n_a))],
        "h_cohen": float(2 * np.arcsin(np.sqrt(p_reg))
                         - 2 * np.arcsin(np.sqrt(p0))),
    }

    av = a[a["CH04"] == 1]["reg"]
    am = a[a["CH04"] == 2]["reg"]
    p1_, p2_ = av.mean(), am.mean()
    n1_, n2_ = len(av), len(am)
    pp = (av.sum() + am.sum()) / (n1_ + n2_)
    z2 = (p1_ - p2_) / np.sqrt(pp * (1 - pp) * (1 / n1_ + 1 / n2_))
    out["z_dos_proporciones"] = {
        "n_varones": int(n1_), "n_mujeres": int(n2_),
        "p_varones": float(p1_), "p_mujeres": float(p2_),
        "diferencia": float(p1_ - p2_), "p_combinada": float(pp),
        "z": float(z2), "p": float(2 * stats.norm.sf(abs(z2))),
        "h_cohen": float(2 * np.arcsin(np.sqrt(p1_))
                         - 2 * np.arcsin(np.sqrt(p2_))),
    }

    # 6 · Chi-cuadrado de bondad de ajuste: los 6 niveles educativos
    obs = a["NIVEL_ED"].value_counts().sort_index().to_numpy()
    chi2b, pb = stats.chisquare(obs)
    out["chi2_bondad_ajuste"] = {
        "observado": obs.tolist(),
        "esperado_uniforme": float(obs.sum() / len(obs)),
        "chi2": float(chi2b), "gl": len(obs) - 1, "p": float(pb),
    }

    # 7 · Potencia: qué n hace falta para detectar la brecha por sexo
    d = abs(out["t_dos_muestras"]["d_cohen"])
    for pot in (0.80, 0.90):
        za, zb = stats.norm.ppf(0.975), stats.norm.ppf(pot)
        out.setdefault("potencia", {})[f"n_por_grupo_{int(pot*100)}"] = (
            float(2 * ((za + zb) / d) ** 2)
        )
    out["potencia"]["d_detectable_n100"] = float(
        (stats.norm.ppf(0.975) + stats.norm.ppf(0.80)) * np.sqrt(2 / 100)
    )
    out["potencia"]["d_usado"] = float(d)

    SALIDA.write_text(json.dumps(out, indent=2, ensure_ascii=False),
                      encoding="utf-8")

    def show(titulo, d_):
        print(f"\n--- {titulo}")
        for k, v_ in d_.items():
            if isinstance(v_, float):
                print(f"  {k:22} {v_:,.6g}")
            else:
                print(f"  {k:22} {v_}")

    for k in ("t_una_media", "t_dos_muestras", "f_varianzas",
              "chi2_independencia", "z_una_proporcion", "z_dos_proporciones",
              "chi2_bondad_ajuste", "potencia"):
        show(k, out[k])
    print(f"\n→ {SALIDA}")


if __name__ == "__main__":
    main()

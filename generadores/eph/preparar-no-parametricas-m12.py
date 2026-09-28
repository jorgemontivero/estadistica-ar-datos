#!/usr/bin/env python
"""
Pruebas no paramétricas de referencia para el módulo M12.

Corre sobre la EPH real las pruebas del módulo y, sobre todo, las **compara con
sus equivalentes paramétricas**, que es lo que el módulo necesita mostrar: cuándo
coinciden, cuándo no y por qué.

Incluye las pruebas de normalidad —con el punto central de que con n grande
rechazan siempre—, el efecto de transformar con logaritmo, y un bootstrap de la
mediana del ingreso, que no tiene fórmula cerrada.

Salida: datos/eph/no-parametricas-m12.json

    python datos/eph/preparar-no-parametricas-m12.py
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
SALIDA = Path(__file__).resolve().parent / "no-parametricas-m12.json"
SEMILLA = 2026


def leer(interno: str, columnas: list[str]) -> pd.DataFrame:
    with zipfile.ZipFile(ESPEJO) as z, z.open(interno) as f:
        return pd.read_csv(f, sep=";", decimal=",", usecols=columnas,
                           low_memory=False)


def main() -> None:
    ind = leer("usu_individual_T126.txt",
               ["ESTADO", "NIVEL_ED", "CH04", "CH06", "P21"])

    oc = ind[(ind["ESTADO"] == 1) & (ind["P21"] > 0)].copy()
    ing = oc["P21"].to_numpy(float)
    edad = oc["CH06"].to_numpy(float)
    v = oc.loc[oc["CH04"] == 1, "P21"].to_numpy(float)
    m = oc.loc[oc["CH04"] == 2, "P21"].to_numpy(float)

    rng = np.random.default_rng(SEMILLA)
    out = {
        "fuente": "EPH continua, 1er trimestre de 2026, total aglomerados urbanos",
        "advertencia": "Sin ponderar; el diseño real es por conglomerados.",
        "semilla": SEMILLA,
    }

    # ---- 1 · Normalidad: con n grande rechazan siempre --------------------
    # Shapiro-Wilk admite hasta 5000 casos: se usa una submuestra
    sub_ing = rng.choice(ing, 5000, replace=False)
    sub_edad = rng.choice(edad, 5000, replace=False)

    normalidad = {
        "ingreso": {
            "n_submuestra": 5000,
            "asimetria": float(stats.skew(ing)),
            "curtosis": float(stats.kurtosis(ing)),
            "shapiro_W": float(stats.shapiro(sub_ing).statistic),
            "shapiro_p": float(stats.shapiro(sub_ing).pvalue),
        },
        "edad": {
            "n_submuestra": 5000,
            "asimetria": float(stats.skew(edad)),
            "curtosis": float(stats.kurtosis(edad)),
            "shapiro_W": float(stats.shapiro(sub_edad).statistic),
            "shapiro_p": float(stats.shapiro(sub_edad).pvalue),
        },
    }
    # Con n chico, la misma variable "pasa" la prueba
    por_n = []
    for n in (10, 20, 30, 50, 100, 500, 1000, 5000):
        ps = [float(stats.shapiro(rng.choice(edad, n, replace=False)).pvalue)
              for _ in range(200)]
        por_n.append({"n": n, "prop_rechaza": float(np.mean(np.array(ps) < 0.05))})
    normalidad["edad_rechazo_por_n"] = por_n
    out["normalidad"] = normalidad

    # ---- 2 · Transformación logarítmica ------------------------------------
    log_ing = np.log(ing)
    out["transformacion"] = {
        "asimetria_original": float(stats.skew(ing)),
        "asimetria_log": float(stats.skew(log_ing)),
        "curtosis_original": float(stats.kurtosis(ing)),
        "curtosis_log": float(stats.kurtosis(log_ing)),
        "media_original": float(ing.mean()),
        "mediana_original": float(np.median(ing)),
        "media_geometrica": float(np.exp(log_ing.mean())),
        "shapiro_p_log": float(stats.shapiro(
            rng.choice(log_ing, 5000, replace=False)).pvalue),
    }

    # ---- 3 · Mann-Whitney vs prueba t --------------------------------------
    U, p_u = stats.mannwhitneyu(v, m, alternative="two-sided")
    t, p_t = stats.ttest_ind(v, m, equal_var=False)
    n1, n2 = len(v), len(m)
    # Probabilidad de superioridad: P(X > Y)
    ps = U / (n1 * n2)
    out["mann_whitney"] = {
        "n_varones": n1, "n_mujeres": n2,
        "mediana_varones": float(np.median(v)),
        "mediana_mujeres": float(np.median(m)),
        "U": float(U), "p": float(p_u),
        "prob_superioridad": float(ps),
        "r_efecto": float(abs(stats.norm.isf(p_u / 2)) / np.sqrt(n1 + n2)),
        "t_welch": float(t), "p_t": float(p_t),
    }

    # ---- 4 · Kruskal-Wallis por nivel educativo ---------------------------
    grupos = [oc.loc[oc["NIVEL_ED"] == nv, "P21"].to_numpy(float)
              for nv in range(1, 7)]
    grupos = [g for g in grupos if len(g) > 0]
    H, p_h = stats.kruskal(*grupos)
    F, p_f = stats.f_oneway(*grupos)
    N = sum(len(g) for g in grupos)
    out["kruskal"] = {
        "H": float(H), "gl": len(grupos) - 1, "p": float(p_h),
        "epsilon2": float((H - len(grupos) + 1) / (N - len(grupos))),
        "F_anova": float(F), "p_anova": float(p_f),
        "medianas": [float(np.median(g)) for g in grupos],
    }

    # ---- 5 · Kolmogorov-Smirnov -------------------------------------------
    z = (sub_ing - sub_ing.mean()) / sub_ing.std(ddof=1)
    out["kolmogorov"] = {
        "ks_ingreso_vs_normal_D": float(stats.kstest(z, "norm").statistic),
        "ks_ingreso_vs_normal_p": float(stats.kstest(z, "norm").pvalue),
        "ks_dos_muestras_D": float(stats.ks_2samp(v, m).statistic),
        "ks_dos_muestras_p": float(stats.ks_2samp(v, m).pvalue),
    }

    # ---- 6 · Bootstrap ----------------------------------------------------
    # Tres estadísticos: uno con fórmula (media, para validar el método), uno
    # sin fórmula (CV) y uno donde el bootstrap FALLA (la mediana).
    B = 10000
    idx = rng.integers(0, len(ing), size=(B, len(ing)))
    remuestras = ing[idx]
    medias = remuestras.mean(axis=1)
    medianas = np.median(remuestras, axis=1)
    cvs = remuestras.std(axis=1, ddof=1) / medias

    def resumir(v_, obs):
        return {
            "observado": float(obs),
            "ee_bootstrap": float(v_.std(ddof=1)),
            "ic95_percentil": [float(np.percentile(v_, 2.5)),
                               float(np.percentile(v_, 97.5))],
            "valores_distintos": int(len(np.unique(v_))),
        }

    out["bootstrap"] = {
        "B": B,
        "media": resumir(medias, ing.mean()),
        "cv": resumir(cvs, ing.std(ddof=1) / ing.mean()),
        "mediana": resumir(medianas, np.median(ing)),
        "ee_media_formula": float(ing.std(ddof=1) / np.sqrt(len(ing))),
        "frecuencia_del_valor_mediano": int((ing == np.median(ing)).sum()),
        "prop_en_5_valores_mas_frecuentes": float(
            pd.Series(ing).value_counts().head(5).sum() / len(ing)),
    }

    # ---- 7 · Prueba de permutación ----------------------------------------
    P = 10000
    dif_obs = v.mean() - m.mean()
    juntos = np.concatenate([v, m])
    difs = np.empty(P)
    for i in range(P):
        perm = rng.permutation(juntos)
        difs[i] = perm[:n1].mean() - perm[n1:].mean()
    out["permutacion"] = {
        "P": P,
        "diferencia_observada": float(dif_obs),
        "p": float((np.sum(np.abs(difs) >= abs(dif_obs)) + 1) / (P + 1)),
        "max_dif_permutada": float(np.max(np.abs(difs))),
        "p_t_welch": float(p_t),
    }

    SALIDA.write_text(json.dumps(out, indent=2, ensure_ascii=False),
                      encoding="utf-8")

    print("== Normalidad ==")
    for k, d_ in normalidad.items():
        if k == "edad_rechazo_por_n":
            continue
        print(f"  {k:8} asim {d_['asimetria']:7.3f}  curt {d_['curtosis']:8.3f}  "
              f"W {d_['shapiro_W']:.4f}  p {d_['shapiro_p']:.3e}")
    print("  Edad: proporción de submuestras donde Shapiro rechaza")
    for r in por_n:
        print(f"    n = {r['n']:5}  rechaza {r['prop_rechaza']:5.1%}")

    print("\n== Transformación log ==")
    t_ = out["transformacion"]
    print(f"  asimetría {t_['asimetria_original']:.2f} → {t_['asimetria_log']:.2f}")
    print(f"  curtosis  {t_['curtosis_original']:.2f} → {t_['curtosis_log']:.2f}")
    print(f"  media {t_['media_original']:,.0f} · mediana {t_['mediana_original']:,.0f}"
          f" · media geométrica {t_['media_geometrica']:,.0f}")

    print("\n== Mann-Whitney ==")
    mw = out["mann_whitney"]
    print(f"  medianas {mw['mediana_varones']:,.0f} vs {mw['mediana_mujeres']:,.0f}")
    print(f"  U {mw['U']:,.0f}  p {mw['p']:.3e}  P(X>Y) {mw['prob_superioridad']:.4f}")
    print(f"  (t de Welch {mw['t_welch']:.2f}, p {mw['p_t']:.3e})")

    print("\n== Kruskal-Wallis ==")
    k_ = out["kruskal"]
    print(f"  H {k_['H']:.1f}  gl {k_['gl']}  epsilon² {k_['epsilon2']:.4f}")
    print(f"  medianas {[f'{x:,.0f}' for x in k_['medianas']]}")

    print("\n== Kolmogorov-Smirnov ==")
    for k, v_ in out["kolmogorov"].items():
        print(f"  {k:28} {v_:.6g}")

    print("\n== Bootstrap ==")
    b = out["bootstrap"]
    for k in ("media", "cv", "mediana"):
        r = b[k]
        print(f"  {k:8} obs {r['observado']:>12,.4f}  EE {r['ee_bootstrap']:>12,.4f}"
              f"  IC95 [{r['ic95_percentil'][0]:,.4f} ; "
              f"{r['ic95_percentil'][1]:,.4f}]  valores distintos "
              f"{r['valores_distintos']}")
    print(f"  EE de la media por fórmula: {b['ee_media_formula']:,.1f}")
    print(f"  casos exactamente en el valor mediano: "
          f"{b['frecuencia_del_valor_mediano']:,}")
    print(f"  proporción en los 5 valores más frecuentes: "
          f"{b['prop_en_5_valores_mas_frecuentes']:.1%}")

    print("\n== Permutación ==")
    pm = out["permutacion"]
    print(f"  diferencia observada {pm['diferencia_observada']:,.0f}")
    print(f"  máxima diferencia permutada {pm['max_dif_permutada']:,.0f}")
    print(f"  p = {pm['p']:.6f}   (t de Welch: {pm['p_t_welch']:.3e})")
    print(f"\n→ {SALIDA}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python
"""
ANOVA de referencia para el módulo M11.

El ejemplo del módulo es el **ingreso de la ocupación principal según nivel
educativo**: seis grupos, una variable de respuesta cuantitativa y un factor
ordinal, que es la estructura canónica del ANOVA de un factor.

Calcula la tabla ANOVA completa, los tamaños de efecto (eta² y omega²), las
comparaciones post hoc de Tukey, los supuestos (Levene, Shapiro sobre residuos)
y la alternativa no paramétrica (Kruskal-Wallis), más un ANOVA de dos factores
con nivel educativo y sexo para mostrar la interacción.

Salida: datos/eph/anova-m11.json

    python datos/eph/preparar-anova-m11.py
"""

from __future__ import annotations

import os

import json
import zipfile
from itertools import combinations
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
SALIDA = Path(__file__).resolve().parent / "anova-m11.json"

NIVELES = {
    1: "Primario incompleto",
    2: "Primario completo",
    3: "Secundario incompleto",
    4: "Secundario completo",
    5: "Superior incompleto",
    6: "Superior completo",
}


def leer(interno: str, columnas: list[str]) -> pd.DataFrame:
    with zipfile.ZipFile(ESPEJO) as z, z.open(interno) as f:
        return pd.read_csv(f, sep=";", decimal=",", usecols=columnas,
                           low_memory=False)


def sc_por_tipo(d2: pd.DataFrame) -> dict:
    """Sumas de cuadrados de tipo I en los dos órdenes, y de tipo III.

    Con un diseño desbalanceado la descomposición NO es única: la SC que
    recibe un factor depende de si entró primero o segundo. Es la razón por
    la que dos personas con los mismos datos publican tablas distintas.
    """
    import statsmodels.api as sm
    import statsmodels.formula.api as smf

    def tabla(formula: str, tipo: int) -> dict:
        t = sm.stats.anova_lm(smf.ols(formula, data=d2).fit(), typ=tipo)
        return {i: {"sc": float(r["sum_sq"]), "gl": float(r["df"]),
                    "F": float(r["F"]) if r["F"] == r["F"] else None,
                    "p": float(r["PR(>F)"]) if r["PR(>F)"] == r["PR(>F)"]
                    else None}
                for i, r in t.iterrows()}

    return {
        "tipo_I_educacion_primero": tabla("P21 ~ C(sec) + C(sexo)", 1),
        "tipo_I_sexo_primero": tabla("P21 ~ C(sexo) + C(sec)", 1),
        "tipo_III": tabla("P21 ~ C(sec) + C(sexo)", 3),
    }


def interaccion_por_escala(d2: pd.DataFrame) -> dict:
    """El ANOVA de dos factores con interacción, en pesos y en logaritmos.

    La interacción NO es invariante a la escala: en pesos no da significativa
    y en logaritmos sí, con los mismos datos. Las dos lecturas son correctas
    y contestan preguntas distintas (brecha absoluta contra brecha relativa).
    """
    import statsmodels.api as sm
    import statsmodels.formula.api as smf

    d2 = d2.copy()
    d2["lg"] = np.log(d2["P21"])
    salida = {}
    for var, nombre in (("P21", "pesos"), ("lg", "logaritmo")):
        t = sm.stats.anova_lm(
            smf.ols(f"{var} ~ C(sec)*C(sexo)", data=d2).fit(), typ=3)
        res = float(t.loc["Residual", "sum_sq"])
        salida[nombre] = {
            i: {"sc": float(r["sum_sq"]), "gl": float(r["df"]),
                "F": float(r["F"]) if r["F"] == r["F"] else None,
                "p": float(r["PR(>F)"]) if r["PR(>F)"] == r["PR(>F)"] else None,
                "eta2_parcial": float(r["sum_sq"] / (r["sum_sq"] + res))}
            for i, r in t.iterrows() if i != "Intercept"
        }
    return salida


def welch_anova(grupos: list[np.ndarray], f_clasico: float, ag) -> dict:
    """ANOVA de Welch: F con gl2 de Welch-Satterthwaite.

    OJO: `stats.alexandergovern` NO es el ANOVA de Welch. Es otra prueba,
    con estadístico distribuido chi-cuadrado y no F. Se guarda aparte y con
    su nombre; confundirlas fue un bug de este archivo.
    """
    n = np.array([len(g) for g in grupos], dtype=float)
    m = np.array([g.mean() for g in grupos])
    w = n / np.array([g.var(ddof=1) for g in grupos])
    k = len(grupos)
    media_w = (w * m).sum() / w.sum()
    lam = (((1 - w / w.sum()) ** 2) / (n - 1)).sum()
    num = (w * (m - media_w) ** 2).sum() / (k - 1)
    den = 1 + 2 * (k - 2) / (k ** 2 - 1) * lam
    F = num / den
    gl2 = (k ** 2 - 1) / (3 * lam)
    return {
        "F_clasico": f_clasico,
        "welch_F": float(F),
        "welch_gl1": int(k - 1),
        "welch_gl2": float(gl2),
        "welch_p": float(stats.f.sf(F, k - 1, gl2)),
        "alexander_govern_A": float(ag.statistic),
        "alexander_govern_p": float(ag.pvalue),
    }


def tukey_hsd(grupos: list[np.ndarray], etiquetas: list[str],
              cme: float, gl_dentro: int) -> list[dict]:
    """Comparaciones de Tukey con el rango estudentizado."""
    k = len(grupos)
    out = []
    for i, j in combinations(range(k), 2):
        n1, n2 = len(grupos[i]), len(grupos[j])
        dif = grupos[i].mean() - grupos[j].mean()
        ee = np.sqrt(cme / 2 * (1 / n1 + 1 / n2))
        q = abs(dif) / ee
        p = stats.studentized_range.sf(q, k, gl_dentro)
        out.append({
            "grupo_1": etiquetas[i], "grupo_2": etiquetas[j],
            "diferencia": float(dif), "q": float(q), "p": float(p),
            "significativa": bool(p < 0.05),
        })
    return out


def main() -> None:
    ind = leer("usu_individual_T126.txt",
               ["ESTADO", "NIVEL_ED", "CH04", "CH06", "P21", "PONDERA"])

    d = ind[(ind["ESTADO"] == 1) & (ind["P21"] > 0) & (ind["CH06"] >= 18)
            & (ind["NIVEL_ED"].between(1, 6))].copy()

    grupos, etiquetas, desc = [], [], []
    for nv in sorted(NIVELES):
        x = d.loc[d["NIVEL_ED"] == nv, "P21"].to_numpy(float)
        grupos.append(x)
        etiquetas.append(NIVELES[nv])
        desc.append({
            "nivel": NIVELES[nv], "n": int(len(x)),
            "media": float(x.mean()), "s": float(x.std(ddof=1)),
            "mediana": float(np.median(x)),
        })

    # ---- ANOVA de un factor -----------------------------------------------
    todos = np.concatenate(grupos)
    N, k = len(todos), len(grupos)
    media_gral = todos.mean()

    sc_entre = sum(len(g) * (g.mean() - media_gral) ** 2 for g in grupos)
    sc_dentro = sum(((g - g.mean()) ** 2).sum() for g in grupos)
    sc_total = ((todos - media_gral) ** 2).sum()

    gl_entre, gl_dentro = k - 1, N - k
    cm_entre, cm_dentro = sc_entre / gl_entre, sc_dentro / gl_dentro
    F = cm_entre / cm_dentro
    p = stats.f.sf(F, gl_entre, gl_dentro)

    eta2 = sc_entre / sc_total
    omega2 = (sc_entre - gl_entre * cm_dentro) / (sc_total + cm_dentro)

    out = {
        "fuente": "EPH continua, 1er trimestre de 2026, total aglomerados urbanos",
        "advertencia": "Sin ponderar; el diseño real es por conglomerados.",
        "variable": "Ingreso de la ocupación principal",
        "factor": "Nivel educativo (6 niveles)",
        "descriptivos": desc,
        "media_general": float(media_gral),
        "anova": {
            "N": int(N), "k": int(k),
            "sc_entre": float(sc_entre), "sc_dentro": float(sc_dentro),
            "sc_total": float(sc_total),
            "gl_entre": int(gl_entre), "gl_dentro": int(gl_dentro),
            "cm_entre": float(cm_entre), "cm_dentro": float(cm_dentro),
            "F": float(F), "p": float(p),
            "eta2": float(eta2), "omega2": float(omega2),
        },
        "supuestos": {
            "levene_p": float(stats.levene(*grupos, center="median").pvalue),
            "bartlett_p": float(stats.bartlett(*grupos).pvalue),
            "razon_var_max_min": float(
                max(g.var(ddof=1) for g in grupos)
                / min(g.var(ddof=1) for g in grupos)),
            "asimetria_residuos": float(stats.skew(
                np.concatenate([g - g.mean() for g in grupos]))),
        },
        "welch": welch_anova(grupos, float(stats.f_oneway(*grupos).statistic),
                             stats.alexandergovern(*grupos)),
        "kruskal": {
            "H": float(stats.kruskal(*grupos).statistic),
            "p": float(stats.kruskal(*grupos).pvalue),
            "gl": int(k - 1),
        },
        "tukey": tukey_hsd(grupos, etiquetas, cm_dentro, gl_dentro),
    }

    # ---- ANOVA de dos factores: educación x sexo ---------------------------
    d2 = d[d["CH04"].isin([1, 2])].copy()
    d2["sec"] = np.where(d2["NIVEL_ED"].isin([4, 5, 6]),
                         "Secundario+", "Hasta sec. inc.")
    d2["sexo"] = np.where(d2["CH04"] == 1, "Varón", "Mujer")

    celdas = []
    for a in ["Hasta sec. inc.", "Secundario+"]:
        for b in ["Varón", "Mujer"]:
            x = d2.loc[(d2["sec"] == a) & (d2["sexo"] == b), "P21"]
            celdas.append({"educacion": a, "sexo": b, "n": int(len(x)),
                           "media": float(x.mean())})
    out["dos_factores"] = {
        "celdas": celdas,
        "brecha_sin_secundario": float(
            celdas[0]["media"] - celdas[1]["media"]),
        "brecha_con_secundario": float(
            celdas[2]["media"] - celdas[3]["media"]),
        "sumas_de_cuadrados": sc_por_tipo(d2),
        "con_interaccion": interaccion_por_escala(d2),
    }

    SALIDA.write_text(json.dumps(out, indent=2, ensure_ascii=False),
                      encoding="utf-8")

    print(f"{'Nivel':24} {'n':>6} {'media':>12} {'desvío':>12}")
    for g in desc:
        print(f"  {g['nivel']:22} {g['n']:6,} {g['media']:12,.0f} "
              f"{g['s']:12,.0f}")
    print(f"\nMedia general: {media_gral:,.0f}")
    print("\nTabla ANOVA")
    a = out["anova"]
    print(f"  Entre grupos   SC {a['sc_entre']:.4e}  gl {a['gl_entre']:>6}  "
          f"CM {a['cm_entre']:.4e}  F {a['F']:.2f}")
    print(f"  Dentro         SC {a['sc_dentro']:.4e}  gl {a['gl_dentro']:>6}  "
          f"CM {a['cm_dentro']:.4e}")
    print(f"  Total          SC {a['sc_total']:.4e}  gl {a['gl_entre']+a['gl_dentro']:>6}")
    print(f"  p = {a['p']:.3e}   eta² = {a['eta2']:.4f}   omega² = {a['omega2']:.4f}")
    print("\nSupuestos:", {k_: round(v, 4) if isinstance(v, float) else v
                           for k_, v in out["supuestos"].items()})
    print("Kruskal-Wallis:", round(out["kruskal"]["H"], 1),
          f"p = {out['kruskal']['p']:.3e}")
    print("\nTukey (15 pares):")
    for t in out["tukey"]:
        marca = "*" if t["significativa"] else " "
        print(f" {marca} {t['grupo_1'][:20]:22} vs {t['grupo_2'][:20]:22} "
              f"dif {t['diferencia']:>12,.0f}  p {t['p']:.4f}")
    print("\nDos factores:")
    for c in celdas:
        print(f"  {c['educacion']:18} {c['sexo']:6} n={c['n']:5,} "
              f"media {c['media']:,.0f}")
    print(f"  brecha sin secundario: {out['dos_factores']['brecha_sin_secundario']:,.0f}")
    print(f"  brecha con secundario: {out['dos_factores']['brecha_con_secundario']:,.0f}")
    print(f"\n→ {SALIDA}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python
"""
Matriz multivariada de referencia para el módulo M14.

Construye una tabla de **aglomerados x indicadores** con la EPH: cada fila es uno
de los 31 aglomerados urbanos y cada columna un indicador socioeconómico. Sobre
esa matriz corre todo lo que el módulo explica:

  · matriz de correlaciones
  · estandarización
  · componentes principales, con varianza explicada y cargas
  · conglomerados jerárquicos (Ward) y k-medias
  · un índice sintético construido con el primer componente

Es el conjunto ideal para el módulo porque tiene pocas filas —se pueden mirar
todas—, variables en unidades muy distintas —lo que obliga a estandarizar— y
grupos que se reconocen sin necesidad de saber estadística.

Salida: datos/eph/multivariado-m14.json
        src/figuras/pca-aglomerados.svg
        src/figuras/dendrograma-aglomerados.svg

    python datos/eph/preparar-multivariado-m14.py
"""

from __future__ import annotations

import os

import io
import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import dendrogram, fcluster, linkage
from scipy.spatial.distance import pdist, squareform


# La carpeta con los microdatos públicos. No se versionan: cada fuente se
# baja de su organismo. La variable de entorno DATOS_AR permite moverla.
DATOS = os.environ.get("DATOS_AR", "datos-fuente")

EPH = Path(
    DATOS + r"\INDEC\EPH\01_microdatos_eph"
    r"\2026\EPH_usu_1_Trim_2026_txt.zip"
)
CARTO = Path(
    DATOS + r"\INDEC\EPH\04_cartografia_eph"
    r"\aglomerados_eph_json.zip"
)
AQUI = Path(__file__).resolve().parent
SALIDA = AQUI / "multivariado-m14.json"
FIGURAS = AQUI.parent.parent / "src" / "figuras"
SEMILLA = 2026


def nombres_aglomerados() -> dict[int, str]:
    import io as _io
    with zipfile.ZipFile(CARTO) as z:
        n = [x for x in z.namelist() if x.endswith(".json")][0]
        g = json.load(_io.TextIOWrapper(z.open(n), encoding="utf-8"))
    feats = g["features"] if isinstance(g, dict) and "features" in g else g
    return {int(f["properties"]["eph_codagl"]): f["properties"]["eph_aglome"]
            for f in feats if f["properties"].get("eph_codagl")}


def gini(x, w):
    o = np.argsort(x)
    x, w = x[o], w[o]
    wx = w * x
    p = np.cumsum(w) / w.sum()
    q = np.cumsum(wx) / wx.sum()
    return float(1 - np.sum((q[1:] + q[:-1]) * np.diff(p)))


def cuantil_ponderado(x, w, q):
    o = np.argsort(x)
    x, w = x[o], w[o]
    p = (np.cumsum(w) - 0.5 * w) / w.sum()
    return float(np.interp(q, p, x))


def dibujar_pca(nombres, puntajes, prop, grupos) -> None:
    """Dispersión de los aglomerados en el plano de los dos primeros CP."""
    W, H = 720, 460
    ML, MR, MT, MB = 62, 20, 30, 52
    x, y = puntajes[:, 0], puntajes[:, 1]
    mx = max(abs(x).max(), 0.1) * 1.18
    my = max(abs(y).max(), 0.1) * 1.18

    def px(v):
        return ML + (v + mx) / (2 * mx) * (W - ML - MR)

    def py(v):
        return H - MB - (v + my) / (2 * my) * (H - MT - MB)

    op = {1: 0.22, 2: 0.75, 3: 0.45}
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
         f'class="grafico" role="img" '
         f'aria-label="Aglomerados en el plano de los dos primeros componentes">']
    p.append(f'<line class="guia" x1="{px(0):.1f}" y1="{MT}" '
             f'x2="{px(0):.1f}" y2="{H-MB}"/>')
    p.append(f'<line class="guia" x1="{ML}" y1="{py(0):.1f}" '
             f'x2="{W-MR}" y2="{py(0):.1f}"/>')
    for i, n in enumerate(nombres):
        g = int(grupos[i])
        p.append(f'<circle class="barra" style="opacity:{op.get(g, .4)}" '
                 f'cx="{px(x[i]):.1f}" cy="{py(y[i]):.1f}" r="5"/>')
        corto = n.split(" - ")[0][:18]
        anchor = "start" if x[i] < mx * 0.45 else "end"
        dx = 8 if anchor == "start" else -8
        p.append(f'<text class="rotulo-chico" x="{px(x[i])+dx:.1f}" '
                 f'y="{py(y[i])+3.5:.1f}" text-anchor="{anchor}">{corto}</text>')
    p.append(f'<line class="eje" x1="{ML}" y1="{H-MB}" x2="{W-MR}" '
             f'y2="{H-MB}"/>')
    p.append(f'<text class="rotulo" x="{(ML+W-MR)/2:.0f}" y="{H-14}" '
             f'text-anchor="middle">Componente 1 ({prop[0]:.1%} de la '
             f'varianza)</text>')
    p.append(f'<text class="rotulo" x="{ML}" y="{MT-10}" text-anchor="start">'
             f'Componente 2 ({prop[1]:.1%})</text>')
    p.append("</svg>")
    (FIGURAS / "pca-aglomerados.svg").write_text("\n".join(p), encoding="utf-8")
    print(f"\n→ {FIGURAS / 'pca-aglomerados.svg'}")


def dibujar_correspondencias(nom_filas, F, nom_cols, G, prop) -> None:
    """Mapa del análisis de correspondencias: filas y columnas en un plano."""
    W, H = 720, 470
    ML, MR, MT, MB = 62, 20, 30, 52
    xs = np.r_[F[:, 0], G[:, 0]]
    ys = np.r_[F[:, 1], G[:, 1]]
    mx = max(abs(xs).max(), 0.05) * 1.20
    my = max(abs(ys).max(), 0.05) * 1.25

    def px(v):
        return ML + (v + mx) / (2 * mx) * (W - ML - MR)

    def py(v):
        return H - MB - (v + my) / (2 * my) * (H - MT - MB)

    p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
         f'class="grafico" role="img" '
         f'aria-label="Mapa de correspondencias entre aglomerados y '
         f'calificación de la tarea">']
    p.append(f'<line class="guia" x1="{px(0):.1f}" y1="{MT}" '
             f'x2="{px(0):.1f}" y2="{H-MB}"/>')
    p.append(f'<line class="guia" x1="{ML}" y1="{py(0):.1f}" '
             f'x2="{W-MR}" y2="{py(0):.1f}"/>')
    # Filas: los aglomerados, en gris
    for i, n in enumerate(nom_filas):
        p.append(f'<circle class="barra" style="opacity:.30" '
                 f'cx="{px(F[i,0]):.1f}" cy="{py(F[i,1]):.1f}" r="4"/>')
        corto = n.split(" - ")[0][:16]
        anchor = "start" if F[i, 0] < mx * 0.40 else "end"
        dx = 7 if anchor == "start" else -7
        p.append(f'<text class="rotulo-chico" x="{px(F[i,0])+dx:.1f}" '
                 f'y="{py(F[i,1])+3.5:.1f}" text-anchor="{anchor}">{corto}</text>')
    # Columnas: las calificaciones, destacadas
    for j, n in enumerate(nom_cols):
        p.append(f'<circle class="barra" style="opacity:.95" '
                 f'cx="{px(G[j,0]):.1f}" cy="{py(G[j,1]):.1f}" r="7"/>')
        anchor = "start" if G[j, 0] < 0 else "end"
        dx = 11 if anchor == "start" else -11
        p.append(f'<text class="rotulo" x="{px(G[j,0])+dx:.1f}" '
                 f'y="{py(G[j,1])+4:.1f}" text-anchor="{anchor}">{n}</text>')
    p.append(f'<line class="eje" x1="{ML}" y1="{H-MB}" x2="{W-MR}" '
             f'y2="{H-MB}"/>')
    p.append(f'<text class="rotulo" x="{(ML+W-MR)/2:.0f}" y="{H-14}" '
             f'text-anchor="middle">Dimensión 1 ({prop[0]:.1%} de la '
             f'inercia)</text>')
    p.append(f'<text class="rotulo" x="{ML}" y="{MT-10}" text-anchor="start">'
             f'Dimensión 2 ({prop[1]:.1%})</text>')
    p.append("</svg>")
    (FIGURAS / "correspondencias-calificacion.svg").write_text(
        "\n".join(p), encoding="utf-8")
    print(f"→ {FIGURAS / 'correspondencias-calificacion.svg'}")


def dibujar_mds(nombres, Y) -> None:
    """El mapa reconstruido por MDS a partir de la tabla de distancias."""
    W, H = 520, 620
    ML, MR, MT, MB = 20, 20, 24, 24
    x, y = Y[:, 0], Y[:, 1]
    mx = max(abs(x).max(), 1.0) * 1.12
    my = max(abs(y).max(), 1.0) * 1.06

    def px(v):
        return ML + (v + mx) / (2 * mx) * (W - ML - MR)

    def py(v):
        return H - MB - (v + my) / (2 * my) * (H - MT - MB)

    p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
         f'class="grafico" role="img" '
         f'aria-label="Mapa de los 32 aglomerados reconstruido por escalamiento '
         f'multidimensional a partir de la tabla de distancias">']
    for i, n in enumerate(nombres):
        p.append(f'<circle class="barra" style="opacity:.70" '
                 f'cx="{px(x[i]):.1f}" cy="{py(y[i]):.1f}" r="4"/>')
        corto = n.split(" - ")[0][:17]
        anchor = "start" if x[i] < mx * 0.25 else "end"
        dx = 7 if anchor == "start" else -7
        p.append(f'<text class="rotulo-chico" x="{px(x[i])+dx:.1f}" '
                 f'y="{py(y[i])+3.5:.1f}" text-anchor="{anchor}">{corto}</text>')
    p.append("</svg>")
    (FIGURAS / "mds-aglomerados.svg").write_text("\n".join(p), encoding="utf-8")
    print(f"→ {FIGURAS / 'mds-aglomerados.svg'}")


def dibujar_dendrograma(nombres, Lk) -> None:
    """Dendrograma horizontal a partir del linkage de scipy."""
    d = dendrogram(Lk, labels=list(nombres), no_plot=True,
                   orientation="left")
    W, H = 720, 560
    ML, MR, MT, MB = 12, 190, 20, 40
    xs = [v for seg in d["dcoord"] for v in seg]
    ys = [v for seg in d["icoord"] for v in seg]
    x1 = max(xs) * 1.02
    y0, y1 = min(ys), max(ys)

    def px(v):
        return W - MR - v / x1 * (W - ML - MR)

    def py(v):
        return MT + (v - y0) / (y1 - y0) * (H - MT - MB)

    p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
         f'class="grafico" role="img" aria-label="Dendrograma de aglomerados">']
    for xc, yc in zip(d["dcoord"], d["icoord"]):
        pts = " ".join(f"{px(a):.1f},{py(b):.1f}" for a, b in zip(xc, yc))
        p.append(f'<polyline class="bigote" fill="none" points="{pts}"/>')
    for i, etq in enumerate(d["ivl"]):
        yv = py(5 + i * 10)
        p.append(f'<text class="rotulo-chico" x="{W-MR+8}" y="{yv+3.5:.1f}" '
                 f'text-anchor="start">{etq[:26]}</text>')
    p.append(f'<text class="rotulo" x="{ML+10}" y="{H-12}" '
             f'text-anchor="start">← Distancia de fusión (Ward)</text>')
    p.append("</svg>")
    (FIGURAS / "dendrograma-aglomerados.svg").write_text("\n".join(p),
                                                         encoding="utf-8")
    print(f"→ {FIGURAS / 'dendrograma-aglomerados.svg'}")


def main() -> None:
    NOM = nombres_aglomerados()
    with zipfile.ZipFile(EPH) as z, z.open("usu_individual_T126.txt") as f:
        ind = pd.read_csv(f, sep=";", decimal=",", low_memory=False,
                          usecols=["AGLOMERADO", "CH04", "CH06", "NIVEL_ED",
                                   "ESTADO", "CAT_OCUP", "PP07H", "P21",
                                   "PP04D_COD", "PONDERA", "PONDIIO"])

    filas = []
    for ag, d in ind.groupby("AGLOMERADO"):
        w = d["PONDERA"].to_numpy(float)
        pea = d[d["ESTADO"].isin([1, 2]) & (d["CH06"] >= 15)]
        ocup = d[d["ESTADO"] == 1]
        con_ing = d[(d["ESTADO"] == 1) & (d["P21"] > 0)]
        adultos = d[d["CH06"] >= 18]
        asal = d[(d["ESTADO"] == 1) & (d["CAT_OCUP"] == 3)
                 & (d["PP07H"].isin([1, 2]))]
        if len(con_ing) < 80 or len(asal) < 60:
            continue

        x = con_ing["P21"].to_numpy(float)
        wi = con_ing["PONDIIO"].to_numpy(float)
        wi = np.where(wi > 0, wi, 1.0)

        filas.append({
            "aglomerado": int(ag),
            "nombre": NOM.get(int(ag), str(ag)),
            "n": int(len(d)),
            "desocupacion": float(
                (pea["PONDERA"] * (pea["ESTADO"] == 2)).sum()
                / pea["PONDERA"].sum() * 100),
            "empleo": float(ocup["PONDERA"].sum() / w.sum() * 100),
            "actividad": float(pea["PONDERA"].sum() / w.sum() * 100),
            "ingreso_medio": float((x * wi).sum() / wi.sum()),
            "ingreso_mediano": cuantil_ponderado(x, wi, 0.5),
            "gini": gini(x, wi),
            "secundario_mas": float(
                (adultos["PONDERA"] * adultos["NIVEL_ED"].isin([4, 5, 6])).sum()
                / adultos["PONDERA"].sum() * 100),
            "no_registrado": float(
                (asal["PONDERA"] * (asal["PP07H"] == 2)).sum()
                / asal["PONDERA"].sum() * 100),
            "edad_media": float((d["CH06"] * w).sum() / w.sum()),
            "prop_65_mas": float(
                (w * (d["CH06"] >= 65)).sum() / w.sum() * 100),
        })

    df = pd.DataFrame(filas).set_index("nombre").sort_index()
    VARS = ["desocupacion", "empleo", "actividad", "ingreso_medio",
            "ingreso_mediano", "gini", "secundario_mas", "no_registrado",
            "edad_media", "prop_65_mas"]
    X = df[VARS].to_numpy(float)

    # ---- Correlaciones -----------------------------------------------------
    R = np.corrcoef(X, rowvar=False)
    pares = []
    for i in range(len(VARS)):
        for j in range(i + 1, len(VARS)):
            pares.append({"a": VARS[i], "b": VARS[j], "r": float(R[i, j])})
    pares.sort(key=lambda p: -abs(p["r"]))

    # ---- Estandarización y PCA --------------------------------------------
    medias = X.mean(axis=0)
    desvios = X.std(axis=0, ddof=1)
    Z = (X - medias) / desvios

    C = np.cov(Z, rowvar=False)
    valores, vectores = np.linalg.eigh(C)
    orden = np.argsort(valores)[::-1]
    valores, vectores = valores[orden], vectores[:, orden]
    # Signo convencional: que la primera carga grande sea positiva
    for k in range(vectores.shape[1]):
        if vectores[np.argmax(np.abs(vectores[:, k])), k] < 0:
            vectores[:, k] *= -1
    puntajes = Z @ vectores
    prop = valores / valores.sum()

    # ---- Conglomerados -----------------------------------------------------
    D = pdist(Z, metric="euclidean")
    Lk = linkage(D, method="ward")
    grupos = {k: fcluster(Lk, k, criterion="maxclust") for k in (2, 3, 4)}

    rng = np.random.default_rng(SEMILLA)
    def kmedias(Z, k, iters=200, reps=50):
        """k-medias con varios arranques: con uno solo la inercia queda hasta
        un 34 % por encima del óptimo, que es justo el error que advierte la
        entrada de k-medias."""
        mejor = None
        for _ in range(reps):
            cent = Z[rng.choice(len(Z), k, replace=False)].copy()
            for _ in range(iters):
                d = ((Z[:, None, :] - cent[None, :, :]) ** 2).sum(axis=2)
                asig = d.argmin(axis=1)
                nuevos = np.array([Z[asig == j].mean(axis=0)
                                   if (asig == j).any() else cent[j]
                                   for j in range(k)])
                if np.allclose(nuevos, cent):
                    break
                cent = nuevos
            inercia = float(((Z - cent[asig]) ** 2).sum())
            if mejor is None or inercia < mejor[2]:
                mejor = (asig, cent, inercia)
        return mejor

    codo = {}
    for k in range(1, 7):
        if k == 1:
            codo[k] = float(((Z - Z.mean(axis=0)) ** 2).sum())
        else:
            codo[k] = kmedias(Z, k)[2]
    asig3, _, _ = kmedias(Z, 3)

    out = {
        "fuente": "EPH continua, 1er trimestre de 2026, INDEC",
        "advertencia": "Sin ponderar entre aglomerados; cada indicador sí usa ponderadores.",
        "semilla": SEMILLA,
        "n_aglomerados": int(len(df)),
        "variables": VARS,
        "datos": df.reset_index().to_dict("records"),
        "medias": {v: float(m) for v, m in zip(VARS, medias)},
        "desvios": {v: float(s) for v, s in zip(VARS, desvios)},
        "correlaciones_extremas": pares[:8],
        "pca": {
            "valores_propios": [float(v) for v in valores],
            "prop_varianza": [float(p) for p in prop],
            "prop_acumulada": [float(p) for p in np.cumsum(prop)],
            "n_componentes_kaiser": int((valores > 1).sum()),
            "cargas_cp1": {v: float(c) for v, c in zip(VARS, vectores[:, 0])},
            "cargas_cp2": {v: float(c) for v, c in zip(VARS, vectores[:, 1])},
            "puntajes": {n: [float(puntajes[i, 0]), float(puntajes[i, 1])]
                         for i, n in enumerate(df.index)},
        },
        "clusters": {
            "metodo": "Ward sobre distancia euclídea de variables estandarizadas",
            "grupos_3": {n: int(g) for n, g in zip(df.index, grupos[3])},
            "kmedias_3": {n: int(g) for n, g in zip(df.index, asig3)},
            "codo": {int(k): v for k, v in codo.items()},
        },
    }

    # Perfil de cada grupo
    df2 = df.copy()
    df2["grupo"] = grupos[3]
    out["clusters"]["perfil_3"] = {
        int(g): {"n": int(len(s)),
                 "aglomerados": list(s.index),
                 **{v: float(s[v].mean()) for v in VARS}}
        for g, s in df2.groupby("grupo")
    }

    # ---- Línea de base: qué devuelven estas técnicas con ruido puro --------
    # Ninguna técnica multivariada sabe decir "acá no hay estructura". La única
    # forma de leer una salida es contra lo que la MISMA técnica devuelve sobre
    # una matriz del mismo tamaño y sin ninguna estructura.
    n_obs, p_var = Z.shape
    rb = np.random.default_rng(SEMILLA + 1)

    def vp(M):
        """Valores propios de la matriz de correlaciones, de mayor a menor."""
        Zs = (M - M.mean(axis=0)) / M.std(axis=0, ddof=1)
        return np.sort(np.linalg.eigvalsh(np.corrcoef(Zs.T)))[::-1]

    def silueta(M, asig):
        D = np.sqrt(((M[:, None, :] - M[None, :, :]) ** 2).sum(axis=2))
        s = np.empty(len(M))
        for i in range(len(M)):
            propio = asig == asig[i]
            if propio.sum() <= 1:
                s[i] = 0.0
                continue
            a = D[i, propio].sum() / (propio.sum() - 1)
            b = min(D[i, asig == g].mean()
                    for g in np.unique(asig) if g != asig[i])
            s[i] = (b - a) / max(a, b)
        return float(s.mean())

    def kmedias_rep(M, k, rng, reps=25):
        """k-medias con varios arranques; se queda con el de menor inercia."""
        mejor, mejor_in = None, np.inf
        for _ in range(reps):
            cent = M[rng.choice(len(M), k, replace=False)].copy()
            for _ in range(200):
                asig = ((M[:, None, :] - cent[None, :, :]) ** 2).sum(axis=2).argmin(axis=1)
                nuevos = np.array([M[asig == j].mean(axis=0) if (asig == j).any()
                                   else cent[j] for j in range(k)])
                if np.allclose(nuevos, cent):
                    break
                cent = nuevos
            inercia = ((M - cent[asig]) ** 2).sum()
            if inercia < mejor_in:
                mejor, mejor_in = asig, inercia
        return mejor

    REP_RUIDO = 20_000
    ev_ruido = np.empty((REP_RUIDO, p_var))
    max_r_ruido = np.empty(REP_RUIDO)
    for i in range(REP_RUIDO):
        Rn = np.corrcoef(rb.normal(size=(n_obs, p_var)).T)
        ev_ruido[i] = np.sort(np.linalg.eigvalsh(Rn))[::-1]
        max_r_ruido[i] = np.abs(Rn[np.triu_indices(p_var, 1)]).max()

    REP_SIL = 2_000
    sil_real, sil_ruido = {}, {}
    for k in (2, 3, 4, 5):
        sil_real[k] = silueta(Z, kmedias_rep(Z, k, np.random.default_rng(SEMILLA + 2)))
        sims = [silueta(Mn, kmedias_rep(Mn, k, rb))
                for Mn in (rb.normal(size=(n_obs, p_var)) for _ in range(REP_SIL))]
        sil_ruido[k] = (float(np.mean(sims)), float(np.percentile(sims, 95)))

    max_r_real = float(max(abs(p["r"]) for p in pares))
    out["linea_de_base"] = {
        "descripcion": (f"{REP_RUIDO} matrices de {n_obs}x{p_var} de ruido normal "
                        "independiente: la misma forma que la matriz del caso."),
        "repeticiones": REP_RUIDO,
        "cp1_prop_ruido": float(ev_ruido[:, 0].mean() / p_var),
        "cp1_prop_real": float(valores[0] / p_var),
        "acum2_ruido": float(ev_ruido[:, :2].sum(axis=1).mean() / p_var),
        "acum4_ruido": float(ev_ruido[:, :4].sum(axis=1).mean() / p_var),
        "kaiser_ruido_medio": float((ev_ruido > 1).sum(axis=1).mean()),
        "kaiser_ruido_p_mayor_igual_4": float(((ev_ruido > 1).sum(axis=1) >= 4).mean()),
        "max_r_ruido_medio": float(max_r_ruido.mean()),
        "max_r_ruido_supera_050": float((max_r_ruido > 0.50).mean()),
        "max_r_ruido_supera_060": float((max_r_ruido > 0.60).mean()),
        "max_r_real": max_r_real,
        # Análisis paralelo: componente por componente contra el p95 del ruido
        "paralelo": [
            {"cp": j + 1,
             "real": float(valores[j]),
             "ruido_medio": float(ev_ruido[:, j].mean()),
             "ruido_p95": float(np.percentile(ev_ruido[:, j], 95)),
             "supera": bool(valores[j] > np.percentile(ev_ruido[:, j], 95))}
            for j in range(p_var)
        ],
        "n_componentes_paralelo": int(sum(
            valores[j] > np.percentile(ev_ruido[:, j], 95) for j in range(p_var))),
        "silueta": {int(k): {"real": sil_real[k],
                             "ruido_medio": sil_ruido[k][0],
                             "ruido_p95": sil_ruido[k][1]} for k in sil_real},
        "repeticiones_silueta": REP_SIL,
    }

    # ---- Sin estandarizar: la escala se come el análisis -------------------
    ev_cov, vec_cov = np.linalg.eigh(np.cov(df[VARS].to_numpy(float).T))
    w1 = vec_cov[:, -1]
    out["sin_estandarizar"] = {
        "cp1_prop": float(ev_cov[-1] / ev_cov.sum()),
        "cargas_cp1": {v: float(abs(c)) for v, c in zip(VARS, w1)},
        "cp1_prop_estandarizado": float(valores[0] / p_var),
    }

    # ---- La matriz por dentro: parciales, singularidad, KMO y Bartlett -----
    Rm = np.corrcoef(Z.T)
    iu = np.triu_indices(len(VARS), 1)
    Pinv = np.linalg.inv(Rm)
    Rpar = -Pinv / np.sqrt(np.outer(np.diag(Pinv), np.diag(Pinv)))
    np.fill_diagonal(Rpar, 1.0)

    def kmo_de(R):
        Pi = np.linalg.inv(R)
        A = -Pi / np.sqrt(np.outer(np.diag(Pi), np.diag(Pi)))
        np.fill_diagonal(A, 0.0)
        Rc = R.copy()
        np.fill_diagonal(Rc, 0.0)
        return float((Rc ** 2).sum() / ((Rc ** 2).sum() + (A ** 2).sum()))

    from scipy import stats as _st
    q = len(VARS)
    chi_b = float(-(len(df) - 1 - (2 * q + 5) / 6) * np.log(np.linalg.det(Rm)))
    gl_b = q * (q - 1) / 2

    # "empleo = actividad x (1 - desocupación/100)" es una identidad contable:
    # una de las diez variables no es una variable.
    emp = df["empleo"].to_numpy(float)
    pred_emp = df["actividad"].to_numpy(float) * (1 - df["desocupacion"].to_numpy(float) / 100)

    # Sacar un aglomerado a la vez: cuánto se mueve la correlación que más se mueve.
    sensibilidad = []
    for k in range(len(df)):
        Y = np.delete(df[VARS].to_numpy(float), k, axis=0)
        Rk = np.corrcoef(((Y - Y.mean(axis=0)) / Y.std(axis=0, ddof=1)).T)
        dif = np.abs(Rk[iu] - Rm[iu])
        jm = int(np.argmax(dif))
        sensibilidad.append({
            "aglomerado": df.index[k],
            "par": [VARS[iu[0][jm]], VARS[iu[1][jm]]],
            "r_con": float(Rm[iu[0][jm], iu[1][jm]]),
            "r_sin": float(Rk[iu[0][jm], iu[1][jm]]),
            "cambio": float(dif[jm]),
        })
    sensibilidad.sort(key=lambda s: -s["cambio"])

    out["matriz"] = {
        "n_correlaciones": int(len(iu[0])),
        "abs_r_medio": float(np.abs(Rm[iu]).mean()),
        "abs_parcial_medio": float(np.abs(Rpar[iu]).mean()),
        "abs_r_maximo": float(np.abs(Rm[iu]).max()),
        "abs_parcial_maximo": float(np.abs(Rpar[iu]).max()),
        "cambian_de_signo": int((np.sign(Rm[iu]) != np.sign(Rpar[iu])).sum()),
        "pares": [
            {"a": VARS[iu[0][k]], "b": VARS[iu[1][k]],
             "r": float(Rm[iu[0][k], iu[1][k]]),
             "parcial": float(Rpar[iu[0][k], iu[1][k]])}
            for k in np.argsort(-np.abs(Rm[iu]))[:8]
        ],
        "determinante": float(np.linalg.det(Rm)),
        "valor_propio_minimo": float(np.sort(np.linalg.eigvalsh(Rm))[0]),
        "numero_condicion": float(np.sort(np.linalg.eigvalsh(Rm))[-1]
                                  / np.sort(np.linalg.eigvalsh(Rm))[0]),
        "vif": {v: float(Pinv[i, i]) for i, v in enumerate(VARS)},
        "kmo": kmo_de(Rm),
        "bartlett": {"chi2": chi_b, "gl": gl_b,
                     "p": float(_st.chi2.sf(chi_b, gl_b))},
        "identidad_empleo": {
            "formula": "empleo = actividad x (1 - desocupacion/100)",
            "error_maximo_pp": float(np.abs(pred_emp - emp).max()),
            "error_medio_pp": float(np.abs(pred_emp - emp).mean()),
            "correlacion": float(np.corrcoef(pred_emp, emp)[0, 1]),
        },
        "sensibilidad_top3": sensibilidad[:3],
        "sensibilidad_cambio_medio": float(np.mean([s["cambio"] for s in sensibilidad])),
    }
    # La misma matriz sin la variable redundante, para mostrar qué se arregla.
    sin_emp = [i for i, v in enumerate(VARS) if v != "empleo"]
    Rs = Rm[np.ix_(sin_emp, sin_emp)]
    out["matriz"]["sin_empleo"] = {
        "determinante": float(np.linalg.det(Rs)),
        "vif_maximo": float(np.diag(np.linalg.inv(Rs)).max()),
        "kmo": kmo_de(Rs),
    }

    # ---- ¿Cambia el resultado según qué escalador se use? ------------------
    # "Estandarizá" se dice como si la forma de hacerlo diera igual. Para el
    # PCA casi da igual; para los conglomerados, no.
    Xm0 = df[VARS].to_numpy(float)

    def escalar(M, modo):
        if modo == "sin escalar":
            return M.copy()
        if modo == "z":
            return (M - M.mean(axis=0)) / M.std(axis=0, ddof=1)
        if modo == "min-max":
            return (M - M.min(axis=0)) / (M.max(axis=0) - M.min(axis=0))
        q1, q3 = np.percentile(M, [25, 75], axis=0)
        return (M - np.median(M, axis=0)) / (q3 - q1)

    def cp1_cov(M):
        u = np.linalg.eigh(np.cov((M - M.mean(axis=0)).T))[1][:, -1]
        return u * np.sign(u[np.argmax(np.abs(u))])

    def ari(a, b):
        """Índice de Rand ajustado, sin dependencias externas."""
        ea, eb = np.unique(a), np.unique(b)
        T = np.array([[np.sum((a == i) & (b == j)) for j in eb] for i in ea])
        c2 = lambda v: v * (v - 1) / 2
        s_ij = c2(T).sum()
        s_a, s_b = c2(T.sum(axis=1)).sum(), c2(T.sum(axis=0)).sum()
        tot = c2(np.array(float(len(a))))
        esp = s_a * s_b / tot
        return float((s_ij - esp) / ((s_a + s_b) / 2 - esp))

    MODOS = ("sin escalar", "z", "min-max", "robusta")
    u_ref = cp1_cov(escalar(Xm0, "z"))
    g_ref = fcluster(linkage(pdist(escalar(Xm0, "z")), "ward"), 3, "maxclust")
    comparacion = {}
    for modo in MODOS:
        M = escalar(Xm0, modo)
        ev_m = np.sort(np.linalg.eigvalsh(np.cov(M.T)))[::-1]
        u = cp1_cov(M)
        if u @ u_ref < 0:
            u = -u
        g = fcluster(linkage(pdist(M), "ward"), 3, "maxclust")
        comparacion[modo] = {
            "cp1_prop": float(ev_m[0] / ev_m.sum()),
            "congruencia_cp1_con_z": float((u @ u_ref) / np.sqrt((u @ u) * (u_ref @ u_ref))),
            "ari_grupos_con_z": ari(g_ref, g),
            "tamanios_grupos": sorted((int(x) for x in np.bincount(g)[1:]), reverse=True),
        }
    out["escaladores"] = {
        "nota": ("Mismos datos, mismo método: lo único que cambia es el escalador. "
                 "El CP1 casi no se mueve entre z, min-max y robusta; "
                 "los conglomerados sí."),
        "k_grupos": 3,
        "comparacion": comparacion,
    }

    # ---- ¿Cuánto cambia el resultado según qué distancia se use? ----------
    # La entrada afirma "con otra distancia, otros grupos". Depende también
    # del enlace, así que se mide con los dos.
    Smat = np.cov(Z.T)
    DISTANCIAS = {
        "euclidea": pdist(Z, "euclidean"),
        "manhattan": pdist(Z, "cityblock"),
        "minkowski_3": pdist(Z, "minkowski", p=3),
        "chebyshev": pdist(Z, "chebyshev"),
        "coseno": pdist(Z, "cosine"),
        "mahalanobis": pdist(Z, "mahalanobis", VI=np.linalg.inv(Smat)),
    }
    dist_cmp = {}
    for nombre, D in DISTANCIAS.items():
        fila = {"correlacion_con_euclidea":
                float(np.corrcoef(D, DISTANCIAS["euclidea"])[0, 1])}
        for enl in ("complete", "average"):
            fila[f"ari_{enl}"] = {
                str(kk): ari(fcluster(linkage(DISTANCIAS["euclidea"], enl), kk, "maxclust"),
                             fcluster(linkage(D, enl), kk, "maxclust"))
                for kk in (2, 3, 4, 5)
            }
        dist_cmp[nombre] = fila

    # Mahalanobis: el techo algebraico y qué se puede marcar con n = 32.
    Cz = Z - Z.mean(axis=0)
    d2_m = np.einsum("ij,jk,ik->i", Cz, np.linalg.inv(Smat), Cz)
    orden_d2 = np.argsort(-d2_m)
    umbral = float(_st.chi2.ppf(0.975, p_var))
    out["distancias"] = {
        "nota": ("Mismos datos estandarizados; sólo cambia la distancia. "
                 "Con enlace promedio los grupos coinciden y con enlace "
                 "completo no: el efecto de la distancia depende del enlace."),
        "comparacion": dist_cmp,
        "mahalanobis": {
            "techo_algebraico": float((len(df) - 1) ** 2 / len(df)),
            "umbral_chi2_975": umbral,
            "suma_d2": float(d2_m.sum()),
            "suma_d2_teorica": float((len(df) - 1) * p_var),
            "marcados": int((d2_m > umbral).sum()),
            "top3": [{"aglomerado": df.index[i], "d2": float(d2_m[i]),
                      "z_mas_extremo": VARS[int(np.argmax(np.abs(Z[i])))],
                      "valor_z": float(Z[i][int(np.argmax(np.abs(Z[i])))])}
                     for i in orden_d2[:3]],
        },
    }

    # ---- El PCA por dentro: sensibilidad, atípicos y contra el factorial ---
    Rm2 = np.corrcoef(Z.T)
    wv, Vv = np.linalg.eigh(Rm2)
    orden_v = np.argsort(-wv)
    wv, Vv = wv[orden_v], Vv[:, orden_v]
    u_cp1 = Vv[:, 0] * np.sign(Vv[np.argmax(np.abs(Vv[:, 0])), 0])

    # Sacar un aglomerado a la vez: ¿se mueve la dirección o la varianza?
    quitando = []
    Xbase = df[VARS].to_numpy(float)
    for k in range(len(df)):
        Y = np.delete(Xbase, k, axis=0)
        Y = (Y - Y.mean(axis=0)) / Y.std(axis=0, ddof=1)
        wk, Vk = np.linalg.eigh(np.corrcoef(Y.T))
        ok = np.argsort(-wk)
        u = Vk[:, ok[0]]
        u = u * np.sign(u[np.argmax(np.abs(u))])
        if u @ u_cp1 < 0:
            u = -u
        quitando.append({
            "aglomerado": df.index[k],
            "congruencia": float((u @ u_cp1) / np.sqrt((u @ u) * (u_cp1 @ u_cp1))),
            "prop_cp1": float(wk[ok[0]] / p_var),
        })

    # Atípicos: el plano de los dos primeros CP no es la distancia completa.
    Pun = Z @ Vv
    d2_plano = (Pun[:, :2] ** 2 / wv[:2]).sum(axis=1)
    Cz2 = Z - Z.mean(axis=0)
    d2_todo = np.einsum("ij,jk,ik->i", Cz2, np.linalg.inv(np.cov(Z.T)), Cz2)

    # Factorial por ejes principales, para contrastar con el PCA.
    def ejes_principales(R, k, iters=500):
        h2 = 1 - 1 / np.diag(np.linalg.inv(R))
        for _ in range(iters):
            Rr = R.copy()
            np.fill_diagonal(Rr, h2)
            wf, Vf = np.linalg.eigh(Rr)
            of = np.argsort(-wf)
            Lf = Vf[:, of[:k]] * np.sqrt(np.maximum(wf[of[:k]], 0))
            h2n = (Lf ** 2).sum(axis=1)
            if np.allclose(h2n, h2, atol=1e-10):
                break
            h2 = np.clip(h2n, 0.001, 0.999)
        return Lf

    L_fa = ejes_principales(Rm2, 2)
    L_pca = Vv[:, :2] * np.sqrt(wv[:2])
    for j in range(2):
        if L_pca[:, j] @ L_fa[:, j] < 0:
            L_fa[:, j] = -L_fa[:, j]

    out["pca_detalle"] = {
        "quitando_un_aglomerado": {
            "congruencia_mediana": float(np.median([q["congruencia"] for q in quitando])),
            "congruencia_minima": float(min(q["congruencia"] for q in quitando)),
            "prop_cp1_minima": float(min(q["prop_cp1"] for q in quitando)),
            "prop_cp1_maxima": float(max(q["prop_cp1"] for q in quitando)),
            "peores": sorted(quitando, key=lambda q: q["congruencia"])[:3],
        },
        "atipicos": {
            "nota": ("El plano de los dos primeros componentes sólo ve a los "
                     "atípicos de esas dos direcciones."),
            "correlacion_rangos": float(_st.spearmanr(d2_plano, d2_todo).statistic),
            "top5_plano": [{"aglomerado": df.index[i], "d2": float(d2_plano[i])}
                           for i in np.argsort(-d2_plano)[:5]],
            "top5_completa": [{"aglomerado": df.index[i], "d2": float(d2_todo[i])}
                              for i in np.argsort(-d2_todo)[:5]],
        },
        "contra_factorial": {
            "metodo": "ejes principales iterados, 2 factores",
            "congruencia_f1": float((L_pca[:, 0] @ L_fa[:, 0])
                                    / np.sqrt((L_pca[:, 0] @ L_pca[:, 0])
                                              * (L_fa[:, 0] @ L_fa[:, 0]))),
            "congruencia_f2": float((L_pca[:, 1] @ L_fa[:, 1])
                                    / np.sqrt((L_pca[:, 1] @ L_pca[:, 1])
                                              * (L_fa[:, 1] @ L_fa[:, 1]))),
            "comunalidad_media_pca": float((L_pca ** 2).sum(axis=1).mean()),
            "comunalidad_media_factorial": float((L_fa ** 2).sum(axis=1).mean()),
            "cargas": [{"variable": VARS[i],
                        "pca_f1": float(L_pca[i, 0]), "fa_f1": float(L_fa[i, 0]),
                        "pca_f2": float(L_pca[i, 1]), "fa_f2": float(L_fa[i, 1])}
                       for i in np.argsort(-np.abs(L_pca[:, 0]))[:6]],
        },
    }

    # ---- ¿Cuánto decide el método de enlace? ------------------------------
    # La partición interpretable del caso existe sólo con Ward; el grupo
    # patagónico, en cambio, sale igual con los tres enlaces razonables.
    Deu = pdist(Z, "euclidean")
    ENLACES = ("single", "complete", "average", "centroid", "median", "ward")
    nombres_agl = list(df.index)
    i_ushuaia = next(i for i, x in enumerate(nombres_agl) if x.startswith("Ushuaia"))
    PATAGONIA = {"Comodoro Rivadavia - Rada Tilly", "Neuquén - Plottier",
                 "Rio Gallegos", "Ushuaia - Rio Grande"}
    enl = {}
    for m in ENLACES:
        Lm = linkage(Deu, m)
        # Centroide y mediana pueden INVERTIR el árbol: una fusión posterior
        # a menor altura que la anterior. Ahí el corte no puede devolver la
        # cantidad de grupos que se le pide.
        fila = {"inversiones": int((np.diff(Lm[:, 2]) < 0).sum())}
        for kk in (3, 4, 5):
            g = fcluster(Lm, kk, "maxclust")
            miembros = {nombres_agl[i] for i in range(len(g)) if g[i] == g[i_ushuaia]}
            fila[str(kk)] = {
                "tamanios": sorted((int(x) for x in np.bincount(g)[1:]), reverse=True),
                "grupo_de_ushuaia": sorted(miembros),
                "es_patagonia_exacta": miembros == PATAGONIA,
            }
        enl[m] = fila
    alturas = linkage(Deu, "ward")[:, 2]
    cortes = []
    for kk in range(2, 7):
        # alturas[-k] es la fusión que DEJA k grupos; el cociente la compara
        # con la fusión inmediatamente anterior del árbol.
        h_kk = float(alturas[-kk])
        h_prev = float(alturas[-kk - 1])
        cortes.append({"k": kk, "altura": h_kk, "cociente": h_kk / h_prev})
    out["enlaces"] = {
        "nota": ("Misma distancia euclídea sobre variables estandarizadas; "
                 "sólo cambia el enlace."),
        "patagonia": sorted(PATAGONIA),
        "comparacion": enl,
        "alturas_ward": cortes,
    }

    # ---- Índice sintético: las decisiones y la incertidumbre del puesto ----
    # Ocho de los diez indicadores tienen una dirección clara; se los orienta
    # para que "más sea mejor" y se construye el índice de varias maneras.
    SIGNO = {"desocupacion": -1, "empleo": +1, "actividad": +1,
             "ingreso_medio": +1, "ingreso_mediano": +1, "gini": -1,
             "secundario_mas": +1, "no_registrado": -1}
    ind_idx = [VARS.index(k) for k in SIGNO]
    signos = np.array([SIGNO[VARS[i]] for i in ind_idx])
    nom_ind = [VARS[i] for i in ind_idx]
    Yi = X[:, ind_idx] * signos

    def norm_z(M):
        return (M - M.mean(axis=0)) / M.std(axis=0, ddof=1)

    def norm_mm(M):
        return (M - M.min(axis=0)) / (M.max(axis=0) - M.min(axis=0))

    def norm_rg(M):
        return np.argsort(np.argsort(M, axis=0), axis=0) / (len(M) - 1)

    Zi = norm_z(Yi)
    wi_, Vi_ = np.linalg.eigh(np.corrcoef(Zi.T))
    ui = Vi_[:, np.argsort(-wi_)[0]]
    ui = ui * np.sign(ui.sum())
    variantes = {
        "z + suma": Zi.mean(axis=1),
        "min-max + suma": norm_mm(Yi).mean(axis=1),
        "rangos + suma": norm_rg(Yi).mean(axis=1),
        "min-max + geométrica": np.exp(np.log(norm_mm(Yi) * 0.98 + 0.01).mean(axis=1)),
        "CP1 del PCA": Zi @ ui,
    }
    base_idx = variantes["z + suma"]
    puesto_base = np.argsort(np.argsort(-base_idx)) + 1
    top5_base = set(df.index[np.argsort(puesto_base)][:5])

    # Peso nominal contra peso efectivo: "ponderar igual" no reparte igual.
    cor_ind = np.array([np.corrcoef(Zi[:, jj], base_idx)[0, 1]
                        for jj in range(Zi.shape[1])])
    peso_ef = cor_ind ** 2 / (cor_ind ** 2).sum()
    DIM = {"desocupacion": "mercado de trabajo", "empleo": "mercado de trabajo",
           "actividad": "mercado de trabajo", "no_registrado": "mercado de trabajo",
           "ingreso_medio": "ingresos", "ingreso_mediano": "ingresos",
           "gini": "ingresos", "secundario_mas": "educación"}

    out["indice"] = {
        "indicadores": nom_ind,
        "peso_nominal": 1 / len(nom_ind),
        "pesos": [{"indicador": nom_ind[jj],
                   "correlacion_con_el_indice": float(cor_ind[jj]),
                   "peso_efectivo": float(peso_ef[jj])}
                  for jj in np.argsort(-peso_ef)],
        "por_dimension": [
            {"dimension": g,
             "indicadores": sum(1 for x in nom_ind if DIM[x] == g),
             "nominal": sum(1 for x in nom_ind if DIM[x] == g) / len(nom_ind),
             "efectivo": float(sum(peso_ef[jj] for jj, x in enumerate(nom_ind)
                                   if DIM[x] == g))}
            for g in ("mercado de trabajo", "ingresos", "educación")],
        "sensibilidad": [
            {"variante": k,
             "spearman_con_base": float(_st.spearmanr(base_idx, v).statistic),
             "movimiento_mediano": float(np.median(np.abs(
                 (np.argsort(np.argsort(-v)) + 1) - puesto_base))),
             "movimiento_maximo": int(np.abs(
                 (np.argsort(np.argsort(-v)) + 1) - puesto_base).max()),
             "cambia_el_top5": bool(
                 set(df.index[np.argsort(np.argsort(np.argsort(-v)) + 1)][:5])
                 != top5_base)}
            for k, v in variantes.items() if k != "z + suma"],
        "top5_base": sorted(top5_base),
    }

    # ¿Cuánto vale un puesto del ranking? Bootstrap de PERSONAS dentro de cada
    # aglomerado: el error de muestreo real de cada indicador.
    def ocho_indicadores(g):
        wg = g["PONDERA"].to_numpy(float)
        pea_ = g[g["ESTADO"].isin([1, 2]) & (g["CH06"] >= 15)]
        ocup_ = g[g["ESTADO"] == 1]
        ci_ = g[(g["ESTADO"] == 1) & (g["P21"] > 0)]
        ad_ = g[g["CH06"] >= 18]
        as_ = g[(g["ESTADO"] == 1) & (g["CAT_OCUP"] == 3) & g["PP07H"].isin([1, 2])]
        if min(len(pea_), len(ci_), len(ad_), len(as_)) == 0:
            return None
        xi = ci_["P21"].to_numpy(float)
        wxi = ci_["PONDERA"].to_numpy(float)
        return np.array([
            -(pea_["PONDERA"] * (pea_["ESTADO"] == 2)).sum() / pea_["PONDERA"].sum() * 100,
            ocup_["PONDERA"].sum() / wg.sum() * 100,
            pea_["PONDERA"].sum() / wg.sum() * 100,
            (xi * wxi).sum() / wxi.sum(),
            cuantil_ponderado(xi, wxi, 0.5),
            -gini(xi, wxi),
            (ad_["PONDERA"] * ad_["NIVEL_ED"].isin([4, 5, 6])).sum() / ad_["PONDERA"].sum() * 100,
            -(as_["PONDERA"] * (as_["PP07H"] == 2)).sum() / as_["PONDERA"].sum() * 100])

    por_aglo = {int(a): g for a, g in ind.groupby("AGLOMERADO")}
    orden_aglo = [int(df.loc[n, "aglomerado"]) for n in df.index]
    rbs = np.random.default_rng(SEMILLA + 7)
    REP_RANK = 500
    puestos = []
    for _ in range(REP_RANK):
        M = np.array([ocho_indicadores(
            por_aglo[a].iloc[rbs.integers(0, len(por_aglo[a]), len(por_aglo[a]))])
            for a in orden_aglo], dtype=float)
        Zr = (M - M.mean(axis=0)) / M.std(axis=0, ddof=1)
        puestos.append(np.argsort(np.argsort(-Zr.mean(axis=1))) + 1)
    Pr = np.array(puestos)
    lo_r = np.percentile(Pr, 5, axis=0)
    hi_r = np.percentile(Pr, 95, axis=0)
    out["indice"]["incertidumbre_del_puesto"] = {
        "metodo": "bootstrap de personas dentro de cada aglomerado",
        "replicas": REP_RANK,
        "amplitud_mediana": float(np.median(hi_r - lo_r)),
        "amplitud_maxima": float((hi_r - lo_r).max()),
        "con_ic_de_10_o_mas": int(((hi_r - lo_r) >= 10).sum()),
        "detalle": [{"aglomerado": df.index[i], "puesto": int(puesto_base[i]),
                     "ic_bajo": float(lo_r[i]), "ic_alto": float(hi_r[i])}
                    for i in np.argsort(puesto_base)],
    }

    # ---- MDS: reconstruir el mapa a partir de la tabla de distancias ------
    # La entrada abre diciendo que el MDS reconstruye la ubicación de las
    # ciudades sin conocer ninguna coordenada. Acá se comprueba.
    def anillos(geom):
        if not geom:
            return []
        if geom["type"] == "Polygon":
            return [np.array(r)[:, :2] for r in geom["coordinates"]]
        return [np.array(r)[:, :2]
                for poly in geom["coordinates"] for r in poly]

    def centro_area(rs):
        """Centroide ponderado por área, con la fórmula del zapatero."""
        sx = sy = sa = 0.0
        for r in rs:
            xx, yy = r[:, 0], r[:, 1]
            a = np.dot(xx, np.roll(yy, -1)) - np.dot(np.roll(xx, -1), yy)
            if abs(a) < 1e-9:
                continue
            cruz = np.roll(xx, -1) * yy - xx * np.roll(yy, -1)
            sx += np.dot(xx + np.roll(xx, -1), cruz)
            sy += np.dot(yy + np.roll(yy, -1), cruz)
            sa += a
        return np.array([sx / (3 * sa), sy / (3 * sa)])

    with zipfile.ZipFile(CARTO) as zc:
        nj = [x for x in zc.namelist() if x.endswith(".json")][0]
        geo = json.load(io.TextIOWrapper(zc.open(nj), encoding="utf-8"))
    feats = geo["features"] if isinstance(geo, dict) and "features" in geo else geo
    piezas = {}
    for f in feats:
        cod = f["properties"].get("eph_codagl")
        if not cod:
            continue
        cod = int(cod)
        piezas.setdefault(cod, {"nom": f["properties"]["eph_aglome"], "r": []})
        piezas[cod]["r"] += anillos(f.get("geometry"))
    piezas = {k: v for k, v in piezas.items() if v["r"]}
    cods = sorted(piezas)
    nom_g = [piezas[k]["nom"] for k in cods]
    XY = np.array([centro_area(piezas[k]["r"]) for k in cods])
    mg = len(cods)
    Dg = np.sqrt(((XY[:, None, :] - XY[None, :, :]) ** 2).sum(axis=2))

    Jg = np.eye(mg) - np.ones((mg, mg)) / mg
    Bg = -0.5 * Jg @ (Dg ** 2) @ Jg
    wg, Vg = np.linalg.eigh(Bg)
    og = np.argsort(-wg)
    wg, Vg = wg[og], Vg[:, og]
    Yg = Vg[:, :2] * np.sqrt(np.maximum(wg[:2], 0))
    Dg_rec = np.sqrt(((Yg[:, None, :] - Yg[None, :, :]) ** 2).sum(axis=2))

    def procrustes(A, B):
        A = A - A.mean(axis=0)
        B = B - B.mean(axis=0)
        A = A / np.linalg.norm(A)
        B = B / np.linalg.norm(B)
        U_, s_, Vt_ = np.linalg.svd(A.T @ B)
        return float(s_.sum()), A, B @ (U_ @ Vt_).T

    corr_pro, Aref, Yal = procrustes(XY, Yg)
    iu_g = np.triu_indices(mg, 1)
    imax = np.unravel_index(Dg.argmax(), Dg.shape)

    # Y la identidad: MDS clásico sobre distancias euclídeas = PCA.
    Dz = pdist(Z)
    Bz = -0.5 * (np.eye(len(Z)) - np.ones((len(Z),) * 2) / len(Z)) \
        @ (squareform(Dz) ** 2) \
        @ (np.eye(len(Z)) - np.ones((len(Z),) * 2) / len(Z))
    wz, Vz = np.linalg.eigh(Bz)
    oz = np.argsort(-wz)
    wz = wz[oz]
    Yz = Vz[:, oz[:2]] * np.sqrt(np.maximum(wz[:2], 0))
    dif_ejes = []
    for jj in range(2):
        a_, b_ = puntajes[:, jj], Yz[:, jj]
        if a_ @ b_ < 0:
            b_ = -b_
        dif_ejes.append(float(np.abs(a_ - b_).max()))

    out["mds"] = {
        "reconstruccion": {
            "nota": ("Centroides de los aglomerados, sus 496 distancias, y el "
                     "mapa que el MDS devuelve sin ver ninguna coordenada."),
            "n": mg,
            "distancias": int(mg * (mg - 1) / 2),
            "distancia_maxima_km": float(Dg.max() / 1000),
            "par_mas_lejano": [nom_g[imax[0]], nom_g[imax[1]]],
            "prop_valores_propios": [float(x) for x in
                                     wg[:4] / wg[wg > 0].sum()],
            "correlacion_procrustes": corr_pro,
            "error_posicion_maximo": float(
                np.sqrt(((Yal - Aref) ** 2).sum(axis=1)).max()),
            "correlacion_distancias": float(
                np.corrcoef(Dg[iu_g], Dg_rec[iu_g])[0, 1]),
            "error_distancia_maximo_km": float(np.abs(Dg - Dg_rec).max() / 1000),
        },
        "identidad_con_pca": {
            "nota": "MDS clásico sobre distancias euclídeas = PCA sobre los datos.",
            "diferencia_maxima_por_eje": dif_ejes,
            "diferencia_maxima_valores_propios": float(
                np.abs(wz[:p_var] / (len(Z) - 1) - valores).max()),
        },
    }
    dibujar_mds(nom_g, Yal)

    # ---- Análisis de correspondencias: aglomerado x calificación ----------
    # Una tabla de 32x4 que ninguna lectura celda por celda resuelve.
    oc = ind[(ind["ESTADO"] == 1) & ind["PP04D_COD"].notna()].copy()
    oc["calif"] = oc["PP04D_COD"].astype("Int64") % 10
    oc = oc[oc["calif"].between(1, 4)]
    ETIQ = {1: "Profesional", 2: "Técnica", 3: "Operativa", 4: "No calificada"}
    oc["cal"] = oc["calif"].map(ETIQ)
    Tc = pd.crosstab(oc["AGLOMERADO"], oc["cal"])[list(ETIQ.values())]
    nom_f = [NOM.get(int(i), str(i)) for i in Tc.index]
    Nc = int(Tc.to_numpy().sum())
    Pc = Tc.to_numpy() / Nc
    rmasa, cmasa = Pc.sum(axis=1), Pc.sum(axis=0)
    Sc = (Pc - np.outer(rmasa, cmasa)) / np.sqrt(np.outer(rmasa, cmasa))
    Uc, Dc, Vtc = np.linalg.svd(Sc, full_matrices=False)
    inercias = Dc ** 2
    Fc = (Uc * Dc) / np.sqrt(rmasa)[:, None]          # coordenadas fila
    Gc = (Vtc.T * Dc) / np.sqrt(cmasa)[:, None]       # coordenadas columna
    d2_fila = (Fc ** 2).sum(axis=1)
    cos2 = Fc ** 2 / d2_fila[:, None]
    contrib = (rmasa[:, None] * Fc ** 2) / inercias[None, :]
    chi_c = float(_st.chi2_contingency(Tc.to_numpy())[0])

    # Línea de base: ¿cuánta inercia produce una tabla INDEPENDIENTE igual?
    rb2 = np.random.default_rng(SEMILLA + 5)
    ine_ruido, ac2_ruido = [], []
    for _ in range(2000):
        Tn = rb2.multinomial(Nc, np.outer(rmasa, cmasa).ravel()).reshape(Tc.shape)
        if (Tn.sum(axis=0) == 0).any() or (Tn.sum(axis=1) == 0).any():
            continue
        Pn = Tn / Nc
        rn, cn = Pn.sum(axis=1), Pn.sum(axis=0)
        Sn = (Pn - np.outer(rn, cn)) / np.sqrt(np.outer(rn, cn))
        dn = np.linalg.svd(Sn, compute_uv=False) ** 2
        ine_ruido.append(dn.sum())
        ac2_ruido.append(dn[:2].sum() / dn.sum())

    orden_f = np.argsort(Fc[:, 0])
    peor_rep = np.argsort(cos2[:, :2].sum(axis=1))
    out["correspondencias"] = {
        "tabla": {"filas": int(Tc.shape[0]), "columnas": int(Tc.shape[1]),
                  "n": Nc, "celdas": int(Tc.shape[0] * Tc.shape[1])},
        "categorias": list(ETIQ.values()),
        "chi2": chi_c,
        "gl": int((Tc.shape[0] - 1) * (Tc.shape[1] - 1)),
        "p": float(_st.chi2_contingency(Tc.to_numpy())[1]),
        "inercia_total": float(inercias.sum()),
        "inercia_chi2_sobre_n": chi_c / Nc,
        "inercias": [float(x) for x in inercias],
        "prop_inercia": [float(x) for x in inercias / inercias.sum()],
        "columnas": [{"categoria": Tc.columns[j], "masa": float(cmasa[j]),
                      "dim1": float(Gc[j, 0]), "dim2": float(Gc[j, 1])}
                     for j in range(Tc.shape[1])],
        "filas_extremas": [{"aglomerado": nom_f[i], "masa": float(rmasa[i]),
                            "dim1": float(Fc[i, 0]), "dim2": float(Fc[i, 1]),
                            "cos2_plano": float(cos2[i, :2].sum()),
                            "contrib_dim1": float(contrib[i, 0])}
                           for i in list(orden_f[:3]) + list(orden_f[-3:])],
        "peor_representadas": [{"aglomerado": nom_f[i],
                                "dim1": float(Fc[i, 0]), "dim2": float(Fc[i, 1]),
                                "cos2_plano": float(cos2[i, :2].sum()),
                                "cos2_dim3": float(cos2[i, 2])}
                               for i in peor_rep[:3]],
        "linea_de_base": {
            "inercia_ruido_media": float(np.mean(ine_ruido)),
            "inercia_ruido_p95": float(np.percentile(ine_ruido, 95)),
            "prop_2dim_real": float(inercias[:2].sum() / inercias.sum()),
            "prop_2dim_ruido_media": float(np.mean(ac2_ruido)),
            "prop_2dim_ruido_p95": float(np.percentile(ac2_ruido, 95)),
        },
    }
    dibujar_correspondencias(nom_f, Fc, list(Tc.columns), Gc,
                             inercias / inercias.sum())

    # ---- Densidad y forma: DBSCAN, mezclas y espectral sobre el caso ------
    # Los métodos que aplastan a k-medias con lunas y anillos pierden acá,
    # porque estos indicadores producen nubes elípticas y separadas.
    from sklearn.cluster import DBSCAN as _DBSCAN, SpectralClustering as _Spec
    from sklearn.cluster import KMeans as _KMeans
    from sklearn.mixture import GaussianMixture as _GMM
    from sklearn.neighbors import NearestNeighbors as _NN

    i_ush = next(i for i, x in enumerate(df.index) if x.startswith("Ushuaia"))
    nombres_lista = list(df.index)

    def veredicto(lab):
        if lab[i_ush] == -1:
            return {"grupo": [], "es_patagonia_exacta": False, "ushuaia_es_ruido": True}
        miembros = sorted(nombres_lista[i] for i in range(len(lab))
                          if lab[i] == lab[i_ush])
        return {"grupo": miembros,
                "es_patagonia_exacta": set(miembros) == PATAGONIA,
                "ushuaia_es_ruido": False}

    metodos_df = {
        "k-medias": _KMeans(3, n_init=25, random_state=SEMILLA).fit_predict(Z),
        "espectral": _Spec(3, affinity="nearest_neighbors", n_neighbors=8,
                           random_state=SEMILLA,
                           assign_labels="kmeans").fit_predict(Z),
    }
    # La mezcla gaussiana NO se puede ajustar acá: con 3 componentes "diag" en
    # 10 dimensiones pide 62 parámetros para 32 observaciones, y cada arranque
    # cae en otro óptimo. Se guarda la inestabilidad, no un resultado.
    gmm_semillas = []
    for s in (0, 1, 7, SEMILLA):
        mg = _GMM(3, covariance_type="diag", n_init=10, random_state=s).fit(Z)
        lab_g = mg.predict(Z)
        gmm_semillas.append({
            "semilla": int(s),
            "tamanio_grupo_de_ushuaia": int((lab_g == lab_g[i_ush]).sum()),
            "log_verosimilitud": float(mg.score(Z) * len(Z)),
            "es_patagonia_exacta": veredicto(lab_g)["es_patagonia_exacta"]})
    n_par_gmm = 3 * (p_var + p_var) + 2
    # DBSCAN: barrido de eps, para mostrar que ningún valor sirve.
    barrido = []
    for eps in np.round(np.arange(2.0, 5.01, 0.25), 2):
        lab = _DBSCAN(eps=float(eps), min_samples=3).fit_predict(Z)
        v = veredicto(lab)
        barrido.append({"eps": float(eps),
                        "grupos": int(len(set(lab[lab >= 0]))),
                        "ruido": int((lab == -1).sum()),
                        "tamanio_grupo_de_ushuaia": len(v["grupo"]),
                        "es_patagonia_exacta": v["es_patagonia_exacta"]})

    # El diagnóstico: separado pero poco denso.
    i_pat = [nombres_lista.index(p) for p in sorted(PATAGONIA)]
    i_resto = [i for i in range(len(df)) if i not in i_pat]
    d3 = _NN(n_neighbors=4).fit(Z).kneighbors(Z)[0][:, 1:].mean(axis=1)
    Dz2 = np.sqrt(((Z[:, None, :] - Z[None, :, :]) ** 2).sum(axis=2))

    out["densidad_y_forma"] = {
        "nota": ("Mismos 32 aglomerados: qué devuelve cada método frente al "
                 "grupo patagónico."),
        "metodos": {k: veredicto(v) for k, v in metodos_df.items()},
        "mezclas_no_se_pueden_ajustar": {
            "parametros": int(n_par_gmm),
            "observaciones": int(len(df)),
            "por_semilla": gmm_semillas,
            "tamanios_distintos": len({g["tamanio_grupo_de_ushuaia"]
                                       for g in gmm_semillas}),
        },
        "dbscan_barrido": barrido,
        "dbscan_encuentra_patagonia": any(b["es_patagonia_exacta"] for b in barrido),
        "diagnostico": {
            "distancia_media_a_3_vecinos_patagonia": float(d3[i_pat].mean()),
            "distancia_media_a_3_vecinos_resto": float(d3[i_resto].mean()),
            "distancia_media_entre_patagonicos": float(
                Dz2[np.ix_(i_pat, i_pat)][np.triu_indices(len(i_pat), 1)].mean()),
            "distancia_media_al_resto": float(Dz2[np.ix_(i_pat, i_resto)].mean()),
        },
    }

    # ---- Estabilidad del CP1: bootstrap sobre los aglomerados --------------
    Xm = df[VARS].to_numpy(float)

    def cp1_de(M):
        Zs = (M - M.mean(axis=0)) / M.std(axis=0, ddof=1)
        u = np.linalg.eigh(np.corrcoef(Zs.T))[1][:, -1]
        return u * np.sign(u[np.argmax(np.abs(u))])

    u0 = cp1_de(Xm)
    rboot = np.random.default_rng(SEMILLA + 3)
    phis = []
    for _ in range(5_000):
        Xb = Xm[rboot.integers(0, n_obs, n_obs)]
        if np.any(Xb.std(axis=0, ddof=1) == 0):
            continue
        ub = cp1_de(Xb)
        if ub @ u0 < 0:
            ub = -ub
        phis.append((ub @ u0) / np.sqrt((ub @ ub) * (u0 @ u0)))
    phis = np.array(phis)
    out["estabilidad_cp1"] = {
        "metodo": "bootstrap de aglomerados; congruencia de Tucker con el CP1 completo",
        "replicas": int(len(phis)),
        "phi_mediana": float(np.median(phis)),
        "phi_p5": float(np.percentile(phis, 5)),
        "prop_phi_mayor_igual_095": float((phis >= 0.95).mean()),
        "cociente_vp1_vp2": float(valores[0] / valores[1]),
    }

    SALIDA.write_text(json.dumps(out, indent=2, ensure_ascii=False),
                      encoding="utf-8")

    # ---- Informe -----------------------------------------------------------
    print(f"{len(df)} aglomerados x {len(VARS)} variables\n")
    print("Correlaciones más fuertes:")
    for p in pares[:6]:
        print(f"  {p['a']:16} {p['b']:16} r = {p['r']:+.3f}")

    print("\nPCA — varianza explicada:")
    for k in range(4):
        print(f"  CP{k+1}: {prop[k]:6.1%}  acumulada {np.cumsum(prop)[k]:6.1%}"
              f"   (valor propio {valores[k]:.3f})")
    print(f"  componentes con valor propio > 1: {(valores > 1).sum()}")

    print("\nCargas del CP1:")
    for v, c in sorted(zip(VARS, vectores[:, 0]), key=lambda t: -abs(t[1])):
        print(f"  {v:16} {c:+.3f}")
    print("\nCargas del CP2:")
    for v, c in sorted(zip(VARS, vectores[:, 1]), key=lambda t: -abs(t[1])):
        print(f"  {v:16} {c:+.3f}")

    print("\nExtremos del CP1:")
    ordenado = sorted(out["pca"]["puntajes"].items(), key=lambda t: t[1][0])
    for n, p in ordenado[:3]:
        print(f"  {n[:30]:32} {p[0]:+.2f}")
    print("  ...")
    for n, p in ordenado[-3:]:
        print(f"  {n[:30]:32} {p[0]:+.2f}")

    print("\nConglomerados (Ward, 3 grupos):")
    for g, s in out["clusters"]["perfil_3"].items():
        print(f"  Grupo {g} ({s['n']}): desoc {s['desocupacion']:.1f} · "
              f"ing.medio ${s['ingreso_medio']:,.0f} · "
              f"no reg {s['no_registrado']:.1f} · sec+ {s['secundario_mas']:.1f}")
        print(f"    {', '.join(x[:22] for x in s['aglomerados'])}")

    print("\nCodo (inercia intra por k):")
    for k, v in codo.items():
        print(f"  k={k}: {v:,.1f}")
    lb = out["linea_de_base"]
    print("\nLínea de base — ruido puro de %dx%d (%d matrices):"
          % (len(df), len(VARS), lb["repeticiones"]))
    print(f"  varianza del CP1:  ruido {lb['cp1_prop_ruido']:6.1%}"
          f"   real {lb['cp1_prop_real']:6.1%}")
    print(f"  componentes con valor propio > 1: ruido {lb['kaiser_ruido_medio']:.2f}"
          f"   real {out['pca']['n_componentes_kaiser']}"
          f"   (el {lb['kaiser_ruido_p_mayor_igual_4']:.1%} del ruido da 4 o más)")
    print(f"  mayor |r|: ruido {lb['max_r_ruido_medio']:.3f}"
          f"   real {lb['max_r_real']:.3f}"
          f"   (el ruido supera 0,50 en el {lb['max_r_ruido_supera_050']:.1%})")
    print("  análisis paralelo — componentes que superan el p95 del ruido: "
          f"{lb['n_componentes_paralelo']}")
    for f in lb["paralelo"][:5]:
        print(f"    CP{f['cp']}: real {f['real']:.3f}  ruido {f['ruido_medio']:.3f}"
              f"  p95 {f['ruido_p95']:.3f}  {'SUPERA' if f['supera'] else 'no'}")
    print("  silueta (k-medias):")
    for k, s in lb["silueta"].items():
        print(f"    k={k}: real {s['real']:.3f}   ruido {s['ruido_medio']:.3f}"
              f"  p95 {s['ruido_p95']:.3f}")

    se = out["sin_estandarizar"]
    print(f"\nSin estandarizar: el CP1 explica el {se['cp1_prop']:.4%} "
          f"(estandarizando, {se['cp1_prop_estandarizado']:.1%})")
    for v, c in sorted(se["cargas_cp1"].items(), key=lambda t: -t[1])[:3]:
        print(f"  carga {v:16} {c:.4f}")

    mz = out["matriz"]
    ie = mz["identidad_empleo"]
    print(f"\nLa matriz por dentro ({mz['n_correlaciones']} correlaciones):")
    print(f"  |r| medio {mz['abs_r_medio']:.3f}  ->  |parcial| medio {mz['abs_parcial_medio']:.3f}")
    print(f"  cambian de signo al pasar a parcial: {mz['cambian_de_signo']} pares")
    for pr in mz["pares"][:5]:
        print(f"    {pr['a']:16} / {pr['b']:16} r {pr['r']:+.3f}  parcial {pr['parcial']:+.3f}")
    print(f"  determinante {mz['determinante']:.3e}   condición {mz['numero_condicion']:,.0f}")
    print("  VIF más altos: " + ", ".join(
        f"{v} {mz['vif'][v]:,.0f}"
        for v in sorted(mz["vif"], key=mz["vif"].get, reverse=True)[:3]))
    print(f"  {ie['formula']}: error máximo {ie['error_maximo_pp']:.4f} pp, "
          f"correlación {ie['correlacion']:.6f}")
    se_ = mz["sin_empleo"]
    print(f"  sin 'empleo': determinante {se_['determinante']:.3e}, "
          f"VIF máximo {se_['vif_maximo']:,.0f}, KMO {se_['kmo']:.3f}")
    print(f"  KMO {mz['kmo']:.3f}   Bartlett chi2 {mz['bartlett']['chi2']:.1f} "
          f"(gl {mz['bartlett']['gl']:.0f}), p {mz['bartlett']['p']:.2e}")
    print("  sacar un aglomerado mueve una correlación, a lo sumo:")
    for s in mz["sensibilidad_top3"]:
        print(f"    sin {s['aglomerado'][:26]:28} {s['par'][0]}/{s['par'][1]}: "
              f"{s['r_con']:+.3f} -> {s['r_sin']:+.3f}")

    print("\nEscaladores — mismos datos, mismo método:")
    print("  %-14s %10s %14s %12s" % ("escalador", "CP1", "congr. con z", "ARI con z"))
    for modo, c in out["escaladores"]["comparacion"].items():
        print("  %-14s %9.1f%% %14.3f %12.3f"
              % (modo, 100 * c["cp1_prop"], c["congruencia_cp1_con_z"],
                 c["ari_grupos_con_z"]))

    ix = out["indice"]
    print("\nÍndice sintético — 'pesos iguales' del %.1f %% cada uno:"
          % (100 * ix["peso_nominal"]))
    for pz in ix["pesos"]:
        print("  %-18s corr %+.3f   peso efectivo %5.1f %%"
              % (pz["indicador"], pz["correlacion_con_el_indice"],
                 100 * pz["peso_efectivo"]))
    for dm in ix["por_dimension"]:
        print("    %-20s %d indicadores: %5.1f %% nominal, %5.1f %% efectivo"
              % (dm["dimension"], dm["indicadores"],
                 100 * dm["nominal"], 100 * dm["efectivo"]))
    print("  sensibilidad del ranking:")
    for sv in ix["sensibilidad"]:
        print("    %-22s Spearman %.3f, se mueve %.1f puestos (máx %d)%s"
              % (sv["variante"], sv["spearman_con_base"],
                 sv["movimiento_mediano"], sv["movimiento_maximo"],
                 "  CAMBIA EL TOP 5" if sv["cambia_el_top5"] else ""))
    iu_ = ix["incertidumbre_del_puesto"]
    print("  incertidumbre del puesto (%d réplicas): IC mediano de %.1f "
          "posiciones, máximo %.0f; %d de %d con IC de 10 o más"
          % (iu_["replicas"], iu_["amplitud_mediana"], iu_["amplitud_maxima"],
             iu_["con_ic_de_10_o_mas"], len(df)))

    dfm = out["densidad_y_forma"]
    print("\nDensidad y forma — el grupo patagónico según cada método:")
    for k, v in dfm["metodos"].items():
        est = ("Patagonia exacta" if v["es_patagonia_exacta"]
               else ("Ushuaia queda como ruido" if v["ushuaia_es_ruido"]
                     else f"{len(v['grupo'])} casos"))
        print(f"  {k:24} {est}")
    gm = dfm["mezclas_no_se_pueden_ajustar"]
    print(f"  mezclas gaussianas: {gm['parametros']} parámetros para "
          f"{gm['observaciones']} observaciones — inestable")
    print("    grupo de Ushuaia por semilla: "
          + ", ".join(f"{g['tamanio_grupo_de_ushuaia']}" for g in gm["por_semilla"])
          + f"  ({gm['tamanios_distintos']} resultados distintos)")
    print(f"  DBSCAN: la encuentra con algún eps de 2,0 a 5,0 -> "
          f"{'sí' if dfm['dbscan_encuentra_patagonia'] else 'NO, con ninguno'}")
    dg = dfm["diagnostico"]
    print(f"    distancia a 3 vecinos: patagónicos "
          f"{dg['distancia_media_a_3_vecinos_patagonia']:.2f}, resto "
          f"{dg['distancia_media_a_3_vecinos_resto']:.2f}  "
          f"(razón {dg['distancia_media_a_3_vecinos_patagonia'] / dg['distancia_media_a_3_vecinos_resto']:.2f})")
    print(f"    separados: {dg['distancia_media_entre_patagonicos']:.2f} entre sí "
          f"contra {dg['distancia_media_al_resto']:.2f} al resto")

    dz = out["distancias"]
    print("\nDistancias — ARI contra la euclídea (enlace completo / promedio):")
    print("  %-14s %10s %22s %22s" % ("distancia", "correl.", "completo k=2..5",
                                      "promedio k=2..5"))
    for nombre, f in dz["comparacion"].items():
        cc = " ".join("%5.2f" % f["ari_complete"][str(k)] for k in (2, 3, 4, 5))
        aa = " ".join("%5.2f" % f["ari_average"][str(k)] for k in (2, 3, 4, 5))
        print("  %-14s %10.3f %22s %22s"
              % (nombre, f["correlacion_con_euclidea"], cc, aa))
    mh = dz["mahalanobis"]
    print(f"  Mahalanobis: techo algebraico {mh['techo_algebraico']:.2f}, "
          f"umbral chi2 97,5% {mh['umbral_chi2_975']:.2f}, "
          f"marcados {mh['marcados']}")
    for t in mh["top3"]:
        print(f"    {t['aglomerado'][:26]:28} d2 {t['d2']:6.2f}  "
              f"z más extremo: {t['z_mas_extremo']} {t['valor_z']:+.2f}")

    pd_ = out["pca_detalle"]
    qa = pd_["quitando_un_aglomerado"]
    print("\nPCA por dentro — sacando un aglomerado a la vez:")
    print(f"  congruencia del CP1: mediana {qa['congruencia_mediana']:.4f}, "
          f"mínima {qa['congruencia_minima']:.4f}")
    print(f"  varianza del CP1: de {qa['prop_cp1_minima']:.1%} a "
          f"{qa['prop_cp1_maxima']:.1%} (con los 32, {valores[0] / p_var:.1%})")
    for q in qa["peores"]:
        print(f"    sin {q['aglomerado'][:28]:30} congruencia {q['congruencia']:.4f}, "
              f"CP1 {q['prop_cp1']:.1%}")
    at = pd_["atipicos"]
    print(f"  atípicos: correlación de rangos entre el plano y la distancia "
          f"completa = {at['correlacion_rangos']:.3f}")
    print("    %-30s | %-30s" % ("por el plano (2 CP)", "por Mahalanobis (10)"))
    for a, b in zip(at["top5_plano"], at["top5_completa"]):
        print("    %-24s %5.2f | %-24s %5.2f"
              % (a["aglomerado"][:24], a["d2"], b["aglomerado"][:24], b["d2"]))
    cf = pd_["contra_factorial"]
    print(f"  contra el factorial: congruencia F1 {cf['congruencia_f1']:.4f}, "
          f"F2 {cf['congruencia_f2']:.4f}")
    print(f"    comunalidad media: PCA {cf['comunalidad_media_pca']:.3f}, "
          f"factorial {cf['comunalidad_media_factorial']:.3f}")

    print("\nEnlaces — misma distancia, sólo cambia el enlace:")
    print("  %-10s %-24s %-28s %s" % ("enlace", "tamaños k=3", "tamaños k=5", "grupo de Ushuaia (k=3)"))
    for m, f in out["enlaces"]["comparacion"].items():
        t3 = " · ".join(str(x) for x in f["3"]["tamanios"])
        t5 = " · ".join(str(x) for x in f["5"]["tamanios"])
        est = "Patagonia exacta" if f["3"]["es_patagonia_exacta"] else f"{len(f['3']['grupo_de_ushuaia'])} casos"
        inv = f"  [{f['inversiones']} inversiones]" if f["inversiones"] else ""
        print("  %-10s %-24s %-28s %s%s" % (m, t3, t5, est, inv))
    print("  alturas de Ward al cortar:")
    for c in out["enlaces"]["alturas_ward"]:
        print(f"    k={c['k']}: altura {c['altura']:6.2f}  cociente {c['cociente']:.2f}")

    es = out["estabilidad_cp1"]
    print(f"\nEstabilidad del CP1 (bootstrap, {es['replicas']} réplicas):")
    print(f"  congruencia mediana {es['phi_mediana']:.3f}   p5 {es['phi_p5']:.3f}"
          f"   φ ≥ 0,95 en el {es['prop_phi_mayor_igual_095']:.1%}")
    print(f"  cociente entre los dos primeros valores propios: {es['cociente_vp1_vp2']:.2f}")

    dibujar_pca(list(df.index), puntajes, prop, grupos[3])
    dibujar_dendrograma(df.index, Lk)
    print(f"\n→ {SALIDA}")


if __name__ == "__main__":
    main()

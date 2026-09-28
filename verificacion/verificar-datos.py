"""Verifica los JSON que producen los scripts de `datos/`.

    npm run datos
    npm run datos -- --todo        (lista cada comprobación, no solo las fallas)

Son los archivos que alimentan los casos y las figuras del sitio, y hasta ahora
eran los únicos sin verificador propio. Un error acá no rompe nada: publica un
número corrido, que es peor.

Cuatro frentes, de menos a más exigente:

  la forma        cada JSON existe, parsea, declara su fuente y es más nuevo
                  que el script que lo genera. Si alguien tocó el script y no
                  lo volvió a correr, el JSON quedó viejo y hay que avisarlo.

  la aritmética   identidades que tienen que cumplirse adentro de cada archivo:
                  las proporciones entre 0 y 1, los deciles sumando 100, la
                  suma de cuadrados del ANOVA cerrando, F siendo el cociente de
                  los cuadrados medios, r² siendo el cuadrado de r, la curva de
                  Lorenz empezando en 0 y terminando en 1.

  la coherencia   la misma magnitud publicada en dos archivos distintos tiene
                  que coincidir. Y lo que un script declara en su campo
                  `advertencia` tiene que llegar a la página: si el JSON avisa
                  que trabajó sin ponderar, el caso que lo usa lo tiene que
                  decir.

  los microdatos  el único frente que detecta un filtro que descarta
                  categorías. Recuenta desde el ZIP de la EPH lo que el JSON
                  afirma: filas, población expandida, tamaños de cada
                  subconjunto. Los otros tres frentes no lo habrían agarrado,
                  y la razón está en el comentario de más abajo.

Por qué el cuarto frente existe. En septiembre de 2026 dos scripts calculaban
la proporción de menores de 15 años dejando afuera a los bebés —la EPH codifica
"menos de un año" como CH06 = -1, y los dos filtraban por CH06 >= 0—. Los dos
daban 21,6 % en vez de 22,2 %, así que **coincidían entre sí** y la coherencia
cruzada los daba por buenos. Solo recontar contra el archivo original los
delató. Coincidir no es verificar.
"""

from __future__ import annotations

import os

import json
import math
import sys
import zipfile
from pathlib import Path


# La carpeta con los microdatos públicos. No se versionan: cada fuente se
# baja de su organismo. La variable de entorno DATOS_AR permite moverla.
MICRODATOS = os.environ.get("DATOS_AR", "datos-fuente")

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "datos"
CASOS = RAIZ / "src" / "content" / "casos"

ESPEJO = Path(
    MICRODATOS + r"\INDEC\EPH\01_microdatos_eph"
    r"\2026\EPH_usu_1_Trim_2026_txt.zip"
)
INTERNO = "usu_individual_T126.txt"

TODO = "--todo" in sys.argv

problemas: list[str] = []
avisos: list[str] = []
comprobaciones = 0


def cierto(descripcion: str, condicion: bool) -> None:
    global comprobaciones
    comprobaciones += 1
    if not condicion:
        problemas.append(descripcion)
    elif TODO:
        print(f"  ok  {descripcion}")


def parecido(descripcion: str, a: float, b: float, tol: float = 1e-9) -> None:
    """Igualdad con tolerancia relativa: los JSON guardan flotantes."""
    escala = max(abs(a), abs(b), 1e-12)
    cierto(f"{descripcion} ({a:.10g} contra {b:.10g})", abs(a - b) / escala <= tol)


def redondeado(descripcion: str, guardado: float, exacto: float,
               decimales: int) -> None:
    """Algunos campos se guardan ya redondeados: se compara contra eso."""
    global comprobaciones
    comprobaciones += 1
    ok = abs(guardado - round(exacto, decimales)) <= 10 ** -(decimales + 6)
    if not ok:
        problemas.append(
            f"{descripcion} (guardado {guardado:.10g}, "
            f"exacto {exacto:.10g} → {round(exacto, decimales)})"
        )
    elif TODO:
        print(f"  ok  {descripcion}")


def leer(ruta: Path):
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        problemas.append(f"{ruta.relative_to(RAIZ)} no se puede leer: {e}")
        return None


# ---------------------------------------------------------------------------
# 1 · La forma
# ---------------------------------------------------------------------------

# Qué script genera cada JSON. Si falta una entrada acá, el frente 1 lo avisa:
# un JSON huérfano es un archivo que nadie sabe cómo regenerar.
GENERADOR = {
    "demografia/tasas-m05.json": "demografia/preparar-tasas-m05.py",
    "eph/anova-m11.json": "eph/preparar-anova-m11.py",
    "eph/bivariada-m03.json": "eph/preparar-bivariada-m03.py",
    "eph/cobertura-ic.json": "eph/preparar-cobertura-ic.py",
    "eph/descriptivos-m02.json": "eph/preparar-descriptivos-m02.py",
    "eph/diseno-complejo-m17.json": "eph/preparar-diseno-complejo-m17.py",
    "eph/ingresos-eph.json": "eph/preparar-ingresos-eph.py",
    "eph/lognormal-m07.json": "eph/preparar-lognormal-m07.py",
    "eph/multivariado-m14.json": "eph/preparar-multivariado-m14.py",
    "eph/no-parametricas-m12.json": "eph/preparar-no-parametricas-m12.py",
    "eph/probabilidad-m06.json": "eph/preparar-probabilidad-m06.py",
    "eph/pruebas-m10.json": "eph/preparar-pruebas-m10.py",
    "eph/regresion-m13.json": "eph/preparar-regresion-m13.py",
    "eph/tablas-m02.json": "eph/preparar-tablas-m02.py",
    "eph/tcl.json": "eph/preparar-tcl.py",
    "series/indices-m04.json": "series/preparar-indices-m04.py",
}


def frente_forma() -> dict[str, dict]:
    cargados: dict[str, dict] = {}
    encontrados = {
        str(p.relative_to(DATOS)).replace("\\", "/")
        for p in DATOS.glob("*/*.json")
    }

    for huerfano in sorted(encontrados - set(GENERADOR)):
        problemas.append(
            f"{huerfano} no figura en GENERADOR: nadie sabe cómo regenerarlo"
        )

    for nombre, script in GENERADOR.items():
        ruta = DATOS / nombre
        cierto(f"{nombre} existe", ruta.exists())
        if not ruta.exists():
            continue
        d = leer(ruta)
        if d is None:
            continue
        cargados[nombre] = d
        cierto(f"{nombre} no está vacío", bool(d))
        texto = json.dumps(d, ensure_ascii=False).lower()
        cierto(f"{nombre} declara su fuente", "fuente" in texto)

        gen = DATOS / script
        cierto(f"{nombre}: su generador existe", gen.exists())
        if gen.exists() and gen.stat().st_mtime > ruta.stat().st_mtime:
            avisos.append(
                f"{nombre} es más viejo que {script}: hay que volver a correrlo"
            )
    return cargados


# ---------------------------------------------------------------------------
# 2 · La aritmética interna
# ---------------------------------------------------------------------------

def entre_cero_y_uno(etiqueta: str, valor: float) -> None:
    cierto(f"{etiqueta} está entre 0 y 1 ({valor:.6g})", 0 <= valor <= 1)


def frente_aritmetica(j: dict[str, dict]) -> None:
    # --- Demografía: pirámide, mercado de trabajo y Gini -------------------
    t = j.get("demografia/tasas-m05.json")
    if t:
        p = t["piramide"]
        suma = sum(p["varones"]) + sum(p["mujeres"])
        parecido("pirámide: varones + mujeres = población total",
                 suma, p["poblacion_total"], 1e-9)
        entre_cero_y_uno("pirámide: prop_0_14", p["prop_0_14"])
        entre_cero_y_uno("pirámide: prop_65_mas", p["prop_65_mas"])
        parecido("pirámide: el índice de envejecimiento sale de las dos proporciones",
                 p["indice_envejecimiento"],
                 p["prop_65_mas"] / p["prop_0_14"] * 100, 1e-6)
        parecido("pirámide: la razón de dependencia sale de las dos proporciones",
                 p["razon_dependencia"],
                 (p["prop_0_14"] + p["prop_65_mas"])
                 / (1 - p["prop_0_14"] - p["prop_65_mas"]) * 100, 1e-6)
        cierto("pirámide: los siete grupos tienen su barra",
               len(p["grupos"]) == len(p["varones"]) == len(p["mujeres"]) == 7)

        m = t["mercado_trabajo"]
        parecido("mercado: ocupados + desocupados = PEA",
                 m["ocupados"] + m["desocupados"], m["pea"], 1e-9)
        parecido("mercado: la tasa de actividad es PEA sobre población",
                 m["tasa_actividad"], m["pea"] / m["poblacion_total"], 1e-9)
        parecido("mercado: la tasa de empleo es ocupados sobre población",
                 m["tasa_empleo"], m["ocupados"] / m["poblacion_total"], 1e-9)
        parecido("mercado: la desocupación se calcula sobre la PEA, no sobre la población",
                 m["tasa_desocupacion"], m["desocupados"] / m["pea"], 1e-9)

        g = t["gini"]
        entre_cero_y_uno("Gini: está entre 0 y 1", g["gini"])
        q = g["curva_q"]
        cierto("Lorenz: la curva arranca en 0", abs(q[0]) < 1e-9)
        cierto("Lorenz: la curva termina en 1", abs(q[-1] - 1) < 1e-9)
        cierto("Lorenz: la curva no decrece",
               all(q[i] <= q[i + 1] + 1e-12 for i in range(len(q) - 1)))
        cierto("Lorenz: la curva queda por debajo de la diagonal",
               all(v <= i / (len(q) - 1) + 1e-12 for i, v in enumerate(q)))
        ac = g["acumulado_por_decil"]
        shares = [ac[i + 1] - ac[i] for i in range(10)]
        parecido("Gini: los diez deciles suman 1", sum(shares), 1.0, 1e-9)
        parecido("Gini: el share del decil 1 coincide con la curva",
                 g["share_decil_1"], shares[0], 1e-9)
        parecido("Gini: el share del decil 10 coincide con la curva",
                 g["share_decil_10"], shares[-1], 1e-9)
        parecido("Gini: la razón 10/1 es el cociente de los dos shares",
                 g["razon_10_1"], shares[-1] / shares[0], 1e-9)
        cierto("Gini: los deciles no decrecen",
               all(shares[i] <= shares[i + 1] + 1e-12 for i in range(9)))

        d = t["defunciones_2023"]
        entre_cero_y_uno("defunciones: prop_65_y_mas", d["prop_65_y_mas"])
        cierto("defunciones: los menores de 1 año no superan el total",
               0 < d["menores_de_1"] < d["total"])

        e = t["estandarizacion"]
        parecido("estandarización: la estructura de referencia suma 1",
                 sum(e["estructura_referencia"].values()), 1.0, 1e-9)

    # --- ANOVA -------------------------------------------------------------
    a = j.get("eph/anova-m11.json")
    if a:
        n = a["anova"]
        parecido("ANOVA: SC entre + SC dentro = SC total",
                 n["sc_entre"] + n["sc_dentro"], n["sc_total"], 1e-9)
        parecido("ANOVA: CM entre = SC entre / gl entre",
                 n["cm_entre"], n["sc_entre"] / n["gl_entre"], 1e-9)
        parecido("ANOVA: CM dentro = SC dentro / gl dentro",
                 n["cm_dentro"], n["sc_dentro"] / n["gl_dentro"], 1e-9)
        parecido("ANOVA: F = CM entre / CM dentro",
                 n["F"], n["cm_entre"] / n["cm_dentro"], 1e-9)
        parecido("ANOVA: eta² = SC entre / SC total",
                 n["eta2"], n["sc_entre"] / n["sc_total"], 1e-9)
        cierto("ANOVA: gl entre = k − 1", n["gl_entre"] == n["k"] - 1)
        cierto("ANOVA: gl dentro = N − k", n["gl_dentro"] == n["N"] - n["k"])
        cierto("ANOVA: omega² no supera a eta²", n["omega2"] <= n["eta2"])
        cierto("ANOVA: los n de los grupos suman N",
               sum(g["n"] for g in a["descriptivos"]) == n["N"])
        total = sum(g["n"] * g["media"] for g in a["descriptivos"])
        parecido("ANOVA: la media general es el promedio ponderado de los grupos",
                 a["media_general"], total / n["N"], 1e-7)

        # Welch. Nació de un bug real: la clave `welch_F` guardaba el
        # estadístico de Alexander-Govern, que es otra prueba y está en escala
        # chi-cuadrado, no F. Daba 865 donde el F de Welch vale 184.
        w = a.get("welch")
        if w:
            parecido("ANOVA/Welch: F clásico coincide con el del bloque anova",
                     w["F_clasico"], n["F"], 1e-9)
            cierto("ANOVA/Welch: gl1 = k − 1", w["welch_gl1"] == n["k"] - 1)
            cierto("ANOVA/Welch: gl2 positivo y por debajo de los gl del clásico",
                   0 < w["welch_gl2"] <= n["gl_dentro"])
            cierto("ANOVA/Welch: el F de Welch NO es el de Alexander-Govern",
                   w["welch_F"] != w["alexander_govern_A"])
            cierto("ANOVA/Welch: los dos p son de pruebas distintas",
                   w["welch_p"] != w["alexander_govern_p"])
            cierto("ANOVA/Welch: el F de Welch está en la escala del clásico",
                   0.2 < w["welch_F"] / n["F"] < 5)
            cierto("ANOVA/Alexander-Govern: A está en escala chi², no F",
                   w["alexander_govern_A"] > w["welch_F"])

        # Tipos de suma de cuadrados en el diseño desbalanceado de 2 factores.
        s = a.get("dos_factores", {}).get("sumas_de_cuadrados")
        if s:
            t1e, t1s, t3 = (s["tipo_I_educacion_primero"],
                            s["tipo_I_sexo_primero"], s["tipo_III"])
            parecido("ANOVA 2f: el residual no depende del orden",
                     t1e["Residual"]["sc"], t1s["Residual"]["sc"], 1e-6)
            parecido("ANOVA 2f: el residual del tipo III es el mismo",
                     t3["Residual"]["sc"], t1e["Residual"]["sc"], 1e-6)
            for f in ("C(sec)", "C(sexo)"):
                parecido(f"ANOVA 2f: tipo III de {f} es su tipo I entrando último",
                         t3[f]["sc"],
                         (t1s if f == "C(sec)" else t1e)[f]["sc"], 1e-6)
            mod1 = t1e["C(sec)"]["sc"] + t1e["C(sexo)"]["sc"]
            parecido("ANOVA 2f: las tipo I suman lo mismo en los dos órdenes",
                     mod1, t1s["C(sec)"]["sc"] + t1s["C(sexo)"]["sc"], 1e-6)
            cierto("ANOVA 2f: las tipo III suman de más (diseño desbalanceado)",
                   t3["C(sec)"]["sc"] + t3["C(sexo)"]["sc"] > mod1)
            cierto("ANOVA 2f: el orden cambia la SC de cada factor",
                   t1e["C(sec)"]["sc"] != t1s["C(sec)"]["sc"])

        # La interacción no es invariante a la escala: en pesos no da
        # significativa y en logaritmos sí. Es el hallazgo de la entrada.
        ci = a.get("dos_factores", {}).get("con_interaccion")
        if ci:
            for esc in ("pesos", "logaritmo"):
                e = ci[esc]
                cierto(f"ANOVA 2f/{esc}: la interacción tiene 1 gl",
                       e["C(sec):C(sexo)"]["gl"] == 1)
                cierto(f"ANOVA 2f/{esc}: los efectos principales rechazan",
                       e["C(sec)"]["p"] < 1e-30 and e["C(sexo)"]["p"] < 1e-30)
                for f, v in e.items():
                    if f == "Residual":
                        continue
                    cierto(f"ANOVA 2f/{esc}: eta² parcial de {f} entre 0 y 1",
                           0 <= v["eta2_parcial"] <= 1)
            cierto("ANOVA 2f: en pesos la interacción NO es significativa",
                   ci["pesos"]["C(sec):C(sexo)"]["p"] > 0.05)
            cierto("ANOVA 2f: en logaritmos la interacción SÍ lo es",
                   ci["logaritmo"]["C(sec):C(sexo)"]["p"] < 1e-20)
            cierto("ANOVA 2f: el residual tiene los mismos gl en las dos escalas",
                   ci["pesos"]["Residual"]["gl"]
                   == ci["logaritmo"]["Residual"]["gl"])

    # --- Bivariada ---------------------------------------------------------
    b = j.get("eph/bivariada-m03.json")
    if b:
        for clave, v in b.items():
            if not isinstance(v, dict) or "pearson" not in v:
                continue
            cierto(f"bivariada/{clave}: |r| ≤ 1", abs(v["pearson"]) <= 1)
            parecido(f"bivariada/{clave}: r² es el cuadrado de r",
                     v["r2"], v["pearson"] ** 2, 1e-6)
            if {"covarianza", "sx", "b1"} <= v.keys():
                parecido(f"bivariada/{clave}: la pendiente es cov / sx²",
                         v["b1"], v["covarianza"] / v["sx"] ** 2, 1e-6)

    # --- Probabilidad ------------------------------------------------------
    p6 = j.get("eph/probabilidad-m06.json")
    if p6:
        conj = p6["conjunta"]
        parecido("probabilidad: las cuatro conjuntas suman 1",
                 sum(conj.values()), 1.0, 1e-9)
        for k, v in conj.items():
            entre_cero_y_uno(f"probabilidad: conjunta {k}", v)
        ms = p6["marginal_secundario"]
        mr = p6["marginal_registrado"]
        parecido("probabilidad: la marginal de secundario suma 1",
                 sum(ms.values()), 1.0, 1e-9)
        parecido("probabilidad: la marginal de registrado suma 1",
                 sum(mr.values()), 1.0, 1e-9)
        for s in ("0", "1"):
            parecido(
                f"probabilidad: P(reg=1|sec={s}) es conjunta sobre marginal",
                p6["cond_registrado_dado_secundario"][s],
                conj[f"sec{s}_reg1"] / ms[s], 1e-9)

    # --- Ingresos ----------------------------------------------------------
    i = j.get("eph/ingresos-eph.json")
    if i:
        cierto("ingresos: la mediana no supera a la media (distribución asimétrica a la derecha)",
               i["mediana"] <= i["media"])
        cierto("ingresos: los cuartiles están ordenados",
               i["minimo"] <= i["q1"] <= i["mediana"] <= i["q3"] <= i["maximo"])
        parecido("ingresos: el rango intercuartílico es q3 − q1",
                 i["ric"], i["q3"] - i["q1"], 1e-6)
        redondeado("ingresos: el CV es desvío sobre media",
                   i["cv"], i["desvio"] / i["media"], 3)
        redondeado("ingresos: la razón media/mediana",
                   i["razon_media_mediana"], i["media"] / i["mediana"], 3)
        # Son los nueve cortes D1..D9, no diez grupos.
        cortes = [i["deciles"][f"D{k}"] for k in range(1, 10)]
        cierto("ingresos: están los nueve cortes de decil", len(i["deciles"]) == 9)
        cierto("ingresos: los cortes de decil no decrecen",
               all(cortes[k] <= cortes[k + 1] for k in range(8)))
        cierto("ingresos: la mediana es el quinto corte",
               abs(i["mediana"] - cortes[4]) < 1e-6)

    # --- Índices y series --------------------------------------------------
    s = j.get("series/indices-m04.json")
    if s:
        ipc = s["ipc"]
        cierto("IPC: el índice del último mes es positivo", ipc["indice_ultimo"] > 0)
        cb = s["cambio_de_base"]
        parecido("cambio de base: el factor es 100 sobre el índice de la base nueva",
                 cb["factor"], 100 / cb["indice_dic_2023_en_base_vieja"], 1e-9)
        parecido("cambio de base: el último índice reexpresado",
                 cb["ejemplo_ultimo_en_base_nueva"],
                 ipc["indice_ultimo"] * cb["factor"], 1e-9)
        de = s["deflactacion"]
        parecido("deflactación: el factor es el cociente de los dos IPC promedio",
                 de["factor"], de["ipc_promedio_1T2026"] / de["ipc_promedio_1T2025"],
                 1e-9)
        parecido("deflactación: el monto a precios del año anterior",
                 de["media_a_precios_1T2025"],
                 de["media_nominal_1T2026"] / de["factor"], 1e-9)
        per = s["pernoctes"]
        ie = per["indices_estacionales"]
        cierto("pernoctes: hay doce índices estacionales", len(ie) == 12)
        parecido("pernoctes: los índices estacionales promedian 1",
                 sum(ie.values()) / 12, 1.0, 1e-9)
        parecido("pernoctes: la razón máx/mín de los estacionales",
                 per["razon_max_min_estacional"],
                 max(ie.values()) / min(ie.values()), 1e-9)
        cierto("pernoctes: el máximo de la serie supera al mínimo",
               per["maximo"]["valor"] > per["minimo"]["valor"])

    # --- Diseño complejo ---------------------------------------------------
    dc = j.get("eph/diseno-complejo-m17.json")
    if dc:
        for r in dc["resultados"]:
            nom = r["indicador"]
            parecido(f"diseño/{nom}: deff es el cuadrado de la razón de EE",
                     r["deff"], r["razon_ee"] ** 2, 1e-9)
            parecido(f"diseño/{nom}: razón de EE",
                     r["razon_ee"], r["ee_conglomerados"] / r["ee_simple"], 1e-9)
            parecido(f"diseño/{nom}: n efectivo es n sobre deff",
                     r["n_efectivo"], r["n"] / r["deff"], 1e-9)
            cierto(f"diseño/{nom}: el EE con diseño no es menor que el simple",
                   r["ee_conglomerados"] >= r["ee_simple"])
            cierto(f"diseño/{nom}: hay menos viviendas que personas",
                   r["conglomerados"] <= r["n"])

        for e in dc["estratificacion"]:
            nom = e["indicador"]
            parecido(f"estrato/{nom}: deff sin estrato es el cuadrado del cociente",
                     e["deff_solo_conglomerado"],
                     (e["ee_solo_conglomerado"] / e["ee_simple"]) ** 2, 1e-9)
            parecido(f"estrato/{nom}: deff con estrato es el cuadrado del cociente",
                     e["deff_con_estrato"],
                     (e["ee_con_estrato"] / e["ee_simple"]) ** 2, 1e-9)
            parecido(f"estrato/{nom}: el exceso es el cociente de los dos EE",
                     e["exceso"],
                     e["ee_solo_conglomerado"] / e["ee_con_estrato"] - 1, 1e-9)
            # Los dos deff describen el mismo conglomerado: no pueden diferir
            # en un orden de magnitud, y ninguno puede quedar por debajo de 1.
            cierto(f"estrato/{nom}: los dos deff superan 1",
                   min(e["deff_solo_conglomerado"], e["deff_con_estrato"]) > 1)
            cierto(f"estrato/{nom}: los dos deff están en el mismo orden",
                   abs(e["exceso"]) < 0.25)

        for p in dc["estimacion_puntual"]:
            parecido(f"ponderar/{p['indicador']}: la diferencia relativa cierra",
                     p["dif_relativa"],
                     p["con_ponderar"] / p["sin_ponderar"] - 1, 1e-9)

        po = dc["ponderador"]
        cierto("ponderador: sin ponderar, la 'población' son los casos",
               po["sin ponderar"]["poblacion"] < 1e5)
        cierto("ponderador: PONDIIO expande a más gente que PONDERA "
               "sobre el mismo filtro",
               po["PONDIIO"]["poblacion"] > po["PONDERA"]["poblacion"])
        parecido("ponderador: PONDIIO es la referencia",
                 po["PONDIIO"]["dif_con_pondiio"], 0.0, 1e-12)
        for nom, v in po.items():
            parecido(f"ponderador/{nom}: la diferencia con PONDIIO cierra",
                     v["dif_con_pondiio"],
                     v["media"] / po["PONDIIO"]["media"] - 1, 1e-9)

        s = dc["subpoblacion"]
        parecido("subpoblación: la subestimación es el cociente de los EE",
                 s["subestimacion"],
                 1 - s["ee_filtrando_primero"] / s["ee_declarando_primero"],
                 1e-9)
        cierto("subpoblación: el subgrupo cabe en la muestra",
               s["viviendas_con_el_subgrupo"] <= s["viviendas_totales"])
        cierto("subpoblación: el subgrupo no tiene más viviendas que personas",
               s["viviendas_con_el_subgrupo"] <= s["n"])

    # --- Cobertura de intervalos -------------------------------------------
    c = j.get("eph/cobertura-ic.json")
    if c:
        cierto("cobertura: contienen + no contienen = cantidad de muestras",
               c["contienen"] + c["no_contienen"] == c["cantidad_de_muestras"])

    # --- Lognormal: las cuatro identidades que definen el ajuste -----------
    ln = j.get("eph/lognormal-m07.json")
    if ln:
        a = ln["lognormal_ajustada"]
        mu, s = a["mu"], a["sigma"]
        s2 = s * s
        parecido("lognormal: la media teórica es exp(mu + sigma²/2)",
                 a["media"], math.exp(mu + s2 / 2), 1e-9)
        parecido("lognormal: la mediana teórica es exp(mu)",
                 a["mediana"], math.exp(mu), 1e-9)
        parecido("lognormal: el modo teórico es exp(mu - sigma²)",
                 a["modo"], math.exp(mu - s2), 1e-9)
        parecido("lognormal: el CV teórico depende solo de sigma",
                 a["cv"], math.sqrt(math.exp(s2) - 1), 1e-9)
        cierto("lognormal: modo < mediana < media, que es el orden obligado",
               a["modo"] < a["mediana"] < a["media"])
        # mu y sigma salen del logaritmo, así que tienen que ser los mismos.
        parecido("lognormal: mu es la media del logaritmo",
                 mu, ln["log_ingreso"]["media"], 1e-12)
        parecido("lognormal: sigma es el desvío del logaritmo",
                 s, ln["log_ingreso"]["desvio"], 1e-12)

        cu = ln["cuantiles"]
        cierto("lognormal: los cuantiles observados crecen",
               all(a1["observado"] <= a2["observado"]
                   for a1, a2 in zip(cu, cu[1:])))
        cierto("lognormal: los cuantiles ajustados crecen",
               all(a1["lognormal"] <= a2["lognormal"]
                   for a1, a2 in zip(cu, cu[1:])))
        med = next(r for r in cu if r["q"] == 0.5)
        parecido("lognormal: el cuantil 0,5 ajustado es la mediana teórica",
                 med["lognormal"], a["mediana"], 1e-9)

        am = ln["amontonamiento"]
        parecido("amontonamiento: el total es la suma de los seis valores",
                 am["pct_en_los_6_mas_repetidos"],
                 sum(v["pct"] for v in am["valores"]), 1e-9)

        n = j.get("eph/lognormal-m07.json")["normal_ajustada"]
        cierto("normal ajustada al ingreso: su percentil 5 es negativo, "
               "que es el argumento contra usarla",
               n["p05"] < 0)

    # -- Absolutos contra tasas: un mapa de conteos es un mapa de población --
    de = j.get("demografia/tasas-m05.json")
    if de and "absolutos_vs_tasas" in de:
        av = de["absolutos_vs_tasas"]
        cierto("absolutos: las jurisdicciones son las del país",
               20 <= av["jurisdicciones"] <= 24)
        cierto("absolutos: la población es del orden de la Argentina",
               40e6 < av["poblacion"] < 50e6)
        cierto("absolutos: las defunciones son del orden anual conocido",
               300_000 < av["defunciones"] < 450_000)
        for k in ("correlacion_poblacion_absolutos", "correlacion_poblacion_tasa"):
            cierto(f"absolutos: {k} está entre -1 y 1", -1 <= av[k] <= 1)
        # El hallazgo: el mapa de conteos ES el mapa de población.
        cierto("absolutos: los conteos correlacionan casi perfecto con la "
               "población — el mapa no informa sobre el fenómeno",
               av["correlacion_poblacion_absolutos"] > 0.99)
        cierto("absolutos: la tasa rompe esa correlación",
               av["correlacion_poblacion_tasa"]
               < av["correlacion_poblacion_absolutos"] - 0.4)
        cierto("absolutos: normalizar cambia el ranking",
               av["cambio_medio_de_puesto"] > 1)
        t5 = av["top5_por_absolutos"]
        cierto("absolutos: el top 5 viene ordenado por conteo",
               all(a["defunciones"] >= b["defunciones"] for a, b in zip(t5, t5[1:])))
        cierto("absolutos: los puestos por conteo son 1 a 5",
               [x["puesto_absolutos"] for x in t5] == [1, 2, 3, 4, 5])
        cierto("absolutos: los puestos por tasa no son los mismos",
               [x["puesto_tasa"] for x in t5] != [1, 2, 3, 4, 5])
        for x in t5:
            parecido(f"absolutos: la tasa de {x['jurisdiccion']} es plausible",
                     min(max(x["tasa"], 3.0), 15.0), x["tasa"], 1e-9)

    # -- Codificación de P21: el faltante que parece un dato -----------------
    ie = j.get("eph/ingresos-eph.json")
    if ie and "codificacion" in ie:
        cd = ie["codificacion"]
        cierto("codificación: P21 no tiene ningún valor vacío",
               cd["p21_sin_vacios"])
        cierto("codificación: el único valor negativo de P21 es -9",
               cd["p21_valores_negativos"] == [-9])
        cierto("codificación: ESTADO=4 son exactamente los menores de 10",
               cd["estado_4_son_menores_de_10"])
        cierto("codificación: CH06 toma -1 y nada más abajo",
               cd["ch06_negativos"]["valores"] == [-1])
        pe = cd["por_estado"]
        cierto("codificación: están las cinco categorías de ESTADO",
               [f["estado"] for f in pe] == [0, 1, 2, 3, 4])
        cierto("codificación: las filas por estado suman el total",
               sum(f["n"] for f in pe) == cd["n_filas"])
        for f in pe:
            cierto(f"codificación: los tres conteos de {f['etiqueta']} suman su n",
                   f["p21_cero"] + f["p21_menos9"] + f["p21_positivo"] == f["n"])
            if f["estado"] != 1:
                cierto(f"codificación: fuera de los ocupados, {f['etiqueta']} "
                       "tiene P21 en cero — está fuera del universo",
                       f["p21_cero"] == f["n"])
        cierto("codificación: la no respuesta (-9) sólo existe entre ocupados",
               all(f["p21_menos9"] == 0 for f in pe if f["estado"] != 1))
        ocup = next(f for f in pe if f["estado"] == 1)
        parecido("codificación: el n del caso son los ocupados con ingreso",
                 float(ie["n"]), float(ocup["p21_positivo"]), 1e-9)
        pr = cd["promedios"]
        # El hallazgo: descartar los -9 casi no corrige; el problema son los ceros.
        cierto("promedios: promediar toda la columna subestima mucho",
               pr["toda_la_columna"] < 0.5 * pr["correcto_ocupados_con_ingreso"])
        cierto("promedios: descartar los -9 corrige sólo una parte chica",
               (pr["descartando_los_menos9"] - pr["toda_la_columna"])
               < 0.1 * (pr["correcto_ocupados_con_ingreso"] - pr["toda_la_columna"]))
        cierto("promedios: los ceros fuera de universo son la causa principal",
               sum(f["p21_cero"] for f in pe) > 20000)

    if ie and "no_respuesta" in ie:
        nr = ie["no_respuesta"]
        pb = nr["poblacion"]
        cierto("no respuesta: los ocupados coinciden con la tabla de codificación",
               nr["ocupados"] == next(f["n"] for f in ie["codificacion"]["por_estado"]
                                      if f["estado"] == 1))
        cierto("no respuesta: los que no responden son los P21 = -9",
               nr["no_respondieron"]
               == next(f["p21_menos9"] for f in ie["codificacion"]["por_estado"]
                       if f["estado"] == 1))
        parecido("no respuesta: el porcentaje es la razón de los dos conteos",
                 nr["pct_no_respuesta"],
                 100 * nr["no_respondieron"] / nr["ocupados"], 1e-9)
        cierto("no respuesta: todos los que no responden tienen PONDIIO cero",
               nr["pondiio_de_los_que_no_responden_es_cero"])
        # El hallazgo: el ponderador de ingresos reconstruye la población entera.
        cierto("no respuesta: PONDIIO reconstruye la misma población que PONDERA",
               abs(pb["pondiio_todos_los_ocupados"]
                   / pb["pondera_todos_los_ocupados"] - 1) < 0.001)
        cierto("no respuesta: usar PONDERA sólo sobre los que responden perdería "
               "una parte grande de la población",
               pb["pondera_de_los_que_responden"]
               < 0.8 * pb["pondera_todos_los_ocupados"])
        cierto("no respuesta: el peso redistribuido va a los que respondieron",
               pb["pondiio_de_los_que_responden"] > pb["pondera_de_los_que_responden"])
        for k, pf in nr["perfil"].items():
            cierto(f"perfil ({k}): las categorías ocupacionales no superan el 100 %",
                   pf["pct_asalariados"] + pf["pct_patrones"]
                   + pf["pct_cuenta_propia"] <= 100.0001)
            for c in ("pct_mujeres", "pct_superior", "pct_hasta_primario"):
                entre_cero_y_uno(f"perfil ({k}): {c} sobre 100", pf[c] / 100)
        a_, b_ = nr["perfil"]["no_respondieron"], nr["perfil"]["respondieron"]
        parecido("perfil: los n de los dos grupos son los de la tabla",
                 float(a_["n"]), float(nr["no_respondieron"]), 1e-9)
        # Dónde está el sesgo y dónde no.
        cierto("perfil: la no respuesta NO se diferencia por nivel educativo",
               abs(a_["pct_superior"] - b_["pct_superior"]) < 3)
        cierto("perfil: sí se diferencia por categoría ocupacional — hay más "
               "patrones entre los que no declaran",
               a_["pct_patrones"] > 1.5 * b_["pct_patrones"])
        ne = nr["no_respuesta_por_nivel_educativo"]
        cierto("perfil: los n por nivel educativo suman los ocupados con nivel",
               sum(x["n"] for x in ne) <= nr["ocupados"])
        cierto("perfil: la tasa por nivel educativo es plana, sin gradiente",
               max(x["pct"] for x in ne) - min(x["pct"] for x in ne) < 10)

    # -- Discriminante sobre el modelo de la logística -----------------------
    rg = j.get("eph/regresion-m13.json")
    if rg and "discriminante" in rg:
        di = rg["discriminante"]
        lo = rg["logistica"]
        cierto("discriminante: usa el mismo conjunto que la logística",
               di["n"] == lo["n"])
        cierto("discriminante: cuenta bien sus predictoras binarias",
               0 <= di["predictoras_binarias"] <= len(di["predictoras"]))
        parecido("discriminante: el acierto trivial es el del grupo mayor",
                 di["acierto_trivial"], lo["acierto_trivial"], 1e-9)
        for k, v in di["acierto"].items():
            entre_cero_y_uno(f"discriminante: acierto de {k}", v)
            cierto(f"discriminante: {k} le gana al acierto trivial",
                   v > di["acierto_trivial"])
        # El hallazgo: los cuatro métodos coinciden pese a que tres de las
        # cuatro predictoras son binarias.
        cierto("discriminante: los cuatro métodos aciertan casi lo mismo, "
               "aunque el LDA suponga normalidad y las predictoras sean binarias",
               max(di["acierto"].values()) - min(di["acierto"].values()) < 0.005)
        cierto("discriminante: la ganancia sobre el trivial es modesta",
               max(di["acierto"].values()) - di["acierto_trivial"] < 0.10)
        bm = di["box_m"]
        parecido("M de Box: los grados de libertad son p(p+1)/2 con dos grupos",
                 bm["gl"], len(di["predictoras"]) * (len(di["predictoras"]) + 1) / 2,
                 1e-9)
        cierto("M de Box: el estadístico es positivo", bm["chi2"] > 0)
        entre_cero_y_uno("M de Box: el valor p", bm["p"])
        cierto("M de Box: rechaza con contundencia y aun así el lineal no pierde "
               "— es el hallazgo de la entrada",
               bm["p"] < 0.001
               and di["acierto"]["lda"] >= di["acierto"]["qda"])

    if rg and "caja_negra" in rg:
        cn = rg["caja_negra"]
        cierto("caja negra: usa el mismo conjunto que la logística",
               cn["n"] == rg["logistica"]["n"])
        parecido("caja negra: el acierto trivial es el mismo",
                 cn["acierto_trivial"], rg["logistica"]["acierto_trivial"], 1e-9)
        cjs = cn["conjuntos"]
        cierto("caja negra: los conjuntos de variables van de menos a más",
               all(a["variables"] < b["variables"] for a, b in zip(cjs, cjs[1:])))
        for c in cjs:
            for k, v in c["acierto"].items():
                entre_cero_y_uno(f"caja negra: acierto de {k} con "
                                 f"{c['variables']} variables", v)
                cierto(f"caja negra: {k} con {c['variables']} variables supera "
                       "al acierto trivial",
                       v > cn["acierto_trivial"])
        base_c, ancho_c = cjs[0], cjs[1]
        # Los dos hallazgos de la entrada.
        cierto("caja negra: con pocas variables la ventaja sobre la logística "
               "es mínima",
               max(base_c["acierto"].values()) - base_c["acierto"]["logistica"]
               < 0.02)
        cierto("caja negra: agregar variables rinde mucho más que cambiar de "
               "método — el hallazgo de la entrada",
               (ancho_c["acierto"]["logistica"] - base_c["acierto"]["logistica"])
               > 5 * (max(base_c["acierto"].values())
                      - base_c["acierto"]["logistica"]))
        cierto("caja negra: con muchas variables la ventaja del boosting sí "
               "aparece",
               ancho_c["acierto"]["boosting"] - ancho_c["acierto"]["logistica"]
               > 0.02)

    # -- Multivariado: el PCA, la línea de base de ruido y la estabilidad ----
    mv = j.get("eph/multivariado-m14.json")
    if mv:
        p_var = len(mv["variables"])
        pca = mv["pca"]
        vp = pca["valores_propios"]
        parecido("PCA: los valores propios de una matriz de correlaciones "
                 "suman la cantidad de variables",
                 sum(vp), float(p_var), 1e-9)
        cierto("PCA: los valores propios vienen de mayor a menor",
               all(a >= b - 1e-12 for a, b in zip(vp, vp[1:])))
        cierto("PCA: todos los valores propios son no negativos",
               all(v >= -1e-12 for v in vp))
        for k in range(p_var):
            parecido(f"PCA: la proporción del CP{k + 1} es su valor propio sobre {p_var}",
                     pca["prop_varianza"][k], vp[k] / p_var, 1e-12)
        parecido("PCA: la proporción acumulada llega a 1",
                 pca["prop_acumulada"][-1], 1.0, 1e-9)
        cierto("PCA: la cantidad de componentes de Kaiser cuenta los "
               "valores propios mayores a 1",
               pca["n_componentes_kaiser"] == sum(1 for v in vp if v > 1))
        for nombre in ("cargas_cp1", "cargas_cp2"):
            parecido(f"PCA: {nombre} es un vector de norma 1",
                     sum(c * c for c in pca[nombre].values()), 1.0, 1e-9)

        lb = mv["linea_de_base"]
        # La línea de base tiene que ser la del MISMO tamaño de matriz.
        cierto("línea de base: se simuló la forma de la matriz real",
               f"{mv['n_aglomerados']}x{p_var}" in lb["descripcion"])
        entre_cero_y_uno("línea de base: varianza del CP1 con ruido",
                         lb["cp1_prop_ruido"])
        entre_cero_y_uno("línea de base: proporción de ruido con 4 componentes o más",
                         lb["kaiser_ruido_p_mayor_igual_4"])
        entre_cero_y_uno("línea de base: mayor |r| medio del ruido",
                         lb["max_r_ruido_medio"])
        parecido("línea de base: la varianza del CP1 real es su valor propio "
                 "sobre la cantidad de variables",
                 lb["cp1_prop_real"], vp[0] / p_var, 1e-12)
        # Con p variables independientes el valor propio medio es 1, así que
        # el CP1 del ruido tiene que explicar más de 1/p y menos que el real.
        cierto("línea de base: el CP1 del ruido explica más que el reparto "
               "parejo de 1/p",
               lb["cp1_prop_ruido"] > 1 / p_var)
        cierto("línea de base: el CP1 real supera al del ruido",
               lb["cp1_prop_real"] > lb["cp1_prop_ruido"])
        cierto("línea de base: las acumuladas del ruido crecen",
               lb["cp1_prop_ruido"] < lb["acum2_ruido"] < lb["acum4_ruido"])
        cierto("línea de base: superar 0,60 es más raro que superar 0,50",
               lb["max_r_ruido_supera_060"] < lb["max_r_ruido_supera_050"])
        cierto("línea de base: el mayor |r| real supera al del ruido",
               lb["max_r_real"] > lb["max_r_ruido_medio"])
        cierto("línea de base: el criterio de Kaiser no distingue señal de "
               "ruido con esta matriz — es el hallazgo de la entrada",
               abs(lb["kaiser_ruido_medio"] - pca["n_componentes_kaiser"]) < 1)

        par = lb["paralelo"]
        cierto("análisis paralelo: hay una fila por componente",
               len(par) == p_var)
        cierto("análisis paralelo: el valor real de cada fila es su valor propio",
               all(abs(f["real"] - vp[i]) < 1e-12 for i, f in enumerate(par)))
        cierto("análisis paralelo: el p95 del ruido supera a su media",
               all(f["ruido_p95"] > f["ruido_medio"] for f in par))
        cierto("análisis paralelo: los valores propios medios del ruido "
               "también van de mayor a menor",
               all(a["ruido_medio"] >= b["ruido_medio"] for a, b in zip(par, par[1:])))
        parecido("análisis paralelo: los valores propios medios del ruido "
                 "suman la cantidad de variables",
                 sum(f["ruido_medio"] for f in par), float(p_var), 1e-6)
        cierto("análisis paralelo: 'supera' es real > p95 del ruido",
               all(f["supera"] == (f["real"] > f["ruido_p95"]) for f in par))
        cierto("análisis paralelo: retiene menos componentes que Kaiser",
               lb["n_componentes_paralelo"] <= pca["n_componentes_kaiser"])

        for k, s in lb["silueta"].items():
            cierto(f"silueta k={k}: la del ruido está entre -1 y 1",
                   -1 <= s["ruido_medio"] <= 1)
            cierto(f"silueta k={k}: la real está entre -1 y 1",
                   -1 <= s["real"] <= 1)
            cierto(f"silueta k={k}: el p95 del ruido supera a su media",
                   s["ruido_p95"] > s["ruido_medio"])
            cierto(f"silueta k={k}: el ruido NUNCA devuelve cero — "
                   "no existe la salida 'acá no hay grupos'",
                   s["ruido_medio"] > 0.05)

        se = mv["sin_estandarizar"]
        cierto("sin estandarizar: el CP1 se come casi toda la varianza",
               se["cp1_prop"] > 0.95)
        cierto("sin estandarizar: explica muchísimo más que estandarizando",
               se["cp1_prop"] > 2 * se["cp1_prop_estandarizado"])
        parecido("sin estandarizar: las cargas del CP1 son un vector de norma 1",
                 sum(c * c for c in se["cargas_cp1"].values()), 1.0, 1e-9)
        cierto("sin estandarizar: el CP1 es la variable de mayor desvío",
               max(se["cargas_cp1"], key=se["cargas_cp1"].get)
               == max(mv["desvios"], key=mv["desvios"].get))

        mz = mv["matriz"]
        cierto("matriz: p variables dan p(p-1)/2 correlaciones distintas",
               mz["n_correlaciones"] == p_var * (p_var - 1) // 2)
        for clave in ("abs_r_medio", "abs_parcial_medio",
                      "abs_r_maximo", "abs_parcial_maximo", "kmo"):
            entre_cero_y_uno(f"matriz: {clave}", mz[clave])
        cierto("matriz: el |r| máximo no es menor que el medio",
               mz["abs_r_maximo"] >= mz["abs_r_medio"])
        cierto("matriz: el |parcial| máximo no es menor que el medio",
               mz["abs_parcial_maximo"] >= mz["abs_parcial_medio"])
        cierto("matriz: los pares que cambian de signo no superan el total",
               0 <= mz["cambian_de_signo"] <= mz["n_correlaciones"])
        cierto("matriz: el mayor |r| de los pares listados coincide con el máximo",
               abs(max(abs(pr["r"]) for pr in mz["pares"]) - mz["abs_r_maximo"]) < 1e-9)
        cierto("matriz: los pares vienen ordenados por |r| decreciente",
               all(abs(a["r"]) >= abs(b["r"]) - 1e-12
                   for a, b in zip(mz["pares"], mz["pares"][1:])))
        cierto("matriz: cada par relaciona dos variables distintas de la lista",
               all(pr["a"] in mv["variables"] and pr["b"] in mv["variables"]
                   and pr["a"] != pr["b"] for pr in mz["pares"]))
        # El hallazgo: la correlación parcial NO es sistemáticamente más chica.
        cierto("matriz: la correlación parcial media supera a la marginal — "
               "desmiente que 'la parcial siempre es más chica'",
               mz["abs_parcial_medio"] > mz["abs_r_medio"])

        # Casi singular: determinante, valor propio mínimo, condición y VIF
        # tienen que contar la misma historia.
        cierto("matriz: el determinante es el producto de los valores propios",
               0 < mz["determinante"] < 1)
        parecido("matriz: el número de condición es el cociente de los valores "
                 "propios extremos",
                 mz["numero_condicion"], vp[0] / mz["valor_propio_minimo"], 1e-6)
        parecido("matriz: el valor propio mínimo es el último del PCA",
                 mz["valor_propio_minimo"], vp[-1], 1e-9)
        cierto("matriz: todos los VIF valen al menos 1",
               all(v >= 1 - 1e-9 for v in mz["vif"].values()))
        cierto("matriz: un determinante casi nulo va con un VIF enorme",
               (mz["determinante"] < 1e-6) == (max(mz["vif"].values()) > 100))

        ie = mz["identidad_empleo"]
        cierto("identidad: empleo = actividad x (1 - desocupación/100) cierra "
               "dentro del redondeo de un decimal",
               ie["error_maximo_pp"] < 0.5)
        cierto("identidad: el error medio no supera al máximo",
               ie["error_medio_pp"] <= ie["error_maximo_pp"])
        cierto("identidad: la fórmula reproduce el empleo casi exactamente",
               ie["correlacion"] > 0.999)
        cierto("identidad: por eso el parcial de empleo/actividad roza 1",
               any(set((pr["a"], pr["b"])) == {"empleo", "actividad"}
                   and abs(pr["parcial"]) > 0.99 for pr in mz["pares"]))

        sn = mz["sin_empleo"]
        cierto("sin empleo: el determinante mejora en órdenes de magnitud",
               sn["determinante"] > 100 * mz["determinante"])
        cierto("sin empleo: el VIF máximo baja mucho",
               sn["vif_maximo"] < max(mz["vif"].values()) / 10)
        cierto("sin empleo: el KMO mejora", sn["kmo"] > mz["kmo"])
        entre_cero_y_uno("sin empleo: KMO", sn["kmo"])

        ba = mz["bartlett"]
        parecido("Bartlett: los grados de libertad son p(p-1)/2",
                 ba["gl"], p_var * (p_var - 1) / 2, 1e-9)
        cierto("Bartlett: el estadístico es positivo con determinante menor a 1",
               ba["chi2"] > 0)
        entre_cero_y_uno("Bartlett: el valor p", ba["p"])
        cierto("Bartlett: rechaza, que es lo que tiene que pasar con estructura",
               ba["p"] < 0.05)

        cierto("sensibilidad: se listan tres aglomerados",
               len(mz["sensibilidad_top3"]) == 3)
        cierto("sensibilidad: vienen del mayor cambio al menor",
               all(a["cambio"] >= b["cambio"] for a, b in
                   zip(mz["sensibilidad_top3"], mz["sensibilidad_top3"][1:])))
        for s in mz["sensibilidad_top3"]:
            parecido(f"sensibilidad ({s['aglomerado']}): el cambio es la "
                     "diferencia entre las dos correlaciones",
                     s["cambio"], abs(s["r_sin"] - s["r_con"]), 1e-9)
            cierto(f"sensibilidad ({s['aglomerado']}): las dos correlaciones "
                   "están entre -1 y 1",
                   -1 <= s["r_con"] <= 1 and -1 <= s["r_sin"] <= 1)
        cierto("sensibilidad: el cambio medio no supera al mayor",
               mz["sensibilidad_cambio_medio"] <= mz["sensibilidad_top3"][0]["cambio"])

        ec = mv["escaladores"]["comparacion"]
        cierto("escaladores: 'z' es la referencia y se compara consigo misma",
               abs(ec["z"]["congruencia_cp1_con_z"] - 1) < 1e-9
               and abs(ec["z"]["ari_grupos_con_z"] - 1) < 1e-9)
        parecido("escaladores: la varianza del CP1 con z es la del PCA estandarizado",
                 ec["z"]["cp1_prop"], vp[0] / p_var, 1e-9)
        parecido("escaladores: sin escalar coincide con el bloque sin estandarizar",
                 ec["sin escalar"]["cp1_prop"], se["cp1_prop"], 1e-9)
        for modo, c in ec.items():
            entre_cero_y_uno(f"escaladores: varianza del CP1 con {modo}",
                             c["cp1_prop"])
            cierto(f"escaladores: la congruencia del CP1 con {modo} no pasa de 1",
                   c["congruencia_cp1_con_z"] <= 1 + 1e-9)
            cierto(f"escaladores: el ARI con {modo} no pasa de 1",
                   c["ari_grupos_con_z"] <= 1 + 1e-9)
            cierto(f"escaladores: los grupos de {modo} reparten los "
                   f"{mv['n_aglomerados']} aglomerados",
                   sum(c["tamanios_grupos"]) == mv["n_aglomerados"])
            cierto(f"escaladores: {modo} devuelve la cantidad de grupos pedida",
                   len(c["tamanios_grupos"]) == mv["escaladores"]["k_grupos"])
        # El hallazgo de la entrada: para el CP1 el escalador casi no importa
        # y para los conglomerados sí.
        cierto("escaladores: entre z, min-max y robusta el CP1 casi no se mueve",
               all(ec[m]["congruencia_cp1_con_z"] > 0.90
                   for m in ("min-max", "robusta")))
        cierto("escaladores: los conglomerados sí cambian con el escalador",
               all(ec[m]["ari_grupos_con_z"] < 0.75
                   for m in ("min-max", "robusta")))
        cierto("escaladores: no escalar se aparta más que cualquier escalador",
               ec["sin escalar"]["congruencia_cp1_con_z"]
               < min(ec[m]["congruencia_cp1_con_z"] for m in ("min-max", "robusta")))

        dz = mv["distancias"]["comparacion"]
        cierto("distancias: la euclídea es la referencia y coincide consigo misma",
               abs(dz["euclidea"]["correlacion_con_euclidea"] - 1) < 1e-9
               and all(abs(v - 1) < 1e-9
                       for enl in ("ari_complete", "ari_average")
                       for v in dz["euclidea"][enl].values()))
        for nombre, f in dz.items():
            cierto(f"distancias: la correlación de {nombre} con la euclídea "
                   "está entre -1 y 1",
                   -1 <= f["correlacion_con_euclidea"] <= 1)
            for enl in ("ari_complete", "ari_average"):
                cierto(f"distancias: {nombre} trae los cuatro k en {enl}",
                       sorted(f[enl]) == ["2", "3", "4", "5"])
                cierto(f"distancias: los ARI de {nombre} en {enl} no pasan de 1",
                       all(v <= 1 + 1e-9 for v in f[enl].values()))
        # Las tres Minkowski son variantes de la misma familia: sus matrices de
        # distancia tienen que parecerse mucho más que las de otra geometría.
        cierto("distancias: la familia Minkowski correlaciona más con la "
               "euclídea que el coseno o Mahalanobis",
               min(dz[m]["correlacion_con_euclidea"]
                   for m in ("manhattan", "minkowski_3"))
               > max(dz[m]["correlacion_con_euclidea"]
                     for m in ("coseno", "mahalanobis")))
        # El hallazgo de la entrada: correlación altísima y grupos distintos.
        cierto("distancias: Manhattan correlaciona más de 0,95 con la euclídea "
               "y aun así sus grupos difieren — es el hallazgo de la entrada",
               dz["manhattan"]["correlacion_con_euclidea"] > 0.95
               and dz["manhattan"]["ari_complete"]["2"] < 0.75)
        cierto("distancias: con enlace promedio el efecto de la distancia "
               "desaparece, y con enlace completo no",
               dz["manhattan"]["ari_average"]["2"]
               > dz["manhattan"]["ari_complete"]["2"])

        mh = mv["distancias"]["mahalanobis"]
        nobs = mv["n_aglomerados"]
        parecido("Mahalanobis: el techo algebraico es (n-1)²/n",
                 mh["techo_algebraico"], (nobs - 1) ** 2 / nobs, 1e-9)
        parecido("Mahalanobis: las d² suman (n-1)·p, que es una identidad",
                 mh["suma_d2"], mh["suma_d2_teorica"], 1e-6)
        parecido("Mahalanobis: la suma teórica es (n-1)·p",
                 mh["suma_d2_teorica"], float((nobs - 1) * p_var), 1e-9)
        cierto("Mahalanobis: con esta n el umbral queda por debajo del techo",
               mh["umbral_chi2_975"] < mh["techo_algebraico"])
        cierto("Mahalanobis: ninguna d² puede superar el techo",
               all(t["d2"] <= mh["techo_algebraico"] + 1e-9 for t in mh["top3"]))
        cierto("Mahalanobis: el top3 viene de mayor a menor",
               all(a["d2"] >= b["d2"] for a, b in zip(mh["top3"], mh["top3"][1:])))
        cierto("Mahalanobis: la cantidad de marcados no supera el total",
               0 <= mh["marcados"] <= nobs)
        cierto("Mahalanobis: el más lejano supera el umbral si hay marcados",
               (mh["marcados"] > 0) == (mh["top3"][0]["d2"] > mh["umbral_chi2_975"]))
        cierto("Mahalanobis: la variable más extrema de cada caso está en la lista",
               all(t["z_mas_extremo"] in mv["variables"] for t in mh["top3"]))

        pdt = mv["pca_detalle"]
        qa = pdt["quitando_un_aglomerado"]
        cierto("PCA: la congruencia mediana al sacar un caso no pasa de 1",
               qa["congruencia_mediana"] <= 1 + 1e-9)
        cierto("PCA: la congruencia mínima no supera a la mediana",
               qa["congruencia_minima"] <= qa["congruencia_mediana"])
        cierto("PCA: la dirección del CP1 aguanta que se saque un caso",
               qa["congruencia_mediana"] > 0.99)
        entre_cero_y_uno("PCA: proporción mínima del CP1", qa["prop_cp1_minima"])
        entre_cero_y_uno("PCA: proporción máxima del CP1", qa["prop_cp1_maxima"])
        cierto("PCA: la proporción con los 32 cae dentro del rango de sacar uno",
               qa["prop_cp1_minima"] <= vp[0] / p_var <= qa["prop_cp1_maxima"])
        cierto("PCA: la varianza explicada se mueve mucho más que la dirección — "
               "es el hallazgo de la entrada",
               (qa["prop_cp1_maxima"] - qa["prop_cp1_minima"]) > 0.05)
        cierto("PCA: los tres peores vienen de menor a mayor congruencia",
               all(a["congruencia"] <= b["congruencia"]
                   for a, b in zip(qa["peores"], qa["peores"][1:])))

        at = pdt["atipicos"]
        cierto("atípicos: la correlación de rangos está entre -1 y 1",
               -1 <= at["correlacion_rangos"] <= 1)
        for clave in ("top5_plano", "top5_completa"):
            cierto(f"atípicos: {clave} lista cinco aglomerados del conjunto",
                   len(at[clave]) == 5
                   and all(t["aglomerado"] in mv["clusters"]["grupos_3"]
                           for t in at[clave]))
            cierto(f"atípicos: {clave} viene de mayor a menor",
                   all(a["d2"] >= b["d2"] for a, b in zip(at[clave], at[clave][1:])))
        cierto("atípicos: el plano y la distancia completa NO dan el mismo orden",
               [t["aglomerado"] for t in at["top5_plano"]]
               != [t["aglomerado"] for t in at["top5_completa"]])

        cf = pdt["contra_factorial"]
        for j in ("congruencia_f1", "congruencia_f2"):
            cierto(f"factorial: {j} no pasa de 1", cf[j] <= 1 + 1e-9)
        cierto("factorial: las cargas del PCA y del factorial casi coinciden",
               min(cf["congruencia_f1"], cf["congruencia_f2"]) > 0.95)
        entre_cero_y_uno("factorial: comunalidad media del PCA",
                         cf["comunalidad_media_pca"])
        entre_cero_y_uno("factorial: comunalidad media del factorial",
                         cf["comunalidad_media_factorial"])
        cierto("factorial: el PCA se atribuye más varianza compartida que el "
               "factorial — el sesgo que la entrada mide",
               cf["comunalidad_media_pca"] > cf["comunalidad_media_factorial"])
        for c in cf["cargas"]:
            cierto(f"factorial: la variable {c['variable']} está en la lista",
                   c["variable"] in mv["variables"])
            cierto(f"factorial: las cargas de {c['variable']} están entre -1 y 1",
                   all(-1.0001 <= c[k] <= 1.0001
                       for k in ("pca_f1", "fa_f1", "pca_f2", "fa_f2")))

        codo = {int(k): v for k, v in mv["clusters"]["codo"].items()}
        ks = sorted(codo)
        cierto("codo: la inercia baja al agregar grupos",
               all(codo[a] >= codo[b] for a, b in zip(ks, ks[1:])))
        cierto("codo: con k=1 la inercia es la suma de cuadrados total",
               codo[1] == max(codo.values()))
        caidas = [(codo[a] - codo[b]) / codo[a] for a, b in zip(ks, ks[1:])]
        cierto("codo: todas las caídas son positivas",
               all(c > 0 for c in caidas))
        # El hallazgo de la entrada: la curva baja suave, sin codo. Un codo de
        # verdad hace que un paso caiga varias veces más que el siguiente.
        cierto("codo: el caso NO tiene un codo nítido — ningún paso cae más del "
               "doble que el siguiente",
               all(a < 2 * b for a, b in zip(caidas, caidas[1:])))

        ix = mv["indice"]
        cierto("índice: los indicadores están entre las variables del caso",
               all(v in mv["variables"] for v in ix["indicadores"]))
        parecido("índice: el peso nominal es 1 sobre la cantidad de indicadores",
                 ix["peso_nominal"], 1 / len(ix["indicadores"]), 1e-12)
        parecido("índice: los pesos efectivos suman 1",
                 sum(p["peso_efectivo"] for p in ix["pesos"]), 1.0, 1e-9)
        cierto("índice: hay un peso por indicador",
               len(ix["pesos"]) == len(ix["indicadores"]))
        cierto("índice: los pesos vienen de mayor a menor",
               all(a["peso_efectivo"] >= b["peso_efectivo"]
                   for a, b in zip(ix["pesos"], ix["pesos"][1:])))
        cierto("índice: todos los indicadores correlacionan positivamente con "
               "el índice — están orientados para que más sea mejor",
               all(p["correlacion_con_el_indice"] > 0 for p in ix["pesos"]))
        # El hallazgo: "pesos iguales" reparte cualquier cosa menos igual.
        cierto("índice: con pesos iguales, el peso efectivo mayor supera varias "
               "veces al menor",
               ix["pesos"][0]["peso_efectivo"]
               > 5 * ix["pesos"][-1]["peso_efectivo"])
        parecido("índice: las dimensiones reparten todos los indicadores",
                 sum(d["nominal"] for d in ix["por_dimension"]), 1.0, 1e-9)
        parecido("índice: las dimensiones reparten todo el peso efectivo",
                 sum(d["efectivo"] for d in ix["por_dimension"]), 1.0, 1e-9)
        cierto("índice: la dimensión con indicadores redundantes pesa más que "
               "su cuota nominal",
               next(d for d in ix["por_dimension"] if d["dimension"] == "ingresos")
               ["efectivo"] > next(d for d in ix["por_dimension"]
                                   if d["dimension"] == "ingresos")["nominal"])

        cierto("sensibilidad: el top 5 base tiene cinco aglomerados del caso",
               len(ix["top5_base"]) == 5
               and all(a in mv["clusters"]["grupos_3"] for a in ix["top5_base"]))
        for sv in ix["sensibilidad"]:
            cierto(f"sensibilidad: el Spearman de {sv['variante']} está entre -1 y 1",
                   -1 <= sv["spearman_con_base"] <= 1)
            cierto(f"sensibilidad: el movimiento de {sv['variante']} no supera "
                   "la cantidad de unidades",
                   0 <= sv["movimiento_mediano"] <= sv["movimiento_maximo"]
                   <= mv["n_aglomerados"])
        # Cambiar la normalización mueve poco; cambiar la agregación, mucho.
        cierto("sensibilidad: cambiar la normalización casi no mueve el ranking",
               all(sv["spearman_con_base"] > 0.95 for sv in ix["sensibilidad"]
                   if "suma" in sv["variante"]))
        cierto("sensibilidad: cambiar la agregación o pasar al PCA sí lo mueve",
               all(sv["spearman_con_base"] < 0.90 for sv in ix["sensibilidad"]
                   if "geométrica" in sv["variante"] or "PCA" in sv["variante"]))
        cierto("sensibilidad: todas las variantes cambian el top 5, incluso la "
               "que correlaciona 0,985 — es el hallazgo de la entrada",
               all(sv["cambia_el_top5"] for sv in ix["sensibilidad"]))

        iu = ix["incertidumbre_del_puesto"]
        cierto("puestos: hay un intervalo por aglomerado",
               len(iu["detalle"]) == mv["n_aglomerados"])
        cierto("puestos: los puestos van de 1 a n sin repetirse",
               sorted(r["puesto"] for r in iu["detalle"])
               == list(range(1, mv["n_aglomerados"] + 1)))
        cierto("puestos: el detalle viene ordenado por puesto",
               all(a["puesto"] < b["puesto"]
                   for a, b in zip(iu["detalle"], iu["detalle"][1:])))
        for r in iu["detalle"]:
            cierto(f"puestos: el intervalo de {r['aglomerado']} contiene su puesto "
                   "y cabe en el ranking",
                   1 <= r["ic_bajo"] <= r["puesto"] <= r["ic_alto"]
                   <= mv["n_aglomerados"])
        parecido("puestos: la amplitud mediana es la de los intervalos",
                 iu["amplitud_mediana"],
                 float(sorted(r["ic_alto"] - r["ic_bajo"]
                              for r in iu["detalle"])[len(iu["detalle"]) // 2 - 1]
                       + sorted(r["ic_alto"] - r["ic_bajo"]
                                for r in iu["detalle"])[len(iu["detalle"]) // 2]) / 2,
                 1e-9)
        cierto("puestos: el conteo de intervalos anchos coincide con el detalle",
               iu["con_ic_de_10_o_mas"]
               == sum(1 for r in iu["detalle"] if r["ic_alto"] - r["ic_bajo"] >= 10))
        # Y el hallazgo: el medio de la tabla no se distingue.
        cierto("puestos: la mayoría del ranking tiene un intervalo de diez "
               "posiciones o más",
               iu["con_ic_de_10_o_mas"] > mv["n_aglomerados"] / 2)
        cierto("puestos: los extremos sí son firmes",
               iu["detalle"][0]["ic_alto"] <= 2
               and iu["detalle"][-1]["ic_bajo"] >= mv["n_aglomerados"] - 6)

        dfm = mv["densidad_y_forma"]
        for k, v in dfm["metodos"].items():
            cierto(f"densidad y forma: el grupo de {k} sale de los aglomerados",
                   all(a in mv["clusters"]["grupos_3"] for a in v["grupo"]))
            cierto(f"densidad y forma: 'es patagonia exacta' de {k} coincide "
                   "con la lista",
                   v["es_patagonia_exacta"]
                   == (v["grupo"] == mv["enlaces"]["patagonia"]))
        cierto("densidad y forma: k-medias encuentra el grupo patagónico",
               dfm["metodos"]["k-medias"]["es_patagonia_exacta"])
        cierto("densidad y forma: el espectral se lo lleva con otros",
               not dfm["metodos"]["espectral"]["es_patagonia_exacta"]
               and len(dfm["metodos"]["espectral"]["grupo"]) > 4)

        bs = dfm["dbscan_barrido"]
        cierto("DBSCAN: el barrido recorre eps crecientes",
               all(a["eps"] < b["eps"] for a, b in zip(bs, bs[1:])))
        for b in bs:
            cierto(f"DBSCAN con eps={b['eps']}: los conteos son coherentes",
                   0 <= b["ruido"] <= mv["n_aglomerados"]
                   and 0 <= b["tamanio_grupo_de_ushuaia"] <= mv["n_aglomerados"])
        cierto("DBSCAN: al crecer eps el ruido no aumenta",
               all(a["ruido"] >= b["ruido"] for a, b in zip(bs, bs[1:])))
        # El hallazgo: ningún eps encuentra el grupo.
        cierto("DBSCAN: ningún eps del barrido encuentra el grupo patagónico",
               dfm["dbscan_encuentra_patagonia"] is False
               and not any(b["es_patagonia_exacta"] for b in bs))
        dg = dfm["diagnostico"]
        cierto("diagnóstico: el grupo patagónico está separado del resto",
               dg["distancia_media_entre_patagonicos"] < dg["distancia_media_al_resto"])
        cierto("diagnóstico: y a la vez es menos denso que el resto — por eso "
               "DBSCAN lo toma por ruido",
               dg["distancia_media_a_3_vecinos_patagonia"]
               > dg["distancia_media_a_3_vecinos_resto"])

        gm = dfm["mezclas_no_se_pueden_ajustar"]
        parecido("mezclas: los parámetros son 3(p+p)+2",
                 float(gm["parametros"]), float(3 * (p_var + p_var) + 2), 1e-9)
        cierto("mezclas: las observaciones son los aglomerados",
               gm["observaciones"] == mv["n_aglomerados"])
        cierto("mezclas: hay más parámetros que observaciones",
               gm["parametros"] > gm["observaciones"])
        cierto("mezclas: se probaron varias semillas",
               len(gm["por_semilla"]) >= 3)
        cierto("mezclas: cada semilla devuelve un grupo posible",
               all(1 <= s["tamanio_grupo_de_ushuaia"] <= mv["n_aglomerados"]
                   for s in gm["por_semilla"]))
        # El hallazgo: sobreparametrizada, cada arranque da otra cosa.
        cierto("mezclas: distintas semillas dan distintos resultados — es lo "
               "que pasa con más parámetros que observaciones",
               gm["tamanios_distintos"] >= 3)

        ms = mv["mds"]["reconstruccion"]
        cierto("MDS: hay un aglomerado por fila del caso",
               ms["n"] == mv["n_aglomerados"])
        cierto("MDS: las distancias son n(n-1)/2",
               ms["distancias"] == ms["n"] * (ms["n"] - 1) // 2)
        cierto("MDS: el par más lejano son dos aglomerados distintos",
               len(ms["par_mas_lejano"]) == 2
               and ms["par_mas_lejano"][0] != ms["par_mas_lejano"][1])
        cierto("MDS: la distancia máxima es plausible para la Argentina",
               1000 < ms["distancia_maxima_km"] < 5000)
        # El hallazgo: distancias que vienen de un plano tienen exactamente
        # dos valores propios, y la reconstrucción es exacta.
        parecido("MDS: los dos primeros valores propios agotan la traza — el "
                 "método descubre que los datos son bidimensionales",
                 sum(ms["prop_valores_propios"][:2]), 1.0, 1e-6)
        cierto("MDS: del tercero en adelante no queda nada",
               all(abs(x) < 1e-6 for x in ms["prop_valores_propios"][2:]))
        cierto("MDS: la reconstrucción coincide con las coordenadas verdaderas",
               ms["correlacion_procrustes"] > 0.999999)
        cierto("MDS: la correlación de Procrustes no pasa de 1",
               ms["correlacion_procrustes"] <= 1 + 1e-9)
        cierto("MDS: el error de posición es del orden del redondeo de la máquina",
               ms["error_posicion_maximo"] < 1e-10)
        cierto("MDS: reproduce las distancias exactamente",
               ms["correlacion_distancias"] > 0.999999
               and ms["error_distancia_maximo_km"] < 1e-6)

        ip = mv["mds"]["identidad_con_pca"]
        cierto("MDS clásico sobre distancias euclídeas ES el PCA: las "
               "coordenadas coinciden hasta el redondeo",
               all(x < 1e-10 for x in ip["diferencia_maxima_por_eje"]))
        cierto("MDS: y sus valores propios son los del PCA por (n-1)",
               ip["diferencia_maxima_valores_propios"] < 1e-10)

        co = mv["correspondencias"]
        tb = co["tabla"]
        cierto("correspondencias: las celdas son filas por columnas",
               tb["celdas"] == tb["filas"] * tb["columnas"])
        cierto("correspondencias: hay una fila por aglomerado",
               tb["filas"] == mv["n_aglomerados"])
        cierto("correspondencias: hay una columna por categoría",
               tb["columnas"] == len(co["categorias"]))
        cierto("correspondencias: los grados de libertad son (f-1)(c-1)",
               co["gl"] == (tb["filas"] - 1) * (tb["columnas"] - 1))
        # La identidad que la entrada enuncia: inercia total = chi2/n.
        parecido("correspondencias: la inercia total es exactamente chi²/n",
                 co["inercia_total"], co["inercia_chi2_sobre_n"], 1e-12)
        parecido("correspondencias: chi²/n se reconstruye con chi² y n",
                 co["inercia_chi2_sobre_n"], co["chi2"] / tb["n"], 1e-12)
        parecido("correspondencias: las inercias por dimensión suman la total",
                 sum(co["inercias"]), co["inercia_total"], 1e-12)
        cierto("correspondencias: hay min(f-1, c-1) dimensiones con inercia",
               sum(1 for x in co["inercias"] if x > 1e-12)
               <= min(tb["filas"] - 1, tb["columnas"] - 1))
        cierto("correspondencias: las inercias vienen de mayor a menor",
               all(a >= b - 1e-15 for a, b in zip(co["inercias"], co["inercias"][1:])))
        parecido("correspondencias: las proporciones de inercia suman 1",
                 sum(co["prop_inercia"]), 1.0, 1e-9)
        cierto("correspondencias: la tabla rechaza la independencia",
               co["p"] < 0.001)

        parecido("correspondencias: las masas de las columnas suman 1",
                 sum(c["masa"] for c in co["columnas"]), 1.0, 1e-9)
        # El primer eje ordena las calificaciones: es el hallazgo del ejemplo.
        d1 = [c["dim1"] for c in co["columnas"]]
        cierto("correspondencias: el primer eje ordena las categorías de "
               "profesional a no calificada, sin que se le diera el orden",
               all(a < b for a, b in zip(d1, d1[1:])))

        for f in co["filas_extremas"] + co["peor_representadas"]:
            entre_cero_y_uno(f"correspondencias: cos² de {f['aglomerado']}",
                             f["cos2_plano"])
        for f in co["filas_extremas"]:
            entre_cero_y_uno(f"correspondencias: masa de {f['aglomerado']}",
                             f["masa"])
            cierto(f"correspondencias: la contribución de {f['aglomerado']} "
                   "es una proporción",
                   0 <= f["contrib_dim1"] <= 1)
        cierto("correspondencias: las peor representadas vienen de menor a mayor cos²",
               all(a["cos2_plano"] <= b["cos2_plano"]
                   for a, b in zip(co["peor_representadas"],
                                   co["peor_representadas"][1:])))
        # El hallazgo: un punto en el origen puede estar sólo mal representado.
        peor = co["peor_representadas"][0]
        cierto("correspondencias: el peor representado cae casi en el origen y "
               "aun así no es un perfil promedio",
               peor["cos2_plano"] < 0.10
               and abs(peor["dim1"]) < 0.05 and abs(peor["dim2"]) < 0.05)
        cierto("correspondencias: lo que el plano no muestra de él está en la "
               "tercera dimensión",
               peor["cos2_dim3"] > 0.80)

        lbc = co["linea_de_base"]
        cierto("correspondencias: la inercia real supera con holgura a la del ruido",
               co["inercia_total"] > 3 * lbc["inercia_ruido_media"])
        cierto("correspondencias: el p95 del ruido supera su media",
               lbc["inercia_ruido_p95"] > lbc["inercia_ruido_media"])
        parecido("correspondencias: la proporción real de las dos dimensiones "
                 "coincide con las inercias",
                 lbc["prop_2dim_real"],
                 sum(co["inercias"][:2]) / co["inercia_total"], 1e-12)
        # Y el hallazgo incómodo: ese porcentaje casi no discrimina.
        cierto("correspondencias: el % explicado por dos dimensiones casi no "
               "distingue la tabla real del azar",
               lbc["prop_2dim_real"] - lbc["prop_2dim_ruido_media"] < 0.20)

        en = mv["enlaces"]
        nobs2 = mv["n_aglomerados"]
        cierto("enlaces: el grupo patagónico tiene cuatro aglomerados",
               len(en["patagonia"]) == 4)
        cierto("enlaces: los cuatro están entre los aglomerados del caso",
               all(a in mv["clusters"]["grupos_3"] for a in en["patagonia"]))
        for m, f in en["comparacion"].items():
            cierto(f"enlaces: {m} trae los cortes 3, 4 y 5",
                   sorted(k for k in f if k != "inversiones") == ["3", "4", "5"])
            cierto(f"enlaces: las inversiones de {m} son un conteo válido",
                   0 <= f["inversiones"] <= nobs2)
            for kk, g in f.items():
                if kk == "inversiones":
                    continue
                cierto(f"enlaces: {m} con k={kk} reparte los {nobs2} aglomerados",
                       sum(g["tamanios"]) == nobs2)
                # Con un árbol invertido el corte NO puede devolver k grupos:
                # es la consecuencia práctica de la inversión.
                cierto(f"enlaces: {m} con k={kk} devuelve a lo sumo {kk} grupos, "
                       "y exactamente k si el árbol no está invertido",
                       len(g["tamanios"]) <= int(kk)
                       and (f["inversiones"] > 0
                            or len(g["tamanios"]) == int(kk)))
                cierto(f"enlaces: {m} con k={kk} ordena los tamaños de mayor a menor",
                       all(a >= b for a, b in zip(g["tamanios"], g["tamanios"][1:])))
                cierto(f"enlaces: {m} con k={kk} — el grupo de Ushuaia no está vacío "
                       "y cabe en el mayor",
                       0 < len(g["grupo_de_ushuaia"]) <= g["tamanios"][0])
                cierto(f"enlaces: {m} con k={kk} — 'es patagonia exacta' coincide "
                       "con la lista",
                       g["es_patagonia_exacta"]
                       == (g["grupo_de_ushuaia"] == en["patagonia"]))
        # Los hallazgos de la entrada, fijados como comprobaciones.
        cierto("enlaces: centroide y mediana devuelven una partición degenerada",
               all(en["comparacion"][m]["3"]["tamanios"][0] >= 0.75 * nobs2
                   for m in ("centroid", "median")))
        cierto("enlaces: sólo Ward reparte los 32 en grupos usables con k=3",
               en["comparacion"]["ward"]["3"]["tamanios"][0] < 0.75 * nobs2)
        cierto("enlaces: el grupo patagónico sale exacto con completo, promedio "
               "y Ward, en los tres cortes — es lo que lo hace creíble",
               all(en["comparacion"][m][kk]["es_patagonia_exacta"]
                   for m in ("complete", "average", "ward")
                   for kk in ("3", "4", "5")))
        cierto("enlaces: el enlace simple no lo encuentra",
               not any(en["comparacion"]["single"][kk]["es_patagonia_exacta"]
                       for kk in ("3", "4", "5")))
        cierto("enlaces: centroide y mediana invierten el árbol y los demás no — "
               "por eso pedirles 4 grupos devuelve 3",
               all(en["comparacion"][m]["inversiones"] > 0
                   for m in ("centroid", "median"))
               and all(en["comparacion"][m]["inversiones"] == 0
                       for m in ("single", "complete", "average", "ward")))

        al = en["alturas_ward"]
        cierto("alturas: se listan los cortes de 2 a 6 grupos",
               [c["k"] for c in al] == [2, 3, 4, 5, 6])
        cierto("alturas: cortar en menos grupos cuesta más",
               all(a["altura"] >= b["altura"] for a, b in zip(al, al[1:])))
        cierto("alturas: todos los cocientes son mayores que 1",
               all(c["cociente"] > 1 for c in al))
        cierto("alturas: el criterio del salto no discrimina — hay tres "
               "cocientes parecidos",
               sum(c["cociente"] > 1.15 for c in al) >= 3)

        es = mv["estabilidad_cp1"]
        entre_cero_y_uno("estabilidad: proporción de réplicas con phi >= 0,95",
                         es["prop_phi_mayor_igual_095"])
        cierto("estabilidad: la congruencia mediana no pasa de 1",
               es["phi_mediana"] <= 1 + 1e-12)
        cierto("estabilidad: el percentil 5 no supera a la mediana",
               es["phi_p5"] <= es["phi_mediana"])
        parecido("estabilidad: el cociente es el de los dos primeros "
                 "valores propios",
                 es["cociente_vp1_vp2"], vp[0] / vp[1], 1e-9)
        cierto("estabilidad: los dos primeros valores propios están cerca, "
               "que es por qué el CP1 se mueve",
               es["cociente_vp1_vp2"] < 2)


# ---------------------------------------------------------------------------
# 3 · La coherencia entre archivos
# ---------------------------------------------------------------------------

def frente_coherencia(j: dict[str, dict]) -> None:
    t = j.get("demografia/tasas-m05.json")
    dc = j.get("eph/diseno-complejo-m17.json")
    i = j.get("eph/ingresos-eph.json")
    b = j.get("eph/bivariada-m03.json")
    ln = j.get("eph/lognormal-m07.json")

    # El caso ingresos-eph y el ajuste lognormal describen exactamente el
    # mismo universo con el mismo ponderador: si no coinciden, uno de los dos
    # cambió de filtro sin avisar.
    if i and ln:
        cierto("lognormal e ingresos-eph tienen el mismo n",
               i["n"] == ln["n"])
        parecido("lognormal e ingresos-eph: la misma población expandida",
                 float(i["poblacion"]), float(ln["poblacion"]), 1e-9)
        parecido("lognormal e ingresos-eph: la misma media",
                 float(i["media"]), ln["ingreso"]["media"], 1e-6)
        parecido("lognormal e ingresos-eph: la misma mediana",
                 float(i["mediana"]), ln["ingreso"]["mediana"], 1e-6)
        redondeado("lognormal e ingresos-eph: la misma asimetría",
                   float(i["asimetria"]), ln["ingreso"]["asimetria"], 2)
        redondeado("lognormal e ingresos-eph: el mismo CV",
                   float(i["cv"]), ln["ingreso"]["cv"], 3)

    if t and dc:
        parecido("población total: pirámide contra mercado de trabajo",
                 t["piramide"]["poblacion_total"],
                 t["mercado_trabajo"]["poblacion_total"], 1e-9)
        por_ind = {r["indicador"]: r for r in dc["resultados"]}
        menores = por_ind.get("Proporción de menores de 15 años")
        if menores:
            parecido("proporción de menores de 15: tasas-m05 contra diseño complejo",
                     t["piramide"]["prop_0_14"], menores["estimacion"], 1e-3)
        desoc = por_ind.get("Tasa de desocupación")
        if desoc:
            parecido("tasa de desocupación: tasas-m05 contra diseño complejo",
                     t["mercado_trabajo"]["tasa_desocupacion"],
                     desoc["estimacion"], 1e-3)

    if t and i:
        cierto("ocupados con ingreso: el n del Gini coincide con el de ingresos",
               t["gini"]["n"] == i["n"])
    if b and i:
        cierto("ocupados con ingreso: el n de bivariada coincide con el de ingresos",
               b["ingreso_edad"]["n"] == i["n"])

    # Lo que el JSON declara tiene que llegar a la página. Si el script avisa
    # que trabajó sin ponderar, el caso que publica esos números lo tiene que
    # decir con todas las letras: no alcanza con que la palabra "ponderador"
    # aparezca en algún lado.
    DECLARA = {
        "eph/anova-m11.json": ["ingreso-educacion-anova.mdx"],
        "eph/bivariada-m03.json": ["ingreso-horas-eph.mdx"],
        "eph/regresion-m13.json": ["modelo-ingreso-eph.mdx"],
        "eph/no-parametricas-m12.json": ["parametricas-vs-no-parametricas.mdx"],
    }
    for archivo, casos in DECLARA.items():
        d = j.get(archivo)
        if not d:
            continue
        aviso = str(d.get("advertencia", "")).lower()
        if "sin ponderar" not in aviso:
            continue
        for caso in casos:
            ruta = CASOS / caso
            if not ruta.exists():
                problemas.append(f"{archivo} apunta a {caso}, que no existe")
                continue
            texto = ruta.read_text(encoding="utf-8").lower()
            cierto(
                f"{caso} dice «sin ponderar», como avisa {archivo}",
                "sin ponderar" in texto,
            )


# ---------------------------------------------------------------------------
# 4 · Contra los microdatos
# ---------------------------------------------------------------------------

def frente_microdatos(j: dict[str, dict]) -> None:
    if not ESPEJO.exists():
        avisos.append(
            f"no está el espejo de la EPH en {ESPEJO}: "
            "el frente de microdatos no corrió"
        )
        return
    try:
        import pandas as pd
    except ImportError:  # pragma: no cover
        avisos.append("falta pandas: el frente de microdatos no corrió")
        return

    with zipfile.ZipFile(ESPEJO) as z, z.open(INTERNO) as f:
        ind = pd.read_csv(f, sep=";", decimal=",", low_memory=False,
                          usecols=["ESTADO", "CH06", "P21", "PONDERA", "PONDIIO"])

    filas = len(ind)
    poblacion = float(ind["PONDERA"].sum())

    t = j.get("demografia/tasas-m05.json")
    if t:
        # La comprobación que faltaba en septiembre de 2026: si un filtro deja
        # gente afuera, la población expandida del JSON no llega al total.
        parecido("microdatos: la pirámide expande a toda la población de la EPH",
                 t["piramide"]["poblacion_total"], poblacion, 1e-9)
        parecido("microdatos: el mercado de trabajo expande a toda la población",
                 t["mercado_trabajo"]["poblacion_total"], poblacion, 1e-9)

        menores = float(ind.loc[ind["CH06"] < 15, "PONDERA"].sum())
        parecido("microdatos: la proporción de menores de 15 se recalcula igual",
                 t["piramide"]["prop_0_14"], menores / poblacion, 1e-9)

        oc = ind[(ind["ESTADO"] == 1) & (ind["P21"] > 0)]
        cierto("microdatos: el n del Gini es el de ocupados con ingreso positivo",
               t["gini"]["n"] == len(oc))
        # El ingreso de la ocupación principal se pondera con PONDIIO.
        x = oc["P21"].to_numpy(float)
        w = oc["PONDIIO"].to_numpy(float)
        orden = x.argsort()
        x, w = x[orden], w[orden]
        p = (w.cumsum() / w.sum())
        q = ((w * x).cumsum() / (w * x).sum())
        gini = 1 - sum((q[1:] + q[:-1]) * (p[1:] - p[:-1]))
        parecido("microdatos: el Gini se recalcula igual, con PONDIIO",
                 t["gini"]["gini"], float(gini), 1e-6)

    i = j.get("eph/ingresos-eph.json")
    if i:
        oc = ind[(ind["ESTADO"] == 1) & (ind["P21"] > 0) & (ind["PONDIIO"] > 0)]
        cierto("microdatos: el n de ingresos es el de ocupados con ingreso",
               i["n"] == len(oc))
        media = float((oc["PONDIIO"] * oc["P21"]).sum() / oc["PONDIIO"].sum())
        parecido("microdatos: el ingreso medio se recalcula igual",
                 float(i["media"]), media, 1e-6)
        parecido("microdatos: la población con ingreso se recalcula igual",
                 float(i["poblacion"]), float(oc["PONDIIO"].sum()), 1e-6)

    ln = j.get("eph/lognormal-m07.json")
    if ln:
        import numpy as np

        oc = ind[(ind["ESTADO"] == 1) & (ind["P21"] > 0) & (ind["PONDIIO"] > 0)]
        cierto("microdatos: el n de la lognormal es el de ocupados con ingreso",
               ln["n"] == len(oc))
        lg = np.log(oc["P21"].to_numpy(float))
        w = oc["PONDIIO"].to_numpy(float)
        mu = float(np.sum(w * lg) / w.sum())
        sigma = float(np.sqrt(np.sum(w * (lg - mu) ** 2) / w.sum()))
        # Estos dos son los que sostienen toda la entrada: si se recalculan
        # mal, la mediana teórica de 779.782 deja de tener respaldo.
        parecido("microdatos: mu del logaritmo se recalcula igual",
                 ln["lognormal_ajustada"]["mu"], mu, 1e-9)
        parecido("microdatos: sigma del logaritmo se recalcula igual",
                 ln["lognormal_ajustada"]["sigma"], sigma, 1e-9)
        # La asimetría del logaritmo es el número que decide si el modelo
        # sirve: tiene que ser la del archivo, no una cuenta de más.
        z = (lg - mu) / sigma
        parecido("microdatos: la asimetría del logaritmo se recalcula igual",
                 ln["log_ingreso"]["asimetria"],
                 float(np.sum(w * z ** 3) / w.sum()), 1e-9)

    dc = j.get("eph/diseno-complejo-m17.json")
    if dc:
        por_ind = {r["indicador"]: r for r in dc["resultados"]}
        for nombre, esperado in (
            ("Proporción de menores de 15 años", filas),
            ("Edad media", filas),
        ):
            r = por_ind.get(nombre)
            if r:
                cierto(
                    f"microdatos: «{nombre}» usa todas las filas del archivo "
                    f"({r['n']} de {esperado})",
                    r["n"] == esperado,
                )


# ---------------------------------------------------------------------------

def main() -> None:
    print("Verificando los JSON de datos/\n")
    cargados = frente_forma()
    frente_aritmetica(cargados)
    frente_coherencia(cargados)
    frente_microdatos(cargados)

    if avisos:
        print("\nAvisos:")
        for a in avisos:
            print(f"  ·  {a}")

    print(f"\n{comprobaciones} comprobaciones")
    if problemas:
        print(f"\n{len(problemas)} fallan:\n")
        for p in problemas:
            print(f"  ✗  {p}")
        sys.exit(1)
    print("Los JSON cierran por dentro, coinciden entre sí y reproducen "
          "los microdatos.")


if __name__ == "__main__":
    main()

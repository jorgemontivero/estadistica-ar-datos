"""Las cuatro figuras, cada una con su tabla.

    barras-<var>        una categórica, ordenada de mayor a menor
    histograma-<var>    una numérica, con las clases de la regla del sitio
    caja-<var>          una numérica por grupo, con los atípicos a la vista
    dispersion-<x>-<y>  dos numéricas, con la recta de mínimos cuadrados

No hay tortas. Con más de dos o tres categorías, comparar ángulos es más
difícil que comparar largos, y la torta obliga a leer las etiquetas para
entender lo que unas barras dicen de un vistazo.
"""

from comun import (ANCHO_CAJA, PALETA, SERIES, agrupar, caja, clases_sugeridas,
                   eje_castellano, escribir_csv, estilo, guardar, numeros, recta)


def barras(datos, variable, etiqueta):
    plt = estilo()
    valores = [f[variable] for f in datos if f.get(variable, "") != ""]
    categorias = sorted(set(valores), key=lambda c: (-valores.count(c), c))
    conteos = [valores.count(c) for c in categorias]
    tabla = [{"categoria": c, "n": n, "pct": n / len(valores) * 100}
             for c, n in zip(categorias, conteos)]
    nombre = f"barras-{variable}"
    escribir_csv(tabla, nombre, ["categoria", "n", "pct"])

    fig, ax = plt.subplots()
    ax.bar(range(len(categorias)), conteos, color=PALETA["acento"], width=0.62)
    ax.set_xticks(range(len(categorias)))
    ax.set_xticklabels(categorias)
    ax.set_title(etiqueta)
    ax.set_ylabel("Casos")
    ax.yaxis.grid(True)
    ax.set_axisbelow(True)
    eje_castellano(ax)
    for i, (n, fila) in enumerate(zip(conteos, tabla)):
        ax.text(i, n, f" {fila['pct']:.1f} %".replace(".", ","), ha="center", va="bottom",
                fontsize=9, color=PALETA["gris"])
    fig.tight_layout()
    guardar(fig, nombre)
    return nombre


def histograma(datos, variable, etiqueta):
    plt = estilo()
    x = numeros(datos, variable)
    k = clases_sugeridas(x)
    clases = agrupar(x, k)
    nombre = f"histograma-{variable}"
    escribir_csv(clases, nombre, ["clase", "desde", "hasta", "marca", "n", "pct"])

    fig, ax = plt.subplots()
    bordes = [c["desde"] for c in clases] + [clases[-1]["hasta"]]
    ax.hist(x, bins=bordes, color=PALETA["acento"], edgecolor=PALETA["papel"], linewidth=0.8)
    ax.set_title(etiqueta)
    ax.set_ylabel("Casos")
    ax.set_xlabel(etiqueta)
    ax.yaxis.grid(True)
    ax.set_axisbelow(True)
    eje_castellano(ax)
    eje_castellano(ax, "x")
    fig.tight_layout()
    guardar(fig, nombre)
    return nombre


def cajas(datos, variable, etiqueta, grupo, etiqueta_grupo):
    plt = estilo()
    niveles = sorted({f[grupo] for f in datos if f.get(grupo, "") != ""})
    por_grupo = [numeros([f for f in datos if f.get(grupo, "") == nivel], variable)
                 for nivel in niveles]
    tabla = []
    for nivel, valores in zip(niveles, por_grupo):
        if not valores:
            continue
        c = caja(valores)
        tabla.append({"grupo": nivel, "n": c["n"], "minimo": c["minimo"], "q1": c["q1"],
                      "mediana": c["mediana"], "q3": c["q3"], "maximo": c["maximo"],
                      "atipicos": len(c["atipicos"])})
    nombre = f"caja-{variable}"
    escribir_csv(tabla, nombre, ["grupo", "n", "minimo", "q1", "mediana", "q3", "maximo",
                                 "atipicos"])

    fig, ax = plt.subplots()
    caja_estilo = {"facecolor": PALETA["acento"], "alpha": 1.0, "edgecolor": PALETA["acento_fuerte"]}
    # El ancho va fijo: matplotlib lo calcula a partir de cuántos grupos hay y
    # ggplot lo deja en 0,5, así que sin fijarlo la misma caja sale de un ancho
    # en cada idioma.
    ax.boxplot([v for v in por_grupo if v], widths=ANCHO_CAJA, patch_artist=True, boxprops=caja_estilo,
               medianprops={"color": PALETA["papel"], "linewidth": 1.6},
               whiskerprops={"color": PALETA["gris"]}, capprops={"color": PALETA["gris"]},
               flierprops={"marker": "o", "markersize": 3, "markerfacecolor": PALETA["alerta"],
                           "markeredgecolor": PALETA["alerta"]},
               tick_labels=[n for n, v in zip(niveles, por_grupo) if v])
    ax.set_title(f"{etiqueta} según {etiqueta_grupo.lower()}")
    ax.set_ylabel(etiqueta)
    ax.yaxis.grid(True)
    ax.set_axisbelow(True)
    eje_castellano(ax)
    fig.tight_layout()
    guardar(fig, nombre)
    return nombre


def dispersion(datos, x_var, y_var, x_etiqueta, y_etiqueta):
    plt = estilo()
    pares = [(f[x_var], f[y_var]) for f in datos
             if f.get(x_var, "") != "" and f.get(y_var, "") != ""]
    x, y = [], []
    for a, b in pares:
        try:
            x.append(float(a))
            y.append(float(b))
        except ValueError:
            continue
    ajuste = recta(x, y)
    nombre = f"dispersion-{x_var}-{y_var}"
    escribir_csv([ajuste], nombre, ["n", "pendiente", "ordenada", "r"])

    fig, ax = plt.subplots()
    # Sin transparencia: con alpha el color deja de ser el de la paleta, y una
    # figura que no se puede comprobar es una figura que no se puede confiar.
    ax.scatter(x, y, s=16, color=PALETA["acento"], edgecolors="none")
    extremos = [min(x), max(x)]
    ax.plot(extremos, [ajuste["ordenada"] + ajuste["pendiente"] * v for v in extremos],
            color=PALETA["alerta"], linewidth=1.6)
    ax.set_title(f"{y_etiqueta} según {x_etiqueta.lower()}")
    ax.set_xlabel(x_etiqueta)
    ax.set_ylabel(y_etiqueta)
    ax.yaxis.grid(True)
    ax.set_axisbelow(True)
    eje_castellano(ax)
    eje_castellano(ax, "x")
    fig.tight_layout()
    guardar(fig, nombre)
    return nombre


def dibujar(datos, variables) -> list[str]:
    grupo = next((v for v in variables if v["tipo"] == "grupo"), None)
    numericas = [v for v in variables if v["tipo"] == "numerica"]
    hechas = []
    for variable in [v for v in variables if v["tipo"] == "categorica"]:
        hechas.append(barras(datos, variable["nombre"], variable["etiqueta"] or variable["nombre"]))
    for variable in numericas:
        etiqueta = variable["etiqueta"] or variable["nombre"]
        hechas.append(histograma(datos, variable["nombre"], etiqueta))
        if grupo:
            hechas.append(cajas(datos, variable["nombre"], etiqueta, grupo["nombre"],
                                grupo["etiqueta"] or grupo["nombre"]))
    if len(numericas) >= 2:
        hechas.append(dispersion(datos, numericas[0]["nombre"], numericas[1]["nombre"],
                                 numericas[0]["etiqueta"] or numericas[0]["nombre"],
                                 numericas[1]["etiqueta"] or numericas[1]["nombre"]))
    return hechas

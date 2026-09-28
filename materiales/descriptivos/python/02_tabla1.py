"""Paso 2: la tabla 1, la que abre todo informe.

Una fila por variable —o por categoría, si es categórica—, una columna por
grupo, más el total y la comparación. Se escribe dos veces: en CSV para seguir
trabajando y en Markdown para pegar en el informe.

Cómo se llena cada celda:

    numérica simétrica     media (DE)
    numérica asimétrica    mediana [Q1–Q3]
    categórica             n (%)

La asimetría decide sola, con la regla del sitio: |asimetría| > 1. Así la misma
variable no se informa con media en una tabla y con mediana en otra.
"""

from comun import (decimales_de, descriptivos, escribir_csv, escribir_texto, numero_texto,
                   p_texto)
from pruebas import comparar_categorica, comparar_numerica

RAYA = "–"  # raya de rango, no guion: «18–65»


def celda_numerica(valores: list[float], forma: str) -> str:
    if not valores:
        return "—"
    d = descriptivos(valores)
    if forma == "asimétrica":
        dec = decimales_de(d["mediana"])
        return f"{numero_texto(d['mediana'], dec)} [{numero_texto(d['q1'], dec)}{RAYA}{numero_texto(d['q3'], dec)}]"
    dec = decimales_de(d["media"])
    desvio = numero_texto(d["desvio"], dec) if d.get("desvio") is not None else "—"
    return f"{numero_texto(d['media'], dec)} ({desvio})"


def celda_categorica(cuantos: int, total: int) -> str:
    if total == 0:
        return "—"
    return f"{cuantos} ({numero_texto(cuantos / total * 100, 1)}%)"


def armar(datos: list[dict], variables: list[dict], calculado: dict) -> dict:
    grupo = next((v["nombre"] for v in variables if v["tipo"] == "grupo"), None)
    niveles = sorted({f[grupo] for f in datos if f.get(grupo, "") != ""}) if grupo else []
    columnas = ["variable", "categoria", "total"] + niveles + ["p", "prueba", "nota"]

    def subconjunto(nivel):
        return [f for f in datos if f.get(grupo, "") == nivel]

    filas = []
    for variable in variables:
        nombre, etiqueta = variable["nombre"], variable["etiqueta"] or variable["nombre"]
        if variable["tipo"] == "numerica":
            todos = [v for v in (numero_de(f, nombre) for f in datos) if v is not None]
            forma = descriptivos(todos)["forma"] if todos else "simétrica"
            por_grupo = [[v for v in (numero_de(f, nombre) for f in subconjunto(n)) if v is not None]
                         for n in niveles]
            fila = {"variable": etiqueta, "categoria": "", "total": celda_numerica(todos, forma)}
            for nivel, valores in zip(niveles, por_grupo):
                fila[nivel] = celda_numerica(valores, forma)
            comparacion = comparar_numerica([g for g in por_grupo if g], forma) if niveles else {}
            fila.update({"p": p_texto(comparacion.get("p")), "prueba": comparacion.get("prueba", ""),
                         "nota": comparacion.get("nota", "")})
            filas.append(fila)
        elif variable["tipo"] == "categorica":
            llenos = [f for f in datos if f.get(nombre, "") != ""]
            categorias = sorted({f[nombre] for f in llenos})
            tabla = [[sum(1 for f in subconjunto(n) if f.get(nombre, "") == c) for n in niveles]
                     for c in categorias]
            comparacion = comparar_categorica(tabla) if niveles else {}
            for i, categoria in enumerate(categorias):
                fila = {"variable": etiqueta if i == 0 else "", "categoria": categoria,
                        "total": celda_categorica(sum(1 for f in llenos if f[nombre] == categoria),
                                                  len(llenos))}
                for j, nivel in enumerate(niveles):
                    fila[nivel] = celda_categorica(tabla[i][j], len(subconjunto(nivel)))
                fila.update({"p": p_texto(comparacion.get("p")) if i == 0 else "",
                             "prueba": comparacion.get("prueba", "") if i == 0 else "",
                             "nota": comparacion.get("nota", "") if i == 0 else ""})
                filas.append(fila)

    escribir_csv(filas, "salidas/tabla1.csv", columnas)
    escribir_texto(markdown(filas, columnas, datos, niveles, grupo), "salidas/tabla1.md")
    return {"filas": filas, "niveles": niveles}


def numero_de(fila: dict, variable: str):
    from comun import numero
    return numero(fila.get(variable, ""))


def markdown(filas, columnas, datos, niveles, grupo) -> list[str]:
    """La misma tabla, para pegar en el informe."""
    def n_de(nivel):
        return sum(1 for f in datos if f.get(grupo, "") == nivel)

    encabezado = ["Variable", f"Total (n = {len(datos)})"]
    encabezado += [f"{nivel} (n = {n_de(nivel)})" for nivel in niveles]
    encabezado += ["p", "Prueba"]
    lineas = ["**Tabla 1.** Características de la muestra" +
              (f", según {grupo}." if grupo else "."), ""]
    lineas.append("| " + " | ".join(encabezado) + " |")
    lineas.append("|" + "---|" * len(encabezado))
    for fila in filas:
        nombre = fila["variable"]
        if fila["categoria"]:
            nombre = (f"**{nombre}**, {fila['categoria']}" if nombre else
                      f"  {fila['categoria']}")
        celdas = [nombre, fila["total"]] + [fila.get(n, "") for n in niveles]
        celdas += [fila["p"], fila["prueba"]]
        lineas.append("| " + " | ".join(celdas) + " |")
    notas = sorted({f["nota"] for f in filas if f["nota"]})
    if notas:
        lineas += [""] + [f"Nota: {n}." for n in notas]
    lineas += ["", "Las variables simétricas se informan como media (desvío estándar) y las "
                   "asimétricas como mediana [Q1–Q3]. Las categóricas, como n (%)."]
    return lineas

"""Paso 1: los descriptivos de cada variable.

Escribe dos archivos: uno con las numéricas y otro con las categóricas. Son los
números completos; la tabla 1 del paso 2 los resume.
"""

from comun import descriptivos, escribir_csv, numero

COLUMNAS_NUM = ["variable", "etiqueta", "n", "faltantes", "media", "desvio", "minimo", "q1",
                "mediana", "q3", "maximo", "asimetria", "forma"]
COLUMNAS_CAT = ["variable", "etiqueta", "categoria", "n", "pct"]


def valores_numericos(datos: list[dict], variable: str) -> list[float]:
    return [v for v in (numero(f.get(variable, "")) for f in datos) if v is not None]


def categorias(datos: list[dict], variable: str) -> list[str]:
    """Las categorías presentes, en orden alfabético: no depende del orden de
    los datos, así que dos bases con las mismas categorías dan la misma tabla."""
    return sorted({f.get(variable, "") for f in datos if f.get(variable, "") != ""})


def calcular(datos: list[dict], variables: list[dict]) -> dict:
    numericas, categoricas = [], []
    for variable in variables:
        nombre, etiqueta = variable["nombre"], variable["etiqueta"] or variable["nombre"]
        if variable["tipo"] == "numerica":
            valores = valores_numericos(datos, nombre)
            fila = {"variable": nombre, "etiqueta": etiqueta,
                    "faltantes": len(datos) - len(valores)}
            fila.update(descriptivos(valores))
            numericas.append({c: fila.get(c) for c in COLUMNAS_NUM})
        elif variable["tipo"] == "categorica":
            llenos = [f[nombre] for f in datos if f.get(nombre, "") != ""]
            for categoria in categorias(datos, nombre):
                cuantos = sum(1 for v in llenos if v == categoria)
                categoricas.append({
                    "variable": nombre, "etiqueta": etiqueta, "categoria": categoria,
                    "n": cuantos, "pct": cuantos / len(llenos) * 100 if llenos else 0.0,
                })
    escribir_csv(numericas, "salidas/descriptivos.csv", COLUMNAS_NUM)
    escribir_csv(categoricas, "salidas/frecuencias.csv", COLUMNAS_CAT)
    return {"numericas": numericas, "categoricas": categoricas}

"""Paso 1: mirar el archivo antes de tocarlo.

Escribe salidas/perfil.csv: una fila por columna del archivo crudo, con lo que
hay y con lo que conviene sospechar. Este paso no cambia ningún dato.
"""

from comun import a_fecha, a_numero, escribir_csv, limpiar_texto

COLUMNAS = ["columna", "en_diccionario", "tipo_declarado", "tipo_detectado", "n", "faltantes",
            "pct_faltantes", "distintos", "ejemplo", "sospecha"]


def tipo_detectado(valores: list[str], decimal: str) -> str:
    """Qué parece la columna, mirando todos sus valores no vacíos."""
    llenos = [v for v in valores if v != ""]
    if not llenos:
        return "vacía"
    numeros = [a_numero(v, decimal)[0] for v in llenos]
    if all(n is not None for n in numeros):
        return "entero" if all(n == int(n) for n in numeros) else "decimal"
    if all(a_fecha(v) is not None for v in llenos):
        return "fecha"
    return "texto"


def sospecha(valores: list[str], tipo: str, en_diccionario: bool, decimal: str) -> str:
    """Lo que conviene mirar antes de confiar en la columna."""
    llenos = [v for v in valores if v != ""]
    if not en_diccionario:
        return "No está en el diccionario: no pasa a la base limpia"
    if not llenos:
        return "No tiene un solo dato"
    if len(valores) - len(llenos) > len(valores) / 2:
        return "Más de la mitad está vacía"
    if len(set(llenos)) == 1:
        return "Toda la columna tiene el mismo valor"
    if tipo in ("entero", "decimal") and any(a_numero(v, decimal)[1] for v in llenos):
        return "Números guardados como texto: traen comas o separadores de miles"
    if len({v.lower() for v in llenos}) < len(set(llenos)):
        return "La misma categoría escrita con mayúsculas y con minúsculas"
    return ""


def perfilar(crudo: dict, diccionario: list[dict]) -> list[dict]:
    declarado = {d["nombre"]: d["tipo"] for d in diccionario}
    filas = []
    for columna in crudo["columnas"]:
        valores = [limpiar_texto(f[columna]) for f in crudo["filas"]]
        llenos = [v for v in valores if v != ""]
        tipo = tipo_detectado(valores, crudo["decimal"])
        filas.append({
            "columna": columna,
            "en_diccionario": columna in declarado,
            "tipo_declarado": declarado.get(columna, ""),
            "tipo_detectado": tipo,
            "n": len(valores),
            "faltantes": len(valores) - len(llenos),
            "pct_faltantes": (len(valores) - len(llenos)) / len(valores) * 100 if valores else 0.0,
            "distintos": len(set(llenos)),
            "ejemplo": llenos[0] if llenos else "",
            "sospecha": sospecha(valores, tipo, columna in declarado, crudo["decimal"]),
        })
    escribir_csv(filas, "salidas/perfil.csv", COLUMNAS)
    return filas

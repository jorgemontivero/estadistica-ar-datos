"""Paso 2: limpiar, dejando anotado cada cambio.

Cada valor que se modifica queda contado en salidas/cambios.csv, por variable y
por regla. Una limpieza que no informa lo que tocó es indistinguible de un
error de carga.
"""

from comun import a_fecha, a_numero, codigos, escribir_csv

# Las reglas que se cuentan. Los espacios de más no están: se sacan al leer el
# archivo, antes de que el diccionario entre en juego, y el perfil los informa.
REGLAS = ["código de faltante a vacío", "decimal convertido", "no es un número", "no es entero",
          "fuera de rango", "categoría desconocida", "categoría normalizada", "fecha normalizada",
          "fecha inválida"]


def limite(texto: str, decimal: str):
    numero, _ = a_numero(texto, decimal)
    return numero


def limpiar_valor(valor: str, variable: dict, decimal: str):
    """Devuelve (valor limpio, regla aplicada). La regla vacía es «no se tocó»."""
    if valor == "":
        return "", ""
    if variable["faltante"] != "" and valor.lower() == variable["faltante"].lower():
        return "", "código de faltante a vacío"

    tipo = variable["tipo"]
    if tipo in ("entero", "decimal"):
        numero, convertido = a_numero(valor, decimal)
        if numero is None:
            return "", "no es un número"
        if tipo == "entero" and numero != int(numero):
            return "", "no es entero"
        minimo, maximo = limite(variable["minimo"], decimal), limite(variable["maximo"], decimal)
        if (minimo is not None and numero < minimo) or (maximo is not None and numero > maximo):
            return "", "fuera de rango"
        salida = str(int(numero)) if tipo == "entero" else f"{numero:.6f}"
        return salida, "decimal convertido" if convertido else ""

    if tipo == "categoria":
        for codigo in codigos(variable["codigos"]):
            if codigo.lower() == valor.lower():
                return codigo, "categoría normalizada" if codigo != valor else ""
        return "", "categoría desconocida"

    if tipo == "fecha":
        fecha = a_fecha(valor)
        if fecha is None:
            return "", "fecha inválida"
        return fecha, "fecha normalizada" if fecha != valor else ""

    return valor, ""


def limpiar(crudo: dict, diccionario: list[dict]) -> dict:
    nombres = [d["nombre"] for d in diccionario]
    columna_id = next((d["nombre"] for d in diccionario if d["id"].lower() in ("sí", "si")), None)
    cambios = {(d["nombre"], r): 0 for d in diccionario for r in REGLAS}
    filas, vistos, duplicadas = [], set(), 0

    for cruda in crudo["filas"]:
        fila = {}
        for variable in diccionario:
            limpio, regla = limpiar_valor(cruda.get(variable["nombre"], ""), variable, crudo["decimal"])
            if regla:
                cambios[(variable["nombre"], regla)] += 1
            fila[variable["nombre"]] = limpio
        if columna_id is not None and fila[columna_id] != "":
            if fila[columna_id] in vistos:
                duplicadas += 1
                continue
            vistos.add(fila[columna_id])
        filas.append(fila)

    escribir_csv(filas, "datos/limpios/base.csv", nombres)
    # En el orden del diccionario y de las reglas, para que no dependa de cómo
    # recorre cada idioma sus estructuras.
    tabla = [{"variable": d["nombre"], "regla": r, "casos": cambios[(d["nombre"], r)]}
             for d in diccionario for r in REGLAS if cambios[(d["nombre"], r)] > 0]
    escribir_csv(tabla, "salidas/cambios.csv", ["variable", "regla", "casos"])
    return {"filas": filas, "duplicadas": duplicadas,
            "modificados": sum(cambios.values()),
            "vacios": sum(1 for f in filas for v in nombres if f[v] == "")}

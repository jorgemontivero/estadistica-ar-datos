"""Paso 1: importar y limpiar.

Lee datos/crudos/encuesta.csv, lo deja usable y escribe
datos/limpios/encuesta.csv. El crudo no se toca nunca.

Las reglas están escritas acá y son las mismas que en R/01-importar.R: los dos
tienen que dar el mismo archivo limpio.
"""

from comun import escribir_csv, leer_csv

LIMITES = {"edad": (0, 110), "ingreso": (0, 100_000_000), "puntaje": (1, 10)}


def limpiar_texto(x: str) -> str:
    """Un texto sin espacios de más: ni en las puntas ni repetidos adentro."""
    return " ".join((x or "").split())


def normalizar_grupo(x: str) -> str:
    """«CONTROL», «control » y «Control» son el mismo grupo."""
    x = limpiar_texto(x)
    return x[:1].upper() + x[1:].lower() if x else ""


def a_numero(x: str, limites: tuple[float, float]):
    """Un número, o None si está vacío, no es un número o cae fuera de su rango."""
    x = limpiar_texto(x)
    if x == "":
        return None
    try:
        v = float(x)
    except ValueError:
        return None
    return None if v < limites[0] or v > limites[1] else v


def importar() -> dict:
    crudo = leer_csv("datos/crudos/encuesta.csv")
    vacios = fuera = 0
    limpio, vistos, repetidas = [], set(), 0
    for fila in crudo:
        salida = {"id": limpiar_texto(fila["id"]), "grupo": normalizar_grupo(fila["grupo"])}
        for v, limites in LIMITES.items():
            texto = limpiar_texto(fila[v])
            numero = a_numero(fila[v], limites)
            vacios += texto == ""
            fuera += texto != "" and numero is None
            salida[v] = numero
        # Filas repetidas: el mismo id cargado dos veces. Se queda la primera.
        if salida["id"] in vistos:
            repetidas += 1
            continue
        vistos.add(salida["id"])
        limpio.append(salida)

    escribir_csv(limpio, "datos/limpios/encuesta.csv")
    return {"filas_crudas": len(crudo), "filas_repetidas": repetidas, "valores_vacios": vacios,
            "valores_fuera_de_rango": fuera, "filas_limpias": len(limpio)}

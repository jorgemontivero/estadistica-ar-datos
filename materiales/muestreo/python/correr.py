"""Selecciona la muestra, arma los ponderadores, estima y escribe el informe.

    python python/correr.py

Desde la carpeta del proyecto, no desde python/.
"""

import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comun import (escribir_csv, escribir_texto, indices_por, leer_csv,  # noqa: E402
                   leer_parametros, limpiar_texto)

DATOS = Path("datos/marco.csv")
VARIABLES = Path("datos/variables.csv")
PARAMETROS = Path("datos/parametros.csv")

for archivo in (DATOS, VARIABLES, PARAMETROS):
    if not archivo.exists():
        raise SystemExit(f"No encuentro {archivo}. ¿Estás parado en la carpeta del proyecto?")

seleccion_ = importlib.import_module("01_seleccion")
ponderadores_ = importlib.import_module("02_ponderadores")
estimacion_ = importlib.import_module("03_estimacion")
redaccion_ = importlib.import_module("04_redaccion")

datos = leer_csv(DATOS)
parametros = leer_parametros(PARAMETROS)
poblacion = len(datos)
valores = [float(f[parametros["variable"]]) for f in datos]

seleccion = seleccion_.calcular(datos, parametros, valores)

# La fracción de primera etapa por estrato: cuántos conglomerados de los que
# hay entraron en la muestra. Es la corrección por población finita, y con
# diseños sin conglomerados es la fracción de unidades.
por_estrato_marco = indices_por(datos, parametros["estrato"])


def fracciones_de(sel, con_conglomerados, estratificado=True):
    """La fracción de primera etapa, por estrato.

    Sin estratos todo entra en una sola celda, porque es lo que corresponde a
    un diseño que no estratificó: la corrección por población finita es
    entonces n/N sobre el marco entero.
    """
    if not estratificado:
        if con_conglomerados:
            en_el_marco = len({f[parametros["conglomerado"]] for f in datos})
            elegidos = len({s["conglomerado"] for s in sel})
        else:
            en_el_marco, elegidos = len(datos), len(sel)
        return {"—": elegidos / en_el_marco if en_el_marco else 0.0}
    salida = {}
    for h, indices in por_estrato_marco.items():
        del_estrato = [s for s in sel
                       if limpiar_texto(datos[s["fila"]].get(parametros["estrato"], "")) == h]
        if con_conglomerados:
            en_el_marco = len({datos[i][parametros["conglomerado"]] for i in indices})
            elegidos = len({s["conglomerado"] for s in del_estrato})
        else:
            en_el_marco = len(indices)
            elegidos = len(del_estrato)
        salida[h] = elegidos / en_el_marco if en_el_marco else 0.0
    return salida


CON_CONGLOMERADOS = {"bietápico"}
# Los diseños que usaron los estratos al SELECCIONAR. Un aleatorio simple y un
# sistemático no los usaron, y estimarles la varianza como si lo hubieran hecho
# les regalaría una precisión que no tienen.
ESTRATIFICADOS = {"estratificado proporcional", "estratificado de Neyman", "bietápico"}

filas_disenos = []
estimaciones = []
for nombre, sel in seleccion["disenos"].items():
    con_cong = nombre in CON_CONGLOMERADOS
    estratificado = nombre in ESTRATIFICADOS
    fracciones = fracciones_de(sel, con_cong, estratificado)
    pesos = ponderadores_.de_diseno(sel)
    filas_disenos.append({
        "diseno": nombre, "n": len(sel),
        "unidades_primarias": (len({s["conglomerado"] for s in sel}) if con_cong
                               else len(sel)),
        "suma_de_pesos": sum(p["peso"] for p in pesos),
        "peso_minimo": min(p["peso"] for p in pesos),
        "peso_maximo": max(p["peso"] for p in pesos),
        "sin_reemplazo": "Sí",
    })
    estimaciones += estimacion_.calcular(datos, parametros, pesos, fracciones,
                                         nombre, estratificado)

# El diseño principal —el bietápico— es el que lleva el resto del proyecto:
# ponderadores ajustados, estimación por estrato y simulación de cobertura.
principal = seleccion["disenos"]["bietápico"]
fracciones_principal = fracciones_de(principal, True, True)

# Quién contestó. Se sortea con el mismo generador de R y una semilla derivada,
# así la no respuesta también es reproducible: en R es
# `set.seed(semilla + 1000); runif(n) >= tasa`.
from azar import GeneradorR  # noqa: E402

tasa = parametros["tasa_de_no_respuesta"]
if tasa > 0:
    sorteo = GeneradorR(parametros["semilla"] + 1000)
    respondieron = [sorteo.unif() >= tasa for _ in principal]
else:
    respondieron = None
ponderadores = ponderadores_.calcular(datos, parametros, principal, respondieron)

por_estrato = estimacion_.por_estrato(datos, parametros, ponderadores["pesos"],
                                      fracciones_principal)


def seleccionar_otra_vez(semilla):
    sel, _ = seleccion_.bietapico(datos, semilla, parametros["estrato"],
                                  parametros["conglomerado"],
                                  parametros["conglomerados_por_estrato"],
                                  parametros["hogares_por_conglomerado"])
    return sel, fracciones_de(sel, True, True)


cobertura = estimacion_.cobertura(datos, parametros, seleccionar_otra_vez,
                                  parametros["replicas_de_cobertura"])

# ------------------------------------------------------------------ salidas
escribir_csv(filas_disenos, "salidas/disenos.csv",
             ["diseno", "n", "unidades_primarias", "suma_de_pesos", "peso_minimo",
              "peso_maximo", "sin_reemplazo"])

escribir_csv([{
    "hogar": datos[p["fila"]].get("hogar", str(p["fila"] + 1)),
    "estrato": limpiar_texto(datos[p["fila"]].get(parametros["estrato"], "")),
    "conglomerado": p["conglomerado"],
    "probabilidad": p["probabilidad"], "peso": p["peso"],
} for p in ponderadores["pesos"]], "salidas/muestra.csv",
    ["hogar", "estrato", "conglomerado", "probabilidad", "peso"])

escribir_csv([{"cuando": etiqueta, **{k: v for k, v in resumen.items()}}
              for etiqueta, resumen in (
                  ("pesos de diseño", ponderadores["antes"]),
                  ("ajustados por no respuesta", ponderadores["tras_no_respuesta"]),
                  ("post-estratificados", ponderadores["despues"]))],
             "salidas/ponderadores.csv",
             ["cuando", "n", "suma", "poblacion", "diferencia_con_la_poblacion",
              "minimo", "maximo", "media", "coeficiente_de_variacion",
              "razon_maximo_minimo", "deff_de_kish", "n_efectivo_de_kish"])

escribir_csv(ponderadores["calibracion"], "salidas/calibracion.csv",
             ["celda", "en_el_marco", "estimado_antes", "factor"])

escribir_csv(estimaciones, "salidas/estimaciones.csv",
             ["diseno", "variable", "que", "verdadero", "estimacion", "error_estandar",
              "inferior", "superior", "gl", "contiene_al_verdadero", "ee_ingenuo",
              "inferior_ingenuo", "superior_ingenuo", "contiene_ingenuo", "deff",
              "n_efectivo", "error_relativo"])

escribir_csv(por_estrato, "salidas/por-estrato.csv",
             ["estrato", "n", "unidades_primarias", "verdadero", "estimacion",
              "error_estandar", "inferior", "superior", "contiene_al_verdadero",
              "error_relativo_del_ee"])

escribir_csv([cobertura] if cobertura else [], "salidas/cobertura.csv",
             ["replicas", "verdadero", "nominal", "cobertura_del_diseno",
              "cobertura_ingenua", "ancho_medio_del_diseno", "ancho_medio_ingenuo"])

avisos = list(ponderadores["avisos"])
del_principal = [e for e in estimaciones if e["diseno"] == "bietápico"]
enganosas = [e for e in del_principal if not e["contiene_ingenuo"] and e["contiene_al_verdadero"]]
if enganosas:
    cuales = ", ".join(f"«{e['variable']}»" for e in enganosas)
    avisos.append({"donde": "estimación",
                   "aviso": f"En {cuales} el intervalo que ignora el diseño no contiene al "
                            f"valor verdadero y el que lo respeta sí. Es la misma muestra: "
                            f"lo único que cambia es la fórmula del error estándar."})
peores = [e for e in del_principal if e["deff"] > 2]
if peores:
    avisos.append({"donde": "estimación",
                   "aviso": "Hay estimaciones con un efecto de diseño mayor que 2: la "
                            "muestra vale menos de la mitad de lo que su tamaño sugiere. Con "
                            "conglomerados eso es lo esperable, y es el precio de no tener "
                            "que recorrer la provincia entera."})
sistematico = [e for e in estimaciones if e["diseno"] == "sistemático"]
if sistematico:
    avisos.append({"donde": "estimación",
                   "aviso": "El error estándar del sistemático está calculado como si fuera "
                            "un aleatorio simple, porque para una muestra sistemática **no "
                            "existe** un estimador insesgado de la varianza con una sola "
                            "muestra. Es la convención habitual y suele ser conservadora, "
                            "pero es una convención, no un cálculo."})
if cobertura and cobertura["cobertura_ingenua"] < cobertura["nominal"] - 0.05:
    avisos.append({"donde": "cobertura",
                   "aviso": f"Sobre {cobertura['replicas']} muestras, el intervalo que "
                            f"ignora el diseño cubrió el valor verdadero el "
                            + f"{cobertura['cobertura_ingenua'] * 100:.1f}".replace(".", ",")
                            + " % de las veces en vez del "
                            + f"{cobertura['nominal'] * 100:.0f}".replace(".", ",")
                            + " % que promete. No es mala suerte de una muestra: es la "
                              "fórmula."})
chicos = [e for e in por_estrato if e["unidades_primarias"] < 10]
if chicos:
    avisos.append({"donde": "estimación",
                   "aviso": f"Hay {len(chicos)} estratos con menos de diez conglomerados en "
                            f"la muestra. El error estándar de esas estimaciones está "
                            f"calculado con muy pocos grados de libertad y es poco confiable: "
                            f"una muestra que alcanza para el total puede no alcanzar para "
                            f"ninguna de sus partes."})
escribir_csv(avisos, "salidas/avisos.csv", ["donde", "aviso"])

escribir_texto(redaccion_.redactar(parametros, seleccion, ponderadores, estimaciones,
                                   por_estrato, cobertura, poblacion),
               "salidas/muestreo.md")

bietapico = {e["variable"]: e for e in del_principal}
principal_media = bietapico.get(parametros["variable"])
escribir_csv([
    {"clave": "poblacion", "valor": poblacion},
    {"clave": "muestra", "valor": seleccion["n"]},
    {"clave": "contestaron", "valor": ponderadores["despues"]["n"]},
    {"clave": "conglomerados_en_la_muestra",
     "valor": len({s["conglomerado"] for s in principal})},
    {"clave": "suma_de_pesos", "valor": ponderadores["despues"]["suma"]},
    {"clave": "deff_de_kish", "valor": ponderadores["despues"]["deff_de_kish"]},
    {"clave": "verdadero", "valor": principal_media["verdadero"] if principal_media else None},
    {"clave": "estimacion", "valor": principal_media["estimacion"] if principal_media else None},
    {"clave": "ee_del_diseno",
     "valor": principal_media["error_estandar"] if principal_media else None},
    {"clave": "ee_ingenuo", "valor": principal_media["ee_ingenuo"] if principal_media else None},
    {"clave": "deff", "valor": principal_media["deff"] if principal_media else None},
    {"clave": "n_efectivo", "valor": principal_media["n_efectivo"] if principal_media else None},
    {"clave": "el_ingenuo_contiene_al_verdadero",
     "valor": principal_media["contiene_ingenuo"] if principal_media else None},
    {"clave": "cobertura_del_diseno",
     "valor": cobertura["cobertura_del_diseno"] if cobertura else None},
    {"clave": "cobertura_ingenua",
     "valor": cobertura["cobertura_ingenua"] if cobertura else None},
    {"clave": "avisos", "valor": len(avisos)},
], "salidas/resumen.csv", ["clave", "valor"])

print("Listo. Salidas en salidas/:")
print("  disenos.csv, muestra.csv, ponderadores.csv, calibracion.csv,")
print("  estimaciones.csv, por-estrato.csv, cobertura.csv, avisos.csv,")
print("  resumen.csv y muestreo.md")
if enganosas:
    print("  Ojo: el intervalo que ignora el diseño no contiene al valor verdadero.")
if cobertura:
    print(f"  Cobertura: {cobertura['cobertura_del_diseno'] * 100:.1f} % con el diseño, "
          f"{cobertura['cobertura_ingenua'] * 100:.1f} % ignorándolo.")

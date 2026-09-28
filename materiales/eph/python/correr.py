"""Lee el archivo del INDEC, calcula las tasas y los ingresos, y escribe el informe.

    python python/correr.py

Desde la carpeta del proyecto, no desde python/.
"""

import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comun import (escribir_csv, escribir_texto, leer_microdatos,  # noqa: E402
                   leer_parametros, preparar_conglomerados)

PARAMETROS = Path("datos/parametros.csv")
if not PARAMETROS.exists():
    raise SystemExit(f"No encuentro {PARAMETROS}. ¿Estás parado en la carpeta del proyecto?")

leer_ = importlib.import_module("01_leer")
tasas_ = importlib.import_module("02_tasas")
ingresos_ = importlib.import_module("03_ingresos")
redaccion_ = importlib.import_module("04_redaccion")

parametros = leer_parametros(PARAMETROS)
columnas, crudas = leer_microdatos(parametros["archivo"], parametros["separador"],
                                   parametros["codificacion"])
base = leer_.leer(columnas, crudas, parametros)
registros = base["registros"]

# Los cortes con los que se abre cada tabla. El orden de las etiquetas es el del
# corte y no el del alfabeto: los tramos de edad van de menor a mayor y las
# regiones en el orden en que el INDEC las numera.
CORTES = [
    ("Sexo", ["Varón", "Mujer"],
     lambda r: leer_.SEXO.get(r["sexo"], "Sin dato")),
    ("Tramo de edad", [e for e, _d, _h in leer_.TRAMOS],
     lambda r: leer_.tramo_de(r["edad"]) if r["edad"] is not None else "Sin dato"),
    ("Región", [leer_.REGIONES[k] for k in (1, 40, 41, 42, 43, 44)],
     lambda r: leer_.REGIONES.get(r["region"], "Sin dato")),
]

CORTES_DE_INGRESO = CORTES + [
    ("Nivel educativo", [leer_.NIVEL[k] for k in (7, 1, 2, 3, 4, 5, 6)],
     lambda r: leer_.NIVEL.get(r["nivel_ed"], "Sin dato")),
    ("Categoría ocupacional", [leer_.CATEGORIA[k] for k in (1, 2, 3, 4)],
     lambda r: leer_.CATEGORIA.get(r["cat_ocup"], "Sin dato")),
]

# Los aglomerados son los estratos y los hogares las unidades primarias. Se
# agrupan una sola vez: todas las estimaciones del proyecto usan los mismos.
conglomerados = preparar_conglomerados([r["aglomerado"] for r in registros],
                                       [r["hogar"] for r in registros])

filas_tasas = tasas_.calcular(registros, conglomerados, parametros)
filas_grupo = tasas_.por_grupo(registros, conglomerados, parametros, CORTES)
identidad = tasas_.identidad(filas_tasas)

contraste = ingresos_.contraste(registros, base["ponderador_de_ingreso"],
                                parametros["ponderador"])
resumen_ingresos, deciles = ingresos_.distribucion(registros, conglomerados, parametros)
ingresos_grupo = ingresos_.por_grupo(registros, CORTES_DE_INGRESO)
informal = ingresos_.informalidad(registros, conglomerados, parametros, CORTES)

avisos = list(base["avisos"])
avisos += tasas_.avisos_de(filas_tasas, identidad, registros)
avisos += ingresos_.avisos_de(contraste, deciles, registros)

# ------------------------------------------------------------------ salidas
escribir_csv(base["poblacion"], "salidas/poblacion.csv",
             ["condicion", "codigo", "n", "poblacion", "porcentaje"])

escribir_csv(filas_tasas, "salidas/tasas.csv",
             ["tasa", "numerador", "denominador", "poblacion_numerador",
              "poblacion_denominador", "n_denominador", "valor", "error_estandar",
              "inferior", "superior", "gl", "deff", "n_efectivo", "sin_ponderar",
              "diferencia_con_la_ponderada"])

escribir_csv(filas_grupo, "salidas/tasas-por-grupo.csv",
             ["corte", "grupo", "tasa", "n_denominador", "poblacion_denominador",
              "valor", "error_estandar", "inferior", "superior", "sin_ponderar"])

escribir_csv(resumen_ingresos, "salidas/ingresos.csv", ["estadistico", "valor"])

escribir_csv(deciles, "salidas/deciles.csv",
             ["decil", "corte_superior", "n", "poblacion", "ingreso_medio",
              "participacion"])

escribir_csv(contraste, "salidas/ponderador-e-ingreso.csv",
             ["caso", "ponderador", "que_hace_con_el_menos_nueve",
              "que_hace_con_el_cero", "n", "poblacion", "media", "mediana",
              "diferencia", "diferencia_relativa"])

escribir_csv(ingresos_grupo, "salidas/ingresos-por-grupo.csv",
             ["corte", "grupo", "n", "poblacion", "media", "mediana",
              "razon_con_el_total"])

escribir_csv(informal, "salidas/informalidad.csv",
             ["corte", "grupo", "n_asalariados", "asalariados", "sin_descuento",
              "tasa", "error_estandar", "inferior", "superior"])

escribir_csv(avisos, "salidas/avisos.csv", ["donde", "aviso"])

escribir_texto(redaccion_.redactar(parametros, base, filas_tasas, identidad, contraste,
                                   resumen_ingresos, deciles, ingresos_grupo, informal,
                                   avisos),
               "salidas/eph.md")


def tasa_de(nombre):
    for t in filas_tasas:
        if t["tasa"] == nombre:
            return t["valor"]
    return None


def caso(nombre):
    for c in contraste:
        if c["caso"] == nombre:
            return c
    return None


valor_ingreso = {f["estadistico"]: f["valor"] for f in resumen_ingresos}
correcto = caso("Lo correcto")
solo_peso = caso("Con el ponderador general")
los_dos = caso("Con el ponderador general y los que no declaran adentro")
total_informal = next((f for f in informal if f["corte"] == "Total"), None)

escribir_csv([
    {"clave": "periodo", "valor": base["periodo"]},
    {"clave": "registros", "valor": len(registros)},
    {"clave": "hogares", "valor": base["hogares"]},
    {"clave": "aglomerados", "valor": base["aglomerados"]},
    {"clave": "columnas_del_archivo", "valor": base["columnas_del_archivo"]},
    {"clave": "poblacion", "valor": base["peso_total"]},
    {"clave": "tasa_de_actividad", "valor": tasa_de("actividad")},
    {"clave": "tasa_de_empleo", "valor": tasa_de("empleo")},
    {"clave": "tasa_de_desocupacion", "valor": tasa_de("desocupación")},
    {"clave": "tasa_de_subocupacion", "valor": tasa_de("subocupación")},
    {"clave": "residuo_de_la_identidad",
     "valor": identidad["residuo"] if identidad else None},
    {"clave": "ponderador_de_ingreso", "valor": base["ponderador_de_ingreso"]},
    {"clave": "el_archivo_trae_ponderador_de_ingreso",
     "valor": base["hay_ponderador_de_ingreso"]},
    {"clave": "ingreso_medio", "valor": valor_ingreso.get("media")},
    {"clave": "ingreso_mediano", "valor": valor_ingreso.get("mediana")},
    {"clave": "ingreso_medio_con_el_ponderador_general",
     "valor": solo_peso["media"] if solo_peso else None},
    {"clave": "ingreso_medio_con_los_dos_descuidos",
     "valor": los_dos["media"] if los_dos else None},
    {"clave": "caida_por_los_dos_descuidos",
     "valor": los_dos["diferencia_relativa"] if los_dos else None},
    {"clave": "razon_entre_deciles",
     "valor": valor_ingreso.get("razón entre el décimo y el primer decil")},
    {"clave": "informalidad", "valor": total_informal["tasa"] if total_informal else None},
    {"clave": "avisos", "valor": len(avisos)},
], "salidas/resumen.csv", ["clave", "valor"])

print("Listo. Salidas en salidas/:")
print("  poblacion.csv, tasas.csv, tasas-por-grupo.csv, ingresos.csv,")
print("  deciles.csv, ponderador-e-ingreso.csv, ingresos-por-grupo.csv,")
print("  informalidad.csv, avisos.csv, resumen.csv y eph.md")
if correcto and los_dos:
    print(f"  Ingreso medio: {correcto['media']:,.0f} bien calculado, "
          f"{los_dos['media']:,.0f} con los dos descuidos "
          f"({100 * los_dos['diferencia_relativa']:+.1f} %).")
if not base["hay_ponderador_de_ingreso"]:
    print("  Ojo: el archivo no trae ponderador de ingreso. Mirá avisos.csv.")

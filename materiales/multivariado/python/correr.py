"""Componentes, conglomerados y correspondencias, y después el informe.

    python python/correr.py

Desde la carpeta del proyecto, no desde python/.
"""

import importlib
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comun import (escribir_csv, escribir_texto, leer_matriz,  # noqa: E402
                   leer_parametros, suma, tipificar)

PARAMETROS = Path("datos/parametros.csv")
if not PARAMETROS.exists():
    raise SystemExit(f"No encuentro {PARAMETROS}. ¿Estás parado en la carpeta del proyecto?")

componentes_ = importlib.import_module("01_componentes")
conglomerados_ = importlib.import_module("02_conglomerados")
correspondencias_ = importlib.import_module("03_correspondencias")
redaccion_ = importlib.import_module("04_redaccion")

parametros = leer_parametros(PARAMETROS)
unidades, columnas, datos = leer_matriz(parametros["datos"], parametros["unidad"])
if len(unidades) < 3:
    raise SystemExit("Con menos de tres unidades no hay nada que agrupar.")

# ------------------------------------------------------------- componentes
con = componentes_.calcular(datos, columnas, True)
sin = componentes_.calcular(datos, columnas, False)
cuantos = min(parametros["componentes"], len(columnas))

filas_componentes = componentes_.tabla_de_componentes(con, columnas)
filas_cargas = componentes_.tabla_de_cargas(con, columnas, cuantos)
filas_puntajes = componentes_.tabla_de_puntajes(con, unidades, cuantos)
filas_contraste = componentes_.contraste(con, sin, columnas)

# ------------------------------------------------------------ conglomerados
base, _medias, _desvios = tipificar(datos)
distancias, por_enlace = conglomerados_.calcular(base, unidades, parametros)
filas_grupos = conglomerados_.tabla_de_grupos(unidades, por_enlace, parametros)
filas_fusiones = conglomerados_.tabla_de_fusiones(por_enlace, unidades)
filas_siluetas = conglomerados_.tabla_de_siluetas(por_enlace, parametros)
filas_nulo = conglomerados_.contra_el_nulo(base, parametros)
nulo = conglomerados_.resumen_del_nulo(
    filas_nulo, por_enlace[parametros["enlace"]]["silueta"])

# --------------------------------------------------------- correspondencias
filas_tabla, columnas_tabla, tabla = leer_matriz(parametros["tabla"],
                                                 parametros["unidad"])
ca = correspondencias_.calcular(tabla, filas_tabla, columnas_tabla, parametros)
filas_ejes = correspondencias_.tabla_de_ejes(ca)
filas_puntos = correspondencias_.tabla_de_puntos(ca, filas_tabla, columnas_tabla,
                                                 parametros)

avisos = componentes_.avisos_de(con, sin, columnas, parametros)
avisos += conglomerados_.avisos_de(por_enlace, nulo, parametros, unidades)
avisos += correspondencias_.avisos_de(ca, filas_tabla, columnas_tabla, parametros, tabla)

# ------------------------------------------------------------------ salidas
escribir_csv(filas_componentes, "salidas/componentes.csv",
             ["componente", "autovalor", "proporcion", "acumulado",
              "supera_el_promedio"])

escribir_csv(filas_cargas, "salidas/cargas.csv",
             ["variable"] + [f"componente_{j + 1}" for j in range(cuantos)]
             + ["representada"])

escribir_csv(filas_puntajes, "salidas/puntajes.csv",
             ["unidad"] + [f"componente_{j + 1}" for j in range(cuantos)])

escribir_csv(filas_contraste, "salidas/sin-estandarizar.csv",
             ["version", "autovalor_1", "proporcion_1", "proporcion_2",
              "variable_mas_pegada", "correlacion_con_esa", "variables_hasta_el_90"])

escribir_csv(filas_grupos, "salidas/conglomerados.csv",
             ["unidad"] + conglomerados_.ENLACES + ["silueta"])

escribir_csv(filas_fusiones, "salidas/fusiones.csv",
             ["enlace", "paso", "unidad_a", "unidad_b", "altura", "tamano"])

escribir_csv(filas_siluetas, "salidas/silueta.csv",
             ["enlace", "grupos", "mayor", "menor", "silueta", "negativas",
              "acuerdo_con_el_elegido"])

escribir_csv(filas_nulo, "salidas/nulo.csv", ["corrimiento", "silueta"])

escribir_csv(filas_ejes, "salidas/correspondencias.csv",
             ["eje", "valor_singular", "inercia", "proporcion", "acumulado",
              "chi2_del_eje"])

ejes = min(parametros["ejes"], ca["ejes_posibles"])
escribir_csv(filas_puntos, "salidas/puntos.csv",
             ["tipo", "punto", "masa", "inercia"]
             + [c for j in range(ejes) for c in (f"eje_{j + 1}", f"aporte_{j + 1}")]
             + ["calidad"])

escribir_csv(avisos, "salidas/avisos.csv", ["donde", "aviso"])

escribir_texto(redaccion_.redactar(parametros, unidades, columnas, filas_componentes,
                                   filas_cargas, filas_contraste, filas_siluetas,
                                   filas_grupos, nulo, ca, filas_ejes, filas_puntos,
                                   avisos, columnas_tabla),
               "salidas/multivariado.md")

# ------------------------------------------------------------------ resumen
tipificada = filas_contraste[0]
cruda = filas_contraste[1]
elegido = parametros["enlace"]
del_elegido = next(f for f in filas_siluetas if f["enlace"] == elegido)
escribir_csv([
    {"clave": "unidades", "valor": len(unidades)},
    {"clave": "variables", "valor": len(columnas)},
    {"clave": "componentes_pedidos", "valor": cuantos},
    {"clave": "proporcion_del_primero", "valor": tipificada["proporcion_1"]},
    {"clave": "proporcion_de_los_dos_primeros",
     "valor": tipificada["proporcion_1"] + (tipificada["proporcion_2"] or 0.0)},
    {"clave": "componentes_hasta_el_90", "valor": tipificada["variables_hasta_el_90"]},
    {"clave": "proporcion_del_primero_sin_tipificar", "valor": cruda["proporcion_1"]},
    {"clave": "variable_que_se_come_el_primero", "valor": cruda["variable_mas_pegada"]},
    {"clave": "correlacion_con_esa_variable", "valor": cruda["correlacion_con_esa"]},
    {"clave": "enlace", "valor": elegido},
    {"clave": "conglomerados", "valor": parametros["conglomerados"]},
    {"clave": "silueta", "valor": del_elegido["silueta"]},
    {"clave": "siluetas_negativas", "valor": del_elegido["negativas"]},
    {"clave": "nulos", "valor": nulo["replicas"]},
    {"clave": "mejor_silueta_del_nulo", "valor": nulo["mayor"]},
    {"clave": "mediana_del_nulo", "valor": nulo["mediana"]},
    {"clave": "nulos_que_igualan_o_superan", "valor": nulo["nulos_que_igualan_o_superan"]},
    {"clave": "peor_acuerdo_entre_enlaces",
     "valor": min(f["acuerdo_con_el_elegido"] for f in filas_siluetas
                  if f["enlace"] != elegido)},
    {"clave": "filas_de_la_tabla", "valor": len(filas_tabla)},
    {"clave": "columnas_de_la_tabla", "valor": len(columnas_tabla)},
    {"clave": "chi2", "valor": ca["chi2"]},
    {"clave": "gl", "valor": ca["gl"]},
    {"clave": "inercia_total", "valor": ca["inercia_total"]},
    {"clave": "inercia_de_los_ejes_graficados",
     "valor": suma([ca["inercias"][j] for j in range(ejes)]) / ca["inercia_total"]},
    {"clave": "avisos", "valor": len(avisos)},
], "salidas/resumen.csv", ["clave", "valor"])

print("Listo. Salidas en salidas/:")
print("  componentes.csv, cargas.csv, puntajes.csv, sin-estandarizar.csv,")
print("  conglomerados.csv, fusiones.csv, silueta.csv, nulo.csv,")
print("  correspondencias.csv, puntos.csv, avisos.csv, resumen.csv y multivariado.md")
print(f"  Tipificado, el primer componente explica "
      f"{100 * tipificada['proporcion_1']:.1f} %; sin tipificar, "
      f"{100 * cruda['proporcion_1']:.1f} % y es «{cruda['variable_mas_pegada']}».")
print(f"  Silueta con {elegido}: {del_elegido['silueta']:.3f}; el mejor de los "
      f"{nulo['replicas']} nulos llega a {nulo['mayor']:.3f}.")

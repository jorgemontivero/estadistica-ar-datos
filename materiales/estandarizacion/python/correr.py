"""Estandariza, compara y escribe el informe.

    python python/correr.py

Desde la carpeta del proyecto, no desde python/.
"""

import importlib
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comun import (escribir_csv, escribir_texto, leer_csv,  # noqa: E402
                   leer_parametros, numero, ordenar)

PARAMETROS = Path("datos/parametros.csv")
if not PARAMETROS.exists():
    raise SystemExit(f"No encuentro {PARAMETROS}. ¿Estás parado en la carpeta del proyecto?")

directa_ = importlib.import_module("01_directa")
indirecta_ = importlib.import_module("02_indirecta")
comparar_ = importlib.import_module("03_comparar")
redaccion_ = importlib.import_module("04_redaccion")

parametros = leer_parametros(PARAMETROS)


def leer_datos(parametros):
    """La tabla de casos y expuestos, y los pesos de cada estándar.

    El **orden de los grupos de edad lo fija el archivo de estándares**, no el
    alfabeto: «10 a 14» va antes que «0 a 9» si uno los ordena como texto, y
    una tabla de edades ordenada así es ilegible.
    """
    columnas = leer_csv(parametros["estandares"])
    if not columnas:
        raise SystemExit(f"{parametros['estandares']} está vacío.")
    nombres = [c for c in columnas[0] if c != "grupo_edad"]
    if not nombres:
        raise SystemExit("El archivo de estándares no tiene ninguna columna de pesos "
                         "además de «grupo_edad».")
    grupos = [f["grupo_edad"] for f in columnas]
    if len(set(grupos)) != len(grupos):
        raise SystemExit("El archivo de estándares repite algún grupo de edad.")
    pesos = {}
    for nombre in nombres:
        pesos[nombre] = {}
        for f in columnas:
            v = numero(f[nombre])
            if v is None or v < 0:
                raise SystemExit(f"El peso de «{f['grupo_edad']}» en el estándar "
                                 f"«{nombre}» no es un número positivo.")
            pesos[nombre][f["grupo_edad"]] = v

    filas = leer_csv(parametros["datos"])
    clave_poblacion = parametros["poblacion"]
    clave_grupo = parametros["grupo"]
    for clave in (clave_poblacion, clave_grupo, parametros["casos"],
                  parametros["expuestos"]):
        if filas and clave not in filas[0]:
            raise SystemExit(f"A {parametros['datos']} le falta la columna «{clave}».")

    poblaciones: dict = {}
    for f in filas:
        nombre = f[clave_poblacion]
        grupo = f[clave_grupo]
        if grupo not in pesos[nombres[0]]:
            raise SystemExit(f"El grupo «{grupo}» está en los datos y no en el archivo "
                             f"de estándares. Los dos tienen que usar los mismos.")
        celdas = poblaciones.setdefault(nombre, {})
        if grupo in celdas:
            raise SystemExit(f"«{nombre}» tiene el grupo «{grupo}» dos veces.")
        casos = numero(f[parametros["casos"]])
        expuestos = numero(f[parametros["expuestos"]])
        if casos is None or expuestos is None or casos < 0 or expuestos < 0:
            raise SystemExit(f"«{nombre}», grupo «{grupo}»: los casos y los expuestos "
                             f"tienen que ser números no negativos.")
        celdas[grupo] = {"casos": casos, "expuestos": expuestos}

    if not poblaciones:
        raise SystemExit(f"{parametros['datos']} no tiene ninguna fila.")
    incompletas = [n for n, c in poblaciones.items() if set(c) != set(grupos)]
    if incompletas:
        raise SystemExit(f"Estas poblaciones no tienen todos los grupos de edad: "
                         f"{', '.join(sorted(incompletas)[:5])}. Una tasa ajustada con "
                         f"grupos faltantes no se puede comparar con otra que los tenga.")
    return poblaciones, grupos, pesos


poblaciones, grupos, todos_los_pesos = leer_datos(parametros)
if parametros["estandar"] not in todos_los_pesos:
    raise SystemExit(f"El estándar «{parametros['estandar']}» no está en "
                     f"{parametros['estandares']}. Hay: "
                     f"{', '.join(ordenar(list(todos_los_pesos)))}.")
pesos = todos_los_pesos[parametros["estandar"]]

# ------------------------------------------------------------------ cálculo
tasas = directa_.calcular(poblaciones, grupos, pesos, parametros)
detalle = directa_.por_edad(poblaciones, grupos, pesos, parametros)

referencia = indirecta_.tasas_de_referencia(
    poblaciones, grupos,
    [p.strip() for p in parametros["referencia"].split("|") if p.strip()])
indirectas = indirecta_.calcular(poblaciones, grupos, referencia, tasas, parametros)

filas_estandar, por_estandar = comparar_.por_estandar(
    poblaciones, grupos, todos_los_pesos, parametros, directa_.calcular)
sensibles = comparar_.sensibilidad(por_estandar, parametros)
niveles = comparar_.niveles(por_estandar)
comparaciones = comparar_.comparar(poblaciones, grupos, tasas, parametros["pares"],
                                   parametros)
descomposicion = comparar_.descomponer(poblaciones, grupos, parametros["pares"],
                                       parametros)

avisos = directa_.avisos_de(tasas, detalle, parametros)
avisos += indirecta_.avisos_de(indirectas, referencia, parametros)
avisos += comparar_.avisos_de(sensibles, niveles, comparaciones)

# ------------------------------------------------------------------ salidas
escribir_csv(tasas, "salidas/tasas.csv",
             ["poblacion", "casos", "expuestos", "proporcion_en_el_grupo_mayor",
              "cruda", "cruda_inferior", "cruda_superior", "estandarizada",
              "estandarizada_inferior", "estandarizada_superior", "cambio_relativo",
              "casos_con_la_estructura_estandar", "rango_crudo", "rango_estandarizado",
              "cambio_de_rango"])

escribir_csv(detalle, "salidas/por-edad.csv",
             ["poblacion", "grupo_edad", "casos", "expuestos", "proporcion_propia",
              "peso_estandar", "tasa_especifica", "aporte"])

escribir_csv(indirectas, "salidas/indirecta.csv",
             ["poblacion", "observados", "esperados", "razon", "razon_inferior",
              "razon_superior", "distinta_de_uno", "estandarizada_indirecta",
              "estandarizada_directa", "diferencia_con_la_directa", "cruda",
              "rango_indirecto", "rango_directo"])

escribir_csv(filas_estandar, "salidas/por-estandar.csv",
             ["estandar", "poblacion", "tasa", "inferior", "superior", "rango"])

escribir_csv(sensibles, "salidas/sensibilidad.csv",
             ["estandar_1", "estandar_2", "poblacion_a", "poblacion_b", "tasa_a_1",
              "tasa_b_1", "tasa_a_2", "tasa_b_2", "distancia_1", "distancia_2",
              "se_pisan_con_1", "se_pisan_con_2", "se_pisan_con_los_dos"])

escribir_csv(niveles, "salidas/niveles.csv",
             ["poblacion", "menor", "mayor", "razon_entre_niveles",
              "estandar_del_menor", "estandar_del_mayor"])

escribir_csv(comparaciones, "salidas/comparaciones.csv",
             ["poblacion_a", "poblacion_b", "cruda_a", "cruda_b", "diferencia_cruda",
              "efecto_estructura", "efecto_tasas", "residuo_de_la_identidad",
              "parte_estructura", "estandarizada_a", "estandarizada_b",
              "diferencia_estandarizada", "razon", "razon_inferior", "razon_superior",
              "la_razon_excluye_al_uno", "se_dan_vuelta"])

escribir_csv(descomposicion, "salidas/descomposicion.csv",
             ["poblacion_a", "poblacion_b", "grupo_edad", "proporcion_a", "proporcion_b",
              "tasa_a", "tasa_b", "efecto_estructura", "efecto_tasas"])

escribir_csv(avisos, "salidas/avisos.csv", ["donde", "aviso"])

escribir_texto(redaccion_.redactar(parametros, tasas, indirectas, referencia, sensibles,
                                   niveles, comparaciones, avisos, grupos),
               "salidas/estandarizacion.md")

# ------------------------------------------------------------------ resumen
mayor_vuelco = max(tasas, key=lambda f: abs(f["cambio_de_rango"]))
mas_alta = tasas[0]
mas_baja = tasas[-1]
peor_nivel = max(niveles, key=lambda f: f["razon_entre_niveles"] or 0)
escribir_csv([
    {"clave": "poblaciones", "valor": len(tasas)},
    {"clave": "grupos_de_edad", "valor": len(grupos)},
    {"clave": "estandar", "valor": parametros["estandar"]},
    {"clave": "estandares_disponibles", "valor": len(todos_los_pesos)},
    {"clave": "casos", "valor": int(math.fsum(f["casos"] for f in tasas))},
    {"clave": "expuestos", "valor": int(math.fsum(f["expuestos"] for f in tasas))},
    {"clave": "tasa_cruda_del_conjunto", "valor": referencia["cruda"]
        * parametros["multiplicador"]},
    {"clave": "mas_alta_ajustada", "valor": mas_alta["poblacion"]},
    {"clave": "mas_alta_ajustada_valor", "valor": mas_alta["estandarizada"]},
    {"clave": "mas_baja_ajustada", "valor": mas_baja["poblacion"]},
    {"clave": "mas_baja_ajustada_valor", "valor": mas_baja["estandarizada"]},
    {"clave": "mayor_vuelco", "valor": mayor_vuelco["poblacion"]},
    {"clave": "mayor_vuelco_rango_crudo", "valor": mayor_vuelco["rango_crudo"]},
    {"clave": "mayor_vuelco_rango_estandarizado",
     "valor": mayor_vuelco["rango_estandarizado"]},
    {"clave": "mayor_vuelco_cruda", "valor": mayor_vuelco["cruda"]},
    {"clave": "mayor_vuelco_estandarizada", "valor": mayor_vuelco["estandarizada"]},
    {"clave": "pares_que_se_dan_vuelta_por_el_estandar", "valor": len(sensibles)},
    {"clave": "de_esos_con_intervalos_pisados_con_los_dos",
     "valor": sum(1 for f in sensibles if f["se_pisan_con_los_dos"])},
    {"clave": "mayor_razon_entre_niveles", "valor": peor_nivel["razon_entre_niveles"]},
    {"clave": "referencia_de_la_indirecta", "valor": referencia["nombre"]},
    {"clave": "razones_que_no_contienen_al_uno",
     "valor": sum(1 for f in indirectas if f["distinta_de_uno"])},
    {"clave": "pares_comparados", "valor": len(comparaciones)},
    {"clave": "avisos", "valor": len(avisos)},
], "salidas/resumen.csv", ["clave", "valor"])

print("Listo. Salidas en salidas/:")
print("  tasas.csv, por-edad.csv, indirecta.csv, por-estandar.csv,")
print("  sensibilidad.csv, niveles.csv, comparaciones.csv, descomposicion.csv,")
print("  avisos.csv, resumen.csv y estandarizacion.md")
print(f"  {mayor_vuelco['poblacion']}: puesto {mayor_vuelco['rango_crudo']} por la tasa "
      f"cruda y {mayor_vuelco['rango_estandarizado']} por la ajustada.")
if sensibles:
    print(f"  {len(sensibles)} pares cambian de orden según el estándar.")

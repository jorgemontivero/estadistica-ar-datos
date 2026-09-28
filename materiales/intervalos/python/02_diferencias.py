"""Paso 2: los intervalos de la diferencia, y por qué no alcanza con mirar los
dos por separado.

Es el error más común con intervalos de confianza: publicar el intervalo de
cada grupo y concluir, porque se pisan, que no hay diferencia. No se sigue. El
intervalo de la diferencia usa el error estándar de la diferencia, que es
√(EE₁² + EE₂²) y no EE₁ + EE₂: es más chico que la suma, así que hay un rango
entero de diferencias donde los dos intervalos se pisan y sin embargo el de la
diferencia no contiene al cero.

Por eso cada fila trae las dos cosas al lado: si los intervalos de los dos
grupos se pisan, y si el de la diferencia excluye al cero. Cuando las dos
columnas dicen «Sí», mirar los intervalos por separado lleva a la conclusión
contraria, y la columna `conclusion_distinta` lo marca.

Con más de dos grupos se comparan todos los pares. Ahí conviene recordar que
cada intervalo es del 95 % por separado: tres intervalos simultáneos no dan
95 % de confianza conjunta.
"""

from comun import desvio, media, numeros
from intervalos import ic_diferencia_medias, ic_diferencia_proporciones

TOTAL = "Total"


def pares(niveles):
    return [(niveles[i], niveles[j])
            for i in range(len(niveles)) for j in range(i + 1, len(niveles))]


def se_pisan(a, b):
    """¿Los dos intervalos comparten algún valor?"""
    return a["inferior"] <= b["superior"] and b["inferior"] <= a["superior"]


def calcular(datos, variables, parametros, calculado):
    confianza = parametros["confianza"]
    grupo = next((v["nombre"] for v in variables if v["tipo"] == "grupo"), None)
    if grupo is None:
        return {"diferencias": [], "niveles": [], "avisos": []}

    niveles = sorted({f.get(grupo, "") for f in datos if f.get(grupo, "") != ""})
    por_nivel = {n: [f for f in datos if f.get(grupo, "") == n] for n in niveles}

    # Los intervalos de una muestra, tal como quedaron publicados en el paso 1:
    # la pregunta es qué concluiría alguien que mira ESOS intervalos.
    ic_media_de = {(f["variable"], f["ambito"]): f for f in calculado["medias"]}
    ic_prop_de = {(f["variable"], f["categoria"], f["ambito"]): f
                  for f in calculado["proporciones"] if f["metodo"] == "wilson"}

    filas = []
    avisos = []

    def agregar(base, ic, uno, dos, tipo):
        for aviso in ic["avisos"]:
            avisos.append({"intervalo": tipo, "variable": base["variable"],
                           "ambito": f'{base["grupo_1"]} contra {base["grupo_2"]}',
                           "detalle": base["categoria"], "aviso": aviso})
        pisan = se_pisan(uno, dos) if uno and dos else None
        excluye = ic["inferior"] > 0 or ic["superior"] < 0
        filas.append({**base,
                      "diferencia": ic["estimacion"], "error_estandar": ic["error_estandar"],
                      "gl": ic["gl"], "critico": ic["critico"],
                      "inferior": ic["inferior"], "superior": ic["superior"],
                      "excluye_cero": excluye, "se_pisan_los_individuales": pisan,
                      "conclusion_distinta": bool(pisan) and excluye})

    for v in variables:
        if v["tipo"] != "numerica":
            continue
        for g1, g2 in pares(niveles):
            x1 = numeros(por_nivel[g1], v["nombre"])
            x2 = numeros(por_nivel[g2], v["nombre"])
            if len(x1) < 2 or len(x2) < 2:
                continue
            ic = ic_diferencia_medias(media(x1), desvio(x1), len(x1),
                                      media(x2), desvio(x2), len(x2), confianza)
            if ic is None:
                continue
            agregar({"variable": v["nombre"], "etiqueta": v["etiqueta"], "que": "media",
                     "categoria": "", "grupo_1": g1, "grupo_2": g2,
                     "n_1": len(x1), "n_2": len(x2),
                     "estimacion_1": media(x1), "estimacion_2": media(x2)},
                    ic, ic_media_de.get((v["nombre"], g1)), ic_media_de.get((v["nombre"], g2)),
                    "diferencia de medias")

    for v in variables:
        if v["tipo"] != "categorica":
            continue
        categorias = sorted({f.get(v["nombre"], "") for f in datos
                             if f.get(v["nombre"], "") != ""})
        for categoria in categorias:
            for g1, g2 in pares(niveles):
                v1 = [f.get(v["nombre"], "") for f in por_nivel[g1] if f.get(v["nombre"], "") != ""]
                v2 = [f.get(v["nombre"], "") for f in por_nivel[g2] if f.get(v["nombre"], "") != ""]
                if not v1 or not v2:
                    continue
                x1, x2 = v1.count(categoria), v2.count(categoria)
                ic = ic_diferencia_proporciones(x1, len(v1), x2, len(v2), confianza)
                if ic is None:
                    continue
                agregar({"variable": v["nombre"], "etiqueta": v["etiqueta"], "que": "proporción",
                         "categoria": categoria, "grupo_1": g1, "grupo_2": g2,
                         "n_1": len(v1), "n_2": len(v2),
                         "estimacion_1": x1 / len(v1), "estimacion_2": x2 / len(v2)},
                        ic, ic_prop_de.get((v["nombre"], categoria, g1)),
                        ic_prop_de.get((v["nombre"], categoria, g2)),
                        "diferencia de proporciones")

    return {"diferencias": filas, "niveles": niveles, "avisos": avisos}

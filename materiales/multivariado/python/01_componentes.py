"""Paso 1: componentes principales.

Un PCA es una rotación: los mismos datos mirados desde el eje que más los
estira. No inventa nada ni descubre nada; ordena la variación que ya estaba.

**La decisión que define el resultado no es del método: es tipificar o no.**
Sin tipificar, cada variable pesa según el cuadrado de su unidad de medida. Con
una población en personas y unos porcentajes en la misma matriz, el primer
componente es la población —correlación 1,000— y los porcentajes no existen. Y
como el resultado igual «funciona» —explica el 99 % de la varianza, que suena
bárbaro— nadie lo mira dos veces.

Este paso calcula las dos versiones y las deja al lado, en
`sin-estandarizar.csv`. No para que se elija: para que se vea qué se está
eligiendo.
"""

import math

from comun import correlacion, centrar, cruzada, suma, tipificar
from jacobi import descomponer


def calcular(datos, columnas, tipificado: bool):
    """Los autovalores, las cargas y los puntajes, tipificando o no.

    Con tipificación la matriz que se descompone es la de correlaciones; sin
    ella, la de covarianzas. Es la misma cuenta sobre matrices distintas, y de
    ahí sale toda la diferencia.
    """
    if tipificado:
        base, medias, desvios = tipificar(datos)
    else:
        base, medias = centrar(datos)
        desvios = [1.0] * len(columnas)
    matriz = cruzada(base)
    valores, vectores, barridos = descomponer(matriz)

    total = suma(valores)
    n = len(base)
    p = len(columnas)

    # Los puntajes: cada unidad proyectada sobre cada componente. La varianza
    # de un puntaje es su autovalor, que es la definición de «componente».
    puntajes = []
    for i in range(n):
        fila = []
        for j in range(p):
            fila.append(suma([base[i][k] * vectores[j][k] for k in range(p)]))
        puntajes.append(fila)

    # Las cargas: la correlación de cada variable con cada componente. Con
    # datos tipificados es el autovector por la raíz del autovalor; se calcula
    # como correlación para que valga también sin tipificar.
    cargas = []
    for k in range(p):
        columna = [base[i][k] for i in range(n)]
        cargas.append([correlacion(columna, [puntajes[i][j] for i in range(n)])
                       for j in range(p)])

    return {
        "tipificado": tipificado,
        "valores": valores,
        "vectores": vectores,
        "puntajes": puntajes,
        "cargas": cargas,
        "total": total,
        "medias": medias,
        "desvios": desvios,
        "barridos": barridos,
        "base": base,
    }


def tabla_de_componentes(salida, columnas):
    """Un renglón por componente: cuánto explica y cuánto va acumulado."""
    filas = []
    acumulado = 0.0
    for j, valor in enumerate(salida["valores"], start=1):
        proporcion = valor / salida["total"] if salida["total"] > 0 else None
        acumulado += proporcion if proporcion is not None else 0.0
        filas.append({
            "componente": j,
            "autovalor": valor,
            "proporcion": proporcion,
            "acumulado": acumulado,
            # El criterio de Kaiser: quedarse con los que superan el autovalor
            # medio. Con datos tipificados el promedio es uno, que es de donde
            # sale la regla famosa; sin tipificar, uno no quiere decir nada.
            "supera_el_promedio": valor > salida["total"] / len(salida["valores"]),
        })
    return filas


def tabla_de_cargas(salida, columnas, cuantos: int):
    filas = []
    for k, nombre in enumerate(columnas):
        fila = {"variable": nombre}
        total = 0.0
        for j in range(min(cuantos, len(columnas))):
            carga = salida["cargas"][k][j]
            fila[f"componente_{j + 1}"] = carga
            total += carga * carga
        # Cuánto de la variable queda representado en los componentes elegidos.
        # Una variable con un cos² bajo está en el gráfico pero no se ve: su
        # posición es proyección de otra cosa.
        fila["representada"] = total
        filas.append(fila)
    return filas


def tabla_de_puntajes(salida, unidades, cuantos: int):
    filas = []
    for i, nombre in enumerate(unidades):
        fila = {"unidad": nombre}
        for j in range(min(cuantos, len(salida["valores"]))):
            fila[f"componente_{j + 1}"] = salida["puntajes"][i][j]
        filas.append(fila)
    return filas


def contraste(con, sin, columnas):
    """Las dos versiones al lado, que es el punto de todo este paso.

    Para cada una: cuánto explica el primer componente y con qué variable está
    correlacionado. Cuando la respuesta es «con una sola, y casi perfecto», el
    primer componente no es un resumen de nada: es esa variable con otro
    nombre.
    """
    filas = []
    for etiqueta, salida in (("tipificada", con), ("sin tipificar", sin)):
        n = len(salida["base"])
        primero = [salida["puntajes"][i][0] for i in range(n)]
        correlaciones = [abs(correlacion([salida["base"][i][k] for i in range(n)],
                                         primero)) for k in range(len(columnas))]
        mayor = 0
        for k in range(1, len(columnas)):
            if correlaciones[k] > correlaciones[mayor]:
                mayor = k
        filas.append({
            "version": etiqueta,
            "autovalor_1": salida["valores"][0],
            "proporcion_1": salida["valores"][0] / salida["total"],
            "proporcion_2": (salida["valores"][1] / salida["total"]
                             if len(salida["valores"]) > 1 else None),
            "variable_mas_pegada": columnas[mayor],
            "correlacion_con_esa": correlaciones[mayor],
            # Cuántas variables hacen falta para llegar al noventa por ciento.
            "variables_hasta_el_90": cuantas_hasta(salida, 0.90),
        })
    return filas


def cuantas_hasta(salida, umbral: float) -> int:
    acumulado = 0.0
    for j, valor in enumerate(salida["valores"], start=1):
        acumulado += valor / salida["total"]
        if acumulado >= umbral:
            return j
    return len(salida["valores"])


def avisos_de(con, sin, columnas, parametros):
    salida = []
    proporcion_sin = sin["valores"][0] / sin["total"]
    n = len(sin["base"])
    primero = [sin["puntajes"][i][0] for i in range(n)]
    correlaciones = [abs(correlacion([sin["base"][i][k] for i in range(n)], primero))
                     for k in range(len(columnas))]
    mayor = max(range(len(columnas)), key=lambda k: (correlaciones[k], -k))
    if correlaciones[mayor] > 0.95 and proporcion_sin > 0.80:
        salida.append({
            "donde": "componentes",
            "aviso": f"Sin tipificar, el primer componente explica el "
                     + f"{100 * proporcion_sin:.1f}".replace(".", ",")
                     + f" % de la varianza y su correlación con «{columnas[mayor]}» es de "
                     + f"{correlaciones[mayor]:.3f}".replace(".", ",")
                     + ". No es un resumen de las variables: es esa variable con otro "
                       "nombre, porque su unidad de medida es la más grande de la tabla."})

    razon = con["valores"][0] / con["valores"][-1] if con["valores"][-1] > 0 else None
    if razon is not None and razon > 1000:
        salida.append({
            "donde": "componentes",
            "aviso": f"El último autovalor es {razon:.0f} veces más chico que el primero: "
                     f"hay al menos una variable que es casi combinación lineal de las "
                     f"otras. Los componentes del final no son ruido, son redundancia, y "
                     f"conviene sacar una variable en vez de rotar."})

    flojas = [f for f in tabla_de_cargas(con, columnas, parametros["componentes"])
              if f["representada"] < 0.5]
    if flojas:
        cuales = ", ".join(f"«{f['variable']}»" for f in flojas)
        salida.append({
            "donde": "componentes",
            "aviso": f"Con {parametros['componentes']} componentes, {cuales} queda(n) "
                     f"representada(s) a menos de la mitad. En un gráfico de los dos "
                     f"primeros ejes esas variables aparecen igual que las demás, y su "
                     f"posición no dice nada: está proyectada desde una dirección que no "
                     f"se está mirando."})
    return salida

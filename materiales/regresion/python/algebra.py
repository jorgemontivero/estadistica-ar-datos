"""Resolver sistemas lineales, a mano y sin dependencias.

Acá hay una decisión que conviene entender antes de usar el proyecto con
datos propios.

Un ajuste por mínimos cuadrados se puede resolver de varias maneras. R usa una
descomposición QR; numpy, por omisión, una SVD. Las dos son más estables que
las **ecuaciones normales**, que es lo que hay acá: armar X'X, invertirla y
multiplicar. Las ecuaciones normales elevan al cuadrado el número de condición
del problema, así que con predictores muy correlacionados entre sí pierden
precisión antes que las otras dos.

Se usan igual, por una razón concreta: son **la única forma de que las dos
versiones den exactamente lo mismo**. Con QR en R y SVD en Python, los
coeficientes empiezan a diferir en el décimo dígito y los archivos dejan de
ser idénticos. Escribir el solucionador una vez de cada lado resuelve eso.

La defensa contra el problema de precisión no es teórica: el proyecto calcula
el **VIF** de cada predictor y avisa cuando pasa de 10. Un VIF alto es
exactamente la señal de que X'X está mal condicionada, y en ese caso el aviso
dice que el modelo hay que repensarlo, no que el número esté un poco corrido.

La inversa se calcula entera porque hace falta: los errores estándar de los
coeficientes son la raíz de la diagonal de (X'X)⁻¹ multiplicada por la
varianza residual.
"""


def matriz_por_matriz(a, b):
    n, m, p = len(a), len(b), len(b[0])
    return [[sum(a[i][k] * b[k][j] for k in range(m)) for j in range(p)] for i in range(n)]


def traspuesta(a):
    return [[a[i][j] for i in range(len(a))] for j in range(len(a[0]))]


def matriz_por_vector(a, v):
    return [sum(a[i][k] * v[k] for k in range(len(v))) for i in range(len(a))]


def invertir(a):
    """Inversa por Gauss-Jordan con pivoteo parcial.

    El pivoteo no es un adorno: sin él, un cero en la diagonal rompe la
    eliminación aunque la matriz sea perfectamente invertible.
    """
    n = len(a)
    # Se trabaja sobre una copia extendida con la identidad a la derecha.
    m = [list(a[i]) + [1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]

    for col in range(n):
        # Pivoteo parcial: la fila con el valor absoluto más grande manda.
        pivote = max(range(col, n), key=lambda f: abs(m[f][col]))
        if abs(m[pivote][col]) < 1e-12:
            return None  # singular: no hay inversa que devolver
        m[col], m[pivote] = m[pivote], m[col]

        divisor = m[col][col]
        m[col] = [v / divisor for v in m[col]]

        for fila in range(n):
            if fila == col:
                continue
            factor = m[fila][col]
            if factor != 0.0:
                m[fila] = [v - factor * w for v, w in zip(m[fila], m[col])]

    return [fila[n:] for fila in m]


def resolver(x, y):
    """Mínimos cuadrados por ecuaciones normales: (X'X)⁻¹ X'y.

    Devuelve los coeficientes y la inversa, porque quien llama casi siempre
    necesita las dos cosas y calcular la inversa dos veces sería tonto.
    """
    xt = traspuesta(x)
    xtx = matriz_por_matriz(xt, x)
    inversa = invertir(xtx)
    if inversa is None:
        return None, None
    return matriz_por_vector(inversa, matriz_por_vector(xt, y)), inversa


def resolver_ponderado(x, y, pesos):
    """El mismo ajuste con pesos, que es lo que cada paso del IRLS necesita.

    Equivale a multiplicar cada fila por la raíz de su peso, pero se arma
    directo X'WX para no recorrer los datos dos veces.
    """
    n, k = len(x), len(x[0])
    xtwx = [[sum(pesos[f] * x[f][i] * x[f][j] for f in range(n)) for j in range(k)]
            for i in range(k)]
    xtwy = [sum(pesos[f] * x[f][i] * y[f] for f in range(n)) for i in range(k)]
    inversa = invertir(xtwx)
    if inversa is None:
        return None, None
    return matriz_por_vector(inversa, xtwy), inversa

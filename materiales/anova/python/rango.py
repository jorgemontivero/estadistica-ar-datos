"""La distribución del rango studentizado, que es lo que necesita Tukey.

Es la única distribución de este proyecto que no sale de una función ya hecha.
Su función de distribución es una integral doble:

    P(Q ≤ q) = ∫₀^∞ fν(s) · R(q·s; k) ds

donde R(w; k) = k ∫ φ(z) [Φ(z) − Φ(z−w)]^{k−1} dz es la probabilidad de que el
rango de k normales estándar no supere w, y fν(s) es la densidad de
s = √(χ²ν/ν), el desvío muestral en unidades del poblacional. Las dos se
resuelven con cuadratura de Gauss-Legendre.

**Por qué no se usa `ptukey`, que R trae de fábrica.** Por lo mismo que el
descargable de regresión no usa `lm`: Python no tiene un equivalente exacto y
las dos versiones tienen que escribir los mismos archivos byte a byte.

Pero acá hay además una razón que no es de comodidad. Medido contra
`scipy.stats.studentized_range`, que es una implementación independiente:

    q = 3,5  k = 3  ν = 144       cola
    esto                          3,828330160608e-02
    scipy                         3,828330160611e-02
    ptukey de R                   3,828330160648e-02

    confianza 0,95  k = 4  ν = 20   valor crítico
    esto                          3,958293560921
    scipy                         3,958293560945
    qtukey de R                   3,958293461450

Las dos implementaciones por cuadratura fina coinciden en once dígitos y la de
R se despega en el octavo, porque `ptukey` integra con dieciséis puntos fijos.
Para decidir si un valor p es mayor o menor que 0,05 da exactamente igual; vale
la pena saberlo igual, porque quien compare este proyecto contra R va a ver la
diferencia y merece saber de dónde sale.
"""

import math

# Nodos de cada cuadratura. Con 120 el peor error absoluto contra scipy es
# 1,1·10⁻¹⁰; con 200 baja a 9·10⁻¹³ y con 300 no mejora más, porque ahí ya
# manda el redondeo de la doble precisión y no la cuadratura.
NODOS = 200

# Nodos de la integral EXTERNA cuando hay que evaluar la CDF muchas veces
# seguidas, como en la bisección del valor crítico. Cada CDF son
# nodos_interna × nodos_externa evaluaciones, así que la externa es la que
# conviene recortar. La externa solo hace falta fina con ν chico, que es donde
# la densidad de s es ancha y asimétrica; de ν = 10 en adelante —o sea, en
# cualquier ANOVA de tamaño razonable— sesenta nodos dan todo lo que la doble
# precisión permite.
NODOS_EXTERNOS_POCOS = 60
UMBRAL_GL = 10

_cuadraturas: dict[int, tuple[list[float], list[float]]] = {}


def gauss_legendre(n: int):
    """Nodos y pesos de Gauss-Legendre en [−1, 1].

    Se calculan por el método de Newton sobre los polinomios de Legendre, una
    vez por cantidad de nodos. Es aritmética pura: ni R ni Python tienen nada
    que aportar de su lado, así que los dos llegan al mismo bit.
    """
    if n in _cuadraturas:
        return _cuadraturas[n]

    nodos = [0.0] * n
    pesos = [0.0] * n
    m = (n + 1) >> 1

    for i in range(m):
        # Aproximación inicial de la i-ésima raíz (Abramowitz-Stegun 25.4.30).
        x = math.cos(math.pi * (i + 0.75) / (n + 0.5))
        dp = 0.0
        for _ in range(100):
            # Recurrencia de Legendre para P_n(x) y su derivada.
            p0, p1 = 1.0, 0.0
            for j in range(n):
                p2 = p1
                p1 = p0
                p0 = ((2 * j + 1) * x * p1 - j * p2) / (j + 1)
            dp = (n * (x * p0 - p1)) / (x * x - 1)
            delta = p0 / dp
            x -= delta
            if abs(delta) < 1e-15:
                break
        nodos[i] = -x
        nodos[n - 1 - i] = x
        w = 2 / ((1 - x * x) * dp * dp)
        pesos[i] = w
        pesos[n - 1 - i] = w

    _cuadraturas[n] = (nodos, pesos)
    return _cuadraturas[n]


def integrar(f, a: float, b: float, n: int) -> float:
    """Integra f entre a y b con n nodos.

    La suma va con `fsum`, que es exacta: del lado de R la hace `sum`, que
    acumula en precisión extendida. Las dos dan lo mismo hasta mucho más allá
    de los diez dígitos que este proyecto escribe.
    """
    nodos, pesos = gauss_legendre(n)
    medio = (a + b) / 2
    semi = (b - a) / 2
    return math.fsum(pesos[i] * f(medio + semi * nodos[i]) for i in range(n)) * semi


def normal_cdf(z: float) -> float:
    return 0.5 * math.erfc(-z / math.sqrt(2))


def normal_pdf(z: float) -> float:
    return math.exp(-0.5 * z * z) / math.sqrt(2 * math.pi)


def rango_normal(w: float, k: int, nodos: int) -> float:
    """R(w; k): probabilidad de que el rango de k normales estándar no supere w.

    El integrando decae como una normal, así que integrar sobre ±9 desvíos deja
    afuera una parte despreciable.
    """
    if w <= 0:
        return 0.0

    def f(z):
        d = normal_cdf(z) - normal_cdf(z - w)
        # La potencia k−1 se hace en logaritmos para no perder precisión con k
        # grande.
        return 0.0 if d <= 0 else normal_pdf(z) * math.exp((k - 1) * math.log(d))

    return k * integrar(f, -9, 9 + w, nodos)


def cdf(q: float, k: int, v: float, nodos_interna: int, nodos_externa: int) -> float:
    """P(Q ≤ q) para k grupos y ν grados de libertad del error.

    Con ν muy grande, s se concentra tanto en 1 que la integral externa deja de
    aportar y se puede usar directamente el rango de normales: eso además evita
    que la densidad de s, que se vuelve altísima y angosta, exija demasiados
    nodos.
    """
    if q <= 0 or k < 2:
        return 0.0
    if not math.isfinite(v) or v > 25000:
        return rango_normal(q, k, nodos_interna)

    # Densidad de s = √(χ²ν/ν), en logaritmos.
    ln_constante = (v / 2) * math.log(v / 2) - math.lgamma(v / 2) + math.log(2)

    def densidad_s(s):
        return math.exp(ln_constante + (v - 1) * math.log(s) - (v * s * s) / 2)

    # s tiene media cercana a 1 y desvío ≈ 1/√(2ν), así que nueve desvíos a cada
    # lado cubren todo lo que aporta.
    desvio = 1 / math.sqrt(2 * v)
    desde = max(1e-8, 1 - 9 * desvio)
    hasta = 1 + 9 * desvio

    return integrar(lambda s: densidad_s(s) * rango_normal(q * s, k, nodos_interna),
                    desde, hasta, nodos_externa)


def _externos(v: float) -> int:
    return NODOS if v < UMBRAL_GL else NODOS_EXTERNOS_POCOS


def rango_cdf(q: float, k: int, v: float) -> float:
    return cdf(q, k, v, NODOS, _externos(v))


def rango_cola(q: float, k: int, v: float) -> float:
    """Cola superior: el valor p de una comparación de Tukey.

    Ojo con los valores p diminutos. La cola se calcula como 1 − CDF, y la CDF
    se arma integrando cantidades de orden 1, así que arrastra un error
    absoluto de alrededor de 10⁻¹³ que no se puede bajar en doble precisión.
    Mientras el p sea mayor que ~10⁻¹⁰ eso no se nota; por debajo, la resta se
    come todos los dígitos y el número solo alcanza para decir «prácticamente
    cero». Es la misma limitación que tienen scipy y `ptukey`.
    """
    return min(1.0, max(0.0, 1 - rango_cdf(q, k, v)))


_criticos: dict[tuple, float] = {}


def rango_inv(p: float, k: int, v: float) -> float:
    """El valor crítico de Tukey, por bisección sobre la CDF.

    Se guarda en memoria porque el post hoc lo pide una vez por comparación y
    siempre con los mismos argumentos: cada paso de la bisección es una CDF
    entera, o sea sesenta mil evaluaciones.
    """
    if p <= 0:
        return 0.0
    if p >= 1:
        return float("inf")

    clave = (p, k, v)
    if clave in _criticos:
        return _criticos[clave]

    externos = _externos(v)

    def F(q):
        return cdf(q, k, v, NODOS, externos)

    lo, hi = 0.0, 2.0
    while hi < 1e4 and F(hi) < p:
        hi *= 2
    # Se corta cuando el intervalo es más fino de lo que la CDF puede
    # distinguir.
    vueltas = 0
    while vueltas < 60 and hi - lo > 1e-10:
        medio = (lo + hi) / 2
        if F(medio) < p:
            lo = medio
        else:
            hi = medio
        vueltas += 1

    _criticos[clave] = (lo + hi) / 2
    return _criticos[clave]

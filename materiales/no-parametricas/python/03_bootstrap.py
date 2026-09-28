"""Paso 3: intervalos por bootstrap y la prueba de permutación.

Una prueba de rangos dice si hay diferencia. No dice **de cuánto**, y para casi
cualquier estadístico que no sea una media no hay fórmula cerrada que dé un
intervalo. El bootstrap la reemplaza por fuerza bruta: se vuelve a muestrear
la propia muestra, con reposición, miles de veces, y se mira cómo se mueve el
estadístico.

Se calculan tres intervalos para cada estadístico, porque no dan lo mismo:

    percentil   los cuantiles de las réplicas, directo. Es el que todo el
                mundo usa y el que peor cobertura tiene cuando el estadístico
                es sesgado o su dispersión depende del valor.
    básico      refleja las réplicas alrededor del valor observado. Corrige
                el sesgo de traslación y nada más.
    BCa         corrige el sesgo y la asimetría, con dos constantes: z₀, que
                mide cuántas réplicas caen por debajo del valor observado, y
                a, la aceleración, que sale de un jackknife. Es el mejor de
                los tres y el que casi nadie calcula.

Con un estadístico simétrico y sin sesgo los tres coinciden y la elección no
importa. Con uno asimétrico —la media de un gasto, un desvío, una razón— se
separan, y ahí el percentil empieza a mentir. El proyecto los escribe a los
tres para que la diferencia se vea en vez de discutirse.

**La prueba de permutación** es aparte y es la otra cara. En vez de suponer
una distribución para el estadístico, se la construye: si los dos grupos
vinieran de la misma población, las etiquetas serían intercambiables, así que
se barajan y se mira con qué frecuencia el azar solo produce una diferencia
tan grande como la observada. No supone nada sobre la forma y sirve para
cualquier estadístico, incluso los que no tienen teoría.
"""

import math

from scipy import stats

from azar import Azar
from comun import cuantil, desvio, media


# --------------------------------------------------------- los estadísticos
def a_diez_digitos(v: float) -> float:
    """Redondea a diez dígitos significativos, sin depender de `round`.

    Hacen falta las dos cosas —redondear, y hacerlo a mano— y cada una por su
    motivo.

    **Redondear**, porque las réplicas se ORDENAN para sacar los cuantiles.
    Dos réplicas que difieren en el último bit pueden intercambiar su lugar en
    ese orden, y ahí el cuantil interpola entre otro par de vecinos y el
    intervalo cambia en el sexto decimal.

    **A mano**, porque `round()` de Python y `round()` de R **no desempatan
    igual**. Sobre exactamente el mismo número de doble precisión:

        round(54955.843065, 5)    Python → 54955,84307
                                  R      → 54955,84306

    No es un error de ninguno de los dos: es un valor que cae justo en la
    mitad, y cada lenguaje eligió una regla distinta para ese caso. Con dos
    mil réplicas y un cuantil interpolado, caer en la mitad deja de ser raro.
    Acá se usa «medio para arriba en valor absoluto», que es una regla
    aritmética y da lo mismo en los dos idiomas.
    """
    if v == 0 or not math.isfinite(v):
        return v
    # Con valores así de chicos la escala se iría fuera de lo que un doble
    # representa exacto, y el número se escribe como cero de todos modos.
    if abs(v) < 1e-13:
        return v
    escala = 10.0 ** (9 - math.floor(math.log10(abs(v))))
    return (math.floor(v * escala + 0.5) if v > 0
            else math.ceil(v * escala - 0.5)) / escala


def redondeadas(fila: dict) -> dict:
    """La fila entera pasada por el mismo redondeo.

    Se aplica al final y no en cada cuenta: así ningún número del bootstrap
    llega al archivo sin haber pasado por la misma regla.
    """
    # Solo los decimales: un entero se escribe sin coma y un booleano se
    # escribe «Sí» o «No».
    return {k: (a_diez_digitos(v) if isinstance(v, float) else v)
            for k, v in fila.items()}


def ric(orden):
    return cuantil(orden, 0.75) - cuantil(orden, 0.25)


# Cada uno recibe la muestra YA ORDENADA cuando lo necesita, así no se ordena
# dos veces: sobre 2.000 réplicas eso se nota.
ESTADISTICOS = [
    ("mediana", lambda v, o: cuantil(o, 0.5)),
    ("media", lambda v, o: media(v)),
    ("ric", lambda v, o: ric(o)),
    ("desvio", lambda v, o: desvio(v)),
]


def _evaluar(valores):
    orden = sorted(valores)
    return [a_diez_digitos(f(valores, orden)) for _, f in ESTADISTICOS]


def intervalos(valores, azar, replicas, confianza):
    """Los tres intervalos para cada estadístico, con las mismas réplicas.

    Se remuestrea una sola vez y se evalúan todos los estadísticos sobre cada
    réplica. No es solo por velocidad: usar las mismas réplicas hace que los
    intervalos sean comparables entre sí, porque comparten el azar.
    """
    n = len(valores)
    if n < 3:
        return []
    observados = _evaluar(valores)

    replicados = [[] for _ in ESTADISTICOS]
    for _ in range(replicas):
        muestra = [valores[i] for i in azar.remuestrear(n)]
        for j, v in enumerate(_evaluar(muestra)):
            replicados[j].append(v)

    # El jackknife, para la aceleración del BCa: cada estadístico recalculado
    # sacando un caso por vez.
    jack = [[] for _ in ESTADISTICOS]
    for i in range(n):
        sin_i = valores[:i] + valores[i + 1:]
        for j, v in enumerate(_evaluar(sin_i)):
            jack[j].append(v)

    alfa = 1 - confianza
    z_baja = float(stats.norm.ppf(alfa / 2))
    z_alta = float(stats.norm.ppf(1 - alfa / 2))

    salida = []
    for j, (nombre, _) in enumerate(ESTADISTICOS):
        rep = sorted(replicados[j])
        observado = observados[j]
        if not math.isfinite(observado):
            continue

        percentil = (cuantil(rep, alfa / 2), cuantil(rep, 1 - alfa / 2))
        # El básico refleja: si las réplicas quedaron por encima del
        # observado, el intervalo tiene que correrse hacia abajo.
        basico = (2 * observado - percentil[1], 2 * observado - percentil[0])

        # z₀: cuántas réplicas cayeron por debajo del observado, en unidades
        # normales. Mide el sesgo de la distribución bootstrap.
        menores = sum(1 for v in replicados[j] if v < observado)
        proporcion = menores / replicas
        if proporcion <= 0 or proporcion >= 1:
            # Con todas las réplicas de un lado no hay corrección posible, y
            # forzarla daría un infinito. Se deja el percentil y se avisa.
            salida.append(redondeadas({
                "estadistico": nombre, "observado": observado,
                "error_estandar": desvio(replicados[j]),
                "sesgo": media(replicados[j]) - observado,
                "percentil_inferior": percentil[0], "percentil_superior": percentil[1],
                "basico_inferior": basico[0], "basico_superior": basico[1],
                "bca_inferior": None, "bca_superior": None,
                "z0": None, "aceleracion": None,
            }))
            continue
        z0 = float(stats.norm.ppf(proporcion))

        promedio_jack = media(jack[j])
        d = [promedio_jack - v for v in jack[j]]
        suma2 = math.fsum(x * x for x in d)
        aceleracion = (math.fsum(x ** 3 for x in d) / (6 * suma2 ** 1.5)) if suma2 > 0 else 0.0

        def ajustado(z):
            denominador = 1 - aceleracion * (z0 + z)
            if denominador == 0:
                return None
            return float(stats.norm.cdf(z0 + (z0 + z) / denominador))

        baja, alta = ajustado(z_baja), ajustado(z_alta)
        bca = ((cuantil(rep, baja), cuantil(rep, alta))
               if baja is not None and alta is not None else (None, None))

        salida.append(redondeadas({
            "estadistico": nombre, "observado": observado,
            "error_estandar": desvio(replicados[j]),
            "sesgo": media(replicados[j]) - observado,
            "percentil_inferior": percentil[0], "percentil_superior": percentil[1],
            "basico_inferior": basico[0], "basico_superior": basico[1],
            "bca_inferior": bca[0], "bca_superior": bca[1],
            "z0": z0, "aceleracion": aceleracion,
        }))
    return salida


def diferencia(a, b, azar, replicas, confianza):
    """El intervalo para la diferencia entre dos grupos, remuestreando cada uno
    por separado.

    Es lo que corresponde con muestras independientes: remuestrear todo junto
    supondría que vienen de la misma población, que es justamente lo que se
    está poniendo en duda.
    """
    na, nb = len(a), len(b)
    if na < 3 or nb < 3:
        return []
    orden_a, orden_b = sorted(a), sorted(b)
    observados = {
        "diferencia_de_medianas": a_diez_digitos(cuantil(orden_b, 0.5)
                                                 - cuantil(orden_a, 0.5)),
        "diferencia_de_medias": a_diez_digitos(media(b) - media(a)),
    }

    replicados = {clave: [] for clave in observados}
    for _ in range(replicas):
        ra = sorted(a[i] for i in azar.remuestrear(na))
        rb = sorted(b[i] for i in azar.remuestrear(nb))
        replicados["diferencia_de_medianas"].append(
            a_diez_digitos(cuantil(rb, 0.5) - cuantil(ra, 0.5)))
        replicados["diferencia_de_medias"].append(a_diez_digitos(media(rb) - media(ra)))

    alfa = 1 - confianza
    salida = []
    for clave, observado in observados.items():
        rep = sorted(replicados[clave])
        inferior, superior = cuantil(rep, alfa / 2), cuantil(rep, 1 - alfa / 2)
        salida.append(redondeadas({
            "estadistico": clave, "observado": observado,
            "error_estandar": desvio(replicados[clave]),
            "sesgo": media(replicados[clave]) - observado,
            "percentil_inferior": inferior, "percentil_superior": superior,
            "basico_inferior": 2 * observado - superior,
            "basico_superior": 2 * observado - inferior,
            "bca_inferior": None, "bca_superior": None, "z0": None, "aceleracion": None,
            # Un intervalo que no contiene al cero dice lo mismo que un valor p
            # menor que alfa, y dice además de cuánto es la diferencia.
            "excluye_el_cero": (inferior > 0) == (superior > 0),
        }))
    return salida


def permutacion(a, b, azar, replicas, confianza):
    """La prueba de permutación sobre la diferencia de medianas.

    El valor p va con la corrección de Davison y Hinkley: (aciertos + 1) sobre
    (réplicas + 1), y no aciertos sobre réplicas. La razón es simple: la
    permutación observada es una de las posibles, así que contarla evita el
    absurdo de informar p = 0, que diría que ninguna reordenación del azar
    podría dar lo que se vio.
    """
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return None
    todos = list(a) + list(b)
    n = na + nb
    observada = a_diez_digitos(cuantil(sorted(b), 0.5) - cuantil(sorted(a), 0.5))

    extremas = 0
    for _ in range(replicas):
        orden = azar.permutar(n)
        ra = sorted(todos[orden[i]] for i in range(na))
        rb = sorted(todos[orden[i]] for i in range(na, n))
        if abs(a_diez_digitos(cuantil(rb, 0.5) - cuantil(ra, 0.5))) >= abs(observada) - 1e-12:
            extremas += 1

    p = (extremas + 1) / (replicas + 1)
    return redondeadas({"observada": observada, "extremas": extremas,
                        "replicas": replicas, "p": p,
                        "significativa": p < 1 - confianza})


def calcular(parametros, valores, grupos):
    replicas = parametros["replicas"]
    confianza = parametros["confianza"]
    # Cada bloque arranca de su propia semilla derivada, así agregar o sacar
    # un bloque no corre el azar de los demás.
    azar_uno = Azar(parametros["semilla"])
    azar_dos = Azar(parametros["semilla"] + 1)
    azar_tres = Azar(parametros["semilla"] + 2)

    filas = intervalos(valores, azar_uno, replicas, confianza) if valores else []
    nombres = list(grupos)
    perm = None
    if len(nombres) == 2:
        a, b = grupos[nombres[0]], grupos[nombres[1]]
        filas += diferencia(a, b, azar_dos, replicas, confianza)
        perm = permutacion(a, b, azar_tres, replicas, confianza)

    avisos = []
    for fila in filas:
        if fila["bca_inferior"] is None and fila["z0"] is None and "excluye_el_cero" not in fila:
            avisos.append({"donde": "bootstrap",
                           "aviso": f"No se pudo calcular el BCa de «{fila['estadistico']}»: "
                                    f"todas las réplicas quedaron del mismo lado del valor "
                                    f"observado. Suele pasar con estadísticos que toman "
                                    f"pocos valores distintos."})
            continue
        if fila["bca_inferior"] is None:
            continue
        # Cuánto se mueve el intervalo al corregir. Si se mueve mucho, el
        # percentil —que es el que todo el mundo informa— está mal.
        ancho = fila["percentil_superior"] - fila["percentil_inferior"]
        corrimiento = max(abs(fila["bca_inferior"] - fila["percentil_inferior"]),
                          abs(fila["bca_superior"] - fila["percentil_superior"]))
        if ancho > 0 and corrimiento / ancho > 0.1:
            avisos.append({"donde": "bootstrap",
                           "aviso": f"En «{fila['estadistico']}», el intervalo BCa se corre "
                                    + f"{corrimiento / ancho * 100:.0f}".replace(".", ",")
                                    + " % del ancho respecto del percentil. El percentil es "
                                      "el que casi todo el mundo informa, y acá está "
                                      "sesgado: el que corresponde es el BCa."})

    if perm and len(nombres) == 2:
        # El p de permutación no puede bajar de 1/(réplicas+1): si dio el
        # mínimo, lo único que se sabe es «menor que eso».
        minimo = 1 / (replicas + 1)
        if perm["p"] <= minimo + 1e-12:
            avisos.append({"donde": "bootstrap",
                           "aviso": f"La prueba de permutación dio el valor p más chico que "
                                    f"puede dar con {replicas} réplicas. No significa que "
                                    f"sea cero: significa que hace falta correr más "
                                    f"réplicas para ponerle un número."})

    return {"intervalos": filas, "permutacion": perm, "replicas": replicas,
            "avisos": avisos}

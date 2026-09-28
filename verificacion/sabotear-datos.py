"""Rompe los JSON de datos/ a propósito, para ver si el verificador se da cuenta.

    python scripts/sabotear-datos.py          # todos
    python scripts/sabotear-datos.py 0 3      # los sabotajes 0 a 2

Cada sabotaje es un cambio de un número, del tipo que produce un filtro mal
puesto o un ponderador equivocado. Los tres primeros **reproducen errores que
de verdad estuvieron publicados** en septiembre de 2026, y están puestos
primero porque son los que justifican que este verificador exista.

Al lado de cada sabotaje detectado va el frente que hizo falta:

  [sin microdatos]   lo agarra la aritmética interna o la coherencia cruzada
  [solo microdatos]  ninguna de las dos alcanza; hubo que recontar el archivo

El sabotaje 2 —el ponderador equivocado del Gini— es el que solo cae con el
recuento. Es la razón de ser del cuarto frente: un número puede cerrar contra
todos los demás números del sitio y aun así no ser el que sale de los datos.
"""

import json
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "datos"
CASOS = RAIZ / "src" / "content" / "casos"

TASAS = DATOS / "demografia" / "tasas-m05.json"
ANOVA = DATOS / "eph" / "anova-m11.json"
PROBA = DATOS / "eph" / "probabilidad-m06.json"
INGRESOS = DATOS / "eph" / "ingresos-eph.json"
DISENO = DATOS / "eph" / "diseno-complejo-m17.json"
SERIES = DATOS / "series" / "indices-m04.json"

# (qué error simula, archivo, lo que dice, lo que va a decir, todas las veces)
SABOTAJES = [
    # ------------------------------------------- los tres que ya pasaron
    ("el filtro que deja afuera a los menores de un año, en los dos lugares "
     "a la vez", TASAS,
     '"poblacion_total": 30095103.0', '"poblacion_total": 29869595.0', True),
    ("la proporción de menores de 15 calculada sin los bebés", TASAS,
     '"prop_0_14": 0.2216911169900299', '"prop_0_14": 0.2158', False),
    ("el Gini del ingreso ponderado con PONDERA en vez de PONDIIO", TASAS,
     '"gini": 0.41985799649510924', '"gini": 0.41576', False),

    # -------------------------------------------------- la aritmética interna
    ("una suma de cuadrados del ANOVA que no cierra", ANOVA,
     '"sc_entre": 1052156236064188.8', '"sc_entre": 1152156236064188.8', False),
    ("un grado de libertad que no es k − 1", ANOVA,
     '"gl_entre": 5', '"gl_entre": 6', False),
    ("una probabilidad conjunta que rompe la suma 1", PROBA,
     '"sec0_reg0": 0.14935016030925508', '"sec0_reg0": 0.16', False),
    ("un cuartil fuera de orden", INGRESOS,
     '"q1": 500000', '"q1": 1500000', False),
    ("un deff que no es el cuadrado de la razón de errores estándar", DISENO,
     '"deff": 3.4193862270939577', '"deff": 3.9193862270939577', False),
    ("un índice estacional que rompe el promedio de 1", SERIES,
     '"ene": 1.5956715471003846', '"ene": 1.7', False),

    # ----------------------------------------------------- la coherencia
    ("un n del Gini que no coincide con el de ingresos", TASAS,
     '"n": 15448', '"n": 15400', False),
    ("un caso que deja de declarar que el análisis va sin ponderar",
     CASOS / "ingreso-horas-eph.mdx",
     "están calculadas **sin ponderar**",
     "están calculadas **con los datos de la EPH**", True),
]

CRLF = chr(13) + chr(10)


def aplicar(archivo: Path, viejo: str, nuevo: str, todas: bool) -> str:
    crudo = archivo.read_bytes().decode("utf-8")
    tiene_crlf = CRLF in crudo
    texto = crudo.replace(CRLF, chr(10))
    if texto.count(viejo) < 1:
        raise SystemExit(f"En {archivo.name} «{viejo[:50]}» no aparece.")
    texto = texto.replace(viejo, nuevo) if todas else texto.replace(viejo, nuevo, 1)
    if tiene_crlf:
        texto = texto.replace(chr(10), CRLF)
    archivo.write_bytes(texto.encode("utf-8"))
    return crudo


def corre_el_verificador() -> bool:
    r = subprocess.run(
        [sys.executable, str(RAIZ / "scripts" / "verificar-datos.py")],
        cwd=RAIZ, capture_output=True, text=True, encoding="utf-8",
        errors="replace")
    return r.returncode == 0


def por_que_frente(archivo: Path, viejo: str, nuevo: str, todas: bool) -> str:
    """Corre el verificador sin el frente de microdatos, para saber si hacía
    falta llegar hasta ahí."""
    original = aplicar(archivo, viejo, nuevo, todas)
    try:
        r = subprocess.run(
            [sys.executable, "-c",
             "import runpy, sys;"
             "sys.argv=['verificar-datos.py'];"
             "m=runpy.run_path(r'scripts/verificar-datos.py', run_name='x');"
             "c=m['frente_forma']();m['frente_aritmetica'](c);"
             "m['frente_coherencia'](c);"
             "sys.exit(1 if m['problemas'] else 0)"],
            cwd=RAIZ, capture_output=True, text=True, encoding="utf-8",
            errors="replace")
        return "sin microdatos" if r.returncode != 0 else "solo microdatos"
    finally:
        archivo.write_bytes(original.encode("utf-8"))


if __name__ == "__main__":
    desde = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    hasta = int(sys.argv[2]) if len(sys.argv) > 2 else len(SABOTAJES)
    sin_detectar = []

    for i in range(desde, min(hasta, len(SABOTAJES))):
        que, archivo, viejo, nuevo, todas = SABOTAJES[i]
        original = None
        try:
            original = aplicar(archivo, viejo, nuevo, todas)
            paso = corre_el_verificador()
        finally:
            if original is not None:
                archivo.write_bytes(original.encode("utf-8"))
        marca = "NO LO VE" if paso else "lo detecta"
        detalle = ""
        if not paso:
            detalle = f"  [{por_que_frente(archivo, viejo, nuevo, todas)}]"
        print(f"  {i:2d}  {marca}  {que}{detalle}")
        if paso:
            sin_detectar.append(f"{i}: {que}")

    if sin_detectar:
        print(f"\n{len(sin_detectar)} sabotajes sin detectar:")
        for s in sin_detectar:
            print(f"  · {s}")
        raise SystemExit(1)
    n = min(hasta, len(SABOTAJES)) - desde
    print(f"\nLos {n} sabotajes de la tanda se detectan.")

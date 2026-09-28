"""Paso 1: abrir el archivo del INDEC y entender qué dice.

Leer la EPH es la mitad del trabajo, y es la mitad que no se publica. Este paso
hace tres cosas, en este orden:

1. **Abre el archivo con el formato correcto.** Punto y coma, latin-1, textos
   entre comillas. Está en `comun.leer_microdatos`.
2. **Traduce los códigos.** `ESTADO = 1` es «ocupado» y `CAT_OCUP = 3` es
   «obrero o empleado». Sin el diccionario, las tablas que salen son ilegibles
   y las decisiones que se toman con ellas, también.
3. **Revisa lo que puede estar mal** y lo escribe en `avisos.csv`. No corrige
   nada por su cuenta: avisa. Un programa que arregla los datos en silencio es
   un programa que produce un número del que nadie puede responder.

Las revisiones no son genéricas: son las cosas que efectivamente pasan con los
archivos de la EPH, y cada una está comentada donde se hace.
"""

from comun import FALTANTES, entero, limpiar_texto, numero, ordenar

# ------------------------------------------------------------ los códigos
#
# Salen del diseño de registro que el INDEC publica junto con la base. No están
# acá para adornar: una tabla que dice «3» en vez de «Obrero o empleado» es una
# tabla que nadie puede revisar.
CONDICION = {
    0: "Entrevista individual no realizada",
    1: "Ocupado",
    2: "Desocupado",
    3: "Inactivo",
    4: "Menor de 10 años",
}

CATEGORIA = {
    1: "Patrón",
    2: "Cuenta propia",
    3: "Obrero o empleado",
    4: "Trabajador familiar sin remuneración",
    9: "Sin especificar",
}

NIVEL = {
    1: "Primaria incompleta",
    2: "Primaria completa",
    3: "Secundaria incompleta",
    4: "Secundaria completa",
    5: "Superior incompleta",
    6: "Superior completa",
    7: "Sin instrucción",
    9: "Sin especificar",
}

SEXO = {1: "Varón", 2: "Mujer"}

INTENSIDAD = {
    1: "Subocupado",
    2: "Ocupado pleno",
    3: "Sobreocupado",
    4: "Ocupado que no trabajó en la semana",
}

DESCUENTO = {1: "Con descuento jubilatorio", 2: "Sin descuento jubilatorio"}

REGIONES = {
    1: "Gran Buenos Aires",
    40: "Noroeste",
    41: "Nordeste",
    42: "Cuyo",
    43: "Pampeana",
    44: "Patagonia",
}

# Los tramos con los que la EPH suele publicar. El orden es este y no el
# alfabético: «10 a 13» antes que «65 y más» no sale de ordenar textos.
TRAMOS = [
    ("10 a 13", 10, 13),
    ("14 a 24", 14, 24),
    ("25 a 34", 25, 34),
    ("35 a 49", 35, 49),
    ("50 a 64", 50, 64),
    ("65 y más", 65, 200),
]

ORDEN_CONDICION = [1, 2, 3, 4, 0]

# Sin estas no hay proyecto. El resto se puede no tener.
IMPRESCINDIBLES = ["ESTADO", "CH04", "CH06"]

# El trimestre a partir del cual el INDEC publica los ponderadores de ingreso.
# Antes de este, `PONDIIO`, `PONDII` y `PONDIH` **no existen en el archivo**, y
# el que reusa un script hecho para un trimestre reciente sobre una base vieja
# se queda sin ellos sin enterarse.
PRIMER_TRIMESTRE_CON_PONDERADOR_DE_INGRESO = (2016, 2)


def tramo_de(edad):
    for etiqueta, desde, hasta in TRAMOS:
        if desde <= edad <= hasta:
            return etiqueta
    return None


def etiqueta(tabla, codigo, sin_dato="Sin dato"):
    return tabla.get(codigo, f"Código {codigo}" if codigo is not None else sin_dato)


def leer(columnas, crudas, parametros):
    """Los registros ya interpretados, más la lista de lo que hay que mirar."""
    avisos = []
    presentes = set(columnas)

    faltan = [c for c in IMPRESCINDIBLES if c not in presentes]
    if faltan:
        raise SystemExit(
            f"Al archivo le faltan columnas que el proyecto necesita: "
            f"{', '.join(faltan)}. ¿Es el archivo de individual y no el de hogar?")

    ponderador = parametros["ponderador"]
    if ponderador not in presentes:
        raise SystemExit(
            f"El archivo no tiene la columna «{ponderador}». Sin ponderador no hay "
            f"nada que estimar: la EPH es una muestra, y sus casos no valen uno.")

    # ------------------------------------------------- el período del archivo
    anos = ordenar([f.get("ANO4", "") for f in crudas]) if "ANO4" in presentes else []
    trimestres = (ordenar([f.get("TRIMESTRE", "") for f in crudas])
                  if "TRIMESTRE" in presentes else [])
    periodo = ""
    ano_num, trimestre_num = None, None
    if len(anos) == 1 and len(trimestres) == 1:
        ano_num = entero(anos[0])
        trimestre_num = entero(trimestres[0])
        periodo = f"{anos[0]}T{trimestres[0]}"
    elif anos and trimestres:
        periodo = f"{len(anos)} años y {len(trimestres)} trimestres"
        avisos.append({
            "donde": "archivo",
            "aviso": "El archivo tiene más de un trimestre adentro. Las tasas que "
                     "salen de acá son un promedio de trimestres distintos, que no es "
                     "lo mismo que la tasa de ninguno de ellos. Si es a propósito, "
                     "está bien; si es porque se concatenaron bases, no."})

    # ------------------------------------- el ponderador del ingreso, o su falta
    #
    # Esta es la trampa que más caro sale. Antes de 2016T2 las bases de la EPH
    # **no traen** PONDIIO, PONDII ni PONDIH. Un script escrito contra un
    # trimestre reciente y corrido sobre uno viejo se queda sin el ponderador
    # de ingreso; si además no se filtra el −9, el ingreso medio se hunde un
    # veinte por ciento y no hay ningún error en pantalla.
    nombre_ingreso_pond = parametros["ponderador_ingreso"]
    hay_ponderador_ingreso = nombre_ingreso_pond in presentes
    if not hay_ponderador_ingreso:
        viejo = (ano_num is not None and trimestre_num is not None
                 and (ano_num, trimestre_num) < PRIMER_TRIMESTRE_CON_PONDERADOR_DE_INGRESO)
        porque = (" Es lo esperable: el INDEC lo publica recién desde 2016T2."
                  if viejo else "")
        avisos.append({
            "donde": "ponderadores",
            "aviso": f"El archivo no tiene «{nombre_ingreso_pond}».{porque} Los "
                     f"ingresos se estiman con «{ponderador}», que **no corrige la no "
                     f"respuesta**: el que no declara ingresos no se parece al que sí, "
                     f"y con el ponderador general su ausencia no se compensa. La "
                     f"tabla «ponderador-e-ingreso.csv» muestra cuánto cambia."})
        nombre_ingreso_pond = ponderador

    nombre_ingreso = parametros["ingreso"]
    hay_ingreso = nombre_ingreso in presentes
    if not hay_ingreso:
        avisos.append({
            "donde": "ingresos",
            "aviso": f"El archivo no tiene la columna «{nombre_ingreso}». Las tablas de "
                     f"ingresos salen vacías."})

    # ---------------------------------------------------------- los registros
    registros = []
    con_na_literal = 0
    peso_no_positivo = 0
    estado_raro = 0
    bebes = 0
    for f in crudas:
        for c in (ponderador, "ESTADO", "CH06", nombre_ingreso):
            if limpiar_texto(f.get(c, "")).upper() in FALTANTES and c in presentes:
                con_na_literal += 1

        peso = numero(f.get(ponderador, ""))
        if peso is None or peso <= 0:
            peso_no_positivo += 1
            continue

        estado = entero(f.get("ESTADO", ""))
        if estado not in CONDICION:
            estado_raro += 1

        edad = entero(f.get("CH06", ""))
        # CH06 = −1 quiere decir «menos de un año», no «falta el dato». Tratarlo
        # como un número sin mirarlo mete edades negativas en cualquier
        # promedio de edad que se calcule después.
        if edad is not None and edad < 0:
            bebes += 1
            edad = 0

        peso_ingreso = numero(f.get(nombre_ingreso_pond, "")) if hay_ingreso else None
        registros.append({
            "pondera": peso,
            "pondera_ingreso": 0.0 if peso_ingreso is None else peso_ingreso,
            "aglomerado": limpiar_texto(f.get("AGLOMERADO", "")),
            "region": entero(f.get("REGION", "")),
            # La unidad primaria disponible. Un hogar es CODUSU + NRO_HOGAR:
            # una vivienda puede tener más de un hogar adentro.
            "hogar": (limpiar_texto(f.get("CODUSU", "")) + "|"
                      + limpiar_texto(f.get("NRO_HOGAR", ""))),
            "sexo": entero(f.get("CH04", "")),
            "edad": edad,
            "nivel_ed": entero(f.get("NIVEL_ED", "")),
            "estado": estado,
            "cat_ocup": entero(f.get("CAT_OCUP", ""), 0),
            "pp07h": entero(f.get("PP07H", ""), 0),
            "intensi": entero(f.get("INTENSI", ""), 0),
            "p21": numero(f.get(nombre_ingreso, "")) if hay_ingreso else None,
        })

    if not registros:
        raise SystemExit("No quedó ningún registro con ponderador positivo.")

    # ------------------------------------------------------------- los filtros
    quedan = registros
    if parametros["region"]:
        pedidas = {limpiar_texto(r) for r in parametros["region"].split(" ")}
        quedan = [r for r in quedan if str(r["region"]) in pedidas]
    if parametros["aglomerado"]:
        pedidos = {limpiar_texto(a) for a in parametros["aglomerado"].split(" ")}
        quedan = [r for r in quedan if r["aglomerado"] in pedidos]
    if not quedan:
        raise SystemExit("El filtro de región o aglomerado no dejó ningún registro.")
    filtrados = len(registros) - len(quedan)

    # ----------------------------------------------------------- las revisiones
    if con_na_literal:
        avisos.append({
            "donde": "archivo",
            "aviso": f"Hay {con_na_literal} celdas con «NA» escrito con letras en las "
                     f"columnas que el proyecto usa. En algunos trimestres —2021T1, "
                     f"2024T3 y 2024T4— el INDEC las escribe así, y eso convierte en "
                     f"texto a ciento cincuenta columnas numéricas en cualquier lector "
                     f"que adivine el tipo. Acá se leen como texto a propósito y se "
                     f"tratan como dato faltante."})
    if peso_no_positivo:
        avisos.append({
            "donde": "ponderadores",
            "aviso": f"Se descartaron {peso_no_positivo} registros con «{ponderador}» "
                     f"nulo o ausente. Un registro sin ponderador no representa a nadie."})
    if estado_raro:
        avisos.append({
            "donde": "códigos",
            "aviso": f"Hay {estado_raro} registros con un valor de ESTADO que no está en "
                     f"el diseño de registro. No entran en ninguna de las cinco "
                     f"condiciones y por lo tanto no entran en el denominador de nada."})
    if bebes:
        avisos.append({
            "donde": "códigos",
            "aviso": f"Hay {bebes} registros con CH06 negativo. En la EPH «−1» quiere "
                     f"decir «menos de un año», no «falta el dato»: se los cuenta como "
                     f"cero. Promediar la columna sin mirarla da una edad media más "
                     f"baja de la que corresponde."})
    if filtrados:
        avisos.append({
            "donde": "filtros",
            "aviso": f"Se dejaron afuera {filtrados} registros por el filtro de región o "
                     f"aglomerado declarado en parametros.csv. Todo lo que sigue es de la "
                     f"parte filtrada, y no del total de los aglomerados relevados."})

    # ----------------------- la coherencia entre el ingreso y su ponderador
    #
    # En las bases del INDEC el ponderador de ingreso vale **cero** justo para
    # los que no declararon. Comprobarlo es la manera de saber si el archivo es
    # el que uno cree que es: si no se cumple, o el archivo está tocado, o la
    # columna que se está usando no es la que se piensa.
    if hay_ingreso and hay_ponderador_ingreso:
        ocupados = [r for r in quedan if r["estado"] == 1]
        sin_declarar = [r for r in ocupados if r["p21"] is not None and r["p21"] < 0]
        mal = sum(1 for r in sin_declarar if r["pondera_ingreso"] > 0)
        if mal:
            avisos.append({
                "donde": "ponderadores",
                "aviso": f"Hay {mal} ocupados que no declararon ingreso y sin embargo "
                         f"tienen «{nombre_ingreso_pond}» mayor que cero. En una base del "
                         f"INDEC eso no pasa: el ponderador de ingreso vale cero para el "
                         f"que no contestó. Conviene revisar de dónde salió el archivo."})
        if sin_declarar:
            peso_total = sum(r["pondera"] for r in ocupados)
            peso_sin = sum(r["pondera"] for r in sin_declarar)
            avisos.append({
                "donde": "ingresos",
                "aviso": f"{len(sin_declarar)} ocupados —el "
                         + f"{100 * peso_sin / peso_total:.1f}".replace(".", ",")
                         + f" % ponderado— tienen «{nombre_ingreso}» negativo, que en la "
                         f"EPH quiere decir «no responde» y no «ingreso negativo». "
                         f"Promediar esa columna sin sacarlos es el error más caro que se "
                         f"puede cometer con esta base."})

    # ------------------------------------------------------------- la población
    peso_total = sum(r["pondera"] for r in quedan)
    poblacion = []
    vistos = {r["estado"] for r in quedan}
    # Primero las cinco condiciones en el orden en que se informan; después
    # cualquier código que el archivo traiga y el diseño de registro no
    # contemple; y al final, si los hay, los que directamente no tienen dato.
    otros = sorted(c for c in vistos if c not in ORDEN_CONDICION and c is not None)
    faltantes = [None] if None in vistos else []
    for codigo in ORDEN_CONDICION + otros + faltantes:
        del_grupo = [r for r in quedan if r["estado"] == codigo]
        if not del_grupo:
            continue
        peso = sum(r["pondera"] for r in del_grupo)
        poblacion.append({
            "condicion": etiqueta(CONDICION, codigo),
            "codigo": codigo, "n": len(del_grupo), "poblacion": peso,
            "porcentaje": peso / peso_total,
        })

    return {
        "registros": quedan,
        "avisos": avisos,
        "periodo": periodo,
        "poblacion": poblacion,
        "peso_total": peso_total,
        "hogares": len({r["hogar"] for r in quedan}),
        "aglomerados": len({r["aglomerado"] for r in quedan}),
        "ponderador_de_ingreso": nombre_ingreso_pond,
        "hay_ponderador_de_ingreso": hay_ponderador_ingreso,
        "hay_ingreso": hay_ingreso,
        "columnas_del_archivo": len(columnas),
    }

"""Módulo propio de análisis de datos de Fórmula 1 con pandas.

Recibe los datos crudos (ya obtenidos por `api_f1.py`) y se encarga de:
1. Aplanar el JSON anidado en una tabla (DataFrame) fácil de analizar.
2. Calcular estadísticas por piloto: puntos, victorias, podios, etc.

Separar esto de `api_f1.py` sigue el principio de responsabilidad única:
un módulo sabe "cómo conseguir los datos", el otro sabe "qué hacer con ellos".
"""

import pandas as pd


def construir_tabla_resultados(carreras: list) -> pd.DataFrame:
    """Aplana la lista de carreras (JSON anidado) en un DataFrame de pandas.

    Cada fila representa el resultado de un piloto en una carrera puntual.

    Args:
        carreras: Lista de carreras tal como la devuelve
            `api_f1.obtener_resultados_temporada`.

    Returns:
        DataFrame con columnas: ronda, gran_premio, fecha, piloto_id,
        piloto, codigo, constructor, posicion, puntos, estado.
    """
    filas = []

    for carrera in carreras:
        for resultado in carrera.get("Results", []):
            piloto = resultado["Driver"]
            constructor = resultado["Constructor"]

            filas.append({
                "ronda": int(carrera["round"]),
                "gran_premio": carrera["raceName"],
                "fecha": carrera["date"],
                "piloto_id": piloto["driverId"],
                "piloto": f"{piloto['givenName']} {piloto['familyName']}",
                "codigo": piloto.get("code", ""),
                "constructor": constructor["name"],
                "posicion": _a_entero_o_none(resultado.get("position")),
                "puntos": float(resultado.get("points", 0)),
                "estado": resultado.get("status", ""),
            })

    return pd.DataFrame(filas)


def _a_entero_o_none(valor):
    """Convierte a entero si es posible; si no (ej. 'R' de retirado), None."""
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def _puntos_sprint_por_piloto(carreras_sprint: list) -> dict:
    """Suma los puntos de sprint por piloto.

    Args:
        carreras_sprint: Lista de carreras sprint (puede ser None o vacía
            si la temporada no tuvo sprints).

    Returns:
        Diccionario {piloto_id: puntos_de_sprint}. Vacío si no hay sprints.
    """
    puntos = {}
    for carrera in carreras_sprint or []:
        for resultado in carrera.get("SprintResults", []):
            piloto_id = resultado["Driver"]["driverId"]
            puntos_sprint = float(resultado.get("points", 0))
            puntos[piloto_id] = puntos.get(piloto_id, 0.0) + puntos_sprint
    return puntos


def listar_pilotos(tabla: pd.DataFrame, carreras_sprint: list = None) -> pd.DataFrame:
    """Devuelve la lista de pilotos de la temporada ordenados por puntos.

    Args:
        tabla: DataFrame generado por `construir_tabla_resultados`.
        carreras_sprint: Lista de carreras sprint (opcional). Si se pasa,
            sus puntos se suman al total de cada piloto, tal como hace la
            clasificación oficial del campeonato.

    Returns:
        DataFrame con columnas piloto_id, piloto, puntos_totales, ordenado
        de mayor a menor cantidad de puntos.
    """
    resumen = (
        tabla.groupby(["piloto_id", "piloto"])["puntos"]
        .sum()
        .reset_index()
        .rename(columns={"puntos": "puntos_totales"})
    )

    puntos_sprint = _puntos_sprint_por_piloto(carreras_sprint)
    if puntos_sprint:
        resumen["puntos_totales"] = resumen.apply(
            lambda fila: fila["puntos_totales"] + puntos_sprint.get(fila["piloto_id"], 0.0),
            axis=1,
        )

    return resumen.sort_values("puntos_totales", ascending=False).reset_index(drop=True)


def estadisticas_piloto(tabla: pd.DataFrame, piloto_id: str, carreras_sprint: list = None) -> dict:
    """Calcula estadísticas de un piloto en la temporada.

    Victorias, podios, posición promedio y % de carreras terminadas se
    calculan solo sobre carreras de Grand Prix (así se cuentan
    oficialmente). Los puntos de sprint, si se pasan, se suman únicamente
    al total de puntos.

    Args:
        tabla: DataFrame generado por `construir_tabla_resultados`.
        piloto_id: Identificador del piloto (ej: "max_verstappen").
        carreras_sprint: Lista de carreras sprint (opcional).

    Returns:
        Diccionario con: nombre, puntos_totales, victorias, podios,
        posicion_promedio, carreras_disputadas, porcentaje_terminadas.
    """
    datos_piloto = tabla[tabla["piloto_id"] == piloto_id]

    if datos_piloto.empty:
        raise ValueError(
            f"No hay datos para el piloto '{piloto_id}' en esta temporada."
        )

    posiciones_validas = datos_piloto["posicion"].dropna()
    patron_terminada = "Finished|\\+"
    coincide = datos_piloto["estado"].str.contains(
        patron_terminada, case=False, regex=True, na=False
    )
    carreras_terminadas = datos_piloto[coincide]

    if posiciones_validas.empty:
        posicion_promedio = None
    else:
        posicion_promedio = round(posiciones_validas.mean(), 2)

    porcentaje_terminadas = round(
        100 * len(carreras_terminadas) / len(datos_piloto), 1
    )

    puntos_sprint = _puntos_sprint_por_piloto(carreras_sprint).get(piloto_id, 0.0)

    return {
        "nombre": datos_piloto["piloto"].iloc[0],
        "puntos_totales": datos_piloto["puntos"].sum() + puntos_sprint,
        "victorias": int((datos_piloto["posicion"] == 1).sum()),
        "podios": int((datos_piloto["posicion"] <= 3).sum()),
        "posicion_promedio": posicion_promedio,
        "carreras_disputadas": len(datos_piloto),
        "porcentaje_terminadas": porcentaje_terminadas,
    }


def comparar_pilotos(
    tabla: pd.DataFrame, pilotos_ids: list, carreras_sprint: list = None
) -> pd.DataFrame:
    """Arma una tabla comparativa de estadísticas para varios pilotos.

    Args:
        tabla: DataFrame generado por `construir_tabla_resultados`.
        pilotos_ids: Lista de identificadores de pilotos a comparar.
        carreras_sprint: Lista de carreras sprint (opcional).

    Returns:
        DataFrame con una fila por piloto y sus estadísticas principales.
    """
    filas = [
        estadisticas_piloto(tabla, piloto_id, carreras_sprint)
        for piloto_id in pilotos_ids
    ]
    return pd.DataFrame(filas)


def podio_temporada(tabla: pd.DataFrame, carreras_sprint: list = None) -> list:
    """Devuelve las estadísticas de los 3 primeros del campeonato.

    Args:
        tabla: DataFrame generado por `construir_tabla_resultados`.
        carreras_sprint: Lista de carreras sprint (opcional).

    Returns:
        Lista de 3 diccionarios (uno por puesto del podio, de 1° a 3°),
        cada uno con el mismo formato que `estadisticas_piloto`.
    """
    top_3 = listar_pilotos(tabla, carreras_sprint).head(3)
    return [
        estadisticas_piloto(tabla, piloto_id, carreras_sprint)
        for piloto_id in top_3["piloto_id"]
    ]


def calendario_temporada(carreras: list) -> pd.DataFrame:
    """Arma el calendario de carreras de la temporada.

    Args:
        carreras: Lista de carreras tal como la devuelve
            `api_f1.obtener_resultados_temporada` (datos crudos).

    Returns:
        DataFrame con columnas: ronda, gran_premio, fecha, circuito, pais,
        ordenado por ronda.
    """
    filas = []
    for carrera in carreras:
        circuito = carrera.get("Circuit", {})
        ubicacion = circuito.get("Location", {})
        filas.append({
            "ronda": int(carrera["round"]),
            "gran_premio": carrera["raceName"],
            "fecha": carrera.get("date", ""),
            "circuito": circuito.get("circuitName", ""),
            "pais": ubicacion.get("country", ""),
        })
    return pd.DataFrame(filas).sort_values("ronda").reset_index(drop=True)


def cambios_de_equipo(tabla: pd.DataFrame) -> pd.DataFrame:
    """Detecta pilotos que cambiaron de equipo durante la temporada.

    Recorre, para cada piloto, el constructor con el que corrió cada ronda
    en orden cronológico; cada vez que cambia de una ronda a la siguiente
    (por ejemplo, un reemplazo a mitad de temporada) se registra como un
    cambio de equipo.

    Args:
        tabla: DataFrame generado por `construir_tabla_resultados`.

    Returns:
        DataFrame con columnas: piloto, ronda, equipo_anterior, equipo_nuevo.
        Vacío si ningún piloto cambió de equipo en la temporada (lo más
        común).
    """
    filas = []
    for piloto_id, grupo in tabla.sort_values("ronda").groupby("piloto_id"):
        grupo_unico = grupo.drop_duplicates(subset="ronda")
        equipos = grupo_unico["constructor"].tolist()
        rondas = grupo_unico["ronda"].tolist()
        nombre = grupo_unico["piloto"].iloc[0]
        for i in range(1, len(equipos)):
            if equipos[i] != equipos[i - 1]:
                filas.append({
                    "piloto": nombre,
                    "ronda": rondas[i],
                    "equipo_anterior": equipos[i - 1],
                    "equipo_nuevo": equipos[i],
                })
    return pd.DataFrame(filas)

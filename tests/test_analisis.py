"""Pruebas simples para el módulo analisis.py.

No usa un framework de testing (pytest, unittest) porque no se vio en la
materia; son funciones de verificación manual con asserts, pensadas para
correrse directamente con: python tests/test_analisis.py
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

import pandas as pd  # noqa: E402 (import después de modificar sys.path a propósito)

import analisis  # noqa: E402

CARRERAS_DE_PRUEBA = [
    {
        "round": "9", "raceName": "Austrian GP", "date": "2021-07-04",
        "Results": [
            {"position": "1", "points": "26", "status": "Finished",
             "Driver": {"driverId": "max_verstappen", "givenName": "Max",
                        "familyName": "Verstappen", "code": "VER"},
             "Constructor": {"name": "Red Bull"}},
            {"position": "R", "points": "0", "status": "Accident",
             "Driver": {"driverId": "hamilton", "givenName": "Lewis",
                        "familyName": "Hamilton", "code": "HAM"},
             "Constructor": {"name": "Mercedes"}},
        ],
    },
]


def test_construir_tabla_resultados():
    """La tabla debe tener una fila por resultado y las columnas esperadas."""
    tabla = analisis.construir_tabla_resultados(CARRERAS_DE_PRUEBA)
    assert len(tabla) == 2
    assert "puntos" in tabla.columns
    assert tabla.iloc[0]["puntos"] == 26.0


def test_posicion_retirado_es_none():
    """Un piloto retirado ('R') no debe romper el cálculo de posición."""
    tabla = analisis.construir_tabla_resultados(CARRERAS_DE_PRUEBA)
    fila_retirado = tabla[tabla["piloto_id"] == "hamilton"].iloc[0]
    # pandas convierte el None en NaN al guardarlo en una columna numérica.
    assert pd.isna(fila_retirado["posicion"])


def test_estadisticas_piloto():
    """Las estadísticas de un ganador deben reflejar la victoria."""
    tabla = analisis.construir_tabla_resultados(CARRERAS_DE_PRUEBA)
    stats = analisis.estadisticas_piloto(tabla, "max_verstappen")
    assert stats["victorias"] == 1
    assert stats["puntos_totales"] == 26.0
    assert stats["porcentaje_terminadas"] == 100.0


if __name__ == "__main__":
    test_construir_tabla_resultados()
    test_posicion_retirado_es_none()
    test_estadisticas_piloto()
    print("✅ Todas las pruebas pasaron correctamente")

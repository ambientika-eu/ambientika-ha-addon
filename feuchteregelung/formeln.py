#!/usr/bin/env python3
"""
formeln.py — die Feuchtephysik hinter dem Home-Assistant-Paket.

Die Formeln stehen im generierten Paket als Jinja-Templates. Hier liegen sie
noch einmal als Python, damit sie gegen Literaturwerte geprüft werden können
(``test_formeln.py``) — ein Vorzeichenfehler in einer Jinja-Zeile fällt sonst
erst auf, wenn die Anlage die Räume befeuchtet statt sie zu trocknen.

Kernaussage für die Regelung: **Lüften trocknet nur dann, wenn die Außenluft
absolut trockener ist als die Innenluft.** Die relative Feuchte taugt dafür
nicht. Draußen 15 °C bei 70 % rF wirkt trockener als drinnen 22 °C bei 60 % rF,
enthält aber 9,0 statt 11,7 g Wasser je m³ — hier trocknet Lüften tatsächlich.
Im Sommer kehrt sich das um: 28 °C bei 60 % rF draußen sind 16,3 g/m³ und damit
deutlich feuchter als dieselben 22 °C bei 60 % drinnen. Wer auf relative Feuchte
regelt, lüftet in diesem Fall Feuchtigkeit ins Haus.
"""

from __future__ import annotations

import math

#: Magnus-Koeffizienten nach Sonntag, gültig über Wasser für -45..60 °C.
MAGNUS_A = 17.62
MAGNUS_B = 243.12
#: Sättigungsdampfdruck bei 0 °C in hPa.
E0 = 6.112
#: Gaskonstante-Term für die Umrechnung Dampfdruck -> absolute Feuchte in g/m³.
AH_CONST = 216.679


def saettigungsdampfdruck(temp_c: float) -> float:
    """Sättigungsdampfdruck in hPa bei gegebener Temperatur."""
    return E0 * math.exp((MAGNUS_A * temp_c) / (MAGNUS_B + temp_c))


def dampfdruck(temp_c: float, rh_pct: float) -> float:
    """Tatsächlicher Wasserdampfdruck in hPa."""
    return (rh_pct / 100.0) * saettigungsdampfdruck(temp_c)


def taupunkt(temp_c: float, rh_pct: float) -> float:
    """Taupunkt in °C.

    Unterhalb dieser Temperatur schlägt sich Feuchtigkeit nieder — der Wert,
    an dem sich Schimmelgefahr an kalten Bauteilen entscheidet.
    """
    if rh_pct <= 0:
        raise ValueError("relative Feuchte muss größer als 0 sein")
    gamma = (math.log(rh_pct / 100.0)
             + (MAGNUS_A * temp_c) / (MAGNUS_B + temp_c))
    return (MAGNUS_B * gamma) / (MAGNUS_A - gamma)


def absolute_feuchte(temp_c: float, rh_pct: float) -> float:
    """Absolute Feuchte in g/m³ — die Größe, auf die geregelt werden muss."""
    return AH_CONST * dampfdruck(temp_c, rh_pct) / (temp_c + 273.15)


def trocknung_moeglich(innen_t: float, innen_rh: float,
                       aussen_t: float, aussen_rh: float,
                       marge: float = 0.8) -> bool:
    """True, wenn Lüften die Raumluft tatsächlich trockener macht.

    ``marge`` in g/m³ ist die Hysterese. Ohne sie schaltet die Regelung am
    Umschaltpunkt hin und her, was bei einer Lüftung hörbar ist und jedes Mal
    einen Bestätigungston auslöst.
    """
    return (absolute_feuchte(aussen_t, aussen_rh)
            < absolute_feuchte(innen_t, innen_rh) - marge)


if __name__ == "__main__":
    beispiele = [
        ("Herbst, kühl und feucht draußen", 22, 60, 15, 70),
        ("Sommer, schwül draußen",          22, 60, 28, 60),
        ("Winter, kalt und trocken",        21, 55, 2, 85),
        ("Regentag, gleiche Temperatur",    21, 55, 21, 80),
    ]
    print(f"{'Situation':<34} {'innen':>10} {'außen':>10}  Lüften trocknet?")
    for name, it, irh, at, arh in beispiele:
        ai, aa = absolute_feuchte(it, irh), absolute_feuchte(at, arh)
        ok = "ja" if trocknung_moeglich(it, irh, at, arh) else "nein"
        print(f"{name:<34} {ai:>7.1f} g/m³ {aa:>7.1f} g/m³  {ok}")

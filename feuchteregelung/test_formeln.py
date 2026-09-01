#!/usr/bin/env python3
"""
Prüfung der Feuchtephysik gegen Literaturwerte.

Diese Formeln steuern am Ende eine Lüftungsanlage. Ein Vorzeichen- oder
Koeffizientenfehler führt nicht zu einem Absturz, sondern dazu, dass die Anlage
bei schwüler Außenluft lüftet und die Räume befeuchtet. Deshalb werden hier
Stützstellen geprüft, die in jeder Mollier-Tabelle nachschlagbar sind.

Ausführen mit:  python3 -m unittest test_formeln -v
"""

from __future__ import annotations

import unittest

from formeln import (
    absolute_feuchte, dampfdruck, saettigungsdampfdruck, taupunkt,
    trocknung_moeglich,
)


class TestSaettigungsdampfdruck(unittest.TestCase):
    """Tabellenwerte in hPa, Toleranz 1 %."""

    def test_stuetzstellen(self):
        for temp, erwartet in [(0, 6.11), (10, 12.28), (20, 23.39),
                               (25, 31.69), (30, 42.46)]:
            with self.subTest(temp=temp):
                self.assertAlmostEqual(saettigungsdampfdruck(temp), erwartet,
                                       delta=erwartet * 0.01)

    def test_steigt_monoton(self):
        werte = [saettigungsdampfdruck(t) for t in range(-20, 51, 5)]
        self.assertEqual(werte, sorted(werte))


class TestTaupunkt(unittest.TestCase):
    def test_bei_hundert_prozent_gleich_lufttemperatur(self):
        for temp in (-5, 0, 10, 21, 30):
            with self.subTest(temp=temp):
                self.assertAlmostEqual(taupunkt(temp, 100), temp, places=6)

    def test_stuetzstellen(self):
        # Nachschlagbare Werte, Toleranz 0,3 K
        for temp, rh, erwartet in [(20, 50, 9.3), (25, 60, 16.7),
                                   (21, 55, 11.6), (30, 80, 26.2)]:
            with self.subTest(temp=temp, rh=rh):
                self.assertAlmostEqual(taupunkt(temp, rh), erwartet, delta=0.3)

    def test_liegt_immer_unter_der_lufttemperatur(self):
        for temp in range(0, 35, 5):
            for rh in (20, 40, 60, 80, 99):
                self.assertLess(taupunkt(temp, rh), temp + 0.001)

    def test_negative_temperatur(self):
        self.assertAlmostEqual(taupunkt(-5, 80), -7.8, delta=0.3)

    def test_null_feuchte_wird_abgewiesen(self):
        with self.assertRaises(ValueError):
            taupunkt(20, 0)


class TestAbsoluteFeuchte(unittest.TestCase):
    def test_stuetzstellen(self):
        # g/m³, Toleranz 2 %
        for temp, rh, erwartet in [(20, 50, 8.65), (20, 100, 17.3),
                                   (25, 60, 13.8), (0, 100, 4.85),
                                   (30, 70, 21.3)]:
            with self.subTest(temp=temp, rh=rh):
                self.assertAlmostEqual(absolute_feuchte(temp, rh), erwartet,
                                       delta=erwartet * 0.02)

    def test_proportional_zur_relativen_feuchte(self):
        self.assertAlmostEqual(absolute_feuchte(20, 100),
                               2 * absolute_feuchte(20, 50), places=6)

    def test_dampfdruck_konsistent(self):
        self.assertAlmostEqual(dampfdruck(20, 50),
                               0.5 * saettigungsdampfdruck(20), places=9)


class TestTrocknungsentscheidung(unittest.TestCase):
    """Die Entscheidung, an der die ganze Regelung hängt."""

    def test_kuehle_feuchte_aussenluft_trocknet_trotzdem(self):
        # 15 °C / 70 % sieht relativ feuchter aus als 22 °C / 60 %,
        # enthält aber weniger Wasser. Lüften hilft.
        self.assertLess(absolute_feuchte(15, 70), absolute_feuchte(22, 60))
        self.assertTrue(trocknung_moeglich(22, 60, 15, 70))

    def test_schwuele_sommerluft_befeuchtet(self):
        # Gleiche relative Feuchte, aber wärmer draußen — der Fall, in dem
        # eine Regelung auf relative Feuchte genau das Falsche tut.
        self.assertGreater(absolute_feuchte(28, 60), absolute_feuchte(22, 60))
        self.assertFalse(trocknung_moeglich(22, 60, 28, 60))

    def test_kalte_winterluft_trocknet_immer(self):
        self.assertTrue(trocknung_moeglich(21, 55, 2, 85))

    def test_regentag_bei_gleicher_temperatur_befeuchtet(self):
        self.assertFalse(trocknung_moeglich(21, 55, 21, 80))

    def test_marge_verhindert_flattern(self):
        # Knapp trockener draußen: ohne Marge würde geschaltet, mit Marge nicht.
        innen = (22.0, 60.0)
        aussen = (21.5, 59.0)
        self.assertTrue(trocknung_moeglich(*innen, *aussen, marge=0.0))
        self.assertFalse(trocknung_moeglich(*innen, *aussen, marge=0.8))

    def test_marge_wirkt_nur_in_eine_richtung(self):
        # Deutlich trockener draußen: die Marge darf das nicht blockieren.
        self.assertTrue(trocknung_moeglich(22, 65, 8, 60, marge=0.8))


class TestFeldmesswerte(unittest.TestCase):
    """Mit einer echten Vergleichsmessung aus einer Anlage nachgerechnet.

    Ein Gerät im Büro meldet 26,0 °C / 46 %. Zwei unabhängige Referenzgeräte
    im selben Raum zeigen 22,9 / 60 und 23,0 / 57, im Mittel 22,95 / 58,5.

    Das Ergebnis war nicht das erwartete: Der Versatz in Temperatur und
    Feuchte hebt sich beim Taupunkt weitgehend auf — nur 0,9 K Unterschied,
    obwohl die Einzelwerte um 3 K und 12,5 Prozentpunkte danebenliegen. Die
    Richtung ist aber eindeutig, und sie ist die ungünstige: Das Gerät meldet
    die Raumluft **trockener**, als sie ist.
    """

    GERAET = (26.0, 46.0)
    REFERENZ = (22.95, 58.5)

    def test_der_taupunktfehler_ist_kleiner_als_die_einzelfehler(self):
        abweichung = taupunkt(*self.GERAET) - taupunkt(*self.REFERENZ)
        self.assertAlmostEqual(abweichung, -0.89, delta=0.05)

    def test_das_geraet_meldet_die_luft_zu_trocken(self):
        # 0,8 g/m³ zu wenig — in derselben Größenordnung wie die Schaltmarge,
        # und deshalb regelungsrelevant.
        fehler = absolute_feuchte(*self.GERAET) - absolute_feuchte(*self.REFERENZ)
        self.assertLess(fehler, 0)
        self.assertAlmostEqual(fehler, -0.79, delta=0.05)

    def test_korrektur_bringt_den_taupunkt_exakt_in_deckung(self):
        offset_t = self.REFERENZ[0] - self.GERAET[0]      # -3,05 K
        offset_rh = self.REFERENZ[1] - self.GERAET[1]     # +12,5 %
        korrigiert = taupunkt(self.GERAET[0] + offset_t,
                              self.GERAET[1] + offset_rh)
        self.assertAlmostEqual(korrigiert, taupunkt(*self.REFERENZ), places=6)

    def test_unkorrigiert_wird_trocknung_verpasst_nicht_erzwungen(self):
        # Der Fehler geht konsequent in eine Richtung: Es wird nicht gelüftet,
        # obwohl es helfen würde. Wer den Eindruck hat, die Anlage entfeuchte
        # zu wenig, findet hier einen Teil der Erklärung.
        for aussen in [(16.0, 80.0), (18.0, 70.0), (22.0, 55.0)]:
            with self.subTest(aussen=aussen):
                self.assertFalse(trocknung_moeglich(*self.GERAET, *aussen),
                                 "Rohwert würde nicht lüften")
                self.assertTrue(trocknung_moeglich(*self.REFERENZ, *aussen),
                                "die echte Raumluft würde vom Lüften profitieren")


if __name__ == "__main__":
    unittest.main(verbosity=2)

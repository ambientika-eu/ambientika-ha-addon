#!/usr/bin/env python3
"""
Prüft das erzeugte Home-Assistant-Paket, indem die Jinja-Templates tatsächlich
gerendert und gegen die getestete Physik aus ``formeln.py`` verglichen werden.

Der Grund: ``test_formeln.py`` prüft die Python-Fassung der Formeln. Im Paket
stehen sie aber ein zweites Mal, als Jinja. Eine vertauschte Klammer dort fällt
sonst niemandem auf — Home Assistant meldet keinen Fehler, es rechnet nur falsch,
und die Lüftung schaltet zum falschen Zeitpunkt.

Hier wird eine kleine Home-Assistant-Umgebung nachgebaut (``states``,
``has_value``, der ``log``-Filter) und jeder generierte Sensor über einen Bereich
realistischer Wetterlagen gerechnet.

Ausführen mit:  python3 -m unittest test_paket -v
"""

from __future__ import annotations

import math
import re
import subprocess
import sys
import unittest
from pathlib import Path

try:
    import yaml
    from jinja2 import Environment
except ImportError:                                    # pragma: no cover
    sys.exit("Für diese Tests werden pyyaml und jinja2 benötigt.")

from formeln import absolute_feuchte, taupunkt, trocknung_moeglich
from generate_package import ha_slug

HIER = Path(__file__).parent
# Die Tests prüfen die Ausgabe aus der Beispielkonfiguration.
PAKET = HIER / "ambientika.beispiel.yaml"


#: Schlüssel, deren Werte wie Entitäten aussehen, aber keine sind.
#: "service: select.select_option" ist ein Dienstaufruf, kein Sensor.
KEINE_ENTITAETEN = ("service", "action")


def alle_strings(knoten, schluessel_ueberspringen=()) -> list:
    """Sammelt rekursiv jeden String aus der Paketstruktur ein.

    Werte unter den in ``schluessel_ueberspringen`` genannten Schlüsseln
    bleiben außen vor.
    """
    if isinstance(knoten, str):
        return [knoten]
    if isinstance(knoten, dict):
        out = []
        for k, v in knoten.items():
            out.extend(alle_strings(k, schluessel_ueberspringen))
            if k in schluessel_ueberspringen:
                continue
            out.extend(alle_strings(v, schluessel_ueberspringen))
        return out
    if isinstance(knoten, (list, tuple)):
        out = []
        for v in knoten:
            out.extend(alle_strings(v, schluessel_ueberspringen))
        return out
    return []


def ha_env(zustaende: dict) -> Environment:
    """Jinja-Umgebung mit den Home-Assistant-Erweiterungen, die das Paket nutzt."""
    env = Environment()
    env.filters["log"] = lambda v, base=math.e: math.log(v, base)
    env.filters["round"] = lambda v, p=0, *a, **k: round(float(v), p)
    env.globals["states"] = lambda e: str(zustaende.get(e, "unknown"))
    env.globals["has_value"] = lambda e: (
        e in zustaende and str(zustaende[e]) not in ("unknown", "unavailable", ""))
    return env


def render(tpl: str, zustaende: dict) -> str:
    return ha_env(zustaende).from_string(tpl).render().strip()


def lade_paket() -> dict:
    if not PAKET.exists():
        subprocess.run([sys.executable, "generate_package.py"],
                       cwd=str(HIER), check=True, capture_output=True)
    return yaml.safe_load(PAKET.read_text(encoding="utf-8"))


class PaketBasis(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.paket = lade_paket()
        cls.sensoren = {s["name"]: s for s in cls.paket["template"][0]["sensor"]}
        cls.binaer = {s["name"]: s
                      for s in cls.paket["template"][1]["binary_sensor"]}
        cls.automationen = {a["id"]: a for a in cls.paket["automation"]}


class TestEntityIds(PaketBasis):
    """Der wichtigste Test der Suite.

    Home Assistant bildet die entity_id aus dem Anzeigenamen. Wer die IDs
    selbst erfindet, bekommt ein Paket, das sich fehlerfrei lädt, in dem aber
    jeder abgeleitete Sensor 'unknown' bleibt und keine Automation je auslöst —
    ohne eine einzige Fehlermeldung im Log. Genau dieser Fehler steckte in der
    ersten Fassung: 13 von 21 Referenzen zeigten ins Leere.
    """

    ENTITY_MUSTER = re.compile(
        r"\b(?:sensor|binary_sensor|select|number|switch|input_boolean)"
        r"\.[a-z0-9_]+")

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cfg = yaml.safe_load(
            (HIER / "geraete.beispiel.yaml").read_text(encoding="utf-8"))

    def erzeugte_ids(self) -> set:
        ids = set()
        for s in self.paket["template"][0]["sensor"]:
            ids.add("sensor." + ha_slug(s["name"]))
        for s in self.paket["template"][1]["binary_sensor"]:
            ids.add("binary_sensor." + ha_slug(s["name"]))
        # Bei input_boolean leitet HA die ID aus dem Schlüssel ab, nicht aus
        # dem Anzeigenamen — deshalb hier der Schlüssel.
        for key in self.paket.get("input_boolean", {}):
            ids.add("input_boolean." + key)
        return ids

    def externe_ids(self) -> set:
        """Entitäten, die von außen kommen und nicht hier erzeugt werden."""
        extern = {self.cfg["aussen"]["temperatur"], self.cfg["aussen"]["feuchte"]}
        for g in self.cfg["geraete"]:
            extern.add(g["temperatur"])
            extern.add(g["feuchte"])
            # Modus- und Stufenentitäten stammen aus der MQTT-Bridge und
            # müssen in der Konfiguration deklariert sein — eine Automation,
            # die auf eine nicht deklarierte Entität schaltet, wäre ein Tippfehler.
            extern.add(g["modus"])
            extern.add(g["stufe"])
        return extern

    def referenzierte_ids(self) -> set:
        gefunden = set()
        for text in alle_strings(self.paket, KEINE_ENTITAETEN):
            gefunden.update(self.ENTITY_MUSTER.findall(text))
        return gefunden

    def test_jede_referenz_zeigt_auf_eine_existierende_entitaet(self):
        bekannt = self.erzeugte_ids() | self.externe_ids()
        fehlend = sorted(self.referenzierte_ids() - bekannt)
        self.assertEqual(
            fehlend, [],
            "Diese Referenzen zeigen ins Leere — Home Assistant meldet dazu "
            "nichts, die Sensoren bleiben einfach 'unknown':\n  "
            + "\n  ".join(fehlend))

    def test_jede_erzeugte_entitaet_wird_auch_benutzt(self):
        # Umgekehrte Richtung: ein Sensor, den niemand referenziert, ist
        # entweder überflüssig oder es fehlt eine Verdrahtung.
        unbenutzt = self.erzeugte_ids() - self.referenzierte_ids()
        # Taupunkt-Sensoren sind zur Anzeige gedacht und dürfen unbenutzt sein.
        unbenutzt = {e for e in unbenutzt if not e.endswith("_taupunkt")}
        self.assertEqual(sorted(unbenutzt), [])

    def test_slugify_stimmt_mit_home_assistant_ueberein(self):
        # Gegenprobe gegen die Bibliothek, die Home Assistant selbst nutzt.
        # Fehlt sie, wird der Test übersprungen statt falsch bestanden.
        try:
            from slugify import slugify
        except ImportError:
            self.skipTest("python-slugify nicht installiert")
        for name in ["Außenluft absolute Feuchte", "Ambientika Büro Taupunkt",
                     "Ambientika Bad OG Trocknung möglich",
                     "Ambientika Küche/Süd Feuchte korrigiert",
                     "Ambientika Gäste-WC Temperatur korrigiert"]:
            with self.subTest(name=name):
                self.assertEqual(ha_slug(name), slugify(name, separator="_"))

    def test_alle_erzeugten_namen_tragen_das_praefix(self):
        for s in self.paket["template"][0]["sensor"]:
            self.assertTrue(s["name"].startswith("Ambientika "), s["name"])
        for s in self.paket["template"][1]["binary_sensor"]:
            self.assertTrue(s["name"].startswith("Ambientika "), s["name"])

    def test_keine_zwei_namen_ergeben_dieselbe_id(self):
        namen = ([s["name"] for s in self.paket["template"][0]["sensor"]]
                 + [s["name"] for s in self.paket["template"][1]["binary_sensor"]])
        ids = [ha_slug(n) for n in namen]
        self.assertEqual(len(ids), len(set(ids)),
                         "zwei Namen slugifizieren gleich — HA hängt _2 an "
                         "und die Referenz greift dann daneben")


class TestStruktur(PaketBasis):
    def test_paket_hat_die_erwarteten_abschnitte(self):
        self.assertIn("template", self.paket)
        self.assertIn("automation", self.paket)

    def test_jede_unique_id_ist_eindeutig(self):
        ids = ([s["unique_id"] for s in self.paket["template"][0]["sensor"]]
               + [s["unique_id"] for s in self.paket["template"][1]["binary_sensor"]])
        self.assertEqual(len(ids), len(set(ids)),
                         "doppelte unique_id — Home Assistant verwirft Entitäten")

    def test_jede_automation_hat_eine_eindeutige_id(self):
        ids = [a["id"] for a in self.paket["automation"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_jeder_sensor_hat_ein_availability_template(self):
        for name, s in self.sensoren.items():
            with self.subTest(sensor=name):
                self.assertIn("availability", s,
                              "ohne availability rechnet HA beim Start mit 'unknown'")


class TestAussenluftBerechnung(PaketBasis):
    """Die Jinja-Formeln müssen exakt das liefern, was formeln.py liefert."""

    WETTERLAGEN = [
        (-8.0, 90.0), (0.0, 85.0), (5.0, 70.0), (12.0, 100.0),
        (15.0, 70.0), (18.0, 65.0), (22.0, 55.0), (28.0, 60.0), (33.0, 40.0),
    ]

    def test_taupunkt_stimmt_mit_der_physik_ueberein(self):
        s = self.sensoren["Ambientika Außenluft Taupunkt"]
        for t, rh in self.WETTERLAGEN:
            with self.subTest(t=t, rh=rh):
                z = {"sensor.aussen_temperatur": t,
                     "sensor.aussen_luftfeuchtigkeit": rh}
                self.assertAlmostEqual(float(render(s["state"], z)),
                                       taupunkt(t, rh), places=1)

    def test_absolute_feuchte_stimmt_mit_der_physik_ueberein(self):
        s = self.sensoren["Ambientika Außenluft absolute Feuchte"]
        for t, rh in self.WETTERLAGEN:
            with self.subTest(t=t, rh=rh):
                z = {"sensor.aussen_temperatur": t,
                     "sensor.aussen_luftfeuchtigkeit": rh}
                self.assertAlmostEqual(float(render(s["state"], z)),
                                       absolute_feuchte(t, rh), places=1)

    def test_availability_meldet_fehlende_quellen(self):
        s = self.sensoren["Ambientika Außenluft Taupunkt"]
        self.assertEqual(render(s["availability"], {}), "False")
        self.assertEqual(
            render(s["availability"],
                   {"sensor.aussen_temperatur": 10,
                    "sensor.aussen_luftfeuchtigkeit": "unknown"}), "False")
        self.assertEqual(
            render(s["availability"],
                   {"sensor.aussen_temperatur": 10,
                    "sensor.aussen_luftfeuchtigkeit": 80}), "True")


class TestKalibrierung(PaketBasis):
    """Die Offsets aus der Konfiguration müssen ankommen."""

    def test_temperaturoffset_wird_angewendet(self):
        # Der Sensor rundet auf eine Nachkommastelle — 22,95 wird zu 22,9.
        # Für die Anzeige richtig, für den Taupunkt ohne Belang.
        s = self.sensoren["Ambientika Büro Temperatur korrigiert"]
        z = {"sensor.ambientika_buero_temperature": 26.0}
        self.assertAlmostEqual(float(render(s["state"], z)), 22.95, delta=0.06)

    def test_feuchteoffset_wird_angewendet(self):
        s = self.sensoren["Ambientika Büro Feuchte korrigiert"]
        z = {"sensor.ambientika_buero_humidity": 46.0}
        self.assertAlmostEqual(float(render(s["state"], z)), 58.5, places=2)

    def test_feuchte_wird_auf_hundert_begrenzt(self):
        # Ein großzügiger Offset darf keine unmögliche Feuchte erzeugen.
        s = self.sensoren["Ambientika Büro Feuchte korrigiert"]
        z = {"sensor.ambientika_buero_humidity": 95.0}
        self.assertLessEqual(float(render(s["state"], z)), 100.0)

    def test_geraet_ohne_offset_bleibt_unveraendert(self):
        s = self.sensoren["Ambientika Schlafzimmer Temperatur korrigiert"]
        z = {"sensor.ambientika_schlafzimmer_temperature": 19.4}
        self.assertAlmostEqual(float(render(s["state"], z)), 19.4, places=2)


class TestTrocknungsentscheidung(PaketBasis):
    """Der Binärsensor, an dem die ganze Regelung hängt."""

    def _rendern(self, innen_af: float, aussen_af: float) -> str:
        s = self.binaer["Ambientika Büro Trocknung möglich"]
        return render(s["state"], {
            "sensor.ambientika_buro_absolute_feuchte": innen_af,
            "sensor.ambientika_aussenluft_absolute_feuchte": aussen_af,
        })

    def test_trockenere_aussenluft_gibt_frei(self):
        self.assertEqual(self._rendern(11.9, 9.0), "True")

    def test_feuchtere_aussenluft_sperrt(self):
        self.assertEqual(self._rendern(11.6, 16.3), "False")

    def test_die_marge_verhindert_flattern(self):
        # 0,5 g/m³ Unterschied liegt innerhalb der Marge von 0,8.
        self.assertEqual(self._rendern(11.5, 11.0), "False")
        self.assertEqual(self._rendern(11.5, 10.0), "True")

    def test_deckt_sich_mit_der_python_entscheidung(self):
        faelle = [
            ((22.0, 60.0), (15.0, 70.0)),
            ((22.0, 60.0), (28.0, 60.0)),
            ((21.0, 55.0), (2.0, 85.0)),
            ((21.0, 55.0), (21.0, 80.0)),
            ((23.0, 62.0), (18.0, 70.0)),
        ]
        for (it, irh), (at, arh) in faelle:
            with self.subTest(innen=(it, irh), aussen=(at, arh)):
                erwartet = trocknung_moeglich(it, irh, at, arh, marge=0.8)
                gerendert = self._rendern(absolute_feuchte(it, irh),
                                          absolute_feuchte(at, arh))
                self.assertEqual(gerendert, str(erwartet))


class TestBestaetigungston(PaketBasis):
    """Jeder angenommene Befehl piept — also darf keiner überflüssig sein."""

    def test_start_schaltet_nicht_wenn_der_modus_schon_stimmt(self):
        a = self.automationen["ambientika_buero_entfeuchten_start"]
        tpl = [c for c in a["condition"] if c["condition"] == "template"]
        self.assertTrue(tpl, "Zustandsprüfung fehlt — jeder Lauf würde senden")
        z = {"select.ambientika_buero_mode": "HRV"}
        self.assertEqual(render(tpl[0]["value_template"], z), "False")
        z = {"select.ambientika_buero_mode": "ECO"}
        self.assertEqual(render(tpl[0]["value_template"], z), "True")

    def test_ende_schaltet_nur_aus_dem_entfeuchtungsmodus(self):
        a = self.automationen["ambientika_buero_entfeuchten_ende"]
        tpl = [c for c in a["condition"] if c["condition"] == "template"][0]
        self.assertEqual(
            render(tpl["value_template"],
                   {"select.ambientika_buero_mode": "ECO"}), "False")
        self.assertEqual(
            render(tpl["value_template"],
                   {"select.ambientika_buero_mode": "HRV"}), "True")

    def test_schlafzimmer_schaltet_nachts_nicht(self):
        for kennung in ("ambientika_schlafzimmer_entfeuchten_start",
                        "ambientika_schlafzimmer_entfeuchten_ende"):
            with self.subTest(automation=kennung):
                a = self.automationen[kennung]
                zeit = [c for c in a["condition"] if c["condition"] == "not"]
                self.assertTrue(zeit, "Nachtruhe fehlt trotz nachtruhe: true")
                inner = zeit[0]["conditions"][0]
                self.assertEqual(inner["after"], "22:00:00")
                self.assertEqual(inner["before"], "06:30:00")

    def test_raeume_ohne_nachtruhe_haben_keine_zeitsperre(self):
        a = self.automationen["ambientika_buero_entfeuchten_start"]
        self.assertFalse([c for c in a["condition"] if c["condition"] == "not"])


class TestUebernahmeUndAbgabe(PaketBasis):
    """Die Regelung darf keinen Eingriff von Hand rückgängig machen.

    Wer abends selbst auf Abluft schaltet, soll das Gerät nicht später im
    Automatikbetrieb wiederfinden. Ein Merker je Gerät hält fest, ob die
    Entfeuchtung von der Automation stammt; nur dann wird zurückgestellt.
    """

    FLAG = "input_boolean.ambientika_buero_entfeuchtung"

    def test_es_gibt_je_geraet_einen_merker(self):
        merker = self.paket.get("input_boolean", {})
        self.assertEqual(len(merker), 3)
        self.assertIn("ambientika_buero_entfeuchtung", merker)

    def test_start_setzt_den_merker_vor_dem_moduswechsel(self):
        a = self.automationen["ambientika_buero_entfeuchten_start"]
        dienste = [s.get("service") for s in a["action"]]
        self.assertIn("input_boolean.turn_on", dienste)
        self.assertLess(dienste.index("input_boolean.turn_on"),
                        dienste.index("select.select_option"),
                        "der Merker muss vor dem Schalten stehen, sonst hält "
                        "die Eingriffserkennung den eigenen Wechsel für einen "
                        "von Hand")

    def test_ende_loescht_den_merker_vor_dem_moduswechsel(self):
        a = self.automationen["ambientika_buero_entfeuchten_ende"]
        dienste = [s.get("service") for s in a["action"]]
        self.assertLess(dienste.index("input_boolean.turn_off"),
                        dienste.index("select.select_option"))

    def test_ende_stellt_nur_zurueck_was_die_automation_setzte(self):
        a = self.automationen["ambientika_buero_entfeuchten_ende"]
        flag_bedingung = [c for c in a["condition"]
                          if c.get("entity_id") == self.FLAG]
        self.assertTrue(flag_bedingung, "ohne diese Bedingung würde die "
                                        "Automation einen Eingriff von Hand "
                                        "zurückstellen")
        self.assertEqual(flag_bedingung[0]["state"], "on")

    def test_eingriff_von_hand_gibt_die_kontrolle_ab(self):
        a = self.automationen["ambientika_buero_eingriff_erkannt"]
        self.assertEqual(a["trigger"][0]["from"], "HRV")
        self.assertEqual(a["condition"][0]["entity_id"], self.FLAG)
        self.assertEqual(a["action"][0]["service"], "input_boolean.turn_off")

    def test_jedes_geraet_hat_alle_drei_automationen(self):
        for slug in ("buero", "schlafzimmer", "bad_og"):
            for zweck in ("entfeuchten_start", "entfeuchten_ende",
                          "eingriff_erkannt"):
                with self.subTest(slug=slug, zweck=zweck):
                    self.assertIn(f"ambientika_{slug}_{zweck}",
                                  self.automationen)


class TestModusnamenAusDerKonfiguration(PaketBasis):
    """Ein Modusname, den die select-Entität nicht kennt, bricht die
    Automation bei jedem Lauf ab — ohne dass am Gerät etwas passiert."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cfg = yaml.safe_load(
            (HIER / "geraete.beispiel.yaml").read_text(encoding="utf-8"))

    def test_die_namen_stammen_aus_der_konfiguration(self):
        e = self.cfg["einstellungen"]
        self.assertIn("modus_entfeuchten", e)
        self.assertIn("modus_normal", e)
        a = self.automationen["ambientika_buero_entfeuchten_start"]
        schalten = [s for s in a["action"]
                    if s.get("service") == "select.select_option"][0]
        self.assertEqual(schalten["data"]["option"], e["modus_entfeuchten"])

    def test_ein_geaenderter_name_schlaegt_bis_in_die_automation_durch(self):
        # Gegenprobe: mit einer anderen Konfiguration muss ein anderer Wert
        # herauskommen. Sonst wäre der Name doch fest verdrahtet.
        import copy
        from generate_package import baue_automationen, ids_fuer
        cfg = copy.deepcopy(self.cfg)
        cfg["einstellungen"]["modus_entfeuchten"] = "EXPULSION"
        autos = {a["id"]: a for a in baue_automationen(cfg, ids_fuer(cfg))}
        a = autos["ambientika_buero_entfeuchten_start"]
        schalten = [s for s in a["action"]
                    if s.get("service") == "select.select_option"][0]
        self.assertEqual(schalten["data"]["option"], "EXPULSION")
        self.assertEqual(
            autos["ambientika_buero_eingriff_erkannt"]["trigger"][0]["from"],
            "EXPULSION")


class TestKeineFloatOhneDefault(PaketBasis):
    """`| float` ohne Default ist in Home Assistant verwarnt und rendert bei
    'unknown' gar nicht — das füllt das Log und lässt Sensoren ausfallen."""

    def test_alle_float_filter_haben_einen_default(self):
        treffer = []
        for text in alle_strings(self.paket):
            for stelle in re.finditer(r"\|\s*float(?!\s*\()", text):
                treffer.append(text[max(0, stelle.start() - 40):stelle.end()])
        self.assertEqual(treffer, [], "float ohne Default gefunden")


class TestAutomationsLogik(PaketBasis):
    def test_start_verlangt_beide_bedingungen(self):
        a = self.automationen["ambientika_buero_entfeuchten_start"]
        arten = [c["condition"] for c in a["condition"]]
        self.assertIn("numeric_state", arten, "Feuchteschwelle fehlt")
        self.assertIn("state", arten, "Trocknungsfreigabe fehlt")

    def test_es_gibt_keine_bedingungslose_lueftungsabschaltung(self):
        # Die Anlage darf nicht komplett ausgeschaltet werden: Feuchteschutz
        # ist wichtig, Luftwechsel aber auch.
        for kennung, a in self.automationen.items():
            for schritt in a["action"]:
                if schritt.get("service") == "select.select_option":
                    with self.subTest(automation=kennung):
                        self.assertNotEqual(schritt["data"]["option"], "OFF")

    def test_hysterese_zwischen_ein_und_ausschalten(self):
        start = self.automationen["ambientika_buero_entfeuchten_start"]
        ende = self.automationen["ambientika_buero_entfeuchten_ende"]
        ein = [t for t in start["trigger"] if "above" in t][0]["above"]
        aus = [t for t in ende["trigger"] if "below" in t][0]["below"]
        self.assertLess(aus, ein, "ohne Hysterese pendelt die Regelung")


if __name__ == "__main__":
    unittest.main(verbosity=2)

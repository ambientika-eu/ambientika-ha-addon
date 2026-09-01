#!/usr/bin/env python3
"""
generate_package.py — erzeugt das Home-Assistant-Paket für eine Ambientika-Anlage.

Warum ein Generator und nicht eine Beispieldatei zum Abtippen: Bei zehn Geräten
entstehen rund fünfzig Template-Sensoren und Automationen. Von Hand gepflegt
schleicht sich beim vierten Gerät ein kopierter Entity-Name ein, und dann regelt
das Bad nach der Feuchte des Schlafzimmers — ein Fehler, der monatelang
unbemerkt bleiben kann.

    cp geraete.beispiel.yaml geraete.yaml
    # geraete.yaml anpassen
    python3 generate_package.py
    # ambientika.yaml nach config/packages/ kopieren, Home Assistant neu laden

Erzeugt je Gerät:
  * korrigierte Temperatur und Feuchte (Offset aus der eigenen Messreihe)
  * Taupunkt und absolute Feuchte aus den korrigierten Werten
sowie anlagenweit:
  * Taupunkt und absolute Feuchte der Außenluft
  * einen Binärsensor "Trocknung möglich"
  * Automationen zum Entfeuchten, die nur schalten, wenn sich etwas ändert
"""

from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML fehlt:  pip install pyyaml")

HIER = Path(__file__).parent
KONFIG = HIER / "geraete.yaml"
BEISPIEL = HIER / "geraete.beispiel.yaml"

# Zwei Ausgabenamen mit Absicht: Nur eine echte geraete.yaml erzeugt die Datei,
# die nach config/packages/ gehört. Aus der Beispielkonfiguration entsteht
# ambientika.beispiel.yaml — die enthält erfundene Entity-IDs und wäre, direkt
# kopiert, ein Paket, das sich lädt und nichts tut.
AUSGABE_ECHT = HIER / "ambientika.yaml"
AUSGABE_BEISPIEL = HIER / "ambientika.beispiel.yaml"

# --------------------------------------------------------------------------
# Entity-IDs
# --------------------------------------------------------------------------
# Home Assistant bildet die entity_id aus dem ANZEIGENAMEN, nicht aus der
# unique_id. Aus "Büro Taupunkt" wird sensor.buro_taupunkt — mit u, nicht ue.
# Wer die IDs selbst erfindet, erzeugt ein Paket, das sich anstandslos laden
# lässt, in dem aber jeder abgeleitete Sensor 'unknown' bleibt und keine
# Automation je auslöst. Ohne Fehlermeldung.
#
# Deshalb werden alle IDs hier aus demselben Namen berechnet, der auch im
# Paket steht. test_paket.py vergleicht das Ergebnis gegen die Bibliothek
# python-slugify, die Home Assistant selbst verwendet.

#: Transliteration wie unidecode sie vornimmt, für die hier vorkommenden Zeichen.
UMLAUTE = {
    "ä": "a", "ö": "o", "ü": "u", "ß": "ss",
    "Ä": "A", "Ö": "O", "Ü": "U",
    "à": "a", "á": "a", "â": "a", "è": "e", "é": "e", "ê": "e",
    "ì": "i", "í": "i", "ò": "o", "ó": "o", "ù": "u", "ú": "u",
}


def ha_slug(text: str) -> str:
    """Bildet einen Namen so ab, wie Home Assistant die entity_id erzeugt."""
    for zeichen, ersatz in UMLAUTE.items():
        text = text.replace(zeichen, ersatz)
    # Verbliebene Akzente entfernen (é -> e), falls oben nicht erfasst.
    text = "".join(c for c in unicodedata.normalize("NFKD", text)
                   if not unicodedata.combining(c))
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    return re.sub(r"_+", "_", text)


#: Präfix für alle erzeugten Entitäten, damit sie sich nicht mit anderen
#: Integrationen ins Gehege kommen und in der Oberfläche zusammen stehen.
PRAEFIX = "Ambientika"


def entity(domain: str, *teile: str) -> tuple:
    """Liefert (Anzeigename, entity_id) für eine erzeugte Entität."""
    name = " ".join([PRAEFIX, *teile])
    return name, f"{domain}.{ha_slug(name)}"

# Magnus-Formel als Jinja, identisch zu formeln.py. Als Makro definiert, damit
# die Koeffizienten genau einmal im Paket stehen und nicht fünfzigmal.
MAKROS = """
{%- macro saettigung(t) -%}
{{ 6.112 * (2.718281828459045 ** ((17.62 * t) / (243.12 + t))) }}
{%- endmacro -%}
{%- macro taupunkt(t, rh) -%}
{%- set g = (rh / 100) | log + (17.62 * t) / (243.12 + t) -%}
{{ ((243.12 * g) / (17.62 - g)) | round(2) }}
{%- endmacro -%}
{%- macro absolute_feuchte(t, rh) -%}
{{ (216.679 * (rh / 100) * 6.112 * (2.718281828459045 ** ((17.62 * t) / (243.12 + t))) / (t + 273.15)) | round(2) }}
{%- endmacro -%}
"""


def j_taupunkt(t_expr: str, rh_expr: str) -> str:
    """Taupunkt-Ausdruck in Jinja, ohne Makro-Import auskommend."""
    return (
        f"{{% set t = {t_expr} %}}\n"
        f"{{% set rh = [[{rh_expr}, 0.1] | max, 100] | min %}}\n"
        "{% set g = (rh / 100) | log + (17.62 * t) / (243.12 + t) %}\n"
        "{{ ((243.12 * g) / (17.62 - g)) | round(2) }}"
    )


def j_absolute_feuchte(t_expr: str, rh_expr: str) -> str:
    return (
        f"{{% set t = {t_expr} %}}\n"
        f"{{% set rh = [[{rh_expr}, 0] | max, 100] | min %}}\n"
        "{% set es = 6.112 * (2.718281828459045 ** ((17.62 * t) / (243.12 + t))) %}\n"
        "{{ (216.679 * (rh / 100) * es / (t + 273.15)) | round(2) }}"
    )


def verfuegbar(*entities: str) -> str:
    """Availability-Template: alle Quellen müssen eine Zahl liefern.

    Ohne das rechnet Home Assistant beim Start mit 'unknown' weiter und die
    Automation schaltet auf einen Wert, den es nicht gibt.
    """
    checks = " and ".join(
        f"has_value('{e}')" for e in entities)
    return "{{ " + checks + " }}"


def ids_fuer(cfg: dict) -> dict:
    """Alle erzeugten Entity-IDs an einer Stelle, damit Definition und
    Referenz nie auseinanderlaufen können."""
    ids = {}
    ids["aussen_taupunkt"] = entity("sensor", "Außenluft Taupunkt")
    ids["aussen_af"] = entity("sensor", "Außenluft absolute Feuchte")
    for g in cfg["geraete"]:
        n = g["name"]
        ids[("t_korr", g["slug"])] = entity("sensor", n, "Temperatur korrigiert")
        ids[("rh_korr", g["slug"])] = entity("sensor", n, "Feuchte korrigiert")
        ids[("taupunkt", g["slug"])] = entity("sensor", n, "Taupunkt")
        ids[("af", g["slug"])] = entity("sensor", n, "absolute Feuchte")
        ids[("trocknung", g["slug"])] = entity("binary_sensor", n,
                                               "Trocknung möglich")
    return ids


def baue_template_sensoren(cfg: dict, ids: dict) -> list:
    aussen_t = cfg["aussen"]["temperatur"]
    aussen_rh = cfg["aussen"]["feuchte"]
    sensoren = []

    # --- Außenluft ---------------------------------------------------------
    name, _ = ids["aussen_taupunkt"]
    sensoren.append({
        "name": name,
        "unique_id": "ambientika_aussen_taupunkt",
        "unit_of_measurement": "°C",
        "device_class": "temperature",
        "state_class": "measurement",
        "availability": verfuegbar(aussen_t, aussen_rh),
        "state": j_taupunkt(f"states('{aussen_t}') | float(0)",
                            f"states('{aussen_rh}') | float(0)"),
    })
    name, _ = ids["aussen_af"]
    sensoren.append({
        "name": name,
        "unique_id": "ambientika_aussen_absolute_feuchte",
        "unit_of_measurement": "g/m³",
        "state_class": "measurement",
        "availability": verfuegbar(aussen_t, aussen_rh),
        "state": j_absolute_feuchte(f"states('{aussen_t}') | float(0)",
                                    f"states('{aussen_rh}') | float(0)"),
    })

    # --- je Gerät ----------------------------------------------------------
    for g in cfg["geraete"]:
        slug = g["slug"]
        off_t = float(g.get("offset_temperatur", 0.0))
        off_rh = float(g.get("offset_feuchte", 0.0))

        t_name, t_korr = ids[("t_korr", slug)]
        rh_name, rh_korr = ids[("rh_korr", slug)]
        tp_name, _ = ids[("taupunkt", slug)]
        af_name, _ = ids[("af", slug)]

        sensoren.append({
            "name": t_name,
            "unique_id": f"ambientika_{slug}_temperatur_korrigiert",
            "unit_of_measurement": "°C",
            "device_class": "temperature",
            "state_class": "measurement",
            "availability": verfuegbar(g["temperatur"]),
            # float(0) statt float: Home Assistant verwarnt einen Filter ohne
            # Default und rendert bei 'unknown' sonst gar nicht. Der Wert 0 wird
            # nie benutzt, weil availability den Sensor dann abschaltet.
            "state": ("{{ (states('%s') | float(0) + %s) | round(1) }}"
                      % (g["temperatur"], off_t)),
        })
        sensoren.append({
            "name": rh_name,
            "unique_id": f"ambientika_{slug}_feuchte_korrigiert",
            "unit_of_measurement": "%",
            "device_class": "humidity",
            "state_class": "measurement",
            "availability": verfuegbar(g["feuchte"]),
            # Auf 0..100 begrenzt: ein großzügiger Offset darf keine
            # physikalisch unmögliche Feuchte erzeugen.
            "state": ("{{ [[(states('%s') | float(0) + %s), 0] | max, 100] "
                      "| min | round(1) }}" % (g["feuchte"], off_rh)),
        })
        sensoren.append({
            "name": tp_name,
            "unique_id": f"ambientika_{slug}_taupunkt",
            "unit_of_measurement": "°C",
            "device_class": "temperature",
            "state_class": "measurement",
            "availability": verfuegbar(t_korr, rh_korr),
            "state": j_taupunkt(f"states('{t_korr}') | float(0)",
                                f"states('{rh_korr}') | float(0)"),
        })
        sensoren.append({
            "name": af_name,
            "unique_id": f"ambientika_{slug}_absolute_feuchte",
            "unit_of_measurement": "g/m³",
            "state_class": "measurement",
            "availability": verfuegbar(t_korr, rh_korr),
            "state": j_absolute_feuchte(f"states('{t_korr}') | float(0)",
                                        f"states('{rh_korr}') | float(0)"),
        })

    return sensoren


def baue_binaersensoren(cfg: dict, ids: dict) -> list:
    marge = float(cfg["einstellungen"]["trocknungs_marge"])
    _, aussen_af = ids["aussen_af"]
    binaer = []

    for g in cfg["geraete"]:
        slug = g["slug"]
        _, innen_af = ids[("af", slug)]
        name, _ = ids[("trocknung", slug)]
        binaer.append({
            "name": name,
            "unique_id": f"ambientika_{slug}_trocknung_moeglich",
            "availability": verfuegbar(innen_af, aussen_af),
            # Der Kern der Regelung: Lüften trocknet nur, wenn die Außenluft
            # absolut trockener ist. Relative Feuchte taugt dafür nicht.
            "state": (
                "{%% set innen = states('%s') | float(0) %%}\n"
                "{%% set aussen = states('%s') | float(0) %%}\n"
                "{{ aussen < (innen - %s) }}" % (innen_af, aussen_af, marge)
            ),
            "attributes": {
                "innen_absolut": "{{ states('%s') }}" % innen_af,
                "aussen_absolut": "{{ states('%s') }}" % aussen_af,
                "marge": str(marge),
            },
        })
    return binaer


def steuerflag(slug: str) -> str:
    """entity_id des Merkers je Gerät.

    Bei input_boolean leitet Home Assistant die ID aus dem SCHLÜSSEL ab, nicht
    aus dem Anzeigenamen — hier ist sie also direkt bestimmbar.
    """
    return f"input_boolean.ambientika_{slug}_entfeuchtung"


def baue_merker(cfg: dict) -> dict:
    """Je Gerät ein Merker: 'Die Entfeuchtung läuft, weil wir sie gestartet haben.'

    Ohne diesen Merker würde die Regelung einen Eingriff von Hand wieder
    zurückstellen: Wer abends selbst auf Abluft schaltet, fände das Gerät später
    im Automatikbetrieb wieder, ohne zu wissen warum. Zurückgestellt wird jetzt
    nur, was die Automation selbst gesetzt hat.
    """
    merker = {}
    for g in cfg["geraete"]:
        merker[f"ambientika_{g['slug']}_entfeuchtung"] = {
            "name": f"Ambientika {g['name']} Entfeuchtung aktiv",
            "icon": "mdi:water-percent",
        }
    return merker


def baue_automationen(cfg: dict, ids: dict) -> list:
    e = cfg["einstellungen"]
    schwelle = float(e["feuchte_schwelle"])
    stufe = int(e["entfeuchtungs_stufe"])
    nacht_beginn = e["nacht_beginn"]
    nacht_ende = e["nacht_ende"]
    # Die Modusnamen kommen aus der Konfiguration, weil sie davon abhängen,
    # welche Bridge die Entitäten anlegt. Ein hier fest verdrahteter Name, den
    # die select-Entität nicht kennt, lässt die Automation bei jedem Lauf mit
    # einem Fehler abbrechen.
    modus_entfeuchten = e.get("modus_entfeuchten", "HRV")
    modus_normal = e.get("modus_normal", "ECO")
    autos = []

    for g in cfg["geraete"]:
        slug, name = g["slug"], g["name"]
        modus = g["modus"]
        stufe_entity = g["stufe"]
        flag = steuerflag(slug)
        _, rh_korr = ids[("rh_korr", slug)]
        _, trocknung = ids[("trocknung", slug)]
        nachtruhe = bool(g.get("nachtruhe", False))

        ruhe_bedingung = []
        if nachtruhe:
            # In Schlafräumen nachts gar nicht schalten. Jeder angenommene
            # Befehl löst am Gerät einen Bestätigungston aus; das ist der
            # einzige heute wirksame Weg, ihn nachts zu vermeiden.
            ruhe_bedingung = [{
                "condition": "not",
                "conditions": [{
                    "condition": "time",
                    "after": nacht_beginn,
                    "before": nacht_ende,
                }],
            }]

        autos.append({
            "id": f"ambientika_{slug}_entfeuchten_start",
            "alias": f"Ambientika {name}: Entfeuchten starten",
            "description": (
                "Schaltet auf Abluft, wenn die Raumfeuchte über der Schwelle "
                "liegt UND die Außenluft absolut trockener ist. Ohne die "
                "zweite Bedingung würde bei schwüler Witterung Feuchtigkeit "
                "hereingelüftet."),
            "mode": "single",
            "trigger": [
                {"platform": "numeric_state", "entity_id": rh_korr,
                 "above": schwelle, "for": {"minutes": 10}},
                {"platform": "state", "entity_id": trocknung, "to": "on"},
            ],
            "condition": [
                {"condition": "numeric_state", "entity_id": rh_korr,
                 "above": schwelle},
                {"condition": "state", "entity_id": trocknung, "state": "on"},
                # Nur schalten, wenn sich wirklich etwas ändert — jeder
                # redundante Befehl kostet einen Bestätigungston.
                {"condition": "template",
                 "value_template": "{{ states('%s') != '%s' }}"
                                   % (modus, modus_entfeuchten)},
            ] + ruhe_bedingung,
            "action": [
                # Merker zuerst: Danach ist erkennbar, dass der folgende
                # Moduswechsel von uns kommt und nicht von Hand.
                {"service": "input_boolean.turn_on",
                 "target": {"entity_id": flag}},
                {"service": "select.select_option",
                 "target": {"entity_id": modus},
                 "data": {"option": modus_entfeuchten}},
                {"delay": {"seconds": 2}},
                {"service": "number.set_value",
                 "target": {"entity_id": stufe_entity},
                 "data": {"value": stufe}},
            ],
        })

        autos.append({
            "id": f"ambientika_{slug}_entfeuchten_ende",
            "alias": f"Ambientika {name}: Entfeuchten beenden",
            "description": (
                "Zurück in den Automatikbetrieb, sobald die Feuchte unter der "
                "Schwelle liegt oder Lüften nicht mehr trocknet. Stellt nur "
                "zurück, was diese Automation selbst gesetzt hat."),
            "mode": "single",
            "trigger": [
                {"platform": "numeric_state", "entity_id": rh_korr,
                 "below": schwelle - 3, "for": {"minutes": 10}},
                {"platform": "state", "entity_id": trocknung, "to": "off",
                 "for": {"minutes": 5}},
            ],
            "condition": [
                {"condition": "state", "entity_id": flag, "state": "on"},
                {"condition": "template",
                 "value_template": "{{ states('%s') == '%s' }}"
                                   % (modus, modus_entfeuchten)},
            ] + ruhe_bedingung,
            "action": [
                # Merker zuerst löschen, sonst deutet die Erkennung unten den
                # eigenen Moduswechsel als Eingriff von Hand.
                {"service": "input_boolean.turn_off",
                 "target": {"entity_id": flag}},
                {"service": "select.select_option",
                 "target": {"entity_id": modus},
                 "data": {"option": modus_normal}},
            ],
        })

        autos.append({
            "id": f"ambientika_{slug}_eingriff_erkannt",
            "alias": f"Ambientika {name}: Eingriff von Hand erkannt",
            "description": (
                "Wird der Modus während einer laufenden Entfeuchtung von "
                "anderer Seite geändert, gibt die Automation die Kontrolle ab "
                "und stellt später nichts zurück."),
            "mode": "single",
            "trigger": [
                {"platform": "state", "entity_id": modus,
                 "from": modus_entfeuchten},
            ],
            "condition": [
                {"condition": "state", "entity_id": flag, "state": "on"},
            ],
            "action": [
                {"service": "input_boolean.turn_off",
                 "target": {"entity_id": flag}},
            ],
        })

    return autos


def main() -> int:
    quelle = KONFIG if KONFIG.exists() else BEISPIEL
    ausgabe = AUSGABE_ECHT if quelle is KONFIG else AUSGABE_BEISPIEL
    if quelle is BEISPIEL:
        print(f"Hinweis: {KONFIG.name} nicht gefunden — verwende "
              f"{BEISPIEL.name}.\n"
              f"Das Ergebnis heißt deshalb {AUSGABE_BEISPIEL.name} und gehört\n"
              "NICHT nach config/packages/: Es enthält erfundene Entity-IDs.\n"
              f"Für die eigene Anlage {BEISPIEL.name} nach {KONFIG.name}\n"
              "kopieren und anpassen.\n")

    cfg = yaml.safe_load(quelle.read_text(encoding="utf-8"))
    for pflicht in ("aussen", "einstellungen", "geraete"):
        if pflicht not in cfg:
            sys.exit(f"Abschnitt '{pflicht}' fehlt in {quelle.name}")
    if not cfg["geraete"]:
        sys.exit("Keine Geräte konfiguriert.")

    slugs = [g["slug"] for g in cfg["geraete"]]
    doppelt = {s for s in slugs if slugs.count(s) > 1}
    if doppelt:
        sys.exit(f"Doppelte slugs: {', '.join(sorted(doppelt))} — "
                 "jedes Gerät braucht einen eindeutigen Kurznamen.")

    ids = ids_fuer(cfg)
    paket = {
        "input_boolean": baue_merker(cfg),
        "template": [
            {"sensor": baue_template_sensoren(cfg, ids)},
            {"binary_sensor": baue_binaersensoren(cfg, ids)},
        ],
        "automation": baue_automationen(cfg, ids),
    }

    kopf = (
        "# Ambientika — Feuchte- und Taupunktregelung für Home Assistant\n"
        "#\n"
        "# ERZEUGT von generate_package.py — nicht von Hand ändern.\n"
        f"# Quelle: {quelle.name}\n"
        "#\n"
        "# Nach config/packages/ kopieren. Falls dort noch nichts liegt, in\n"
        "# configuration.yaml ergänzen:\n"
        "#\n"
        "#   homeassistant:\n"
        "#     packages: !include_dir_named packages\n"
        "#\n"
        "# Danach Entwicklerwerkzeuge -> YAML -> Konfiguration neu laden.\n"
        "#\n"
        "# Die Offsets je Gerät stammen aus einer eigenen Vergleichsmessung\n"
        "# und gelten nur für das jeweilige Gerät.\n\n"
    )

    text = yaml.safe_dump(paket, allow_unicode=True, sort_keys=False,
                          default_flow_style=False, width=100)
    ausgabe.write_text(kopf + text, encoding="utf-8")

    n_sensoren = len(paket["template"][0]["sensor"])
    n_binaer = len(paket["template"][1]["binary_sensor"])
    print(f"{ausgabe.name} geschrieben:")
    print("\n  Erzeugte Entitäten — so heißen sie in Home Assistant:")
    for schluessel in sorted(ids, key=str):
        name, eid = ids[schluessel]
        print(f"    {eid}")
    print()
    print(f"  {len(cfg['geraete'])} Geräte")
    print(f"  {n_sensoren} Template-Sensoren")
    print(f"  {n_binaer} Binärsensoren")
    print(f"  {len(paket['automation'])} Automationen")
    nacht = [g["name"] for g in cfg["geraete"] if g.get("nachtruhe")]
    if nacht:
        print(f"  Nachtruhe aktiv für: {', '.join(nacht)}")
    ohne_offset = [g["name"] for g in cfg["geraete"]
                   if not float(g.get("offset_temperatur", 0))
                   and not float(g.get("offset_feuchte", 0))]
    if ohne_offset:
        print(f"\n  Noch ohne Kalibrierung: {', '.join(ohne_offset)}")
        print("  Diese Geräte regeln auf unkorrigierte Werte. Eine")
        print("  Vergleichsmessung gegen ein Referenzgerät im selben Raum")
        print("  genügt, um den Offset zu bestimmen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

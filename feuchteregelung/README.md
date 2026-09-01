# Ambientika in Home Assistant: Feuchte- und Taupunktregelung

Ein fertiges Home-Assistant-Paket für die Lüftungssteuerung nach Innen- und
Außenfeuchte, Taupunkt und Tag-/Nachtsituation. Es entsteht aus einer kurzen
Konfigurationsdatei, damit auch zehn Geräte ohne Copy-Paste-Fehler abgedeckt
sind.

## Der eine Punkt, auf den es ankommt

**Lüften trocknet nur, wenn die Außenluft absolut trockener ist als die
Innenluft.** Die relative Feuchte taugt für diese Entscheidung nicht.

| Situation | innen | außen | Lüften trocknet? |
|---|---|---|---|
| Herbst, kühl und feucht draußen | 22 °C / 60 % = 11,6 g/m³ | 15 °C / 70 % = 9,0 g/m³ | ja |
| Sommer, schwül draußen | 22 °C / 60 % = 11,6 g/m³ | 28 °C / 60 % = 16,3 g/m³ | **nein** |
| Winter, kalt und trocken | 21 °C / 55 % = 10,1 g/m³ | 2 °C / 85 % = 4,7 g/m³ | ja |
| Regentag, gleiche Temperatur | 21 °C / 55 % = 10,1 g/m³ | 21 °C / 80 % = 14,6 g/m³ | **nein** |

Zeile zwei ist die Falle: Draußen ist dieselbe relative Feuchte, aber die
wärmere Luft trägt deutlich mehr Wasser. Eine Regelung auf relative Feuchte
lüftet hier Feuchtigkeit ins Haus. Das Paket rechnet deshalb durchgehend auf
absolute Feuchte und Taupunkt.

## Vorher: Sensoren kalibrieren

Die Temperatur- und Feuchtefühler sitzen im Gehäuse des Geräts und werden von
seinem Luftstrom überstrichen, nicht frei im Raum. Sie messen dadurch einen
Mischwert aus Raumluft und Betriebszustand, und der Versatz hängt daran, ob das
Gerät gerade absaugt, einbläst oder steht.

Für eine Taupunktregelung ist das kein Problem, solange der Versatz bekannt
ist. Bestimmen lässt er sich in wenigen Minuten:

1. Ein Referenzmessgerät für ein bis zwei Stunden in den Raum stellen, ungefähr
   auf halber Höhe zwischen Boden und Lüfter, nicht direkt im Luftstrom.
2. Beide Werte notieren, wenn sich nichts mehr bewegt.
3. Differenz eintragen: `offset_temperatur = Referenz − Gerät`, dasselbe für die
   Feuchte.

Aus einem echten Vergleich: Das Gerät meldete 26,0 °C bei 46 %, zwei
unabhängige Referenzen im selben Raum 22,9 / 60 und 23,0 / 57. Daraus ergeben
sich −3,05 K und +12,5 Prozentpunkte.

Interessant daran ist die Richtung. Beim Taupunkt heben sich die beiden Fehler
weitgehend auf — 13,5 statt 14,4 °C, also nur 0,9 K daneben. Aber sie heben
sich nicht ganz auf, und der Rest geht konsequent in dieselbe Richtung: Das
Gerät meldet die Luft **um 0,8 g/m³ trockener, als sie ist**. Das entspricht
ziemlich genau der Schaltmarge. Praktisch heißt das: Ohne Korrektur wird nicht
gelüftet, obwohl Lüften helfen würde. Wer den Eindruck hat, die Anlage
entfeuchte zu wenig, findet hier einen Teil der Erklärung.

**Der Versatz gilt je Gerät.** Er hängt am Einbau und am Betriebszustand und
lässt sich nicht von einem Gerät auf ein anderes übertragen. Geräte ohne
Messung bekommen Offset 0 und regeln auf die Rohwerte — der Generator weist am
Ende darauf hin, welche das sind.

## Installation

```bash
pip install pyyaml            # für den Generator
pip install jinja2            # zusätzlich, falls Sie die Tests laufen lassen
cp geraete.beispiel.yaml geraete.yaml
# geraete.yaml an die eigene Anlage anpassen
python3 generate_package.py
```

Die erzeugte `ambientika.yaml` nach `config/packages/` kopieren. Falls dort noch
nichts liegt, in `configuration.yaml` ergänzen:

```yaml
homeassistant:
  packages: !include_dir_named packages
```

Danach **Entwicklerwerkzeuge → YAML → Konfiguration neu laden**.

> Ohne eigene `geraete.yaml` erzeugt das Skript `ambientika.**beispiel**.yaml`.
> Diese Datei gehört nicht nach `config/packages/` — sie enthält erfundene
> Entity-IDs und ergäbe ein Paket, das sich lädt und nichts tut. Der andere
> Dateiname ist genau dafür da, diesen Griff zu verhindern.

## Die eigenen Entity-IDs finden

Die IDs in `geraete.yaml` müssen zu Ihrer Installation passen. Nachschauen unter
**Einstellungen → Geräte & Dienste → Entitäten**, dort nach `ambientika`
filtern. Gebraucht werden je Gerät vier: Modus, Lüfterstufe, Temperatur,
Feuchte.

Stimmt eine davon nicht, bleibt der zugehörige Sensor `unknown` und die
Automation löst nie aus — **ohne Fehlermeldung im Log.** Home Assistant
beschwert sich über eine Referenz auf eine nicht existierende Entität nicht.
Deshalb gibt es dafür einen Test:

```bash
python3 -m unittest test_paket.TestEntityIds -v
```

Er sammelt jede im Paket referenzierte Entität ein und meldet die, die weder
selbst erzeugt noch in `geraete.yaml` deklariert ist.

Am Ende jedes Laufs listet der Generator außerdem auf, wie die erzeugten
Entitäten in Home Assistant heißen werden — damit lässt sich in der Oberfläche
direkt gegenprüfen, dass sie auch angelegt wurden.

## Was entsteht

Je Gerät vier Sensoren — korrigierte Temperatur, korrigierte Feuchte, Taupunkt,
absolute Feuchte — plus ein Binärsensor „Trocknung möglich" und ein Merker für
den Regelungszustand. Dazu Taupunkt und absolute Feuchte der Außenluft und drei
Automationen je Gerät: Entfeuchten starten, beenden, und Kontrolle abgeben, wenn
jemand von Hand eingreift.

Entfeuchtet wird nur, wenn **beides** zutrifft: Die Raumfeuchte liegt über der
Schwelle *und* die Außenluft ist absolut trockener. Fällt eines davon weg, geht
das Gerät zurück in den Automatikbetrieb.

## Zum Bestätigungston

Jeder vom Gerät angenommene Befehl löst den Quittungston aus — über App,
Fernbedienung oder Home Assistant gleichermaßen. Abschalten lässt er sich
derzeit nicht. Das Paket geht deshalb auf zwei Wegen damit um.

Erstens prüft jede Automation vor dem Schalten den aktuellen Zustand und sendet
nur bei echter Änderung. Ohne diese Prüfung schreibt eine zyklisch laufende
Automation denselben Modus immer wieder — und piept jedes Mal.

Zweitens gibt es je Gerät `nachtruhe: true`. Damit wird zwischen 22:00 und 06:30
gar nicht geschaltet. Für Schlafräume ist das die einzige heute zuverlässige
Lösung. Der Feuchteschutz im Gerät selbst bleibt davon unberührt und arbeitet
weiter.

## Eingriffe von Hand haben Vorrang

Wer selbst am Gerät oder in der App den Modus ändert, soll es nicht später im
Automatikbetrieb wiederfinden. Je Gerät merkt sich deshalb ein Schalter, ob die
laufende Entfeuchtung von der Automation stammt:

- Startet die Automation, setzt sie den Merker **vor** dem Moduswechsel.
- Zurückgestellt wird nur, solange der Merker gesetzt ist.
- Wird der Modus währenddessen von anderer Seite geändert, löscht die Automation
  den Merker und gibt die Kontrolle ab — sie greift dann nicht mehr ein.

Läuft das Gerät bereits im Entfeuchtungsmodus, weil Sie ihn selbst gewählt
haben, übernimmt die Automation gar nicht erst.

## Die Modusnamen prüfen

`modus_entfeuchten` und `modus_normal` in `geraete.yaml` müssen exakt so heißen
wie die Optionen der `select`-Entität. Nachsehen unter **Entwicklerwerkzeuge →
Zustände**: Die Modus-Entität führt die zulässigen Werte im Attribut `options`.

Ein Name, den die Entität nicht kennt, lässt die Automation bei jedem Auslösen
mit einem Fehler abbrechen — am Gerät passiert dabei nichts, im Log steht ein
Eintrag, den man leicht übersieht.

## Absichtlich nicht enthalten

Die Automationen schalten **kein Gerät ab**. Feuchteschutz ist wichtig,
Luftwechsel aber auch — eine Regelung, die bei schwüler Witterung die Lüftung
komplett stilllegt, tauscht ein Feuchteproblem gegen ein Luftqualitätsproblem.
Bei ungünstiger Außenluft wird lediglich nicht zusätzlich entfeuchtet. Ein Test
stellt sicher, dass sich `OFF` nicht durch eine spätere Änderung einschleicht.

## Prüfung

```bash
python3 -m unittest -v
```

56 Tests, gegliedert in vier Schichten.

**Die Physik** wird gegen Tabellenwerte geprüft — Sättigungsdampfdruck, Taupunkt
und absolute Feuchte an nachschlagbaren Stützstellen, dazu die Trocknungslogik
an vier typischen Wetterlagen.

**Die Templates** werden anschließend tatsächlich gerendert. Die Formeln stehen
zweimal im Projekt — einmal als Python, einmal als Jinja im Paket — und genau
diese Doppelung wird abgesichert: Ein Klammerfehler im Template würde Home
Assistant nicht auffallen, es rechnet dann einfach falsch und die Anlage
schaltet zum falschen Zeitpunkt.

**Die Verdrahtung** ist die dritte Schicht und praktisch die wichtigste. Jede im
Paket referenzierte Entität muss entweder selbst erzeugt oder in `geraete.yaml`
deklariert sein. Diese Prüfung existiert, weil in der ersten Fassung 13 von 21
Referenzen ins Leere zeigten: Die Entity-IDs waren erfunden statt aus den
Anzeigenamen abgeleitet. Das Paket hätte sich sauber geladen und wäre wirkungslos
geblieben.

**Das Verhalten** ist die vierte: dass die Regelung einen Eingriff von Hand
nicht zurückstellt, dass der Merker in der richtigen Reihenfolge gesetzt wird
und dass die Modusnamen tatsächlich aus der Konfiguration stammen statt fest
verdrahtet zu sein.

Zusätzlich geprüft: Hysterese zwischen Ein- und Ausschalten, Nachtruhe in
Schlafräumen, das Fehlen einer bedingungslosen Abschaltung, die Eindeutigkeit
aller `unique_id`, dass keine zwei Anzeigenamen dieselbe Entity-ID ergeben und
dass kein `float`-Filter ohne Default stehen bleibt.

## Dateien

| Datei | Zweck |
|---|---|
| `geraete.beispiel.yaml` | Vorlage für die eigene Konfiguration |
| `generate_package.py` | erzeugt das Paket |
| `formeln.py` | die Feuchtephysik als Python, Referenz für die Tests |
| `test_formeln.py` | Physik gegen Tabellenwerte |
| `test_paket.py` | rendert die Templates und prüft die Verdrahtung |
| `ambientika.yaml` | das erzeugte Paket — nicht von Hand ändern |

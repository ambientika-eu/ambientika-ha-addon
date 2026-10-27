# Changelog – Ambientika MQTT Bridge

Alle nennenswerten Änderungen dieses Add-ons. Neueste zuerst.
Ausführliche technische Hinweise stehen unter „Releases" im GitHub-Repository.

## 1.6.30
- Hysterese für „Humidity (averaged)" je Gerät: Neue Option
  `humidity_avg_hysteresis_devices`, z. B. `Gäste-Bad=1`. Der angezeigte
  gemittelte Feuchtewert ändert sich erst, wenn das Mittel um mindestens so viele
  Prozentpunkte von ihm abweicht. Hintergrund: Das Gerät meldet die Feuchte in
  groben Stufen von 2–3 Punkten, und bei einem kurzen Fenster kann eine einzige
  Phase der langsam wandernden Abtastung das ganze Fenster füllen - in ruhigen
  Stunden wanderte das 10-Minuten-Mittel dann um 1–2 Punkte, ohne dass sich im
  Raum etwas änderte. Mit der Hysterese bleibt der Wert dort stehen, eine Dusche
  (Dutzende Punkte) kommt sofort durch. Der Preis: Der angezeigte Wert kann bis
  zur Hysterese neben dem echten Mittel liegen, und langsame echte Änderungen
  kommen in Stufen. 1 ist ein guter Anfang, 1,5 wenn nachts noch Stufen zu sehen
  sind. Einträge und Namenszuordnung wie bei `average_window_devices`
  (Seriennummer oder Name wie in der App), 0–10 Punkte mit Dezimalpunkt, ein
  `%` dahinter ist erlaubt; 0 oder nicht genannt = keine Hysterese. Nur
  „Humidity (averaged)" ist betroffen - Rohwerte, „Temperature (averaged)" und
  die Mittelung selbst bleiben unverändert, nach „unbekannt" wird das erste
  Mittel wie berechnet gezeigt. Das Log nennt die Einstellung nach dem Start.
  Ein Median statt des Mittelwerts wurde nachgerechnet und verworfen: Auf dem
  groben Stufenraster springt er um eine ganze Stufe, sobald eine Phase etwa
  die Hälfte des Fensters einnimmt. Danke für die Auswertung und den Vorschlag.
- DOCS: Messwerte aus einer realen Installation zu 10 statt 15 Minuten im Bad
  ergänzt (Duschspitze etwa 4 Minuten früher, nachts etwa ein Drittel mehr
  Unruhe).
- Bridge 1.4.38.

## 1.6.29
- NeuraCell-X: Die zeitgesteuerte Abluft (TimedExpulsion, 20 Minuten) wird nicht
  mehr als „Modus davor" gespeichert. Griff der Radon- oder Taupunktschutz ein,
  während ein Gerät in dieser Abluft lief, stellte die Bridge sie nach dem
  Schutz wieder her: noch einmal 20 Minuten volle Abluft, und danach fiel das
  Gerät in den Schutzmodus (Off bzw. Zuluft) zurück statt in seinen normalen
  Betrieb. Jetzt wird der Modus gespeichert, zu dem die Abluft selbst
  zurückgekehrt wäre (`last_operating_mode` des Geräts). Meldet das Gerät keinen
  brauchbaren, bleibt es beim bisherigen Verhalten - mit Hinweis im Log.
- Eine während des Schutzes angeforderte zeitgesteuerte Abluft wird nicht mehr
  für später vorgemerkt (sie ist eine Aktion mit Ende, kein Modus), das Log
  sagt es. Alle anderen Moduswechsel werden wie bisher nach dem Schutz angewandt.
- Bridge 1.4.37.

## 1.6.28
- Slave-Filterzähler richtiggestellt (Log und DOCS): Der Hersteller setzt den
  Filter je Zone nur über den Master zurück - der Reset löscht den Zähler des
  Masters, ein Slave behält seinen eigenen, und am Gerät selbst gibt es dafür
  nichts zu drücken (der Filteralarm der Geräte ist nur bei Mastern aktiv).
  Der bisherige Hinweis „Reset the filter directly at the unit" war falsch.
  Der einzige Weg, den eigenen Zähler eines Slaves zu löschen, ist ein Reset,
  solange das Gerät Master ist: in der App vorübergehend als Einzelgerät
  einrichten, Filter zurücksetzen, wieder als Slave koppeln. Für den Alltag
  bleibt die Wartungsquittung (`slave_filter_soft_reset`) der einfachere Weg.
- Bridge 1.4.36 (nur Logtext und Doku, keine Funktionsänderung).

## 1.6.27
- Wartungsquittung sichtbar: „Filter Reset Status" zeigt `acknowledged`, solange
  die Quittung eines Slaves gilt - auch nach einem Neustart oder Update des
  Add-ons (bisher stand dort danach `idle`, obwohl die Quittung weiter galt),
  und fällt auf `idle` zurück, sobald sie endet. Mit `slave_filter_soft_reset`
  hat jedes Gerät zwei neue Diagnose-Sensoren „Filter Acknowledged Since" und
  „Filter Acknowledgement Valid Until" (`filter_ack_since` / `filter_ack_until`
  im Status): wann die Quittung gesetzt wurde und bis wann sie gilt. Der Tag,
  an dem der wirksame Filterstatus wieder auf den Gerätewert zurückfällt, ist
  damit vorher zu sehen. Das Log nennt beim Start jede noch gültige Quittung mit
  Datum und Ablauf. Danke für den Hinweis.
- `average_window_devices`: Bindestrich, Unterstrich und Leerzeichen gelten im
  Gerätenamen als dasselbe Trennzeichen (`Gäste-Bad` trifft ein Gerät namens
  `Gäste Bad`, auch mit einem Gedankenstrich vom Handy; `Gästebad` nicht). Die
  Doku nennt jetzt die Seriennummer als sicheren Weg und verwendet sie im
  Beispiel.
- „Filter Reset Status": Ein Reset, der wirklich greift (Zähler am Gerät
  gelöscht), entfernt eine gespeicherte Quittung; das Urteil eines gedrückten
  Resets (`confirmed` / `unconfirmed`) bleibt wie bisher stehen. Nach einem
  Reconnect zum Broker werden die Zustände neu gesendet. Eine beschädigte
  `filter_ack.json` kostet weder den Start noch einen Abruf: unbrauchbare
  Einträge werden mit Logzeile entfernt.
- Dokumentation: Die Optionstabellen in README und DOCS führen jetzt alle
  Optionen auf - NeuraCell-X (Radon), den Taupunkt-Block, `average_window_min`
  und `average_window_devices` -, mit Standardwert und Erklärung. Die
  Funktionsübersicht in der README nennt die Entitäten, die es wirklich gibt
  (statt „Filter alarm", „defrost", „power consumption"), und der Sensor für die
  laufende Funktion im SMART-Modus heißt in der Doku wie in Home Assistant
  „Last Mode".
- Bridge 1.4.35.

## 1.6.26
- Mittelungsfenster je Gerät: Neue Option `average_window_devices` gibt
  einzelnen Geräten ein eigenes Fenster für „Humidity (averaged)" und
  „Temperature (averaged)", z. B. `Gäste-Bad=15, Schlafzimmer Eltern=60` -
  das Bad folgt dem Duschen schneller, das Schlafzimmer wird stärker geglättet.
  Gerätename wie in der App oder Seriennummer, Groß-/Kleinschreibung egal,
  1-240 Minuten je Eintrag; nicht genannte Geräte behalten
  `average_window_min`. Die Untergrenze von 20 Abrufen gilt auch hier. Ein
  kürzeres Fenster folgt einer Änderung schneller, zeigt aber mehr von der
  Restschwankung (simuliert: 15 min etwa doppelt so viel wie 30 min je Stunde,
  60 min etwa halb so viel). Das Log
  nennt nach dem Start die wirksamen Fenster; ein Name ohne passendes Gerät
  oder ein unlesbarer Eintrag wird dort genannt und ignoriert. Minuten als
  Zahl mit Dezimalpunkt (z. B. 7.5). Leer (Standard)
  verhält sich wie bisher. Danke für den Vorschlag und die Auswertung.
- DOCS: Messwerte aus einer realen Installation zum 30-Minuten-Fenster ergänzt.
- Bridge 1.4.34.

## 1.6.25
- Gemittelte Messwerte: Jedes Gerät hat zwei neue Sensoren „Humidity (averaged)"
  und „Temperature (averaged)". Weil die Einheit etwa alle halbe Minute die
  Richtung wechselt, sieht der Fühler abwechselnd Raum- und Zuluft, und ein
  einzelner Feuchtewert springt um bis zu rund 20 Prozentpunkte - die Kachel
  zeigt bei jedem Blick etwas anderes, und eine Automation auf eine Feuchte-
  schwelle löst je nach Taktphase aus. Die neuen Sensoren zeigen das zeitlich
  gewichtete Mittel der veröffentlichten Werte über die letzten 30 Minuten
  (Option `average_window_min`, 1-240, mindestens 20 Abrufe). Mehrfach gelesene
  Statuspakete, Zusatzveröffentlichungen und ausgefallene Abrufe verschieben das
  Mittel nicht; zurückgehaltene unplausible Werte zählen nicht. Nach dem Start
  „unbekannt", bis rund zwei Minuten Werte vorliegen. „Humidity" und
  „Temperature" bleiben unverändert daneben und reagieren sofort, etwa auf das
  Duschen. Das Mittel umfasst den ganzen Takt (Raum- und Zuluft): ein ruhiger
  Wert für Anzeige, Verlauf und Schwellen, kein reiner Raumluftwert. Zu
  erwarten: Die Cloud liefert etwa ein Paket je halbe Minute, also etwa einen
  Messwert je Umkehrung; welche Taktphase dabei erwischt wird, wandert langsam.
  Das Mittel ist darum deutlich ruhiger als der Rohwert, kann aber über eine
  Stunde noch um einige Punkte wandern - ein längeres Fenster (60 min) halbiert
  das. Am besten mit dem Abrufintervall 30 s (Standard) oder kürzer. Danke für
  den Vorschlag.
- Bridge 1.4.33.

## 1.6.24
- Modus von Slave-Einheiten: Ein gekoppelter Slave läuft mit dem Master seiner
  Zone, sein eigenes Modusfeld gibt nicht wieder, wie er lüftet - ein Slave kann
  „Surveillance" melden und trotzdem im Takt des Masters mit Wärmerückgewinnung
  arbeiten. Wie die Ambientika-App, die je Zone nur den Master zeigt, zeigt „Mode"
  eines Slaves jetzt den Modus seines Masters. Der eigene Wert des Geräts steht
  daneben in den neuen Sensoren „Mode raw" und „Mode raw (num)". Master werden je
  Durchlauf zuerst abgefragt. Unter NeuraCell-X-Schutz oder wenn der Master länger
  nicht gelesen wurde, wird der eigene Wert gezeigt. Weicht der eigene Wert ab,
  steht das einmal je Änderung im Log. Der Master einer Zone wird nur noch im
  selben Haus gesucht (mehrere Häuser im Konto haben jeweils eine Zone 0), und
  die Rollen kommen aus dem Status, den jedes Gerät selbst meldet: Umkoppeln
  oder Zurücksetzen in der App wird ohne Neustart nachvollzogen, ein
  zurückgesetztes Gerät mit altem Zonen-Index ist kein Slave. Für Automationen:
  „Mode" und „Mode (num)" eines Slaves folgen jetzt dem Master; ein auf dem
  Slave gewählter Modus geht weiterhin an dieses Gerät, die Anzeige zeigt beim
  nächsten Abruf wieder den Master - Modi gehören auf den Master.
- Korrektur zu 1.6.22: Behält ein Slave einen anderen Modus als sein Master, ist
  das kein Zeichen einer unterbrochenen Verbindung. Die Warnung nach einem
  Moduswechsel sagt das nicht mehr.
- Unplausible Messwerte werden nicht mehr veröffentlicht. Feuchte außerhalb
  1-100 % und Temperatur außerhalb -40 bis 85 °C fallen weg, ebenso ein einzelner
  Sturz der Feuchte unter 20 %, wenn kurz davor keine trockene Luft gemessen
  wurde (z. B. 6 % zwischen 55 und 70 %). Anstiege, Duschspitzen und der
  Wechseltakt bleiben unberührt; bei trockener Winterluft wird nur der erste
  trockene Wert nach einer langen feuchten Phase um einen Abruf verzögert. Ein
  innerhalb von zwei Minuten mehrfach gelesenes Statuspaket (die Cloud hält das
  letzte Paket des Geräts) zählt nicht als neue Messung. Solange wird der letzte plausible Wert gezeigt,
  höchstens zehn Minuten, danach „unbekannt". Beides steht einmal im Log,
  bei einem flatternden Sensor höchstens einmal pro Stunde. Danke für den
  Hinweis auf das Minimum von 6 %.
- Wartungsquittung: Der wirksame Filterstatus wird sofort veröffentlicht, nicht
  erst beim nächsten Abruf - Logzeile und Anzeige stimmen damit überein. Lässt
  sich die Quittung nicht speichern, meldet die Bridge das als Warnung und
  „unconfirmed" statt „acknowledged".
- Bridge 1.4.32.

## 1.6.23
- Nachkontrolle zu 1.6.22. „Dauerhaft grün" heißt für die Wartungsquittung jetzt:
  mindestens zehn Abrufe in Folge und mindestens zehn Minuten. Zehn Abrufe allein
  waren bei einem Abrufintervall von 10 s nur 100 s — ein neu startender Slave, der
  kurz einen Standardstatus meldet, hätte die Quittung weiter löschen können.
- Die Modusprüfung nach einem Befehl ist vom Statusabruf getrennt: Ein Fehler darin
  kann nie als fehlgeschlagener Abruf zählen oder den Status unterdrücken.
- Zusätzlicher Test durch den echten Abrufpfad mit dem gemeldeten Fall (ein einzelner
  unbekannter Filterwert zwischen lauter „Bad"): Die Quittung bleibt, der Status bleibt
  grün. Auf dem alten Stand nachgestellt war sie danach weg.

## 1.6.22
- Die Wartungsquittung für Slave-Einheiten („slave_filter_soft_reset") verschwindet
  nicht mehr vorzeitig. Bisher genügte ein einziger Abruf, in dem das Gerät einen
  unbekannten oder kurz grünen Filterwert meldete, und die Quittung war endgültig
  gelöscht — ohne Eintrag im Log. So konnte sie nach wenigen Wochen statt nach 90 Tagen
  weg sein. Jetzt endet sie nur noch, wenn „filter_ack_ttl_days" abgelaufen ist oder
  das Gerät selbst zehn Abrufe in Folge „Good" meldet (Filter direkt am Gerät
  zurückgesetzt). Beides steht mit Grund im Log. Ein unbekannter Wert lässt die
  Quittung stehen und wird einmal protokolliert. Eine bereits verschwundene Quittung
  bitte einmal neu setzen.
- Moduswechsel werden nachgeprüft. „change_mode OK" hieß bisher nur, dass die Cloud
  den Aufruf angenommen hat, nicht dass das Gerät umgeschaltet hat. Die Zeile lautet
  jetzt „change_mode OK … (accepted by the cloud)". Die Bridge beobachtet die folgenden
  Abrufe und meldet „operating mode … confirmed", sobald das Gerät den Modus zeigt,
  oder nach drei Minuten eine Warnung mit dem tatsächlichen Modus. Bei einem Slave
  nennt die Warnung den Master der Zone: Ein Slave übernimmt seinen Modus über das
  WLAN vom Master, der Modus gehört deshalb an den Master. Behält ein Slave einen
  anderen Modus als sein Master, ist seine Verbindung zum Master unterbrochen.
- Übernommen aus der Bridge (1.4.22 bis 1.4.29), bisher nur im Hauptrepository:
  - Lüfterstufen „Night" und „Turbo", die das Gerät selbst wählt, werden nie mehr an
    die Cloud zurückgeschickt. Ein Moduswechsel bei einem Gerät auf „Turbo" endete
    bisher mit „HTTP 500 … unsigned byte".
  - NeuraCell-X: Radon hat Vorrang vor der Taupunktsperre, Rückkehr in den vorherigen
    Modus übersteht Neustart und Update, Befehle und Schutzwechsel laufen je Gerät
    nacheinander.
  - Das Ambientika Radon-Messgerät (radon/<id>/state) und die Ambientika
    Taupunktsteuerung (dew-point/<id>/state) werden direkt gelesen. Neue Sensoren
    „Radon Meter Connected" und „Dew Point Controller Connected"; die NeuraCell-X-
    Sensoren stehen auf „nicht verfügbar", solange das Add-on nicht läuft.
  - Neue Optionen: radon_meter_topic, radon_value_key, radon_meter_timeout,
    dewpoint_block_key, dewpoint_availability_topic, dewpoint_signal_timeout,
    dewpoint_lost_action, dewpoint_controller_topic, dewpoint_controller_key. Die
    Standardwerte entsprechen dem bisherigen Verhalten der Bridge, es ist nichts
    einzustellen.

## 1.6.21
- Die Installationsanleitung nannte den Menüpunkt „Einstellungen → Add-ons → Add-on Store". Home Assistant hat ihn mit Version 2026.2 umbenannt: Er heißt dort „Apps", und der Store öffnet sich über die Schaltfläche zum Installieren auf dieser Seite. README und Dokumentation nennen jetzt den aktuellen Weg und den alten in Klammern. Danke für den Hinweis.

## 1.6.20
- Temperatur und Luftfeuchte werden jetzt als Messwerte gemeldet
  („state_class: measurement"). Home Assistant legt damit eine Langzeitstatistik
  an. Bisher fehlte diese Angabe, die Werte verschwanden mit der
  Recorder-Aufbewahrung nach rund zehn Tagen und ließen sich weder im
  Statistik-Diagramm noch über die Heizperiode auswerten.
- Die beiden Passwortfelder in den Add-on-Optionen sind jetzt als Passwort
  deklariert. Home Assistant stellt sie damit verdeckt dar, statt sie wie bisher
  im Klartext anzuzeigen.

## 1.6.19
- Das Sammelfenster für Kommandos lässt sich jetzt in den Add-on-Optionen
  einstellen: „command_coalesce_ms", Standard 800 Millisekunden, 0 führt jedes
  Kommando sofort aus. Bisher war es nur über eine Umgebungsvariable erreichbar
  und damit im Add-on gar nicht änderbar — wen die knappe Sekunde Verzögerung
  beim Schalten stört, der hatte keine Möglichkeit.
- Die README im Wurzelverzeichnis des Repositories führte den MQTT-Benutzer
  weiterhin als „optional" und kannte drei Optionen nicht. Sie ist jetzt auf
  demselben Stand wie die Dokumentation im Add-on.

## 1.6.18
- Neue Datei DOCS.md: Home Assistant zeigt im Reiter „Dokumentation" ausschließlich
  diese Datei an. Bisher gab es nur eine README.md, die der Supervisor dort nicht
  darstellt — im Add-on selbst stand also gar keine Anleitung. Die neue Datei nennt
  die Voraussetzungen, erklärt die Zugangsdaten und beschreibt alle Optionen.
- Klarstellung: Die einzutragenden Zugangsdaten sind dieselbe E-Mail-Adresse und
  dasselbe Passwort wie in der Ambientika-App. Ein eigenes Konto für die Bridge
  gibt es nicht. Die Fehlermeldung sagt das jetzt auch selbst.
- MQTT-Fehler werden im Klartext gemeldet statt nur als Zahl. „rc=5" heißt, dass
  der Broker die Anmeldung abgelehnt hat, und verweist auf mqtt_username und
  mqtt_password — das offizielle Mosquitto-Add-on lässt keine anonymen
  Verbindungen zu. Die Optionsbeschreibung nannte diese Felder bisher „optional",
  was für Mosquitto nicht zutrifft.

## 1.6.17
- Mehrere Einstellungen in einer Automation funktionieren jetzt. Bisher füllte
  jedes Kommando die Attribute, die es nicht selbst setzt, aus dem gerade
  gelesenen Cloud-Status — und die Cloud kannte die eben gesendete Änderung noch
  nicht. Wer Modus und Lüfterstufe nacheinander setzte, bei dem schrieb das
  zweite Kommando den alten Modus zurück. Kommandos für dasselbe Gerät werden
  jetzt innerhalb eines kurzen Fensters gesammelt und in einem einzigen Aufruf
  angewandt. Das halbiert nebenbei die Cloud-Aufrufe.
- Neues Kommando-Topic „<prefix>/<seriennummer>/set" nimmt ein JSON-Objekt mit
  mehreren Attributen entgegen, zum Beispiel
  {"operating_mode": "MasterSlaveFlow", "fan_speed": "High"}. Die Kurznamen
  „mode", „fanSpeed", „humidityLevel" und „lightSensorLevel" werden ebenfalls
  verstanden. Ein ungültiger Wert verwirft das ganze Kommando, ein unbekannter
  Schlüssel wird mit einer Meldung übersprungen.
- Das Sammelfenster lässt sich über die Umgebungsvariable COMMAND_COALESCE_MS
  einstellen (Standard 800 Millisekunden, 0 schaltet es ab).
- Die MQTT-Dokumentation im Projekt-README beschrieb Topics und Nutzlasten, die
  es so nie gab. Sie ist jetzt aus dem laufenden Betrieb heraus korrigiert.

## 1.6.16
- Die Wartungsquittung wirkt jetzt auch auf den Text-Sensor „Filter Status". Bisher
  meldete er weiterhin „Bad", während die Zahlenwerte bereits grün waren — wer den
  lesbaren Klartext im Dashboard nutzt, sah die Quittung also nicht. Die Hauptfelder
  „filters_status" und „filter_status_num" zeigen nun beide den quittierten Wert.
- Neuer Sensor „Filter Status raw" (`filters_status_raw`) mit dem unveränderten
  Gerätewert als Text — passend zum bereits vorhandenen `filter_status_raw_num`.
  Bei ausgeschalteter Quittung, also im Standard, sind Haupt- und Rohwert identisch.
- Der Diagnosesensor „Filter Reset Status" kennt den eigenen Zustand „acknowledged".
  Bisher stand dort nach einer Quittung „unconfirmed", was neben einer grünen Anzeige
  widersprüchlich wirkte. „unconfirmed" bedeutet jetzt wieder das, was es sagt: der
  Reset ist weder durchgekommen noch vermerkt worden.

## 1.6.15
- Filter-Reset greift jetzt auch bei Filterstatus „Medium" (gelb). Bisher stieg
  die Bridge bei allem außer Rot vorzeitig aus und meldete „nothing to do", ohne
  überhaupt einen Reset zu senden — wer den Filter vor dem Alarm reinigt, drückte
  ins Leere. Übersprungen wird nur noch ein Zähler, der bereits auf „Good" steht.
- Die Erfolgsprüfung misst jetzt die tatsächliche Verbesserung des Zählers statt
  nur „nicht mehr rot". Ein Reset aus „Medium" heraus wird dadurch nicht mehr
  fälschlich als bestätigt gemeldet, wenn sich nichts bewegt hat.
- Die Wartungsquittung für Slave-Einheiten gilt entsprechend für jeden fälligen
  Zähler, also für Gelb wie für Rot.

## 1.6.14
- Filter-Reset meldet bei Slave-Einheiten jetzt den tatsächlichen Sachverhalt: Der Zähler
  einer Slave-Einheit lässt sich über die Cloud nicht löschen, weil die Rückstellung vom
  Master der Zone ausgeführt wird und nur dessen eigenen Zähler betrifft. Statt auf einen
  späteren Poll zu vertrösten, weist die Bridge im Klartext darauf hin, dass die Rückstellung
  direkt an der Einheit nötig ist. Bei Master- und Einzelgeräten wird der Erfolg weiterhin
  am echten Gerätestatus geprüft.
- Neue Option „slave_filter_soft_reset" (Standard: aus): Ist sie aktiv, vermerkt die Bridge
  einen Reset an einer Slave-Einheit als Wartungsquittung. `filter_status_num` zeigt die
  gewartete Einheit dann wieder grün, während der rohe Gerätewert unverändert bleibt und
  weiterhin unter `filters_status` sowie im neuen Feld `filter_status_raw_num` sichtbar ist.
  Damit lösen Warnregeln wieder korrekt aus, ohne dass eine gewartete Einheit dauerhaft auf
  Rot hängt.
- Neue Option „filter_ack_ttl_days" (Standard: 90): Gültigkeitsdauer der Wartungsquittung
  in Tagen.

## 1.6.13
Behebt einen Ausfall im Dauerbetrieb: Nach dem Token-Refresh (etwa alle sechs Stunden) stellte die Bridge das Polling dauerhaft ein. Beim Re-Auth werden die Geräte jetzt wieder korrekt mit dem frischen Cloud-Token verbunden, sodass das Polling nahtlos weiterläuft.

## 1.6.12
Helligkeits-/Dämmerungssensor bleibt beim Aus- und Wiedereinschalten über Home Assistant erhalten (vorher sprang er auf „Medium" zurück, statt die Voreinstellung wie „Off" zu behalten). Interne Korrektur: die NeuraCell-X-Moduswiederherstellung sendet den Helligkeitswert wieder korrekt mit.

## 1.6.11
- Luftqualitäts-Zahlenwert (`air_quality_num`) auf die saubere fünfstufige
  Geräteskala gebracht: VeryGood = 4, Good = 3, Medium = 2, Poor = 1, Bad = 0.
  Damit sind Langzeitstatistik und Diagramme über den gesamten Bereich eindeutig.

## 1.6.10
- Filter-Reset vereinfacht und beruhigt: Das dokumentierte Reset-Kommando wird
  einmalig an das Gerät und den Master seiner Zone gesendet, der Status danach
  einmal nachgelesen – ohne wiederholte Versuche und ohne Log-Rauschen.
- Neuer Diagnosesensor „Filter Reset Status" (standardmäßig ausgeblendet,
  bei Bedarf für Fortgeschrittene einblendbar).

## 1.6.8
- Automatische Token-Auffrischung: Läuft das Cloud-Token ab, erneuert die Bridge
  es selbst – Geräte werden nicht mehr bis zum nächsten Neustart „nicht verfügbar".
- Neuer Sensor „Ambientika Bridge (online/offline)" samt Last-Will: Ein Ausfall
  des Add-ons ist sofort in Home Assistant sichtbar.
- Robusterer MQTT-Reconnect; ein laufender Filter-Reset übersteht einen Neustart.

## 1.6.1 – 1.6.7
- Schrittweise Verbesserungen rund um den Filter-Reset (Zustellung an Gerät und
  Zonen-Master, an die App angeglichene Anfrage).

## 1.6.0
- Volle Funktionsparität mit der ambientika-mqtt-bridge: numerische Begleitsensoren
  je Textwert (Langzeitstatistik/Grafana ohne eigene Übersetzungstabelle),
  Filter-Reset-Taste, Zonen-Index sowie NeuraCell-X Radon- und Taupunktquellen
  direkt aus der Cloud.
- Fix: Nachtstufe („Night") wird korrekt verarbeitet – keine Lücken mehr in den
  Messreihen, wenn ein Gerät im Nachtbetrieb läuft.
- Verfügbarkeits-Entprellung: kein Flackern auf „nicht verfügbar" bei einem
  einzelnen fehlgeschlagenen Poll (Standard: 3 Fehlversuche in Folge).

## Ältere Versionen
- 1.4.x / 1.2.x: frühe Ausgaben vor der vollen MQTT-Funktionsparität.

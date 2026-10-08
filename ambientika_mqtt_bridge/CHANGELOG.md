# Changelog – Ambientika MQTT Bridge

Alle nennenswerten Änderungen dieses Add-ons. Neueste zuerst.
Ausführliche technische Hinweise stehen unter „Releases" im GitHub-Repository.

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

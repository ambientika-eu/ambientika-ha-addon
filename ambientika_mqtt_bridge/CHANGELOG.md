# Changelog – Ambientika MQTT Bridge

Alle nennenswerten Änderungen dieses Add-ons. Neueste zuerst.
Ausführliche technische Hinweise stehen unter „Releases" im GitHub-Repository.

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

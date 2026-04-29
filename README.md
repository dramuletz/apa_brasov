# 💧 APA Brasov — Integrare Home Assistant

Integrare custom pentru portalul **https://www.apabrasov.ro** care aduce datele
contului tău de apă direct în Home Assistant.

---

## Entitati disponibile

### Senzori (`sensor.*`)
| Entitate | Descriere |
|---|---|
| `sensor.apa_brasov_index_apometru_curent` | Indexul apometrului (m³) |
| `sensor.apa_brasov_index_apometru_anterior` | Indexul lunii anterioare |
| `sensor.apa_brasov_consum_curent` | Consum lunar (m³) |
| `sensor.apa_brasov_sold_cont` | Sold cont curent (RON) |
| `sensor.apa_brasov_factura_1_suma` | Ultima factură — sumă + detalii |
| `sensor.apa_brasov_factura_2_suma` | Penultima factură |
| `sensor.apa_brasov_factura_3_suma` | Antepenultima factură |
| `sensor.apa_brasov_numar_contract` | Număr contract + adresă |
| `sensor.apa_brasov_ultima_actualizare` | Timestamp ultima sincronizare |

### Introducere index (`number.*`)
| Entitate | Descriere |
|---|---|
| `number.apa_brasov_autocitire_index_apometru` | Introdu indexul → trimis pe portal |

---

## Instalare

### Varianta 1 — Manual (fără HACS)

1. Copiază folderul `custom_components/apa_brasov/` în directorul
   `config/custom_components/` al instalației tale Home Assistant.

   Structura finală:
   ```
   config/
   └── custom_components/
       └── apa_brasov/
           ├── __init__.py
           ├── api.py
           ├── config_flow.py
           ├── const.py
           ├── manifest.json
           ├── number.py
           ├── sensor.py
           └── translations/
               └── ro.json
   ```

2. Repornește Home Assistant.

3. Mergi la **Setări → Dispozitive și Servicii → Adaugă Integrare**.

4. Caută **APA Brasov** și introdu credențialele portalului.

### Dependințe Python

Pachetele sunt declarate în `manifest.json` și se instalează automat:
- `requests`
- `beautifulsoup4`

---

## Dashboard Lovelace

Importă fișierul `lovelace_dashboard.yaml` în dashboard-ul tău:

1. Edit Dashboard → Raw Configuration Editor
2. Lipeste conținutul fișierului `lovelace_dashboard.yaml`

---

## Automatizări utile

### Notificare factură neplatită
```yaml
automation:
  - alias: "APA Brasov - Factura neplatita"
    trigger:
      - platform: state
        entity_id: sensor.apa_brasov_factura_1_suma
    condition:
      - condition: template
        value_template: >
          {{ state_attr('sensor.apa_brasov_factura_1_suma', 'status') | lower 
             in ['neplatit', 'restant', 'unpaid'] }}
    action:
      - service: notify.mobile_app
        data:
          title: "💧 APA Brasov — Factură neachitată"
          message: >
            Factura {{ state_attr('sensor.apa_brasov_factura_1_suma', 'numar') }}
            în valoare de {{ states('sensor.apa_brasov_factura_1_suma') }} RON
            este neachitată. Scadență: 
            {{ state_attr('sensor.apa_brasov_factura_1_suma', 'data_scadenta') }}
```

### Reminder lunar autocitire (în a 25-a zi a lunii)
```yaml
automation:
  - alias: "APA Brasov - Reminder autocitire"
    trigger:
      - platform: time
        at: "09:00:00"
    condition:
      - condition: template
        value_template: "{{ now().day == 25 }}"
    action:
      - service: notify.mobile_app
        data:
          title: "💧 Autocitire apometru"
          message: >
            Nu uita să transmiți indexul apometrului!
            Index actual: {{ states('sensor.apa_brasov_index_apometru_curent') }} m³
```

---

## Note tehnice

- Datele se actualizează **la fiecare 6 ore** (configurabil în `const.py` → `SCAN_INTERVAL`).
- Integrarea funcționează prin **scraping HTML** al portalului — dacă APA Brasov
  modifică structura site-ului, este posibil să necesite actualizare.
- Credențialele sunt stocate **local** în `config/.storage/` — nu sunt transmise
  nicăieri în afară de portalul oficial.

---

## Depanare

Activează logging detaliat în `configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    custom_components.apa_brasov: debug
```

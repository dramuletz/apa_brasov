# 🗺️ Lovelace Dashboard — APA Brasov

Acest card afișează toate datele disponibile din integrarea APA Brasov într-un singur loc: index apometru, ultima factură, arhiva plăților, transmitere index și date utilizator.

---

## 📋 Cerințe

Înainte de a importa dashboard-ul, asigură-te că ai instalat:

| Plugin | Necesar pentru | Instalare |
|---|---|---|
| [ApexCharts Card](https://github.com/RomRider/apexcharts-card) | Graficul arhivei de plăți | HACS → Frontend |

### Instalare ApexCharts Card prin HACS
1. HACS → **Frontend**
2. Caută **ApexCharts Card**
3. Click **Download**
4. Repornește Home Assistant (sau doar reîncarcă browserul)

---

## 📥 Import Dashboard

### Metoda 1 — Manual (Raw Config Editor)

1. Mergi la **Setări → Dashboards**
2. Click **+ Adaugă dashboard** → dă-i un nume (ex: `APA Brasov`)
3. Deschide noul dashboard → click **⋮** (trei puncte) → **Edit Dashboard**
4. Click din nou **⋮** → **Raw configuration editor**
5. Șterge tot ce e acolo și lipește conținutul de mai jos
6. Click **Save**

### Metoda 2 — Card manual

1. Deschide orice dashboard existent
2. Click **Edit** → **+ Add Card** → **Manual**
3. Lipește conținutul cardului de mai jos
4. Click **Save**

---

## 📄 Conținut `lovelace_dashboard.yaml`

```yaml
type: vertical-stack
cards:

  - type: markdown
    content: >
      ## 💧 APA Brasov
      Ultima actualizare: {{ states('sensor.apa_brasov_ultima_actualizare') | as_datetime | as_local | datetime_format('%d.%m.%Y %H:%M') }}

  # ── Index & Consum ─────────────────────────────────────────
  - type: entities
    title: Apometru
    entities:
      - entity: sensor.apa_brasov_index_apometru_curent
        name: Index Curent
      - entity: sensor.apa_brasov_consum_ultima_perioada
        name: Consum Ultima Perioadă

  # ── Autocitire ─────────────────────────────────────────────
  - type: entities
    title: ✍️ Transmite Index
    entities:
      - entity: number.apa_brasov_autocitire_index_apometru
        name: Index de transmis

  # ── Ultima factura & sold ──────────────────────────────────
  - type: entities
    title: Facturare
    entities:
      - entity: sensor.apa_brasov_ultima_factura
        name: Ultima Factură (RON)
        secondary_info: last-changed
      - entity: sensor.apa_brasov_total_de_plata
        name: Total de Plată

  # ── Grafic plati ───────────────────────────────────────────
  - type: custom:apexcharts-card
    header:
      show: true
      title: 💳 Istoricul Plăților (RON)
    series:
      - entity: sensor.apa_brasov_arhiva_plati
        name: Suma plătită (RON)
        data_generator: |
          const plati = entity.attributes.plati || [];
          return plati
            .filter(p => p.data && p.suma)
            .map(p => {
              const parts = p.data.split('.');
              const date = new Date(`${parts[2]}-${parts[1]}-${parts[0]}`);
              return [date.getTime(), p.suma];
            })
            .reverse();
    chart_type: bar

  # ── Date utilizator ────────────────────────────────────────
  - type: entities
    title: 👤 Date Utilizator
    entities:
      - entity: sensor.apa_brasov_date_utilizator
        name: Cod Client
    footer:
      type: markdown
      content: >
        **Contract:** {{ state_attr('sensor.apa_brasov_date_utilizator', 'nr_contract') }}
        | **Cod autocitire:** {{ state_attr('sensor.apa_brasov_date_utilizator', 'cod_autocitire') }}
        | **Adresă:** {{ state_attr('sensor.apa_brasov_date_utilizator', 'adresa') }}
```

---

## 🃏 Descrierea cardurilor

### 1. Header cu timestamp
Afișează data și ora ultimei sincronizări cu portalul APA Brasov.

### 2. Apometru
| Câmp | Descriere |
|---|---|
| **Index Curent** | Indexul actual al apometrului în m³ |
| **Consum Ultima Perioadă** | Diferența față de citirea anterioară |

> **Atribute disponibile** pe `sensor.apa_brasov_index_apometru_curent`:
> - `data_citire` — data citirii curente
> - `index_anterior` — indexul lunii trecute
> - `data_citire_anterioara` — data citirii anterioare
> - `cod_autocitire` — codul apometrului

### 3. Transmite Index ✍️
Câmp numeric pentru trimiterea autocitiri direct din Home Assistant.

> ⚠️ Portalul APA Brasov acceptă autocitiri **doar între zilele 15–21 ale lunii**. În afara acestui interval, trimiterea va fi ignorată.

### 4. Facturare
| Câmp | Descriere |
|---|---|
| **Ultima Factură** | Valoarea în RON a celei mai recente facturi |
| **Total de Plată** | Soldul actual al contului |

> **Atribute disponibile** pe `sensor.apa_brasov_ultima_factura`:
> - `cod` — codul intern al facturii
> - `serie_nr` — seria și numărul (ex: CAB26 187817)
> - `data_emitere` — data emiterii
> - `data_scadenta` — data scadenței
> - `tva` — valoarea TVA

### 5. Grafic Plăți 💳
Grafic bar cu istoricul tuturor plăților efectuate, afișate cronologic.

> **Atribute disponibile** pe `sensor.apa_brasov_arhiva_plati`:
> ```json
> {
>   "plati": [
>     {"data": "08.02.2024", "suma": 165.0, "serie": "OP 1", "note": "Ordin de plata"},
>     ...
>   ]
> }
> ```

### 6. Date Utilizator 👤
Afișează codul de client ca state și toate detaliile contractului ca atribute.

> **Atribute disponibile** pe `sensor.apa_brasov_date_utilizator`:
> - `cod_client` — ex: P561/238
> - `nr_contract` — ex: C5557
> - `data_contract` — ex: 17.09.2018
> - `valabilitate` — ex: nedeterminat
> - `tip_serviciu` — ex: Apa rece contorizata HARMAN POPULATIE
> - `in_reziliere` — Da / Nu
> - `adresa` — adresa completă
> - `cod_autocitire` — codul apometrului (ex: 133668)

---

## 🔔 Automatizări utile

### Notificare factură nouă
```yaml
automation:
  - alias: "APA Brasov - Factură nouă"
    trigger:
      - platform: state
        entity_id: sensor.apa_brasov_ultima_factura
    condition:
      - condition: template
        value_template: "{{ trigger.from_state.state != trigger.to_state.state }}"
    action:
      - service: notify.mobile_app
        data:
          title: "💧 Factură nouă APA Brasov"
          message: >
            Factură {{ state_attr('sensor.apa_brasov_ultima_factura', 'serie_nr') }}
            în valoare de {{ states('sensor.apa_brasov_ultima_factura') }} RON.
            Scadență: {{ state_attr('sensor.apa_brasov_ultima_factura', 'data_scadenta') }}
```

### Reminder autocitire (în a 15-a zi a lunii)
```yaml
automation:
  - alias: "APA Brasov - Reminder autocitire"
    trigger:
      - platform: time
        at: "09:00:00"
    condition:
      - condition: template
        value_template: "{{ now().day == 15 }}"
    action:
      - service: notify.mobile_app
        data:
          title: "💧 Autocitire apometru"
          message: >
            Nu uita să transmiți indexul apometrului!
            Index actual: {{ states('sensor.apa_brasov_index_apometru_curent') }} m³
```

---

*Documentație generată pentru integrarea [APA Brasov](https://github.com/dramuletz/apa_brasov) de [@dramuletz](https://github.com/dramuletz)*

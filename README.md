# 💧 APA Brasov — Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub release](https://img.shields.io/github/release/USERNAME/apa_brasov.svg)](https://github.com/USERNAME/apa_brasov/releases)

Integrare custom pentru portalul **[myaccount.apabrasov.ro](https://myaccount.apabrasov.ro)** care aduce datele contului tău de apă direct în Home Assistant.

---

## 📦 Instalare prin HACS (recomandat)

1. Deschide **HACS** în Home Assistant
2. Mergi la **Integrări** → butonul **⋮** (trei puncte) → **Custom repositories**
3. Adaugă URL-ul: `https://github.com/USERNAME/apa_brasov`
4. Categoria: **Integration**
5. Click **Add** → caută **APA Brasov** → **Download**
6. Repornește Home Assistant
7. Mergi la **Setări → Dispozitive și Servicii → + Adaugă integrare** → caută **APA Brasov**
8. Introdu email-ul și parola de pe portal

---

## 🔧 Instalare manuală

1. Descarcă ultima versiune de pe [Releases](https://github.com/USERNAME/apa_brasov/releases)
2. Copiază folderul `custom_components/apa_brasov/` în `config/custom_components/`
3. Repornește Home Assistant
4. Adaugă integrarea din UI

---

## 📊 Entități disponibile

| Entitate | Descriere |
|---|---|
| `sensor.apa_brasov_total_de_plata` | Soldul contului (RON) |
| `sensor.apa_brasov_index_apometru_curent` | Index apometru curent (m³) |
| `sensor.apa_brasov_consum_ultima_perioada` | Consum față de citirea anterioară (m³) |
| `sensor.apa_brasov_ultima_factura` | Valoarea ultimei facturi (RON) + detalii în atribute |
| `sensor.apa_brasov_arhiva_plati` | Lista completă a plăților în atribute |
| `sensor.apa_brasov_date_utilizator` | Cod client, nr contract, adresă, cod autocitire |
| `sensor.apa_brasov_ultima_actualizare` | Timestamp ultima sincronizare |
| `number.apa_brasov_autocitire_index_apometru` | Câmp pentru transmiterea indexului |

---

## 🗺️ Dashboard Lovelace

În folderul `lovelace_dashboard.yaml` găsești un card gata de import cu grafice pentru plăți și evoluție consum.

Graficele folosesc [ApexCharts Card](https://github.com/RomRider/apexcharts-card) (instalabil din HACS → Frontend).

---

## ⚙️ Configurare

Autentificarea se face cu **email** și **parolă** de pe [myaccount.apabrasov.ro](https://myaccount.apabrasov.ro). Nu sunt necesare alte date.

Datele se actualizează **la fiecare 6 ore**.

> **Autocitirea indexului** este acceptată de portal doar în intervalul **15–21 ale lunii**.

---

## 🐛 Depanare

Activează logging detaliat în `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.apa_brasov: debug
```

---

## 📄 Licență

MIT License — vezi [LICENSE](LICENSE)

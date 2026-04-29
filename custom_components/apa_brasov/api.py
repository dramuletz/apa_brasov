"""Client API pentru portalul APA Brasov (myaccount.apabrasov.ro).

Flux confirmat prin debug extensiv:
  1. GET  /crosweb/auth/doli  -> JSESSIONID + CWID2
  2. POST /crosweb/auth/doli  -> 303 cu Location gol, dar seteaza uid + t in cookies
  3. GET  /crosweb/myaccount/servicii_online  -> dashboard, contine crosweb.contextID si p_loccons.id
  4. Subpaginile se acceseaza cu GET la URL + ?p_loccons.id=<id>
     SAU prin POST cu crosweb.contextID + trigger (ambele merg)

Structura tabel facturi confirmata:
  Cod factura | Serie/Nr | Data | Scadenta | Valoare lei | TVA | ...
  ex: 23658653 | CAB26 187817 | 21.04.2026 | 06.05.2026 | 187,33 | 18,56

Structura index confirmata:
  Cod autocitire | Data citire | Index citit | Cadran | Tip citire
  ex: 133668 | 08.04.2026 | 226 | AR | Citire

Structura contract confirmata:
  Cod client | Numar contract | Data contract | ...
  ex: P561/238 | C5557 | 17.09.2018 | ...

Structura consum confirmata - tabel lunar pe ani:
  an | 01 | 02 | ... | 12 | Total
  ex: 2025 | 10 | 10 | 13 | ... | 124
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

import requests
from bs4 import BeautifulSoup

from .const import (
    BASE_URL,
    CONSUM_URL,
    CONTRACT_URL,
    DASHBOARD_URL,
    EVPLATI_URL,
    FACTURI_URL,
    INDEX_URL,
    LOGIN_URL,
)

_LOGGER = logging.getLogger(__name__)


class ApaBrasovAuthError(Exception):
    """Eroare autentificare."""


class ApaBrasovAPIError(Exception):
    """Eroare generala API."""


class ApaBrasovAPI:
    """Client pentru portalul myaccount.apabrasov.ro."""

    def __init__(self, username: str, password: str) -> None:
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ro-RO,ro;q=0.9,en;q=0.8",
        })
        self._logged_in = False
        self._loccons_id = ""   # p_loccons.id — ID-ul locului de consum
        self._context_id = ""   # crosweb.contextID

    # ------------------------------------------------------------------
    # Autentificare
    # ------------------------------------------------------------------

    def login(self) -> bool:
        """Autentificare in portalul CROSWeb APA Brasov."""
        # Pasul 1: GET pentru JSESSIONID + CWID2
        try:
            r_get = self.session.get(
                LOGIN_URL,
                params={"from": "/crosweb/myaccount/servicii_online"},
                timeout=15,
            )
            r_get.raise_for_status()
        except requests.RequestException as err:
            raise ApaBrasovAPIError(f"Nu pot accesa pagina de login: {err}") from err

        # Pasul 2: POST - serverul raspunde 303 + Location gol, seteaza uid+t
        try:
            r_post = self.session.post(
                LOGIN_URL,
                data={
                    "username": self.username,
                    "password": self.password,
                    "login": "Autentificare",
                    "rememberme": "",
                },
                timeout=15,
                allow_redirects=False,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Referer": r_get.url,
                    "Origin": BASE_URL,
                },
            )
        except requests.RequestException as err:
            raise ApaBrasovAPIError(f"Eroare POST login: {err}") from err

        if "uid" not in self.session.cookies:
            raise ApaBrasovAuthError(
                "Autentificare esuata — verifica username/parola pe myaccount.apabrasov.ro"
            )

        # Pasul 3: GET dashboard — extrage p_loccons.id si crosweb.contextID
        try:
            r_dash = self.session.get(DASHBOARD_URL, timeout=15)
            r_dash.raise_for_status()
            self._extract_session_ids(r_dash.text)
        except requests.RequestException as err:
            _LOGGER.warning("Nu pot accesa dashboard-ul: %s", err)

        self._logged_in = True
        _LOGGER.info(
            "Autentificare reusita. uid=%s loccons_id=%s context_id=%s",
            self.session.cookies.get("uid"),
            self._loccons_id,
            self._context_id,
        )
        return True

    def _extract_session_ids(self, html: str) -> None:
        """Extrage p_loccons.id si crosweb.contextID din HTML-ul dashboard-ului."""
        soup = BeautifulSoup(html, "html.parser")

        # crosweb.contextID — input hidden in form
        ctx = soup.find("input", {"name": "crosweb.contextID"})
        if ctx:
            self._context_id = ctx.get("value", "")

        # p_loccons.id — din href-urile meniului lateral
        for a in soup.find_all("a", href=True):
            m = re.search(r"p_loccons\.id=(\d+)", a["href"])
            if m:
                self._loccons_id = m.group(1)
                break

        # Daca nu am gasit in href-uri, cauta in soldBox
        if not self._loccons_id:
            sold_box = soup.find(id="soldBoxlnkTxt")
            if sold_box and sold_box.get("href"):
                m = re.search(r"p_loccons\.id=(\d+)", sold_box["href"])
                if m:
                    self._loccons_id = m.group(1)

        _LOGGER.debug("context_id=%s loccons_id=%s", self._context_id, self._loccons_id)

    def _ensure_logged_in(self) -> None:
        if not self._logged_in:
            self.login()

    def _get_page(self, url: str) -> requests.Response:
        """GET autentificat pe o pagina, cu p_loccons.id atasat."""
        params = {}
        if self._loccons_id:
            params["p_loccons.id"] = self._loccons_id
        resp = self.session.get(
            url,
            params=params,
            timeout=15,
            headers={"Referer": DASHBOARD_URL},
        )
        resp.raise_for_status()
        return resp

    # ------------------------------------------------------------------
    # Sold (din dashboard - "Total de plata per client")
    # ------------------------------------------------------------------

    def get_sold(self) -> float | None:
        """Extrage soldul din div-ul soldBoxAmount din dashboard."""
        self._ensure_logged_in()
        try:
            resp = self.session.get(DASHBOARD_URL, timeout=15)
            soup = BeautifulSoup(resp.text, "html.parser")
            # <span id="soldBoxAmount">0,00 lei</span>
            sold_span = soup.find(id="soldBoxAmount")
            if sold_span:
                text = sold_span.get_text(strip=True)
                m = re.search(r"(-?\d+[.,]\d{2})", text.replace(".", "").replace(",", "."))
                if m:
                    return float(m.group(1))
                # format romanesc: "0,00 lei" -> 0.00
                m2 = re.search(r"(-?\d+),(\d{2})", text)
                if m2:
                    return float(f"{m2.group(1)}.{m2.group(2)}")
        except Exception as err:
            _LOGGER.warning("Eroare la preluarea soldului: %s", err)
        return None

    # ------------------------------------------------------------------
    # Facturi (evidenta_online)
    # ------------------------------------------------------------------

    def get_facturi(self) -> list[dict[str, Any]]:
        """Returneaza ultimele 3 facturi.

        Structura tabel confirmata:
        Cod factura | Serie/Nr | Data | Scadenta | Valoare lei | TVA | PDF | PDF | PDF
        Skip primele 3 randuri (header dublu + randuri PDF)
        """
        self._ensure_logged_in()
        try:
            resp = self._get_page(FACTURI_URL)
        except requests.RequestException as err:
            raise ApaBrasovAPIError(f"Eroare la preluarea facturilor: {err}") from err

        soup = BeautifulSoup(resp.text, "html.parser")
        facturi = []

        # Gaseste tabelul cu facturi (are header "Cod factura")
        target_table = None
        for tbl in soup.find_all("table"):
            if "Cod factura" in tbl.get_text():
                target_table = tbl
                break

        if not target_table:
            _LOGGER.warning("Tabelul de facturi nu a fost gasit")
            return []

        rows = target_table.find_all("tr")
        # Skip header rows (cele care au th sau celule goale/PDF)
        data_rows = []
        for row in rows:
            cells = [td.get_text(strip=True) for td in row.find_all("td")]
            # Un rand valid de factura are cod numeric + serie + date
            if len(cells) >= 6 and cells[0].isdigit():
                data_rows.append(cells)

        for cells in data_rows[:3]:
            try:
                # Valoare: "187,33" -> 187.33
                valoare_str = cells[4].replace(".", "").replace(",", ".")
                valoare = float(valoare_str)
                tva_str = cells[5].replace(".", "").replace(",", ".") if len(cells) > 5 else "0"
                tva = float(tva_str) if tva_str else 0.0

                facturi.append({
                    "cod": cells[0],
                    "serie_nr": cells[1],
                    "data_emitere": cells[2],
                    "data_scadenta": cells[3],
                    "suma": valoare,
                    "tva": tva,
                })
            except (ValueError, IndexError) as err:
                _LOGGER.debug("Eroare parsare rand factura %s: %s", cells, err)

        _LOGGER.debug("Facturi gasite: %s", facturi)
        return facturi

    # ------------------------------------------------------------------
    # Index apometru (index_online)
    # ------------------------------------------------------------------

    def get_index(self) -> dict[str, Any]:
        """Returneaza indexul curent si istoricul de citiri.

        Structura tabel confirmata:
        Cod autocitire | Data citire | Index citit | Cadran | Tip citire
        ex: 133668 | 08.04.2026 | 226 | AR | Citire
        """
        self._ensure_logged_in()
        data: dict[str, Any] = {
            "cod_autocitire": None,
            "index_curent": None,
            "data_citire_curenta": None,
            "index_anterior": None,
            "data_citire_anterioara": None,
            "consum_mc": None,
        }

        try:
            resp = self._get_page(INDEX_URL)
        except requests.RequestException as err:
            _LOGGER.warning("Eroare la preluarea indexului: %s", err)
            return data

        soup = BeautifulSoup(resp.text, "html.parser")

        # Extrage cod autocitire (apare singur inainte de tabel)
        text = soup.get_text()
        cod_match = re.search(r"Cod autocitire\s*\n\s*(\d+)", text)
        if cod_match:
            data["cod_autocitire"] = cod_match.group(1)

        # Gaseste tabelul cu "Istoric citiri"
        target_table = None
        for tbl in soup.find_all("table"):
            if "Index citit" in tbl.get_text() or "Data citire" in tbl.get_text():
                target_table = tbl
                break

        if not target_table:
            _LOGGER.warning("Tabelul de index nu a fost gasit")
            return data

        rows = target_table.find_all("tr")
        citiri = []
        for row in rows:
            cells = [td.get_text(strip=True) for td in row.find_all("td")]
            # Rand valid: data in format dd.mm.yyyy, index numeric
            if len(cells) >= 3 and re.match(r"\d{2}\.\d{2}\.\d{4}", cells[0]):
                try:
                    citiri.append({
                        "data": cells[0],
                        "index": int(cells[1]),
                        "cadran": cells[2] if len(cells) > 2 else "",
                    })
                except (ValueError, IndexError):
                    pass

        if citiri:
            data["index_curent"] = citiri[0]["index"]
            data["data_citire_curenta"] = citiri[0]["data"]
            if len(citiri) > 1:
                data["index_anterior"] = citiri[1]["index"]
                data["data_citire_anterioara"] = citiri[1]["data"]
                data["consum_mc"] = citiri[0]["index"] - citiri[1]["index"]

        # Extrage cod autocitire daca nu l-am gasit inca
        if not data["cod_autocitire"]:
            for row in rows:
                cells = [td.get_text(strip=True) for td in row.find_all("td")]
                if cells and cells[0].isdigit() and len(cells[0]) > 4:
                    data["cod_autocitire"] = cells[0]
                    break

        _LOGGER.debug("Index data: %s", data)
        return data

    # ------------------------------------------------------------------
    # Consum lunar (evolcons_online)
    # ------------------------------------------------------------------

    def get_consum_lunar(self) -> dict[str, Any]:
        """Returneaza consumul lunii curente si al anului curent.

        Structura tabel confirmata:
        an | 01 | 02 | 03 | 04 | 05 | 06 | 07 | 08 | 09 | 10 | 11 | 12 | Total
        ex: 2026 | 13 | 12 | 12 | 3 | | | | | | | | | 40
        """
        self._ensure_logged_in()
        data: dict[str, Any] = {
            "consum_luna_curenta": None,
            "consum_an_curent": None,
            "contract_nr": None,
            "adresa_consum": None,
        }

        try:
            resp = self._get_page(CONSUM_URL)
        except requests.RequestException as err:
            _LOGGER.warning("Eroare la preluarea consumului: %s", err)
            return data

        soup = BeautifulSoup(resp.text, "html.parser")
        text = soup.get_text(separator="\n")

        # Extrage nr contract si adresa
        contract_match = re.search(r"Contract\s*\n\s*(C\d+[^\n]*)", text)
        if contract_match:
            data["contract_nr"] = contract_match.group(1).strip()

        adresa_match = re.search(r"Adresa contract\s*\n\s*([^\n]+)", text)
        if adresa_match:
            data["adresa_consum"] = adresa_match.group(1).strip()

        # Gaseste tabelul cu evolutia consumului
        target_table = None
        for tbl in soup.find_all("table"):
            tbl_text = tbl.get_text()
            if "an" in tbl_text and any(str(y) in tbl_text for y in [2024, 2025, 2026]):
                target_table = tbl
                break

        if not target_table:
            _LOGGER.warning("Tabelul de consum nu a fost gasit")
            return data

        current_year = datetime.now().year
        current_month = datetime.now().month
        luni = ["01","02","03","04","05","06","07","08","09","10","11","12"]

        arhiva: dict[str, Any] = {}
        rows = target_table.find_all("tr")
        for row in rows:
            cells = [td.get_text(strip=True) for td in row.find_all("td")]
            if not cells or not cells[0].isdigit() or len(cells[0]) != 4:
                continue
            an = cells[0]
            an_data: dict[str, int] = {}
            for i, luna in enumerate(luni):
                idx = i + 1
                if idx < len(cells) and cells[idx].strip().isdigit():
                    an_data[luna] = int(cells[idx].strip())
            if an_data:
                arhiva[an] = an_data

            if an == str(current_year):
                try:
                    total_str = cells[-1].strip()
                    if total_str.isdigit():
                        data["consum_an_curent"] = int(total_str)
                    if len(cells) > current_month:
                        luna_val = cells[current_month].strip()
                        if luna_val.isdigit():
                            data["consum_luna_curenta"] = int(luna_val)
                        elif current_month > 1:
                            for m in range(current_month - 1, 0, -1):
                                if len(cells) > m and cells[m].strip().isdigit():
                                    data["consum_luna_curenta"] = int(cells[m].strip())
                                    break
                except (ValueError, IndexError) as err:
                    _LOGGER.debug("Eroare parsare consum an curent: %s", err)

        data["arhiva_consum"] = arhiva
        _LOGGER.debug("Consum data: %s", data)
        return data

    # ------------------------------------------------------------------
    # Contract (info_cntr)
    # ------------------------------------------------------------------

    def get_contract(self) -> dict[str, Any]:
        """Returneaza informatiile contractului.

        Structura confirmata:
        Cod client: P561/238
        Numar contract: C5557
        Data contract: 17.09.2018
        Data valabilitatii: nedeterminat
        Ultimul tip serviciu: Apa rece contorizata HARMAN POPULATIE
        In reziliere: Nu
        Adresa corespondenta: Strada BRASOVULUI, nr 36, ap 1, loc HARMAN, jud BRASOV
        """
        self._ensure_logged_in()
        data: dict[str, Any] = {
            "cod_client": None,
            "nr_contract": None,
            "data_contract": None,
            "valabilitate": None,
            "tip_serviciu": None,
            "in_reziliere": None,
            "adresa": None,
            "cod_autocitire": None,
        }

        try:
            resp = self._get_page(CONTRACT_URL)
        except requests.RequestException as err:
            _LOGGER.warning("Eroare la preluarea contractului: %s", err)
            return data

        soup = BeautifulSoup(resp.text, "html.parser")

        # Gaseste tabelul cu info contract
        target_table = None
        for tbl in soup.find_all("table"):
            if "Cod client" in tbl.get_text():
                target_table = tbl
                break

        # Structura confirmata prin debug:
        # Tabel 1 (mare, nested) - skip
        # Tabel 2: rand 0 = headers, rand 1 = valori contract
        # Tabel 3: rand 0 = "Cod autocitire"/"Adresa", rand 1 = valori
        all_tables = soup.find_all("table")
        for tbl in all_tables:
            rows = tbl.find_all("tr")
            if len(rows) < 2:
                continue
            headers = [td.get_text(strip=True) for td in rows[0].find_all(["th","td"])]
            values  = [td.get_text(strip=True) for td in rows[1].find_all(["th","td"])]
            if not headers or not values:
                continue
            mapping = dict(zip(headers, values))
            if "Cod client" in mapping:
                data["cod_client"]   = mapping.get("Cod client")
                data["nr_contract"]  = mapping.get("Numar contract")
                data["data_contract"]= mapping.get("Data contract")
                data["valabilitate"] = mapping.get("Data valabilitatii")
                data["tip_serviciu"] = mapping.get("Ultimul tip serviciu activ si validat")
                data["in_reziliere"] = mapping.get("În reziliere")
                data["adresa"]       = mapping.get("Adresa corespondenta")
            if "Cod autocitire" in mapping:
                data["cod_autocitire"] = mapping.get("Cod autocitire")

        _LOGGER.debug("Contract data: %s", data)
        return data

    # ------------------------------------------------------------------
    # Autocitire index
    # ------------------------------------------------------------------

    def submit_autocitire(self, index_value: float) -> bool:
        """Trimite autocitirea indexului catre portal."""
        self._ensure_logged_in()
        try:
            resp = self._get_page(INDEX_URL)
            soup = BeautifulSoup(resp.text, "html.parser")

            # Verifica daca suntem in perioada de autocitire (15-21 ale lunii)
            text = soup.get_text()
            if "numai in intervalul 15 - 21" in text:
                _LOGGER.warning(
                    "Autocitirea nu este posibila acum. "
                    "Portalul accepta indexul doar intre zilele 15-21 ale lunii."
                )
                return False

            # Gaseste form-ul de autocitire
            ctx = soup.find("input", {"name": "crosweb.contextID"})
            ctx_val = ctx["value"] if ctx else self._context_id

            # Gaseste campul de index si trigger-ul
            idx_input = soup.find("input", {"name": re.compile(r"index|citire", re.I)})
            trigger_input = soup.find("input", {"type": "submit"})

            payload: dict[str, Any] = {
                "crosweb.contextID": ctx_val,
                "index": str(int(index_value)),
            }
            if self._loccons_id:
                payload["p_loccons.id"] = self._loccons_id
            if trigger_input:
                payload[trigger_input.get("name", "submit")] = trigger_input.get("value", "Salvează")

            post_resp = self.session.post(
                INDEX_URL,
                data=payload,
                timeout=15,
                allow_redirects=True,
                headers={"Referer": resp.url, "Origin": BASE_URL},
            )
            post_resp.raise_for_status()

            resp_text = post_resp.text.lower()
            if any(kw in resp_text for kw in ["succes", "inregistrat", "salvat", "confirmat", "multumim"]):
                _LOGGER.info("Autocitire trimisa cu succes: %s m3", index_value)
                return True

            _LOGGER.warning("Raspuns neclar dupa autocitire (status %s)", post_resp.status_code)
            return False

        except requests.RequestException as err:
            raise ApaBrasovAPIError(f"Eroare la trimiterea autocitiri: {err}") from err

    # ------------------------------------------------------------------
    # Fetch complet
    # ------------------------------------------------------------------

    def fetch_all_data(self) -> dict[str, Any]:
        """Preia toate datele disponibile de pe portal."""
        if not self._logged_in:
            self.login()

        result: dict[str, Any] = {}

        try:
            result["sold"] = self.get_sold()
        except Exception as err:
            _LOGGER.error("Eroare sold: %s", err)
            result["sold"] = None

        try:
            result["facturi"] = self.get_facturi()
        except Exception as err:
            _LOGGER.error("Eroare facturi: %s", err)
            result["facturi"] = []

        try:
            result.update(self.get_index())
        except Exception as err:
            _LOGGER.error("Eroare index: %s", err)

        try:
            result.update(self.get_consum_lunar())
        except Exception as err:
            _LOGGER.error("Eroare consum: %s", err)

        try:
            result.update(self.get_contract())
        except Exception as err:
            _LOGGER.error("Eroare contract: %s", err)

        try:
            result.update(self.get_arhiva_plati())
        except Exception as err:
            _LOGGER.error("Eroare arhiva plati: %s", err)

        result["last_update"] = datetime.now().isoformat()
        _LOGGER.debug("Fetch complet: %s", result)
        return result


    # ------------------------------------------------------------------
    # Arhiva plati (evplati_online)
    # ------------------------------------------------------------------

    def get_arhiva_plati(self) -> dict[str, Any]:
        """Returneaza istoricul platilor.

        Structura confirmata:
        Data inregistrarii platii | Suma achitata | Serie/Nr | Note
        ex: 08.02.2024 | 165,00 | OP 1 | Ordin de plata
        """
        self._ensure_logged_in()
        data: dict[str, Any] = {
            "arhiva_plati": [],
            "total_plati": None,
        }

        try:
            resp = self._get_page(EVPLATI_URL)
        except requests.RequestException as err:
            _LOGGER.warning("Eroare la preluarea platilor: %s", err)
            return data

        soup = BeautifulSoup(resp.text, "html.parser")

        # Gaseste tabelul cu "Facturi incasate"
        target_table = None
        for tbl in soup.find_all("table"):
            if "Suma achitată" in tbl.get_text() or "Suma achitata" in tbl.get_text():
                target_table = tbl
                break

        if not target_table:
            return data

        plati = []
        total = 0.0
        rows = target_table.find_all("tr")
        for row in rows:
            cells = [td.get_text(strip=True) for td in row.find_all("td")]
            # Rand valid: data dd.mm.yyyy + suma
            if len(cells) >= 3 and re.match(r"\d{2}\.\d{2}\.\d{4}", cells[0]):
                try:
                    suma = float(cells[1].replace(".", "").replace(",", "."))
                    plati.append({
                        "data": cells[0],
                        "suma": suma,
                        "serie": cells[2] if len(cells) > 2 else "",
                        "note": cells[3] if len(cells) > 3 else "",
                    })
                    total += suma
                except (ValueError, IndexError):
                    pass

        data["arhiva_plati"] = plati
        data["total_plati"] = round(total, 2) if plati else None
        _LOGGER.debug("Arhiva plati: %d inregistrari, total=%.2f", len(plati), total or 0)
        return data

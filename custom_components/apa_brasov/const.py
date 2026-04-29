"""Constante pentru integrarea APA Brasov."""

DOMAIN = "apa_brasov"
BASE_URL = "https://myaccount.apabrasov.ro"
CROSWEB = f"{BASE_URL}/crosweb"

LOGIN_URL       = f"{CROSWEB}/auth/doli"
DASHBOARD_URL   = f"{CROSWEB}/myaccount/servicii_online"

# URL-uri reale confirmate prin debug (necesita p_loccons.id ca param)
FACTURI_URL     = f"{CROSWEB}/myaccount/evidenta_online"
EVPLATI_URL     = f"{CROSWEB}/myaccount/evplati_online"
INDEX_URL       = f"{CROSWEB}/myaccount/index_online"
CONSUM_URL      = f"{CROSWEB}/myaccount/evolcons_online"
CONTRACT_URL    = f"{CROSWEB}/myaccount/info_cntr"

# Intervalul de actualizare (ore)
SCAN_INTERVAL = 6

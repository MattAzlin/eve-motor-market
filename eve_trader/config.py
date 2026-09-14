"""Configuration, constants and persisted user settings."""
import json
import os

# ORDNERNAME FUER DIE NUTZERDATEN.
# BEWUSST EIN EIGENES WORT und nicht `APP_NAME` aus eve_trader/__init__.py,
# obwohl beide gerade gleich lauten: der Anzeigename darf sich jederzeit
# wieder aendern, der Datenordner NICHT einfach mit. Waeren sie gekoppelt,
# wuerde die naechste Umbenennung des Programms unbemerkt einen weiteren
# Umzug ausloesen - und jeder Umzug ist ein Risiko fuer die Daten.
DATENORDNER_NAME = "EVE Motor Market"

# Der Ordner hiess frueher so (alter Projektname). app_data_dir() benennt
# ihn EINMAL um. Dieser Eintrag darf NIE geloescht werden: sonst findet das
# Programm bei jedem, der noch nicht umgestiegen ist, seine Daten nicht mehr
# und startet scheinbar leer.
_ALTER_DATENORDNER_NAME = "EveTradeLedger"

# ---- Distribution ------------------------------------------------------------
# Paste YOUR Client-ID between the quotes to share the program with others.
# With it set, anyone who runs the app skips setup entirely and only logs in
# their own character. The Client-ID is NOT a secret (PKCE flow), so embedding
# it here is safe and intended.
EMBEDDED_CLIENT_ID = "6a34624f4e954d6e9f4e9c23aed3ff52"

# GitHub-Repository fuer die PROGRAMM-Update-Pruefung (Auftrag F4).
# Form: "KONTO/REPO". Der Kontoname darf kein Leerzeichen enthalten -
# aus "Peanut Motor" wird deshalb "PeanutMotor".
# Umbenennen ist spaeter unkritisch: GitHub leitet alte Adressen weiter,
# und geaendert werden muss nur diese eine Zeile.
GITHUB_REPO = "PeanutMotor/eve-motor-market"
# COMMUNITY-SERVER (Nutzer, Sitzung 17) - EINE Stelle; der Knopf in der
# Seitenleiste oeffnet ihn im Browser. Das Werkzeug verbindet sich NICHT
# selbst dorthin (deshalb in aa293 bei den Ausnahmen).
DISCORD_URL = "https://discord.gg/Atuqe6c2Rj"

# ---- EVE SSO / ESI endpoints ------------------------------------------------
SSO_AUTHORIZE = "https://login.eveonline.com/v2/oauth/authorize/"
SSO_TOKEN = "https://login.eveonline.com/v2/oauth/token"
ESI_BASE = "https://esi.evetech.net/latest"

# Market data
FORGE_REGION = 10000002          # The Forge
JITA_STATION = 60003760          # Jita IV - Moon 4 - Caldari Navy Assembly Plant

# Core access rights – these are always requested and known to work.
DEFAULT_SCOPES = [
    "publicData",
    "esi-wallet.read_character_wallet.v1",
    "esi-markets.read_character_orders.v1",
]
# Optional, only added when the user enables inventory import.
ASSETS_SCOPE = "esi-assets.read_assets.v1"
# Optional, only added when the user enables player-structure markets.
# EINE QUELLE FUER DIESEN EINEN SCOPE (Sitzung 19): die Struktur-Suche muss
# pruefen koennen, ob ein Charakter ihn WIRKLICH erteilt hat - sonst kann sie
# ein 403 nicht von "kein Andockrecht" unterscheiden. Als Positionsindex in
# STRUCTURE_SCOPES waere das still falsch, sobald jemand die Liste umsortiert.
STRUCTURE_READ_SCOPE = "esi-universe.read_structures.v1"
STRUCTURE_SCOPES = ["esi-markets.structure_markets.v1", STRUCTURE_READ_SCOPE]
# Optional, only added when the user enables opening items in the game client.
UI_SCOPE = "esi-ui.open_window.v1"
# Optional, only added when fees are derived from skills (auto-read levels+standings).
SKILL_SCOPES = ["esi-skills.read_skills.v1", "esi-characters.read_standings.v1",
                "esi-industry.read_character_jobs.v1",
                "esi-characters.read_blueprints.v1"]
# Optional, only added when the user enables implant-based time-bonus detection
# (Zainou 'Beancounter' Industry BX-80X etc.).
IMPLANT_SCOPE = "esi-clones.read_implants.v1"

# ============================================================================
# HARTCODIERTE CCP-SPIELWERTE: GEBÜHREN (bewusste Ausnahme von der Grundregel
# "alles aus ESI/SDE" - diese Formeln sind CCP-Server-Logik und stehen WEDER
# in der SDE NOCH sind sie per ESI abrufbar; hartcodieren ist unvermeidbar).
#
# >>> WENN CCP DIE GEBÜHREN PER PATCH ÄNDERT, NUR HIER ANPASSEN. <<<
#
# Alle anderen Stellen im Tool lesen die EFFEKTIVEN Werte aus den Settings
# (sales_tax_pct / broker_fee_pct) - die werden bei fees_from_skills=True
# laufend aus DIESEN Formeln neu berechnet (MainWindow._sync_fees_to_hub und
# MainWindow.save_settings). Wer hier ändert, muss danach prüfen:
#   1. SALES_TAX_BASE / effective_sales_tax  (Basis-%, Reduktion je
#      Accounting-Level)
#   2. BROKER_FEE_BASE / effective_broker_fee  (Basis-%, Reduktion je
#      Broker-Relations-Level, Standings-Koeffizienten, Floor/Cap)
#   3. Die aus den Formeln ABGELEITETEN Defaults unten in DEFAULT_SETTINGS
#      (sales_tax_pct, broker_fee_pct) - passiert automatisch mit, weil sie
#      hier per Funktionsaufruf berechnet werden. NICHT wieder als freie
#      Zahlen eintragen.
#   4. Verwandte CCP-Policy-Werte in DEFAULT_SETTINGS, die NICHT aus diesen
#      Formeln kommen, aber derselben Klasse angehören (bei einem Gebühren-
#      Patch mitprüfen!): structure_broker_pct (0,5 % SCC-Aufschlag + Owner-%
#      im Upwell-Markt) und bau_scc (4 % SCC-Surcharge auf Industriejobs).
#   5. Struktur-Rollen-Boni in industry.py (_STRUCT_ROLE_ME etc.) - eigene,
#      bereits dokumentierte Ausnahme, siehe OFFENE_PUNKTE.md.
#
# VERIFIKATION (nur ingame möglich): 1 Buy-Order + 1 Verkauf an einer
# NPC-Station aufgeben und die angezeigte Gebühr gegen die Formel rechnen.
# Stand: siehe OFFENE_PUNKTE.md (Ausnahme-Block).
# ============================================================================
SALES_TAX_BASE = 7.5      # % before Accounting
BROKER_FEE_BASE = 3.0     # % before Broker Relations / standings (NPC station)


def effective_sales_tax(accounting_level: int) -> float:
    """Base 7.5 %, reduced 11 % per Accounting level (3.375 % at V)."""
    lvl = max(0, min(5, int(accounting_level)))
    return round(SALES_TAX_BASE * (1 - 0.11 * lvl), 3)


def effective_broker_fee(broker_level: int, faction_standing: float = 0.0,
                         corp_standing: float = 0.0) -> float:
    """NPC station: 3 % − 0.3 %/BrokerRelations − 0.03 %/faction − 0.02 %/corp,
    floored at 1 %. Uses unmodified standings (skills like Connections don't
    count). Negative standings raise the fee (capped at 5 %)."""
    lvl = max(0, min(5, int(broker_level)))
    fee = (BROKER_FEE_BASE - 0.3 * lvl
           - 0.03 * faction_standing - 0.02 * corp_standing)
    return round(max(1.0, min(5.0, fee)), 3)


# AUSGELIEFERTE STANDARDWERTE SIND NEUTRAL (Auftrag F1, Sitzung 11).
#
# Hier standen bis Sitzung 11 die Standings des Entwicklers zum Jita-4-4-Owner
# (corp und faction je knapp 10) und dazu Accounting V und Broker Relations V -
# also die Werte eines maximal geskillten Haendlers. Beim Erststart gegen ein
# leeres Verzeichnis bekam damit JEDER fremde Spieler diese Zahlen, ohne es
# zu merken: seine Margen waren still zu optimistisch, und 9,86 / 9,40 sind
# persoenliche Zahlen, die in einer oeffentlichen Fassung nichts verloren
# haben.
#
# NUTZER-ENTSCHEID: "zuerst muss man einen charakter verlinken." Die Werte
# kommen also NICHT mehr aus einer Annahme, sondern aus den echten Skills -
# und bis dahin steht hier der ungeskillte Grundfall. Der ist bewusst
# PESSIMISTISCH (7,5 % statt 3,375 % Steuer): wer ohne Charakter rechnet,
# sieht zu schlechte Margen statt zu guter. Ein Kauf, der sich nachher als
# besser herausstellt, ist verzeihlich - andersherum nicht.
_NEUTRALE_STANDINGS = {"corp": 0.0, "faction": 0.0}

DEFAULT_SETTINGS = {
    "client_id": EMBEDDED_CLIENT_ID,   # baked-in id for distribution (optional)
    "callback_port": 8635,    # must match the callback URL you register
    "target_margin": 20.0,    # flag a position once net margin >= this
    # Effektive Arbeitswerte - werden bei fees_from_skills=True laufend aus den
    # Formeln oben überschrieben, sobald ein Charakter verlinkt und seine
    # Skills geladen sind. Defaults = Formel mit den Werten unten (KEINE
    # Skills, KEINE Standings), damit hier NIE eine freie Zahl steht, die zu
    # keiner Formel passt (alter Wert 4.5 war so ein Restwert).
    "sales_tax_pct": effective_sales_tax(0),
    "broker_fee_pct": effective_broker_fee(
        0, _NEUTRALE_STANDINGS["faction"], _NEUTRALE_STANDINGS["corp"]),
    "structure_broker_pct": 1.0,  # player Upwell market: 0.5% SCC surcharge + owner %
    # ---- fees derived from EVE skills (opt-in; NPC-station formulas) ----
    "fees_from_skills": True,      # an: sobald Skills da sind, gelten die echten
    "skill_accounting": 0,         # Accounting level 0-5 (sales tax)
    "skill_broker_relations": 0,   # Broker Relations level 0-5 (broker fee)
    # per-hub unmodified standings to the station owner (corp + faction). The
    # broker fee is computed per hub because each hub has a different owner.
    # LEER ausgeliefert - Standings sind persoenlich und kommen aus ESI.
    "hub_standings": {},
    "sell_mode": "relist",    # "relist" = Jita sell min, "instant" = Jita buy max
    "use_assets": True,       # real inventory import on by default (needs assets scope)
    # STANDARD AN (Nutzer, Sitzung 17): "player structures ... soll bitte
    # standard einstellung sein". Wirkt auf NEUE Installationen; wer den
    # Schalter schon gespeichert hat, behaelt seinen Wert.
    "use_structures": True,   # player-structure markets (needs structure scopes)
    "use_ui": True,           # opening items in the game client on by default (needs ui scope)
    "bau_me": 10,             # assumed blueprint material efficiency % (BPO research)
    "bau_te": 0,              # assumed blueprint time efficiency % (0..20)
    # ---- ME/TE je Item-Kategorie (Punkt: "wir kaufen sonst zu viel Material") ----
    # Endprodukt kommt weiterhin aus bau_me/bau_te oben (meist T2, oft 0/0 ab
    # Invention). Alles andere hat ein EIGENES Forschungslevel: T1-Komponenten/
    # -Hüllen/Fuel Blocks/Tools sind normalerweise voll ausgeforschte BPOs (10/10).
    # Reaktionen sind absichtlich NICHT dabei – die sind in EVE nie erforschbar.
    # TE-Defaults sind 20, nicht 10: ein voll erforschtes BPO hat ME 10 % UND
    # TE 20 % (das sind die jeweiligen Maxima). Die frühere 10 hier war eine
    # Altlast, die nie gewirkt hat - der Bauplan-Dialog setzte hart 20. Diese
    # Werte sind jetzt der GLOBALE STANDARD für neue Baupläne und werden vom
    # Dialog zurückgeschrieben, sobald der Nutzer die Regler dreht
    # (MainWindow._CAT_ME_TE_KEYS ist die zugehörige Attribut-Zuordnung).
    "bau_me_component": 10,   # Komponenten-Blaupausen ME %
    "bau_te_component": 20,   # Komponenten-Blaupausen TE %
    "bau_me_t1hull": 10,      # T1-Schiffshüllen (Invention-Basis) ME %
    "bau_te_t1hull": 20,      # T1-Schiffshüllen TE %
    "bau_me_fuel": 10,        # Fuel-Block-Blaupausen ME %
    "bau_te_fuel": 20,        # Fuel-Block-Blaupausen TE %
    "bau_me_tools": 10,       # Tools (R.A.M. u.Ä.) ME %
    "bau_te_tools": 20,       # Tools (R.A.M. u.Ä.) TE %
    # Invention-Einkauf: Standard AN. Es wird ohnehin nur gekauft, was FEHLT -
    # der ESI-/eingefuegte Bestand wird vorher abgezogen (s. "covered_by_stock"
    # in _add_build_materials_to_cart). Ein voller Brutto-Einkauf ist also
    # nicht moeglich.
    "bau_buy_datacores": True,    # Datacores in die Einkaufsliste
    "bau_buy_decryptors": True,   # Decryptoren in die Einkaufsliste
    "bau_buy_inv_default_applied": False,   # Marker der Einmal-Migration
    "bau_cat_me_te_reset_applied": False,   # Marker: Kategorie-ME/TE-Aufraeumung
    # Fracht: BEIDE Kostenarten zaehlen immer und werden addiert (Frachtdienst
    # nach ISK/m3 + Pauschale je eigener Fahrt). "bau_transport_mode" ist damit
    # Geschichte - der Schluessel bleibt nur fuer die Einmal-Migration stehen.
    "fees_char_id": None,                 # Charakter fuer Tax/Broker-Berechnung
    "bau_freight_in_decision": True,       # ISK/m3 auf den Kaufpreis aufschlagen
    "bau_transport_both_applied": False,   # Marker der Einmal-Migration
    "bau_rollen_vorbelegt": False,         # Marker: Rollen-Haken nachgezogen
    "bau_job_pct": 3,         # job-cost overhead % on material value
    "bau_reactions": True,    # build T2 reaction intermediates yourself
    "bau_invention": True,    # include T2 invention cost (datacores / success chance)
    "bau_struct": "raitaru",  # manufacturing structure type (role bonus: cost/time)
    "bau_me_rig": 2,          # 0=none, 1=T1, 2=T2 material-efficiency rig
    "bau_te_rig": 2,          # 0=none, 1=T1, 2=T2 time-efficiency rig (for build time)
    "bau_security": 1.0,      # rig multiplier: 1.0 high · 1.9 low · 2.1 null/WH
    "bau_location": "npc",    # manufacturing structure (structure_id) or "npc"
    "bau_system_id": 0,       # solar system of the build location (for the cost index)
    "bau_system_name": "",    # its name (display)
    "bau_mfg_index": 0.0,     # manufacturing system cost index (live from ESI)
    "bau_reaction_index": 0.0,  # reaction system cost index (live from ESI)
    "bau_role_bonus": 0.0,    # structure manufacturing job-cost role bonus % (e.g. 3)
    "bau_facility_tax": 0.25,  # facility tax % set by the structure owner
    "bau_decryptor": "Kein Decryptor",  # invention decryptor choice
    "bau_parallel_chars": 1,   # build characters working in parallel (time estimate)
    "bau_buy_surplus": 0,      # extra % of materials to buy (safety, rounded up)
    "bau_blacklist_names": [],  # exact item names to never build (paste list)
    # GANZE GRUPPEN nie bauen und nie kaufen (Nutzer, Sitzung 20).
    # Werte = die Gruppen des Materialien-Reiters, s. _MATERIAL_GRUPPEN.
    "bau_blacklist_gruppen": [],
    # Zuletzt sortierte Reihenfolge von "Meine Bauplaene" (Plan-IDs).
    # Damit stehen die Karten beim Oeffnen gleich richtig, statt sichtbar
    # umzuspringen, sobald der ESI-Fortschritt eintrifft.
    "bau_plan_sortierung": [],
    # Verdeckte Kennzahlen (Portfolio/Gewinne) - fuer Streams und
    # Screenshots. Nur die ANZEIGE, gerechnet wird unveraendert.
    "kpi_zensiert": [],
    "bau_sell_hub": 0,         # optimizer sell-hub station_id
    "bau_transport_m3": 350000,   # cargo capacity per trip for the buy-list (m3, ~1 jump freighter)
    "bau_transport_mode": "per_m3",  # "per_m3" (ISK/m3) or "per_trip" (flat/fuel per trip)
    "bau_transport_rate": 0.0,    # ISK per m3 (mode "per_m3")
    "bau_transport_trip_cost": 0.0,  # ISK flat cost per trip, e.g. fuel (mode "per_trip")
    # Frei eingebbarer Einmalbetrag je Bauplan (gekaufte BPCs, Gebuehren) -
    # geht vom Gewinn ab, nicht in die Baukosten je Stueck.
    "bau_extra_cost": 0.0,
    "bau_saved_plans": [],     # saved named build plans
    "bau_structures": [],      # player structures with rigs (Struktur-Fitting)
    "bau_activity_struct": {}, # activity -> structure id mapping
    "bau_scc": 0.04,           # SCC surcharge (CCP policy value, editable)
    "bau_build_chars": [],     # chars for manufacturing (components + end)
    "bau_reaction_chars": [],  # chars for reactions
    "bau_invention_chars": [], # chars for invention
    "bau_copy_chars": [],      # chars for blueprint copying
    "bau_component_bp": 1,     # copies of each component blueprint you own (split cap)
    "bau_reaction_bp": 1,      # copies of each reaction blueprint you own (split cap)
    "bau_char_roles": {},      # {char_id: [role keys]} for multi-char build scheduling
    "bau_char_slots": {},      # {char_id: [max_mfg, max_react]} from skills
    "bau_char_free": {},       # {char_id: [free_mfg, free_react]} from active ESI jobs
    "bau_char_skills": {},     # {char_id: {skill_id: level}} cached per build character
    "bau_character": 0,        # character whose manufacturing skills apply (0 = none)
    "bau_skills": {},          # cached manufacturing skill levels {skill_id: level}
    "bau_react_character": 0,  # character whose reaction skills apply (0 = none)
    "bau_react_skills": {},    # cached reaction skill levels {skill_id: level}
    "bau_blacklist": [],       # categories to NEVER build (always buy)
    "tx_cache_minutes": 5,    # how long imported transactions stay fresh (war 30 -
                               # neue Transaktionen sollten deutlich schneller
                               # sichtbar sein; 5 Min ist immer noch ein sinnvoller
                               # Puffer gegen zu häufige ESI-Anfragen bei jedem Klick
                               # auf "Alles aktualisieren")
    # ---- monetisation (local accounting; server validation comes later) ----
    "test_mode": True,        # unlimited Order Marks + everything unlockable (for the dev)
    "credits": 0,             # Order Marks balance
    "subs": {},               # {tab_key: unix expiry timestamp}
    "master": False,          # unlocked once via the secret master code
    "sim_slave": False,       # master flips this on to test the friend experience
    "trial_until": 0,         # unix ts a redeemed trial runs until (whole tool)
    "redeemed_codes": [],     # nonces of trial codes already used on this machine
}

# ----- Order Marks economy -------------------------------------------------
CREDIT_NAME = "Order Marks"        # bilingual DE/EN; rename here only
CREDIT_ABBR = "OM"
ISK_PER_CREDIT = 1_000_000         # 1 OM = 1,000,000 ISK  → 1000 OM = 1B ISK
SUB_DAYS = 30                      # a tab subscription lasts this many days
CORP_NAME = "Der Handelsorden"     # ISK transfers go to this in-game corp

# unlockable (paid) tabs → cost in Order Marks per SUB_DAYS


def app_data_dir() -> str:
    """Per-user writable directory for settings + database.

    UMZUG (Sitzung 11, Nutzer: "es soll ueberall EVE Motor Market heissen"):
    der Ordner hiess bis dahin "EveTradeLedger", nach dem alten Projektnamen.
    Er wird EINMAL umbenannt, sobald das Programm das erste Mal in der neuen
    Fassung startet.

    DIE WICHTIGSTE REGEL DABEI: geht der Umzug schief, wird WEITER MIT DEM
    ALTEN ORDNER gearbeitet. Ein Programm, das nach einem misslungenen Umzug
    einen frischen, leeren Ordner anlegt, sieht fuer den Nutzer so aus, als
    waeren Handelsjournal, Einstellungen und alle gespeicherten Bauplaene
    verschwunden - und er merkt es erst, wenn er nachsieht. Lieber der alte
    Name als verlorene Daten.
    """
    if os.name == "nt":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    else:
        base = os.path.join(os.path.expanduser("~"), ".local", "share")
    neu = os.path.join(base, DATENORDNER_NAME)
    alt = os.path.join(base, _ALTER_DATENORDNER_NAME)
    if not os.path.exists(neu) and os.path.isdir(alt):
        try:
            # os.rename im selben Verzeichnis: EIN Schritt, kein Kopieren.
            # Entweder der Ordner heisst danach neu, oder es hat sich nichts
            # geaendert - es kann kein halb umgezogener Zustand entstehen.
            os.rename(alt, neu)
        except Exception:
            # Nichts weiter tun: die Zeile darunter faengt diesen Fall
            # ohnehin ab (alt ist noch da, neu nicht -> alt wird
            # zurueckgegeben). Ein zweiter Rueckgabeweg hier sah nach
            # Absicherung aus, war aber wirkungslos - eine Rotprobe hat es
            # aufgedeckt: die Mutation "except: pass" aenderte nichts.
            pass
    if os.path.isdir(alt) and not os.path.isdir(neu):
        # HIER haengt die Zusage "misslungener Umzug -> alte Daten
        # weiterbenutzen". Gilt auch, wenn der neue Ordner nachtraeglich
        # von Hand geloescht wurde.
        return alt
    os.makedirs(neu, exist_ok=True)
    return neu


def db_path() -> str:
    return os.path.join(app_data_dir(), "ledger.db")


def settings_path() -> str:
    return os.path.join(app_data_dir(), "settings.json")


def load_settings() -> dict:
    path = settings_path()
    data = dict(DEFAULT_SETTINGS)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data.update(json.load(f))
        except Exception:
            # NICHT STILL UEBERGEHEN (Nutzer-Befund Sitzung 11: auf einem
            # zweiten Rechner standen ploetzlich die Vorgaben statt der
            # eigenen Werte). Vorher stand hier `pass`: eine unlesbare
            # Datei wurde ignoriert, das Programm lief mit den Vorgaben
            # weiter - und beim naechsten Speichern war die kaputte Datei
            # ueberschrieben. Damit sind Gebuehren, Hub-Standings und alle
            # Einstellungen endgueltig weg, ohne dass je etwas gesagt wurde.
            # Jetzt wird sie ZUERST beiseitegelegt; wiederherstellen kann
            # man dann von Hand, und die Oberflaeche sagt Bescheid.
            _rette_defekte_settings(path)
    return _nach_migrationen(data)


# Wohin die unlesbare Datei gerettet wurde - die Oberflaeche liest das aus
# und sagt es dem Nutzer. None, solange nichts passiert ist.
defekte_settings_kopie = None


def _rette_defekte_settings(path):
    """Unlesbare settings.json beiseitelegen statt sie zu verlieren."""
    global defekte_settings_kopie
    import time as _t
    ziel = f"{path}.defekt-{_t.strftime('%Y%m%d-%H%M%S')}"
    try:
        os.replace(path, ziel)
        defekte_settings_kopie = ziel
    except Exception:
        # Selbst das Umbenennen kann scheitern (Datei in Benutzung). Dann
        # lieber gar nichts tun: eine unlesbare Datei ist immer noch besser
        # als eine geloeschte.
        defekte_settings_kopie = path


def _nach_migrationen(data: dict) -> dict:
    # Migration: tx_cache_minutes war nie über die UI einstellbar - jeder
    # gespeicherte Wert von genau 30 ist also der alte hartkodierte Default,
    # nicht eine bewusste Nutzerwahl. Auf den neuen, kürzeren Default heben,
    # damit neue Transaktionen schneller sichtbar werden.
    if data.get("tx_cache_minutes") == 30:
        data["tx_cache_minutes"] = DEFAULT_SETTINGS["tx_cache_minutes"]
    # Migration (Nutzer-Wunsch: "in die Standardisierung aufnehmen"): die
    # beiden Invention-Einkaufshaken sind ab jetzt Standard AN. Ein frueher
    # gespeichertes False haette den neuen Default fuer immer verdeckt.
    # GENAU EINMAL nachziehen, per Marker - danach gilt wieder ausschliesslich
    # die Nutzerwahl (sonst koennte man sie nie wieder ausschalten).
    _migrated = False
    if not data.get("bau_buy_inv_default_applied"):
        data["bau_buy_datacores"] = True
        data["bau_buy_decryptors"] = True
        data["bau_buy_inv_default_applied"] = True
        _migrated = True
    # Migration: die Kategorie-ME/TE ("ANDERE BLAUPAUSEN") waren kurzzeitig
    # "letzter Reglerwert wird globaler Standard". Ein versehentlicher
    # Pfeilklick konnte damit z.B. TE 19 % zum Standard fuer ALLE kuenftigen
    # Plaene machen. Nutzer-Entscheid: Standard ist fest 10/20, Abweichungen
    # gehoeren in den EINZELNEN Bauplan (wird dort mitgespeichert). Einmalig
    # auf die Defaults zuruecksetzen, damit keine verirrten Werte kleben.
    if not data.get("bau_cat_me_te_reset_applied"):
        for _k in ("bau_me_component", "bau_te_component",
                   "bau_me_t1hull", "bau_te_t1hull",
                   "bau_me_fuel", "bau_te_fuel",
                   "bau_me_tools", "bau_te_tools"):
            data[_k] = DEFAULT_SETTINGS[_k]
        data["bau_cat_me_te_reset_applied"] = True
        _migrated = True
    # Migration: frueher galt ENTWEDER ISK/m3 ODER Pauschale/Fahrt (Dropdown).
    # Jetzt zaehlen beide. Ein liegengebliebener Wert der damals INAKTIVEN
    # Variante wuerde ab sofort ploetzlich Kosten verursachen, die der Nutzer
    # nie gewollt hat - deshalb einmalig auf 0 setzen.
    if not data.get("bau_transport_both_applied"):
        _m = data.get("bau_transport_mode")
        if _m == "per_trip":
            data["bau_transport_rate"] = 0.0
        elif _m == "per_m3":
            data["bau_transport_trip_cost"] = 0.0
        data["bau_transport_both_applied"] = True
        _migrated = True
    # ROLLEN-HAKEN FUER SCHON VERKNUEPFTE CHARAKTERE (Sitzung 19).
    # Wer seine Charaktere vor dieser Fassung verknuepft hat, hat womoeglich
    # gar keine Rollen gesetzt - dann bleiben Runplaner UND Blueprints-Tabelle
    # leer, ohne dass irgendwo steht warum. Neue Charaktere bekommen die Haken
    # jetzt beim Verknuepfen (_bau_rollen_vorbelegen); die bestehenden holt
    # diese Einmal-Migration nach.
    #
    # NUR wenn NICHTS gesetzt ist. Wer bewusst einzelne Charaktere abgewaehlt
    # hat, hat mindestens einen drin - dem wird hier nichts umgestellt.
    if not data.get("bau_rollen_vorbelegt"):
        _rollen = ("bau_build_chars", "bau_reaction_chars",
                   "bau_invention_chars", "bau_copy_chars")
        if not any(data.get(_k) for _k in _rollen):
            try:
                from . import store as _st
                _cids = [int(c["character_id"]) for c in _st.list_characters()]
            except Exception:
                _cids = []
            if _cids:
                for _k in _rollen:
                    data[_k] = list(_cids)
        data["bau_rollen_vorbelegt"] = True
        _migrated = True
    if _migrated:
        try:
            save_settings(data)   # Marker muss ueberleben, sonst Endlos-Lauf
        except Exception:
            pass
    return data


def save_settings(settings: dict) -> None:
    """Atomar speichern: erst vollständig in eine Temp-Datei im selben Ordner
    schreiben, dann per os.replace über die alte Datei schieben (atomar, auch
    unter Windows). Grund: settings.json enthält Guthaben/Subs/Trial und
    gespeicherte Baupläne - ein Absturz mitten im Schreiben (oder zwei Threads
    gleichzeitig) darf die Datei nicht halb geschrieben zurücklassen, sonst
    fällt load_settings still auf die Defaults zurück und alles ist weg."""
    # Ein noch laufendes Hintergrund-Schreiben ZUERST abwarten, sonst koennte
    # es hinterher den aelteren Stand ueber den neueren schieben.
    flush_settings()
    _schreibe_settings(json.dumps(settings, indent=2))


def _schreibe_settings(text: str) -> None:
    """Der eigentliche atomare Schreibvorgang - Text rein, Datei raus."""
    import tempfile
    fd, tmp_path = tempfile.mkstemp(prefix="settings-", suffix=".tmp",
                                    dir=app_data_dir())
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, settings_path())
    except Exception:
        # Halb geschriebene Temp-Datei nicht liegen lassen; Original bleibt
        # unangetastet gültig.
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise


# ---- Hintergrund-Schreiben ---------------------------------------------------
# NUTZER-BEFUND (Sitzung 10 + 11): "wenn ich da mehrere Sachen und Charaktere
# austauschen und anhaken will, dauert es sehr lange, teilweise friert mir das
# Tool fast ein" - nachgemessen ~3 s je Klick auf seinem Rechner.
#
# GEMESSEN (hier, an einer settings.json in seiner Groessenordnung):
#   JSON-Text bauen  ~57 ms   <- muss auf dem Oberflaechen-Faden passieren,
#                                sonst koennte sich das Dict waehrenddessen
#                                aendern ("dictionary changed size")
#   Platte + fsync    ~8 ms   <- hier auf schneller SSD ohne Virenscanner;
#                                bei ihm ist GENAU DAS der teure Teil, weil
#                                der Scanner jede frisch angelegte Temp-Datei
#                                anfasst, bevor os.replace sie umhaengt.
# Deshalb wird der teure Teil ausgelagert: der Text entsteht sofort (der Stand
# ist damit eingefroren und kann nicht mehr verlorengehen), das Schreiben
# laeuft im Hintergrund. Die Oberflaeche wartet nicht mehr auf die Platte.
_schreib_sperre = None
_schreib_offen = {"text": None}
_schreib_faden = None


def _schreib_sperre_holen():
    global _schreib_sperre
    if _schreib_sperre is None:
        import threading
        _schreib_sperre = threading.Lock()
    return _schreib_sperre


def save_settings_async(settings: dict) -> None:
    """Wie save_settings, aber die Platte wartet nicht auf die Oberflaeche.

    Der JSON-Text wird SOFORT erzeugt (Momentaufnahme - spaetere Aenderungen
    am Dict koennen ihn nicht mehr verfaelschen), geschrieben wird er von
    einem Hintergrundfaden. Laeuft schon einer, uebernimmt der einfach den
    neuesten Text - es gibt also nie eine Warteschlange veralteter Staende,
    immer nur den letzten.
    """
    import threading
    global _schreib_faden
    text = json.dumps(settings, indent=2)
    with _schreib_sperre_holen():
        _schreib_offen["text"] = text
        if _schreib_faden is not None and _schreib_faden.is_alive():
            return                      # laufender Faden nimmt den neuen Text
        _schreib_faden = threading.Thread(target=_schreib_schleife,
                                          name="settings-writer", daemon=True)
        _schreib_faden.start()


def _schreib_schleife():
    while True:
        with _schreib_sperre_holen():
            text = _schreib_offen["text"]
            _schreib_offen["text"] = None
            if text is None:
                return
        try:
            _schreibe_settings(text)
        except Exception:
            return                      # naechster Aufruf versucht es erneut


def flush_settings(timeout: float = 10.0) -> None:
    """Auf ein laufendes Hintergrund-Schreiben warten.

    Wird vor jedem synchronen Speichern und beim Schliessen des Programms
    gerufen: ein Fenster-Schliessen darf die letzte Auswahl nicht mitnehmen,
    nur weil sie noch im Hintergrund unterwegs war.
    """
    faden = _schreib_faden
    if faden is not None and faden.is_alive():
        faden.join(timeout)


def callback_url(port: int) -> str:
    return f"http://localhost:{port}/callback"

# Spenden (Nutzer-Entscheidung, Sitzung 8: Abo-Modell verworfen). Der
# Name erscheint im Spenden-Hinweis; ingame oeffnet der Spieler damit das
# Corporation-Fenster. Hier zentral aenderbar.
# Spenden-Ziel: NAME der Corporation ingame. Die ID wird zur Laufzeit ueber
# ESI aufgeloest (esi.resolve_corp_id) - so bleibt der Eintrag lesbar und
# ueberpruefbar, statt einer stillen Zahl.
DONATION_CORP = "Der Handelsorden"

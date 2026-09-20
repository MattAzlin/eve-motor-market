"""Regional / structure arbitrage: compare two trade locations and find items
that are cheaper at the source than they sell for at the target."""
import concurrent.futures as cf
from datetime import date as _date, datetime, timedelta, timezone


from . import config, esi

_UA = {"User-Agent": "MotorMarket/0.1"}

# DIE 401/403-MELDUNG ALS SCHLUESSEL, NICHT ALS WORTLAUT.
# Bis Sitzung 22 stand in main_window `if "Kein Zugriff" in str(msg)` - und
# `msg` ist der bereits UEBERSETZTE Text. Auf der englischen Oberflaeche
# heisst er "No access to the order book of ...", die Bedingung traf also
# nie zu und die Neupruefung der Struktur lief dort NIE an. Wer eine
# uebersetzte Meldung spaeter wiedererkennen will, muss ueber den Katalog
# gehen - genau das macht `ist_zugriffsfehler`.
KEIN_ZUGRIFF_SCHLUESSEL = (
    "No access to the order book of „{name}“ with the linked "
    "character (check docking/market rights or the token).")


def ist_zugriffsfehler(text):
    """Stammt diese Fehlermeldung aus dem 401/403-Fall? Sprachunabhaengig:
    verglichen wird der Textanfang VOR dem Platzhalter, in beiden
    Fassungen - englischer Schluessel und deutscher Katalogeintrag."""
    from .sprache import KATALOG
    _de = KATALOG.get("de", {}).get(KEIN_ZUGRIFF_SCHLUESSEL,
                                    KEIN_ZUGRIFF_SCHLUESSEL)
    _vorn = [s.split("{name}")[0].strip()
             for s in (KEIN_ZUGRIFF_SCHLUESSEL, _de)]
    return any(v and v in (text or "") for v in _vorn)

# Built-in NPC trade hubs: (key, label, region_id, station_id)
NPC_HUBS = [
    ("jita", "Jita (The Forge)", 10000002, 60003760),
    ("amarr", "Amarr (Domain)", 10000043, 60008494),
    ("dodixie", "Dodixie (Sinq Laison)", 10000032, 60011866),
    ("rens", "Rens (Heimatar)", 10000030, 60004588),
    ("hek", "Hek (Metropolis)", 10000042, 60005686),
]

# Station owner corp + faction per hub — these are the standings that reduce the
# broker fee at that hub (corp reduces 0.02%/pt, faction 0.03%/pt). Verified
# against EVE station ownership.
HUB_OWNERS = {
    "jita":    {"corp": "Caldari Navy",     "faction": "Caldari State"},
    "amarr":   {"corp": "Emperor Family",   "faction": "Amarr Empire"},
    "dodixie": {"corp": "Federation Navy",  "faction": "Gallente Federation"},
    "rens":    {"corp": "Brutor Tribe",     "faction": "Minmatar Republic"},
    "hek":     {"corp": "Boundless Creation", "faction": "Minmatar Republic"},
}


def hub_key_for_region(region_id: int) -> str:
    """Map a scan region back to its hub key (defaults to jita)."""
    for key, _label, rid, _sid in NPC_HUBS:
        if rid == region_id:
            return key
    return "jita"


def station_for_region(region_id: int) -> int:
    """The hub STATION for a scan region (so a scan can be limited to the actual
    trade hub, not the whole region). Defaults to Jita 4-4."""
    for _key, _label, rid, sid in NPC_HUBS:
        if rid == region_id:
            return sid
    return NPC_HUBS[0][3]


def fetch_hub_orders(region_id: int, station_id: int, progress=None) -> dict:
    """Best buy/sell + on-book qty per type at a specific NPC station.
    Fehlgeschlagene Seiten werden NICHT still weggelassen (das hieße: falsche
    sell_min/buy_max im Vergleich) - erst Retry pro Seite (esi._get_with_retry),
    dann serieller Nachversuch, sonst harter Fehler."""
    url = f"{config.ESI_BASE}/markets/{region_id}/orders/"
    first = esi._get_with_retry(url, params={"order_type": "all", "page": 1},
                                headers=_UA, timeout=40)
    pages = int(first.headers.get("X-Pages", "1"))
    agg = {}
    region_n = {}          # orders per type in the WHOLE region, all stations

    def fold(orders):
        for o in orders:
            region_n[o["type_id"]] = region_n.get(o["type_id"], 0) + 1
            if o["location_id"] != station_id:
                continue
            tid = o["type_id"]
            a = agg.setdefault(tid, {"sell_min": 0.0, "buy_max": 0.0,
                                     "sell_qty": 0, "buy_qty": 0,
                                     "sell_orders": [], "buy_ladder": []})
            if o["is_buy_order"]:
                a["buy_qty"] += o["volume_remain"]
                a["buy_max"] = max(a["buy_max"], o["price"])
                a["buy_ladder"].append((o["price"], o["volume_remain"]))
            else:
                a["sell_qty"] += o["volume_remain"]
                a["sell_min"] = o["price"] if a["sell_min"] == 0 else min(a["sell_min"], o["price"])
                a["sell_orders"].append((o["price"], o["volume_remain"]))

    fold(first.json())
    if progress:
        progress(1, pages)

    def get_page(p):
        r = esi._get_with_retry(url, params={"order_type": "all", "page": p},
                                headers=_UA, timeout=40)
        return r.json()

    failed_pages = []
    with cf.ThreadPoolExecutor(max_workers=16) as ex:
        futures = {ex.submit(get_page, p): p for p in range(2, pages + 1)}
        done = 1
        for fut in cf.as_completed(futures):
            try:
                fold(fut.result())
            except Exception:
                failed_pages.append(futures[fut])
            done += 1
            if progress:
                progress(done, pages)
    still_failed = []
    for p in sorted(failed_pages):
        try:
            fold(get_page(p))
        except Exception:
            still_failed.append(p)
    if still_failed:
        from .sprache import t as _txt
        raise RuntimeError(_txt(
            "Hub fetch incomplete: {n} of {pages} order book pages could not be "
            "loaded (e.g. page {p}) \u2013 the comparison would be distorted, "
            "please try again.").format(n=len(still_failed), pages=pages,
                                         p=still_failed[0]))
    # ESI has market history per REGION only. How many of the region's orders
    # for the item stand at this station is the evidence we have for the hub.
    for tid, a in agg.items():
        a["region_orders"] = region_n.get(tid, 0)
    return agg


def load_location_orders(loc: dict, settings, progress=None) -> dict:
    """loc is a favourite/hub dict: {kind:'hub'|'structure', ...}.
    WICHTIG: liefert für BEIDE Seiten dieselbe Form wie fetch_hub_orders -
    insbesondere sell_orders als PREISLEITER [(preis, menge), …]. Der alte
    Pfad nahm esi.fetch_structure_orders, dessen sell_orders eine ANZAHL
    (int) ist - hubs.arbitrage sortiert die Quell-Leiter und stürzte bei
    Struktur-QUELLE mit "'int' object is not iterable" ab (Nutzer-Fall
    X47L-Q -> 4-HWWF; NPC->Struktur lief nur, weil dort die NPC-Seite die
    Quelle war)."""
    if loc["kind"] == "hub":
        return fetch_hub_orders(loc["region_id"], loc["station_id"], progress)
    try:
        book = esi.fetch_structure_orders_full(
            settings["client_id"], loc["character_id"],
            loc["structure_id"], progress)
    except Exception as e:
        code = getattr(getattr(e, "response", None), "status_code", None)
        if code in (401, 403):
            from .sprache import t as _txt
            raise RuntimeError(_txt(KEIN_ZUGRIFF_SCHLUESSEL).format(
                    name=loc.get('name', loc['structure_id']))) from e
        raise
    return {tid: {"sell_min": b["sell_min"], "buy_max": b["buy_max"],
                  "sell_qty": b["sell_qty"], "buy_qty": b["buy_qty"],
                  "sell_orders": list(b["sell"]),
                  "buy_ladder": list(b["buy"])}
            for tid, b in book.items()}


def leere_zielmaerkte(source: dict, target: dict, deals: list, cap: int = 200) -> list:
    """Kandidaten fuer den Fall "am Ziel liegt NICHTS, obwohl dort gehandelt
    wird" - nach Quell-Wert sortiert, gedeckelt.

    NUTZER (Sitzung 16): "Falls der Zielhub ein Item gar nicht mehr hat, was
    passiert dann mit dem Tool? Eigentlich waere das eine wahre Goldgrube,
    ein Item was Handelsvolumen hat, aber der Markt leer ist. So etwas muss
    gefunden werden!"

    GEMESSEN, WARUM ES BISHER NICHT GEFUNDEN WURDE - `arbitrage` hat zwei
    harte Ausstiege:
      * `t = target.get(tid); if not t: continue`  -> Item am Ziel unbekannt
      * `if sell_price <= 0: continue`             -> keine Sell-Orders da
    Und `load_location_orders` baut das Ziel-Orderbuch AUS den vorhandenen
    Orders: ein Item ohne jede Order ist dort gar kein Eintrag. Genau der
    interessante Fall fiel also raus, BEVOR die Absatzpruefung begann.

    DIESE FUNKTION SUCHT NUR AUS, SIE BEWERTET NICHT. Ob am Ziel wirklich
    gehandelt wird, kann sie nicht wissen - das steht in der Markthistorie
    und wird vom Aufrufer geprueft. Sie liefert die type_ids, fuer die sich
    ein Historien-Abruf lohnt.

    RANGFOLGE nach `sell_min * min(sell_qty, 100)`: ein GROBER Stellvertreter
    fuer "wie viel Kapital koennte diese Luecke aufnehmen". Der echte Wert
    waere (Zielpreis - Quellpreis) x Menge - aber den Zielpreis gibt es ja
    gerade nicht, das ist der ganze Punkt. Die Deckelung bei 100 Stueck
    verhindert, dass ein einziger Riesenstapel billiger Ware die Liste
    belegt. Der Nutzer hat die Top 200 gewaehlt ("Scan bleibt schnell").
    """
    schon = {d.get("type_id") for d in (deals or [])}
    kandidaten = []
    for tid, s in (source or {}).items():
        if tid in schon:
            continue
        sell_min = s.get("sell_min") or 0
        if sell_min <= 0:
            continue                      # in der Quelle gar nicht kaufbar
        t = (target or {}).get(tid)
        # NUR WIRKLICH LEERE ZIELE. Liegt dort eine Sell-Order, ist es der
        # normale Fall und `arbitrage` hat ihn bereits bewertet (oder wegen
        # der Marge verworfen - das ist dann kein leerer Markt).
        if t is not None and (t.get("sell_min") or 0) > 0:
            continue
        menge = min(int(s.get("sell_qty") or 0), 100)
        kandidaten.append((sell_min * max(menge, 1), tid))
    kandidaten.sort(reverse=True)
    return [tid for _w, tid in kandidaten[:max(0, int(cap))]]


def _letzte_tage(hist, tage, heute):
    """Die Zeilen der letzten `tage` KALENDERTAGE bis `heute`.

    ESI liefert fuer einen Tag OHNE Handel keine Zeile (0 Null-Zeilen in 4 Mio
    gespeicherten). `hist[-7:]` waren deshalb die letzten 7 HANDELSTAGE - bei
    einem Item, das vor Monaten zuletzt lief, immer noch 7 Zeilen "mit Umsatz".
    Zeilen ohne brauchbares Datum (aeltere Daten): das alte zeilenweise Fenster."""
    try:
        _date.fromisoformat(str(hist[-1]["date"])[:10])
        grenze = (heute - timedelta(days=tage)).isoformat()
        return [r for r in hist if str(r["date"])[:10] >= grenze]
    except (KeyError, ValueError, TypeError, IndexError):
        return hist[-tage:]


def bewerte_leeren_markt(tid, quell_preis, hist, tax, broker, ziel_eintrag=None,
                         today=None):
    """Macht aus einem leeren Zielmarkt einen Treffer - oder None.

    ES GIBT AM ZIEL KEINEN PREIS. Das ist der ganze Punkt und zugleich das
    Problem: was dort erzielbar ist, ist eine SCHAETZUNG. Genommen wird der
    30-Tage-DURCHSCHNITT aus der Markthistorie, nicht das Hoch - eine grosse
    gruene Marge, die auf dem Bestpreis eines einzelnen Tages steht, waere
    eine Luege (Regel 3: im Zweifel die schlechtere Zahl).

    ABSATZ IN DER HISTORIE IST NICHT ABSATZ HEUTE. Ein Item mit Umsatz vor
    drei Wochen und nichts seither ist tot, keine Goldgrube. Deshalb wird
    auf TAGE MIT UMSATZ IN DEN LETZTEN 7 gefiltert, nicht auf den
    30-Tage-Schnitt.

    Rueckgabe: dict in derselben Form wie `arbitrage`, zusaetzlich
    `leerer_markt=True` und `sell_geschaetzt=True` - die Oberflaeche MUSS
    das kennzeichnen koennen, sonst sieht eine Schaetzung aus wie ein
    gerechneter Preis.
    """
    if not hist or quell_preis <= 0:
        return None
    heute = today or datetime.now(timezone.utc).date()
    letzte7 = _letzte_tage(hist, 7, heute)
    tage_mit_umsatz = sum(1 for r in letzte7 if (r.get("volume") or 0) > 0)
    if tage_mit_umsatz < 1:
        return None                       # am Ziel wird gar nicht gehandelt
    monat = _letzte_tage(hist, 30, heute)
    preise = [r.get("average") or 0 for r in monat
              if (r.get("volume") or 0) > 0 and (r.get("average") or 0) > 0]
    if not preise:
        return None
    schaetzung = sum(preise) / len(preise)
    netto = schaetzung * (1 - tax - broker)
    gewinn = netto - quell_preis
    if gewinn <= 0:
        return None
    tagesmenge = sum((r.get("volume") or 0) for r in monat) / 30.0
    t = ziel_eintrag or {}
    return {
        "type_id": tid,
        "source_sell": quell_preis,
        "target_sell": schaetzung,
        "target_buy": t.get("buy_max", 0) or 0,
        "profit_unit": gewinn,
        "margin": gewinn / quell_preis * 100.0,
        "target_demand": t.get("buy_qty", 0) or 0,
        "target_supply": 0,               # genau darum geht es: nichts da
        "sell_orders": [],
        "leerer_markt": True,
        "sell_geschaetzt": True,
        "tage_mit_umsatz_7": tage_mit_umsatz,
        # DAS ZIEL-VOLUMEN GLEICH MITGEBEN. Diese Treffer laufen NICHT durch
        # die normale Absatz-Schleife des Scans (sie standen nie in deren
        # id-Liste) - ohne diesen Wert stuende in der Spalte "Ø daily vol
        # destination" ein Strich, ausgerechnet bei den Zeilen, deren
        # ganzer Sinn der nachgewiesene Absatz ist.
        "target_vol": tagesmenge,
        "score": gewinn * max(1, min(int(tagesmenge), 10_000)),
    }


# Minimum number of units the source price is averaged over when selling via a
# sell order ("relist"). If the source book holds fewer, the average is over all
# of them.
MIN_FILL_QTY = 100
# Most units a single deal is sized to (source depth in relist mode, matched
# quantity in instant mode).
MAX_FILL_QTY = 1000


def _buy_ladder(t: dict) -> list:
    """Destination bids [(price, qty)], highest first. Data without a ladder
    (older callers) falls back to one level: the best bid over the whole buy
    quantity, which is what instant mode used to assume."""
    ladder = t.get("buy_ladder")
    if ladder:
        return sorted(ladder, reverse=True)
    if (t.get("buy_max") or 0) > 0 and (t.get("buy_qty") or 0) > 0:
        return [(t["buy_max"], t["buy_qty"])]
    return []


def _match_instant(asks: list, bids: list, tax: float, cap: int):
    """Flip as many units as still pay: walk the source asks (cheapest first)
    against the destination bids (highest first) while bid * (1 - tax) > ask.
    Returns (units, cost, gross) - gross is what the bids pay before tax."""
    units = 0
    cost = gross = 0.0
    ai = bi = 0
    ask_left = bid_left = 0
    ask_p = bid_p = 0.0
    while units < cap:
        if ask_left <= 0:
            if ai >= len(asks):
                break
            ask_p, ask_left = asks[ai]
            ai += 1
            continue
        if bid_left <= 0:
            if bi >= len(bids):
                break
            bid_p, bid_left = bids[bi]
            bi += 1
            continue
        if bid_p * (1 - tax) <= ask_p:
            break
        n = min(ask_left, bid_left, cap - units)
        units += n
        cost += n * ask_p
        gross += n * bid_p
        ask_left -= n
        bid_left -= n
    return units, cost, gross


def preselect(deals: list, volumes: dict, cap: int) -> list:
    """Cut the candidate deals to `cap` for the network-bound steps (item
    volumes, sales history at the destination), keeping the ones the table
    will actually lead with.

    The table sorts by profit per m3, which is profit / volume - freight. The
    freight is the same for every row, so the ORDER does not depend on it and
    the selection does not need to know it. Half of the slots go to the
    highest profit per m3 (volumes from the local SDE, no network); the rest
    keep the old order, profit x demand, for whoever sorts by ISK. Items whose
    volume is unknown can still get in through that second half. Without any
    volumes this is exactly the old cut."""
    if cap is None or len(deals) <= cap:
        return deals
    dense = []
    for d in deals:
        v = volumes.get(d["type_id"]) or 0
        if v > 0:
            dense.append((d["profit_unit"] / v, d))
    dense.sort(key=lambda p: p[0], reverse=True)
    chosen = [d for _x, d in dense[:cap // 2]]
    seen = {d["type_id"] for d in chosen}
    for d in sorted(deals, key=lambda r: r["score"], reverse=True):
        if len(chosen) >= cap:
            break
        if d["type_id"] not in seen:
            chosen.append(d)
            seen.add(d["type_id"])
    chosen.sort(key=lambda r: r["score"], reverse=True)
    return chosen


def arbitrage(source: dict, target: dict, settings: dict, filters: dict,
              sell_mode: str = "relist", target_is_structure: bool = False) -> list:
    """Buy at source (sell orders), sell at target. Returns ranked deals.
    In a player Upwell structure the sell-order broker fee is the structure's
    fee (0.5% SCC surcharge + owner %), not the skill-reduced NPC fee."""
    tax = settings["sales_tax_pct"] / 100.0
    if target_is_structure:
        broker = settings.get("structure_broker_pct", 1.0) / 100.0
    else:
        broker = settings["broker_fee_pct"] / 100.0
    pmin = filters.get("price_min", 0) or 0
    pmax = filters.get("price_max", 0) or 0
    min_margin = filters.get("min_margin", 0) or 0
    min_profit = filters.get("min_profit_isk", 0) or 0
    min_liq = filters.get("min_liquidity", 0) or 0
    cap = filters.get("max_items", 400)

    out = []
    for tid, s in source.items():
        # realistic source buy price: average to fill a representative quantity,
        # so a single ghost order at the very bottom can't distort the margin
        ladder = sorted(s.get("sell_orders", []))
        sell_min = s["sell_min"]
        if sell_min <= 0:
            continue
        t = target.get(tid)
        if not t:
            continue
        units = None
        if sell_mode == "instant":
            # INSTANT: trade exactly what the two order books allow. Selling
            # into the bids only pays the best price for the top order; deeper
            # units get the lower levels, so cost, proceeds and profit are all
            # for the same matched quantity (1 unit @ 120 in front of 999 @ 60
            # is a 1-unit deal, not a 1000-unit one).
            units, cost, gross = _match_instant(ladder, _buy_ladder(t), tax,
                                                MAX_FILL_QTY)
            if not units:
                continue              # not a single unit pays after tax
            buy = cost / units
        else:
            # RELIST: the source price is averaged over a representative depth.
            # The destination's buy orders say nothing about how much you buy,
            # and with none at all want was 1 - the "average" was then the
            # single cheapest order, so one ghost listing at the bottom of the
            # source book set the price (1 unit @ 10 before 5,000 @ 100 showed a
            # 1137 % margin instead of ~25 %). Hence a minimum depth.
            want = min(max(int(t.get("buy_qty", 0)), MIN_FILL_QTY), MAX_FILL_QTY)
            filled = 0
            spent = 0.0
            for price, vol in ladder:
                take = min(want - filled, vol)
                spent += take * price
                filled += take
                if filled >= want:
                    break
            buy = (spent / filled) if filled else sell_min
        if buy <= 0:
            continue
        if pmin and buy < pmin:
            continue
        if pmax and buy > pmax:
            continue
        if sell_mode == "instant":
            sell_price = gross / units    # average proceeds of the matched units
            net = sell_price * (1 - tax)
            liquidity = t["buy_qty"]
        else:
            sell_price = t["sell_min"]
            net = sell_price * (1 - tax - broker)
            liquidity = t["buy_qty"]  # demand at target
        if sell_price <= 0:
            continue
        profit = net - buy
        if profit < min_profit:
            continue
        margin = (profit / buy * 100) if buy else 0
        if margin < min_margin:
            continue
        if min_liq and liquidity < min_liq:
            continue
        # Share of the region's orders for this item that stand at the
        # destination station (None when the region count is unknown, e.g. a
        # structure). Evidence for the hub, not an estimate of its volume.
        region_n = t.get("region_orders")
        share = None
        if region_n:
            here = sum(len(x) for x in (t.get("sell_orders"), t.get("buy_ladder"))
                       if isinstance(x, (list, tuple)))
            share = min(1.0, here / region_n)
        out.append({
            "type_id": tid,
            "source_sell": buy,
            "target_sell": t["sell_min"],
            # Instant: the AVERAGE price the matched units sell at (like
            # source_sell is the average cost), so the shown price and the
            # profit beside it agree. Relist: the best bid, as before.
            "target_buy": sell_price if sell_mode == "instant" else t["buy_max"],
            "target_buy_best": t["buy_max"],
            "units": units,
            "profit_unit": profit,
            "margin": margin,
            "target_demand": t["buy_qty"],
            "target_supply": t["sell_qty"],
            "target_order_share": share,
            "sell_orders": sorted(s.get("sell_orders", [])),
            "score": profit * max(1, min(liquidity if units is None else units,
                                         10_000)),
        })
    out.sort(key=lambda r: r["score"], reverse=True)
    return out[:cap]

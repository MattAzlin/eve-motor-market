"""Buy/hold/margin- und FIFO-Berechnungen des Portfolios.

Preise kommen AUSSCHLIESSLICH aus dem ESI-Markt-Snapshot (store.get_snapshot)
- die frühere Fuzzwork-Aggregator-Abfrage (Drittanbieter, verstieß gegen die
Grundregel "nur ESI/SDE" und war die einzige zweite Preisquelle im Tool) wurde
entfernt."""
from dataclasses import dataclass


@dataclass
class Holding:
    type_id: int
    name: str
    quantity: int
    avg_buy: float
    oldest_date: str = ""
    jita_sell_min: float = 0.0
    jita_buy_max: float = 0.0
    net_unit: float = 0.0
    margin_pct: float = 0.0
    profit_total: float = 0.0
    flag: bool = False


def aggregate_holdings(transactions) -> dict:
    """FIFO lot tracking PER CHARACTER (each character's sells consume only that
    character's own buy lots), then merged per type_id. So combining several
    characters can't mismatch one character's sells against another's buys – the
    combined view is exactly the sum of the individual characters.
    Returns {type_id: {"quantity", "avg_buy", "oldest"}} for qty > 0."""
    from collections import defaultdict, deque
    lots = defaultdict(deque)  # (character_id, type_id) -> deque[[qty, price, date]]
    # buys before sells on the same day so FIFO consumes correctly
    ordered = sorted(transactions, key=lambda x: (x["date"], 0 if x["is_buy"] else 1))
    for t in ordered:
        key = (t.get("character_id"), t["type_id"])
        if t["is_buy"]:
            lots[key].append([t["quantity"], t["unit_price"], t["date"]])
        else:
            qty = t["quantity"]
            dq = lots[key]
            while qty > 0 and dq:
                lot = dq[0]
                take = min(qty, lot[0])
                lot[0] -= take
                qty -= take
                if lot[0] == 0:
                    dq.popleft()
            # leftover sells (items owned before tracking began) are ignored
    holdings = {}
    for (_char, tid), dq in lots.items():
        remaining = [l for l in dq if l[0] > 0]
        if not remaining:
            continue
        qty = sum(l[0] for l in remaining)
        val = sum(l[0] * l[1] for l in remaining)
        oldest = min(l[2] for l in remaining)[:10]
        if tid in holdings:                     # anderen Charakter mit gleichem Item mergen
            h = holdings[tid]
            newq = h["quantity"] + qty
            h["avg_buy"] = (h["avg_buy"] * h["quantity"] + val) / newq
            h["quantity"] = newq
            h["oldest"] = min(h["oldest"], oldest)
        else:
            holdings[tid] = {"quantity": qty, "avg_buy": val / qty, "oldest": oldest}
    return holdings


def realized_trades(transactions, tax: float = 0.0, broker: float = 0.0,
                    paar=None) -> list:
    """Match each sell against FIFO buy lots to get realised profit per sale.
    tax/broker are fractions (e.g. 0.045). Returns events sorted by date.
    Sells whose buy lot isn't in the data are matched only for the known part.

    `paar` = Menge von character_ids, die als EIN Haendler gelten.

    WARUM ES DAS GIBT (Sitzung 16). Der Nutzer kauft mit einem Charakter in
    Jita und verkauft mit einem anderen in 4-HWWF. FIFO je Charakter findet
    fuer diesen Verkauf KEIN Kauf-Lot - der Handel verschwindet spurlos aus
    dem Profits-Tab. In seinen echten Daten gemessen: 26,4 Mrd ISK Umsatz,
    der genau so wegfiel.

    DIE TRENNUNG JE CHARAKTER BLEIBT DIE VORGABE und ist richtig: ohne sie
    matchen Verkaeufe von Char A gegen Kaeufe von Char B, und bei "Alle
    Charaktere" blaeht sich der Umsatz auf (Entscheidung aus Sitzung 9).
    Nur wer ein Handels-PAAR ausdruecklich eingetragen hat, sagt damit: diese
    beiden sind ein Betrieb. Dann - und nur dann - teilen sie sich die Lots.
    """
    from collections import defaultdict, deque
    paar = {int(c) for c in (paar or []) if str(c).lstrip("-").isdigit()}
    lots = defaultdict(deque)
    events = []
    ordered = sorted(transactions, key=lambda x: (x["date"], 0 if x["is_buy"] else 1))
    for t in ordered:
        tid = t["type_id"]
        _cid = t.get("character_id")
        # Alle Charaktere des Paares teilen sich EINEN Schluessel.
        key = (("paar" if (_cid is not None and int(_cid) in paar) else _cid),
               tid)                            # FIFO je Charakter getrennt halten,
        if t["is_buy"]:                         # sonst matchen Verkäufe von Char A gegen
            lots[key].append([t["quantity"], t["unit_price"]])   # Käufe von Char B →
        else:                                   # falscher, aufgeblähter Umsatz bei „Alle“.
            qty = t["quantity"]
            sell = t["unit_price"]
            dq = lots[key]
            matched_qty = 0
            matched_cost = 0.0
            while qty > 0 and dq:
                lot = dq[0]
                take = min(qty, lot[0])
                matched_qty += take
                matched_cost += take * lot[1]
                lot[0] -= take
                qty -= take
                if lot[0] == 0:
                    dq.popleft()
            if matched_qty <= 0:
                continue
            buy_avg = matched_cost / matched_qty
            gross = (sell - buy_avg) * matched_qty
            net = (sell * (1 - tax - broker) - buy_avg) * matched_qty
            events.append({
                "date": t["date"][:10],
                "type_id": tid,
                "qty": matched_qty,
                "sell": sell,
                "buy": buy_avg,
                "gross": gross,
                "net": net,
                "revenue": sell * matched_qty,
            })
    return events


def realized_summary(events, days: int = 0):
    """Aggregate realised events over the last `days` (0 = all). Returns
    (totals dict, per_type list sorted by net profit)."""
    import datetime as _dt
    if days:
        cutoff = (_dt.date.today() - _dt.timedelta(days=days)).isoformat()
        events = [e for e in events if e["date"] >= cutoff]
    by_type = {}
    tot_net = tot_gross = tot_rev = 0.0
    tot_qty = 0
    for e in events:
        tot_net += e["net"]
        tot_gross += e["gross"]
        tot_rev += e["revenue"]
        tot_qty += e["qty"]
        a = by_type.setdefault(e["type_id"], {"type_id": e["type_id"], "qty": 0,
                                              "net": 0.0, "revenue": 0.0, "cost": 0.0})
        a["qty"] += e["qty"]
        a["net"] += e["net"]
        a["revenue"] += e["revenue"]
        a["cost"] += e["buy"] * e["qty"]
    rows = sorted(by_type.values(), key=lambda x: x["net"], reverse=True)
    for r in rows:
        r["margin"] = (r["net"] / r["cost"] * 100) if r["cost"] else 0.0
    totals = {"net": tot_net, "gross": tot_gross, "revenue": tot_rev,
              "qty": tot_qty, "trades": len(events)}
    return totals, rows


def _fill(ladder, qty, buy=True):
    """Walk an order ladder to fill `qty`. ladder is [(price, volume), ...]
    ascending for buying, descending for selling."""
    remaining = qty
    total = 0.0
    marginal = 0.0
    for price, vol in ladder:
        if remaining <= 0:
            break
        take = min(remaining, vol)
        total += take * price
        marginal = price
        remaining -= take
    filled = qty - remaining
    key = "cost" if buy else "revenue"
    return {key: total, "avg": (total / filled if filled else 0.0),
            "marginal": marginal, "filled": filled, "short": max(0, remaining)}


def worthwhile_fill(sell_ladder, cutoff):
    """Walk ascending sell orders and take every order whose price is still at
    or below `cutoff` (the point where the trade stops being worth it).
    Returns the cumulative worthwhile quantity, its average price and the last
    (highest still-worthwhile) price."""
    qty = 0
    cost = 0.0
    last = 0.0
    if not cutoff or cutoff <= 0:
        # Ohne gültigen Break-even-Preis wäre JEDE Order "lohnend" und die
        # ganze Leiter würde empfohlen - dann lieber ehrlich: nichts.
        return {"qty": 0, "avg": 0.0, "last": 0.0, "cost": 0.0}
    for price, vol in sell_ladder:
        if cutoff and price > cutoff:
            break
        qty += vol
        cost += price * vol
        last = price
    return {"qty": qty, "avg": (cost / qty if qty else 0.0),
            "last": last, "cost": cost}


def fill_buy(sell_ladder, qty):
    """Realistic cost to buy qty by walking ascending sell orders."""
    return _fill(sell_ladder, qty, buy=True)


def holdings_from_assets(assets: dict, transactions) -> dict:
    """Real inventory (from the assets endpoint) priced with the FIFO cost basis
    derived from transactions. assets = {type_id: quantity}.
    Items you hold but never bought on the market show avg_buy = 0 (unknown)."""
    lots = aggregate_holdings(transactions)
    holdings = {}
    for tid, qty in assets.items():
        if qty <= 0:
            continue
        lot = lots.get(tid)
        holdings[tid] = {
            "quantity": qty,
            "avg_buy": lot["avg_buy"] if lot else 0.0,
            "oldest": lot["oldest"] if lot else "",
        }
    return holdings


def evaluate(holdings: dict, names: dict, prices: dict, settings: dict) -> list:
    tax = settings["sales_tax_pct"] / 100.0
    broker = settings["broker_fee_pct"] / 100.0
    target = settings["target_margin"]
    mode = settings["sell_mode"]
    rows = []
    for tid, h in holdings.items():
        p = prices.get(tid, {})
        sell_min = p.get("sell_min", 0.0)
        buy_max = p.get("buy_max", 0.0)
        if mode == "instant":
            market = buy_max
            net = market * (1 - tax)
        else:
            market = sell_min
            net = market * (1 - tax - broker)
        avg_buy = h["avg_buy"]
        if avg_buy and avg_buy > 0:
            margin = (net - avg_buy) / avg_buy * 100.0
            profit_total = (net - avg_buy) * h["quantity"]
            flag = margin >= target
        else:
            margin = 0.0
            profit_total = 0.0
            flag = False
        rows.append(Holding(
            type_id=tid,
            name=names.get(tid, f"#{tid}"),
            quantity=h["quantity"],
            avg_buy=avg_buy,
            oldest_date=h.get("oldest", ""),
            jita_sell_min=sell_min,
            jita_buy_max=buy_max,
            net_unit=net,
            margin_pct=margin,
            profit_total=profit_total,
            flag=flag,
        ))
    rows.sort(key=lambda r: r.margin_pct, reverse=True)
    return rows

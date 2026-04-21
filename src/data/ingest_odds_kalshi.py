"""Kalshi draft-odds ingestion.

Pulls live 2026 NFL Draft event-contract prices from Kalshi and writes
them to data/features/betting_odds_2026.json in a normalized schema.

Auth — modern Kalshi API (RSA-signed requests):
  KALSHI_KEY_ID            UUID string from your Kalshi account > API Keys
  KALSHI_PRIVATE_KEY_PATH  path to the .pem private key file
  KALSHI_ENV               "prod" (default) or "demo"

Fallback auth — legacy email/password (demo only):
  KALSHI_EMAIL
  KALSHI_PASSWORD

Usage:
  python -m src.data.ingest_odds_kalshi            # refresh odds cache
  python -m src.data.ingest_odds_kalshi --dry-run  # print without writing
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

PROD_BASE = "https://api.elections.kalshi.com/trade-api/v2"
DEMO_BASE = "https://demo-api.kalshi.co/trade-api/v2"
CACHE_PATH = ROOT / "data/features/betting_odds_2026.json"

# Series/event tickers Kalshi uses for the NFL draft. Kalshi may list
# markets under several series; we search each.
DRAFT_SEARCH_TERMS = ("NFL Draft", "nfl-draft", "NFLDRAFT", "KXNFLDRAFT")


# ---------- auth ----------

def _load_private_key(path: Path):
    from cryptography.hazmat.primitives import serialization
    with path.open("rb") as fh:
        return serialization.load_pem_private_key(fh.read(), password=None)


def _sign(private_key, message: str) -> str:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    sig = private_key.sign(
        message.encode("utf-8"),
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.DIGEST_LENGTH,
        ),
        hashes.SHA256(),
    )
    return base64.b64encode(sig).decode("ascii")


class KalshiClient:
    def __init__(self) -> None:
        self.env = os.getenv("KALSHI_ENV", "prod").lower()
        self.base = DEMO_BASE if self.env == "demo" else PROD_BASE
        self.key_id = os.getenv("KALSHI_KEY_ID", "").strip()
        pk_path = os.getenv("KALSHI_PRIVATE_KEY_PATH", "").strip()
        self.pk_path = Path(pk_path) if pk_path else None
        self.email = os.getenv("KALSHI_EMAIL", "").strip()
        self.password = os.getenv("KALSHI_PASSWORD", "").strip()
        self.session = requests.Session()
        self._private_key = None
        self._token = None
        self._auth_mode = None

    def _ensure_auth(self) -> None:
        if self._auth_mode:
            return
        if self.key_id and self.pk_path and self.pk_path.exists():
            self._private_key = _load_private_key(self.pk_path)
            self._auth_mode = "rsa"
            return
        if self.email and self.password:
            r = self.session.post(
                f"{self.base}/login",
                json={"email": self.email, "password": self.password},
                timeout=15,
            )
            r.raise_for_status()
            self._token = r.json().get("token")
            if not self._token:
                raise RuntimeError("Kalshi login returned no token")
            self._auth_mode = "token"
            return
        raise RuntimeError(
            "No Kalshi credentials found. Set KALSHI_KEY_ID + "
            "KALSHI_PRIVATE_KEY_PATH, or KALSHI_EMAIL + KALSHI_PASSWORD."
        )

    def _headers(self, method: str, path: str) -> dict:
        self._ensure_auth()
        if self._auth_mode == "rsa":
            ts_ms = str(int(time.time() * 1000))
            msg = ts_ms + method.upper() + path
            return {
                "KALSHI-ACCESS-KEY": self.key_id,
                "KALSHI-ACCESS-SIGNATURE": _sign(self._private_key, msg),
                "KALSHI-ACCESS-TIMESTAMP": ts_ms,
                "accept": "application/json",
            }
        return {"Authorization": f"Bearer {self._token}", "accept": "application/json"}

    def _get(self, path: str, params: dict | None = None,
             max_retries: int = 5) -> dict:
        full = f"{self.base}{path}"
        backoff = 1.5
        for attempt in range(max_retries):
            r = self.session.get(full, headers=self._headers("GET", path),
                                 params=params, timeout=20)
            if r.status_code == 429:
                wait = backoff * (2 ** attempt)
                time.sleep(wait)
                continue
            if r.status_code >= 400:
                raise RuntimeError(f"Kalshi GET {path} failed {r.status_code}: {r.text[:200]}")
            # Gentle default spacing — Kalshi read limit ~10 req/s
            time.sleep(0.15)
            return r.json()
        raise RuntimeError(f"Kalshi GET {path} rate-limited after {max_retries} retries")

    def list_events(self, status: str | None = "open",
                    series_ticker: str | None = None) -> list[dict]:
        out: list[dict] = []
        cursor = None
        for _ in range(40):  # pagination safety
            params: dict = {"limit": 200}
            if status:
                params["status"] = status
            if series_ticker:
                params["series_ticker"] = series_ticker
            if cursor:
                params["cursor"] = cursor
            data = self._get("/events", params=params)
            out.extend(data.get("events") or [])
            cursor = data.get("cursor")
            if not cursor:
                break
        return out

    def list_series(self, category: str | None = None) -> list[dict]:
        """List all Kalshi series (lightweight — just metadata)."""
        params = {"limit": 200}
        if category:
            params["category"] = category
        data = self._get("/series", params=params)
        return data.get("series") or []

    def list_markets_for_event(self, event_ticker: str) -> list[dict]:
        out: list[dict] = []
        cursor = None
        for _ in range(20):
            params = {"event_ticker": event_ticker, "limit": 200}
            if cursor:
                params["cursor"] = cursor
            data = self._get("/markets", params=params)
            out.extend(data.get("markets") or [])
            cursor = data.get("cursor")
            if not cursor:
                break
        return out


# ---------- market parsing ----------

# Kalshi 2026 NFL draft markets use structured fields. Parser routes by event prefix:
#
#   KXNFLDRAFT1-26-<CODE>        exact pick #1             → bound_type="exact"
#   KXNFLDRAFTPICK-26-<N>-<CODE> exact pick at slot N      → bound_type="exact"
#   KXNFLDRAFTOU-26-<CODE>       "before pick N.5"         → bound_type="top_n"
#   KXNFLDRAFT{POS}-26P<N>-...   Nth at position           → bound_type="pos_rank"
#   KXNFLDRAFTTEAM-26<P>-<T>     per-team landing          → bound_type="team"
#   KXNFLDRAFTCAT-26<POS>R1-<K>  at-least-K POS in R1      → bound_type="pos_count"
#   KXNFLDRAFT1ST-26-1-<TEAM>    which team picks #1       → bound_type="team_pick1"

_PICK_TICKER_RE = re.compile(r"KXNFLDRAFTPICK-26-(\d+)-", re.IGNORECASE)
_POS_RANK_RE = re.compile(r"KXNFLDRAFT(QB|WR|OL|RB|EDGE|DB|TE|LB|DT|CB|S)-26P(\d+)-", re.IGNORECASE)
_CAT_RE = re.compile(r"KXNFLDRAFTCAT-26(\w+?)R1-(\d+)", re.IGNORECASE)
_RULES_PLAYER_RE = re.compile(r"If\s+(.+?)\s+is\s+(?:selected|the|drafted)", re.IGNORECASE)


# Kalshi emits team names as city + single-letter disambiguator for the
# NYC / LA clubs. Map these to standard NFL codes.
KALSHI_TEAM_TO_CODE = {
    "arizona": "ARI", "atlanta": "ATL", "baltimore": "BAL", "buffalo": "BUF",
    "carolina": "CAR", "chicago": "CHI", "cincinnati": "CIN", "cleveland": "CLE",
    "dallas": "DAL", "denver": "DEN", "detroit": "DET", "green bay": "GB",
    "houston": "HOU", "indianapolis": "IND", "jacksonville": "JAX",
    "kansas city": "KC", "las vegas": "LV", "los angeles c": "LAC",
    "los angeles r": "LAR", "miami": "MIA", "minnesota": "MIN",
    "new england": "NE", "new orleans": "NO", "new york g": "NYG",
    "new york j": "NYJ", "philadelphia": "PHI", "pittsburgh": "PIT",
    "san francisco": "SF", "seattle": "SEA", "tampa bay": "TB",
    "tennessee": "TEN", "washington": "WAS",
}


def _normalize_team(raw: str | None) -> str | None:
    if not isinstance(raw, str):
        return None
    return KALSHI_TEAM_TO_CODE.get(raw.strip().lower())


def _parse_float(v) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def _price_yes_prob(market: dict) -> float | None:
    """Extract YES-probability (0..1) from a Kalshi market's price fields.

    Precedence: last trade > yes midpoint > inverse NO midpoint > single-side quote.
    Returns None only if no price info at all.
    """
    last = _parse_float(market.get("last_price_dollars"))
    ya = _parse_float(market.get("yes_ask_dollars"))
    yb = _parse_float(market.get("yes_bid_dollars"))
    na = _parse_float(market.get("no_ask_dollars"))
    nb = _parse_float(market.get("no_bid_dollars"))

    # Last trade — trust only if the market has actually traded (oi or volume > 0)
    oi = _parse_float(market.get("open_interest_fp")) or 0.0
    vol = _parse_float(market.get("volume")) or 0.0
    has_liquidity = (oi > 0) or (vol > 0)

    if last is not None and has_liquidity and 0.0 < last < 1.0:
        return last
    if ya is not None and yb is not None and (ya + yb) > 0:
        return max(0.0, min(1.0, (ya + yb) / 2.0))
    if na is not None and nb is not None and (na + nb) > 0:
        return max(0.0, min(1.0, 1.0 - (na + nb) / 2.0))
    if ya is not None and 0.0 < ya < 1.0:
        return ya
    if last is not None and 0.0 < last < 1.0:
        return last
    return None


def _player_from_rules(market: dict) -> str | None:
    """For team-landing markets the Person is not in custom_strike; pull it
    from rules_primary which reads 'If <Player> is selected by <Team>...'"""
    rules = market.get("rules_primary") or ""
    m = _RULES_PLAYER_RE.search(rules)
    if m:
        return m.group(1).strip()
    return None


def _parse_market(market: dict) -> dict | None:
    """Route a Kalshi market by event_ticker, pull player + bound from structured fields."""
    event = (market.get("event_ticker") or "").upper()
    ticker = market.get("ticker") or ""
    custom = market.get("custom_strike") or {}
    if not isinstance(custom, dict):
        custom = {}

    yes_prob = _price_yes_prob(market)
    if yes_prob is None:
        return None

    base = {
        "ticker": ticker,
        "title": market.get("title"),
        "subtitle": market.get("yes_sub_title"),
        "status": market.get("status"),
        "yes_cents": yes_prob * 100.0,
        "yes_prob": yes_prob,
        "volume": _parse_float(market.get("volume")),
        "open_interest": _parse_float(market.get("open_interest_fp")),
        "close_ts": market.get("close_time") or market.get("close_ts"),
    }

    # ---- TEAM-LANDING: "Will X be drafted by TEAM?" ----
    if event.startswith("KXNFLDRAFTTEAM-26"):
        player = _player_from_rules(market)
        team_code = _normalize_team(market.get("yes_sub_title"))
        if not player or not team_code:
            return None
        return {**base, "player_raw": player, "bound_type": "team",
                "team_code": team_code, "pick_bound": None}

    # ---- TEAM-AT-PICK-1: "Will TEAM make 1st Overall Pick?" ----
    if event == "KXNFLDRAFT1ST-26-1":
        team_code = _normalize_team(market.get("yes_sub_title"))
        if not team_code:
            return None
        return {**base, "player_raw": None, "bound_type": "team_pick1",
                "team_code": team_code, "pick_bound": 1}

    # ---- CAT: "Will there be K+ <pos> drafted in R1?" ----
    if event.startswith("KXNFLDRAFTCAT-26"):
        floor_k = _parse_float(market.get("floor_strike"))
        cap_k = _parse_float(market.get("cap_strike"))
        strike_type = (market.get("strike_type") or "").lower()
        rules = (market.get("rules_primary") or "").lower()
        pos = None
        for p, label in (("QB", "quarterback"), ("WR", "wide receiver"),
                          ("RB", "running back"), ("TE", "tight end"),
                          ("OL", "offensive line"), ("OT", "offensive tackle"),
                          ("IOL", "interior offensive"), ("EDGE", "edge"),
                          ("DL", "defensive lineman"), ("DT", "defensive tackle"),
                          ("DB", "defensive back"), ("CB", "cornerback"),
                          ("S", "safety"), ("LB", "linebacker"), ("K", "kicker"),
                          ("P", "punter")):
            if label in rules:
                pos = p
                break
        if pos is None or (floor_k is None and cap_k is None):
            return None
        k = int(floor_k if floor_k is not None else cap_k)
        return {**base, "player_raw": None, "bound_type": "pos_count",
                "position": pos, "pos_count_min": k,
                "strike_type": strike_type, "pick_bound": None}

    # ---- POSITION-RANK: "Will X be the Nth <pos> drafted?" ----
    m = _POS_RANK_RE.search(event + "-")
    if m:
        pos = m.group(1).upper()
        rank = int(m.group(2))
        player = custom.get("Person") or market.get("yes_sub_title")
        if not isinstance(player, str) or not player.strip():
            return None
        player = player.strip()
        # Kalshi lists a "No Nth X Drafted" ticker as the complementary
        # option on these events; skip it — it's not a player.
        if player.lower().startswith("no ") and "drafted" in player.lower():
            return None
        return {**base, "player_raw": player, "bound_type": "pos_rank",
                "position": pos, "pos_rank": rank, "pick_bound": None}

    # ---- PICK-EXACT & OU (original handlers) ----
    player = custom.get("Person") or market.get("yes_sub_title")
    if not isinstance(player, str) or not player.strip():
        return None
    player = player.strip()

    if event.startswith("KXNFLDRAFTOU-"):
        cs = _parse_float(market.get("cap_strike"))
        strike_type = (market.get("strike_type") or "").lower()
        if cs is None:
            return None
        if strike_type == "less":
            pick_bound = int(cs - 0.5) if (cs % 1) != 0 else int(cs) - 1
        else:
            pick_bound = int(cs)
        if pick_bound < 1:
            return None
        return {**base, "player_raw": player, "bound_type": "top_n",
                "pick_bound": pick_bound}

    if event == "KXNFLDRAFT1-26":
        return {**base, "player_raw": player, "bound_type": "exact", "pick_bound": 1}

    if event.startswith("KXNFLDRAFTPICK-26-"):
        m = _PICK_TICKER_RE.search(event + "-")
        if not m:
            return None
        return {**base, "player_raw": player, "bound_type": "exact",
                "pick_bound": int(m.group(1))}

    return None


def _event_looks_like_draft(event: dict) -> bool:
    fields = [
        (event.get("title") or "").lower(),
        (event.get("sub_title") or "").lower(),
        (event.get("event_ticker") or "").lower(),
        (event.get("series_ticker") or "").lower(),
        (event.get("category") or "").lower(),
    ]
    hay = " ".join(fields)
    return any(term.lower() in hay for term in DRAFT_SEARCH_TERMS)


# ---------- player-name normalization ----------

_SUFFIX_RE = re.compile(r"\s+(jr|sr|ii|iii|iv|v)\.?$", re.IGNORECASE)
_PUNCT_RE = re.compile(r"[.,']")

# Known Kalshi name typos → canonical name in our prospects CSV.
KALSHI_NAME_ALIASES = {
    "gabe jucas": "Gabe Jacas",
}


def _normalize_name(name: str) -> str:
    s = re.sub(r"[^\w\s'\-.]", "", name).strip()
    s = re.sub(r"\s+", " ", s)
    return s


def _stripped_key(name: str) -> str:
    """Canonical key for fuzzy matching: lowercase, no punct, no Jr/Sr/III."""
    n = _normalize_name(name).lower()
    n = _SUFFIX_RE.sub("", n)
    n = _PUNCT_RE.sub("", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n


def _match_to_prospect(raw_name: str, prospect_names: list[str]) -> str | None:
    """Fuzzy-match a Kalshi market player name to our prospects CSV.
    Handles: exact, alias table, surname-only, Jr./Sr./III variants,
    punctuation variants, hyphenation, and first-initial forms."""
    n = _normalize_name(raw_name).lower()
    # Alias override for known Kalshi typos
    aliased = KALSHI_NAME_ALIASES.get(n)
    if aliased:
        low_a = {p.lower(): p for p in prospect_names}
        if aliased.lower() in low_a:
            return low_a[aliased.lower()]
    low = {p.lower(): p for p in prospect_names}
    if n in low:
        return low[n]

    # Canonical-key match (drops Jr./punctuation)
    raw_key = _stripped_key(raw_name)
    key_map: dict[str, str] = {}
    for p in prospect_names:
        key_map.setdefault(_stripped_key(p), p)
    if raw_key in key_map:
        return key_map[raw_key]

    # Substring both directions (existing behavior)
    for p_low, p_orig in low.items():
        if n in p_low or p_low in n:
            return p_orig

    # Canonical-substring
    for k, p_orig in key_map.items():
        if raw_key and (raw_key in k or k in raw_key):
            return p_orig

    # Surname-only ("Mendoza" → Fernando Mendoza if unique)
    tokens = raw_key.split()
    if len(tokens) == 1:
        surname = tokens[0]
        cands = [p_orig for k, p_orig in key_map.items()
                 if k.endswith(" " + surname)]
        if len(cands) == 1:
            return cands[0]

    # First+last hyphen/space variant: "T.J." vs "TJ", "Omar Jr." vs "Omar"
    compact = raw_key.replace(" ", "")
    for k, p_orig in key_map.items():
        if compact == k.replace(" ", ""):
            return p_orig

    return None


# ---------- main fetch ----------

def _discover_draft_series(client: KalshiClient, verbose: bool = True) -> list[str]:
    """Return a list of series_ticker strings that look like NFL-draft series.
    Uses /series (much lighter than paging all events)."""
    candidates = ["KXNFLDRAFT", "KXNFLDRAFTPICK", "NFLDRAFT"]
    tickers: list[str] = []
    try:
        series = client.list_series(category="Sports")
        for s in series:
            title = (s.get("title") or "").lower()
            tk = s.get("ticker") or ""
            if "nfl draft" in title or tk in candidates or any(
                c in tk.upper() for c in ("NFLDRAFT",)):
                tickers.append(tk)
    except Exception as exc:
        if verbose:
            print(f"[kalshi] series listing failed ({exc}); "
                  f"using hardcoded candidate tickers")
    # De-dupe while preserving order
    seen = set()
    out: list[str] = []
    for tk in tickers + candidates:
        if tk and tk not in seen:
            seen.add(tk)
            out.append(tk)
    return out


def fetch_and_cache(verbose: bool = True, dry_run: bool = False) -> dict:
    client = KalshiClient()

    # Strategy: try series-scoped queries first (lightweight, no rate-limit
    # risk). Only fall back to full event scan if series discovery returns
    # nothing usable.
    series_tickers = _discover_draft_series(client, verbose=verbose)
    if verbose:
        print(f"[kalshi] draft series candidates: {series_tickers}")

    draft_events: list[dict] = []
    for tk in series_tickers:
        try:
            evs = client.list_events(status=None, series_ticker=tk)
            if evs:
                if verbose:
                    print(f"[kalshi] series {tk}: {len(evs)} events")
                draft_events.extend(evs)
        except Exception as exc:
            if verbose:
                print(f"[kalshi] series {tk} fetch failed: {exc}")
    # De-dupe events by ticker
    seen_ev = set()
    draft_events = [e for e in draft_events
                    if e.get("event_ticker") and e["event_ticker"] not in seen_ev
                    and not seen_ev.add(e["event_ticker"])]

    if not draft_events:
        if verbose:
            print("[kalshi] no events via series; falling back to open-event scan")
        events = client.list_events(status="open")
        draft_events = [e for e in events if _event_looks_like_draft(e)]
        if verbose:
            print(f"[kalshi] {len(events)} total open events; "
                  f"{len(draft_events)} match draft")

    # Pull prospect names from the enriched CSV for matching
    import pandas as pd
    pros_path = ROOT / "data/processed/prospects_2026_enriched.csv"
    prospect_names: list[str] = []
    if pros_path.exists():
        prospect_names = (
            pd.read_csv(pros_path, usecols=["player"])["player"]
              .dropna().astype(str).tolist()
        )

    all_markets: list[dict] = []
    for ev in draft_events:
        ticker = ev.get("event_ticker")
        if not ticker:
            continue
        try:
            markets = client.list_markets_for_event(ticker)
        except Exception as exc:
            print(f"[kalshi] event {ticker} markets fetch failed: {exc}", file=sys.stderr)
            continue
        if verbose:
            print(f"[kalshi] event {ticker}: {len(markets)} markets")
        for m in markets:
            parsed = _parse_market(m)
            if not parsed:
                continue
            parsed["event_ticker"] = ticker
            parsed["event_title"] = ev.get("title")
            raw = parsed.get("player_raw")
            if raw:
                matched = _match_to_prospect(raw, prospect_names)
                parsed["player"] = matched or raw
                parsed["matched_to_prospect"] = bool(matched)
            else:
                # Player-less markets (team_pick1, pos_count) — no matching needed.
                parsed["player"] = None
                parsed["matched_to_prospect"] = False
            all_markets.append(parsed)

    out = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source": "kalshi",
        "env": client.env,
        "n_events": len(draft_events),
        "n_markets": len(all_markets),
        "markets": all_markets,
    }

    if verbose:
        from collections import Counter as _C
        matched = sum(1 for m in all_markets if m.get("matched_to_prospect"))
        by_type = _C(m.get("bound_type") for m in all_markets)
        print(f"[kalshi] parsed {len(all_markets)} draft markets; "
              f"{matched} matched to prospects")
        print(f"[kalshi] by type: {dict(by_type)}")

    if not dry_run:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(json.dumps(out, indent=2), encoding="utf-8")
        if verbose:
            print(f"[kalshi] wrote {CACHE_PATH}")
    return out


def load_cached() -> dict:
    if not CACHE_PATH.exists():
        return {"markets": [], "fetched_at": None}
    return json.loads(CACHE_PATH.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)
    try:
        fetch_and_cache(verbose=not args.quiet, dry_run=args.dry_run)
    except Exception as exc:
        print(f"[kalshi] ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

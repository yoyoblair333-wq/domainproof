# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
"""
DomainProof - "this wallet controls this website", proven by validator consensus
===============================================================================

Many contracts need to know that an address really speaks for a website: a
lender checking a business, a marketplace checking a seller, a DAO checking a
partner, a court checking that a party is who it says it is. The weak version
("the page shows my address somewhere") is easy to fake: anyone can post an
address in a comment, a forum, a review or a page they do not control.

DomainProof uses the web's standard proof of control instead: a file at a
fixed, site-controlled location that only the site's operator can publish,
carrying a one-time challenge the contract itself issued.

    1. request_challenge(domain)   -> the exact line to publish
    2. publish that line at  https://<domain>/.well-known/genlayer-proof.txt
    3. verify(domain)              -> every validator fetches the file itself;
                                      VERIFIED only if the exact line is there

Consensus anchor: no model is asked anything. Each validator fetches the file
and computes one of a fixed set of outcome codes; the leader's result is
accepted only if a validator computes EXACTLY the same code. The challenge
binds the domain, the claiming address and a contract-issued nonce, so a line
published for one address can never verify another, and an old line cannot be
replayed after a new challenge.

Proofs go stale: control of a site can change hands. A verification is valid
for PROOF_DAYS; and ANYONE may call recheck(domain, address) at any time. If
the line is gone, the proof is REVOKED on the spot. The owner can also
revoke(domain) their own proof.

For consuming contracts (views):
    is_verified(domain, address) -> bool     (VERIFIED and not expired)
    get_proof(domain, address)   -> full record
    verified_addresses(domain)   -> addresses currently verified for a domain

SDK target: GenVM v0.2.16 Python SDK. Caller errors start with [EXPECTED].
"""

from genlayer import *

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

ERR = "[EXPECTED]"

PROOF_PATH = "/.well-known/genlayer-proof.txt"
PROOF_TAG = "genlayer-domain-proof v1"
CHALLENGE_HOURS = 72            # a challenge must be verified within 3 days
PROOF_DAYS = 90                 # a verification is valid for 90 days
MAX_FILE_BYTES = 8_192          # a proof file is a few lines; anything bigger is refused
MAX_ADDRESSES_PER_DOMAIN = 16
UA = {"User-Agent": "Mozilla/5.0 (compatible; GenLayer-DomainProof/1; +https://genlayer.com)"}

# Outcome codes: the ONLY thing validators compare.
OK = "OK"
NOT_FOUND = "FILE_NOT_FOUND"          # non-2xx status or a failed fetch
WRONG_TYPE = "FILE_NOT_TEXT"          # served as HTML/JSON/etc. (e.g. a catch-all 200 page)
TOO_BIG = "FILE_TOO_BIG"
LINE_MISSING = "LINE_MISSING"         # file is there, the exact challenge line is not
OUTCOMES = (OK, NOT_FOUND, WRONG_TYPE, TOO_BIG, LINE_MISSING)

STATUS_PENDING, STATUS_VERIFIED, STATUS_REVOKED, STATUS_FAILED = "PENDING", "VERIFIED", "REVOKED", "FAILED"

_LABEL_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
_TLD_RE = re.compile(r"^[a-z][a-z0-9-]{1,62}$")
_BLOCKED_SUFFIXES = (".localhost", ".local", ".internal", ".lan", ".home", ".corp", ".test", ".invalid",
                     ".example", ".onion")


@allow_storage
@dataclass
class Proof:
    domain: str
    address: Address
    nonce: str
    status: str                # PENDING / VERIFIED / REVOKED / FAILED
    challenged_at: str
    verified_at: str           # "" until first verified
    valid_until: str           # "" unless VERIFIED
    last_checked_at: str
    last_outcome: str          # one of OUTCOMES, or "" before any check
    checks: u32


def _fail(msg: str):
    raise gl.vm.UserError(f"{ERR} {msg}")


def iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(raw: str) -> datetime:
    dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def canonical_domain(raw) -> str:
    """Lower-case ASCII host name of a public site, e.g. "shop.example.com".
    Rejects schemes, paths, ports, credentials, IP literals, single labels and
    private/reserved suffixes. www.x.com and x.com are different domains on purpose."""
    if not isinstance(raw, str):
        _fail("domain must be text")
    d = raw.strip().lower().rstrip(".")
    if not 4 <= len(d) <= 253:
        _fail("domain must be 4..253 characters")
    if any(ch in d for ch in "/:@?#% \t") or any(ord(ch) > 126 or ord(ch) < 33 for ch in d):
        _fail("give a bare domain like shop.example.com (no scheme, path, port or spaces; punycode for IDNs)")
    labels = d.split(".")
    if len(labels) < 2 or not all(_LABEL_RE.match(x) for x in labels) or not _TLD_RE.match(labels[-1]):
        _fail("not a valid public domain name")
    if all(x.isdigit() for x in labels):
        _fail("IP addresses are not domains")
    if d == "localhost" or ("." + d).endswith(_BLOCKED_SUFFIXES):
        _fail("domain must be public")
    return d


def addr_hex(raw) -> str:
    """Hex form of an address given as an Address or as a 0x-hex string."""
    if isinstance(raw, Address):
        return raw.as_hex
    if isinstance(raw, (bytes, bytearray)) and len(raw) == 20:
        return Address(bytes(raw)).as_hex
    if not isinstance(raw, str) and hasattr(raw, "as_hex"):
        raw = str(raw.as_hex)
    if not isinstance(raw, str) or not re.fullmatch(r"0x[0-9a-fA-F]{40}", raw.strip()):
        _fail("address must be 0x followed by 40 hex characters")
    return Address(raw.strip()).as_hex


def challenge_line(domain: str, address_hex: str, nonce: str) -> str:
    return f"{PROOF_TAG} domain={domain} address={address_hex.lower()} nonce={nonce}"


def make_nonce(domain: str, address_hex: str, issued_at: str, seq: int) -> str:
    """24 hex chars bound to the domain, the claimant, the issue time and a
    per-contract counter: deterministic for validators, unique per challenge."""
    return hashlib.sha256(f"{domain}|{address_hex.lower()}|{issued_at}|{seq}".encode()).hexdigest()[:24]


def _header(headers, name: str) -> str:
    if not isinstance(headers, dict):
        return ""
    for key, v in headers.items():
        if str(key).lower() == name:
            return v.decode("utf-8", "replace") if isinstance(v, (bytes, bytearray)) else str(v)
    return ""


def classify(status, headers, body, expected_line: str) -> str:
    """Deterministic outcome code for one fetch of the proof file."""
    try:
        code = int(status)
    except Exception:
        return NOT_FOUND
    if not 200 <= code < 300:
        return NOT_FOUND
    data = body or b""
    if len(data) > MAX_FILE_BYTES:
        return TOO_BIG
    ctype = _header(headers, "content-type").lower().split(";")[0].strip()
    if ctype not in ("", "text/plain", "application/octet-stream"):
        return WRONG_TYPE
    text = data.decode("utf-8", "replace") if isinstance(data, (bytes, bytearray)) else str(data)
    if text.lstrip().lower().startswith(("<!doctype", "<html")):
        return WRONG_TYPE
    for line in text.splitlines():
        if line.strip() == expected_line:
            return OK
    return LINE_MISSING


def fetch_outcome(domain: str, expected_line: str) -> str:
    """NON-DETERMINISTIC: fetch https://<domain>/.well-known/genlayer-proof.txt."""
    try:
        r = gl.nondet.web.get("https://" + domain + PROOF_PATH, headers=UA)
    except Exception:
        return NOT_FOUND
    return classify(r.status, r.headers, r.body, expected_line)


class DomainProof(gl.Contract):
    proofs: TreeMap[str, Proof]              # "<domain>|<address hex lower>" -> proof
    domain_addresses: TreeMap[str, str]      # domain -> comma-separated address hex list
    challenges_issued: u256

    def __init__(self):
        self.challenges_issued = u256(0)

    # ------------------------------------------------------------- helpers

    def _now(self) -> datetime:
        return parse_iso(gl.message_raw["datetime"])

    def _key(self, domain: str, address_hex: str) -> str:
        return domain + "|" + address_hex.lower()

    def _addresses(self, domain: str) -> list:
        raw = self.domain_addresses.get(domain, "")
        return [a for a in raw.split(",") if a]

    def _to_dict(self, p: Proof, now: datetime) -> dict:
        live = p.status == STATUS_VERIFIED and p.valid_until != "" and now <= parse_iso(p.valid_until)
        return {
            "domain": p.domain,
            "address": p.address.as_hex,
            "status": p.status,
            "verified_now": live,
            "challenge_line": challenge_line(p.domain, p.address.as_hex, p.nonce),
            "proof_url": "https://" + p.domain + PROOF_PATH,
            "challenged_at": p.challenged_at,
            "verified_at": p.verified_at,
            "valid_until": p.valid_until,
            "last_checked_at": p.last_checked_at,
            "last_outcome": p.last_outcome,
            "checks": int(p.checks),
        }

    def _check(self, p: Proof) -> str:
        """Consensus on the fetch outcome code (exact equality)."""
        expected = challenge_line(p.domain, p.address.as_hex, p.nonce)
        domain = p.domain

        def leader_fn() -> str:
            return fetch_outcome(domain, expected)

        def validator_fn(leader_res) -> bool:
            if not isinstance(leader_res, gl.vm.Return) or leader_res.calldata not in OUTCOMES:
                return False
            return leader_res.calldata == fetch_outcome(domain, expected)

        return gl.vm.run_nondet_unsafe(leader_fn, validator_fn)

    # ---------------------------------------------------------------- write

    @gl.public.write
    def request_challenge(self, domain: str) -> dict:
        """Issue (or re-issue) the line the caller must publish for `domain`.
        Re-issuing replaces the old nonce, so an old published line stops working."""
        d = canonical_domain(domain)
        me = gl.message.sender_address
        key = self._key(d, me.as_hex)
        now = self._now()
        addrs = self._addresses(d)
        if me.as_hex.lower() not in addrs and len(addrs) >= MAX_ADDRESSES_PER_DOMAIN:
            _fail(f"domain already has {MAX_ADDRESSES_PER_DOMAIN} claimants")
        seq = int(self.challenges_issued) + 1
        self.challenges_issued = u256(seq)
        nonce = make_nonce(d, me.as_hex, iso(now), seq)
        if key in self.proofs:
            p = self.proofs[key]
            p.nonce = nonce
            p.status = STATUS_PENDING
            p.challenged_at = iso(now)
            p.verified_at = ""
            p.valid_until = ""
        else:
            self.proofs[key] = Proof(domain=d, address=me, nonce=nonce, status=STATUS_PENDING,
                                     challenged_at=iso(now), verified_at="", valid_until="",
                                     last_checked_at="", last_outcome="", checks=u32(0))
            self.domain_addresses[d] = ",".join(addrs + [me.as_hex.lower()])
        return self._to_dict(self.proofs[key], now)

    @gl.public.write
    def verify(self, domain: str) -> dict:
        """The claimant asks the validators to fetch the proof file now."""
        d = canonical_domain(domain)
        me = gl.message.sender_address
        key = self._key(d, me.as_hex)
        if key not in self.proofs:
            _fail("request a challenge for this domain first")
        p = self.proofs[key]
        now = self._now()
        if p.status == STATUS_VERIFIED and p.valid_until != "" and now <= parse_iso(p.valid_until):
            _fail("already verified; use recheck() to refresh or revoke() to withdraw")
        if p.status != STATUS_PENDING:
            _fail("request a new challenge first")
        if now > parse_iso(p.challenged_at) + timedelta(hours=CHALLENGE_HOURS):
            p.status = STATUS_FAILED
            p.last_checked_at = iso(now)
            return self._to_dict(p, now)
        outcome = self._check(p)
        p.checks = u32(int(p.checks) + 1)
        p.last_checked_at = iso(now)
        p.last_outcome = outcome
        if outcome == OK:
            p.status = STATUS_VERIFIED
            p.verified_at = iso(now)
            p.valid_until = iso(now + timedelta(days=PROOF_DAYS))
        return self._to_dict(p, now)

    @gl.public.write
    def recheck(self, domain: str, address: str) -> dict:
        """ANYONE may re-fetch a verified proof. If the line is no longer
        published, the proof is revoked; if it is, the validity window restarts."""
        d = canonical_domain(domain)
        key = self._key(d, addr_hex(address))
        if key not in self.proofs:
            _fail("no proof for that domain and address")
        p = self.proofs[key]
        if p.status != STATUS_VERIFIED:
            _fail("only a verified proof can be rechecked")
        now = self._now()
        outcome = self._check(p)
        p.checks = u32(int(p.checks) + 1)
        p.last_checked_at = iso(now)
        p.last_outcome = outcome
        if outcome == OK:
            p.verified_at = iso(now)
            p.valid_until = iso(now + timedelta(days=PROOF_DAYS))
        else:
            p.status = STATUS_REVOKED
            p.valid_until = ""
        return self._to_dict(p, now)

    @gl.public.write
    def revoke(self, domain: str) -> dict:
        """The claimant withdraws their own proof."""
        d = canonical_domain(domain)
        key = self._key(d, gl.message.sender_address.as_hex)
        if key not in self.proofs:
            _fail("no proof for that domain")
        p = self.proofs[key]
        now = self._now()
        p.status = STATUS_REVOKED
        p.valid_until = ""
        p.last_checked_at = iso(now)
        return self._to_dict(p, now)

    # ---------------------------------------------------------------- views

    @gl.public.view
    def is_verified(self, domain: str, address: str) -> bool:
        """True only if `address` holds an unexpired VERIFIED proof for `domain`."""
        d = canonical_domain(domain)
        key = self._key(d, addr_hex(address))
        if key not in self.proofs:
            return False
        p = self.proofs[key]
        return p.status == STATUS_VERIFIED and p.valid_until != "" and self._now() <= parse_iso(p.valid_until)

    @gl.public.view
    def get_proof(self, domain: str, address: str) -> dict:
        d = canonical_domain(domain)
        key = self._key(d, addr_hex(address))
        if key not in self.proofs:
            _fail("no proof for that domain and address")
        return self._to_dict(self.proofs[key], self._now())

    @gl.public.view
    def verified_addresses(self, domain: str) -> list:
        d = canonical_domain(domain)
        now = self._now()
        out = []
        for a in self._addresses(d):
            p = self.proofs[self._key(d, a)]
            if p.status == STATUS_VERIFIED and p.valid_until != "" and now <= parse_iso(p.valid_until):
                out.append(p.address.as_hex)
        return out

    @gl.public.view
    def get_config(self) -> dict:
        return {"proof_path": PROOF_PATH, "proof_tag": PROOF_TAG, "challenge_hours": CHALLENGE_HOURS,
                "proof_days": PROOF_DAYS, "max_file_bytes": MAX_FILE_BYTES,
                "max_addresses_per_domain": MAX_ADDRESSES_PER_DOMAIN, "outcomes": list(OUTCOMES),
                "challenges_issued": int(self.challenges_issued)}

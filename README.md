# DomainProof: prove a wallet controls a website, by validator consensus

**One Intelligent Contract. No model calls. No oracle operator.** Every GenLayer validator fetches the proof file itself, and the contract records VERIFIED only if they all see the exact one-time line it issued.

Contracts increasingly need to know that an address really speaks for a website: a lender checking a business, a marketplace checking a seller, a court checking that a party is who it claims to be, an agent checking a counterparty before it pays. The weak check is "the page shows my address somewhere", and it is easy to fake: anyone can post an address in a review, a forum, a comment or a profile page on a site they do not control.

DomainProof uses the web's own standard for proving control of a site: a file at a fixed path under `/.well-known/` that only the site's operator can publish, carrying a challenge the contract itself issued.

```
1. request_challenge("shop.example.com")
      -> "genlayer-domain-proof v1 domain=shop.example.com address=0xabc… nonce=9f3c…"
2. publish that line at  https://shop.example.com/.well-known/genlayer-proof.txt
3. verify("shop.example.com")
      -> each validator fetches the file; VERIFIED only if the exact line is there
```

## What a consuming contract calls

```python
proofs = gl.get_contract_at(Address(DOMAIN_PROOF))
if not proofs.view().is_verified("shop.example.com", seller):
    raise gl.vm.UserError("[EXPECTED] seller has not proven control of their site")
```

| View | Returns |
|---|---|
| `is_verified(domain, address)` | `true` only for an unexpired VERIFIED proof |
| `verified_addresses(domain)` | every address currently verified for that domain |
| `get_proof(domain, address)` | the full record: status, the challenge line, proof URL, timestamps, last outcome, check count |
| `get_config()` | path, tag, windows, size cap, outcome codes, challenges issued |

## How consensus works

No model is asked anything. Each validator fetches `https://<domain>/.well-known/genlayer-proof.txt` itself and reduces what it saw to **one outcome code**:

| Code | Meaning |
|---|---|
| `OK` | 2xx, plain text, under 8 KB, and one line equals the challenge exactly (surrounding whitespace and CRLF forgiven) |
| `FILE_NOT_FOUND` | non-2xx status, or the fetch failed |
| `FILE_NOT_TEXT` | served as HTML/JSON, or an HTML body served as text. This blocks catch-all 200 pages that echo the URL or a search query back |
| `FILE_TOO_BIG` | over 8 KB: a proof file is a few lines |
| `LINE_MISSING` | the file is there, but the exact line is not |

`run_nondet_unsafe` accepts the leader's code only if a validator computes **exactly** the same code from its own fetch. A validator that sees a different file disagrees, and the transaction does not decide on a reading only the leader saw.

## Why it cannot be faked

- **The line binds the domain, the claiming address and a contract-issued nonce.** Alice's published line never verifies Bob. A line for `www.x.com` never verifies `x.com` (they are different sites on purpose).
- **An address merely mentioned on the site is not a proof.** Only the exact line at the fixed path counts.
- **Re-issuing a challenge kills the old line**, so a leaked or stale line cannot be replayed.
- **Challenges expire after 72 hours; proofs after 90 days.**
- **Anyone can `recheck(domain, address)` at any time.** If the line is gone (for example, the site changed hands), the proof is REVOKED on the spot. If it is still there, the 90-day window restarts. The owner can also `revoke(domain)`.
- **Strict input gate.** Only a bare public host name is accepted: no scheme, path, port, credentials, IP literal, single label, or private/reserved suffix (`.local`, `.internal`, `.corp`, `.test`, …).

## Live on studionet

Deployed and exercised end to end against a real site, `yoyoblair333-wq.github.io` ([its proof file](https://yoyoblair333-wq.github.io/.well-known/genlayer-proof.txt)). 10 transactions, all finalized with majority agreement:

| Step | Outcome read back from the chain |
|---|---|
| Alice publishes her challenge line on the site, then calls `verify` | **VERIFIED** (`OK`), `is_verified = true`, valid 90 days |
| Bob claims the same domain but never publishes his line | stays **PENDING** (`LINE_MISSING`), `is_verified = false` |
| Bob claims `github.com`, which serves no proof file | **PENDING** (`FILE_NOT_FOUND`) |
| A URL is passed instead of a domain | reverted `[EXPECTED] give a bare domain…` |
| Bob rechecks Alice's proof while the line is still up | still **VERIFIED**, window restarted |
| The line is removed from the site; Bob rechecks again | **REVOKED** (`LINE_MISSING`), `verified_addresses = []` |

Every transaction, the outcome codes and the state read back are in **[docs/LIVE_EVIDENCE.md](docs/LIVE_EVIDENCE.md)**, rendered from [`docs/live/run.json`](docs/live/run.json) by [glkit](https://github.com/yoyoblair333-wq/glkit).

## Tests

```
pip install genlayer-test==0.29.2 pytest
python -m pytest -q tests/direct      # real GenVM v0.2.16 SDK, proof file mocked
genvm-lint check contracts/domain_proof.py
```

The direct-mode tests cover the happy path, canonicalisation, every outcome code, cross-address lines, HTML catch-all pages, re-issued challenges, partial and prefixed lines, both expiry windows, recheck in both directions, owner revoke, two claimants for one domain, the input gate, and the consensus property itself: a validator replay with a *different* file must return `False`, and a shared failure code must return `True`.

## Run it live yourself

```
pip install "genlayer-py>=0.19" "glkit @ git+https://github.com/yoyoblair333-wq/glkit"
DOMAINPROOF_DOMAIN=your.site python scripts/live_run.py challenge   # prints the line to publish
python scripts/live_run.py verify
python scripts/live_run.py revoke                                    # after removing the line
```

Studionet is fee-aware since November 2026. The run script sends estimated, in-bounds fees through glkit.

MIT licensed. Building on GenLayer? [Join the builder program](https://portal.genlayer.foundation/?ref=JTR01FHP).

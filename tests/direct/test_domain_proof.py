"""
Direct-mode tests for contracts/domain_proof.py.

Real GenVM v0.2.16 Python SDK in-process; the proof file is mocked by regex.
`direct_vm.run_validator()` replays the captured validator through the CURRENT
mocks, so swapping mocks between the leader run and the replay simulates a
validator that fetched something different.

Run:  python -m pytest tests/direct -q
"""

from pathlib import Path

import pytest

from conftest import set_tx_time

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = str(ROOT / "contracts" / "domain_proof.py")
DOMAIN = "shop.acme-bakery.com"
URL = f"https://{DOMAIN}/.well-known/genlayer-proof.txt"
T0 = "2026-11-23T12:00:00Z"


def serve(vm, body, status=200, ctype="text/plain; charset=utf-8", url=URL):
    vm.mock_web("^" + url.replace(".", r"\.") + "$", {"method": "GET", "response": {
        "status": status, "headers": {"content-type": ctype.encode()}, "body": body.encode()}})


@pytest.fixture
def dp(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    c = direct_deploy(CONTRACT)
    set_tx_time(direct_vm, T0)
    return c


def challenge(dp, domain=DOMAIN):
    return dp.request_challenge(domain)


class TestHappyPath:
    def test_challenge_verify_and_views(self, dp, direct_vm, direct_alice):
        c = challenge(dp)
        assert c["status"] == "PENDING" and c["proof_url"] == URL
        line = c["challenge_line"]
        assert line.startswith("genlayer-domain-proof v1 domain=shop.acme-bakery.com address=0x")
        serve(direct_vm, "# DomainProof\n" + line + "\n")
        v = dp.verify(DOMAIN)
        assert v["status"] == "VERIFIED" and v["last_outcome"] == "OK" and v["verified_now"] is True
        assert v["valid_until"] == "2027-02-21T12:00:00Z"            # 90 days
        assert dp.is_verified(DOMAIN, direct_alice) is True
        assert dp.verified_addresses(DOMAIN) == [v["address"]]

    def test_domain_is_canonicalised(self, dp, direct_vm, direct_alice):
        c = dp.request_challenge("  SHOP.Acme-Bakery.com.  ")
        assert c["domain"] == DOMAIN
        serve(direct_vm, c["challenge_line"])
        dp.verify("shop.acme-bakery.COM")
        assert dp.is_verified("Shop.Acme-Bakery.com", direct_alice)

    def test_line_with_surrounding_whitespace_and_crlf_still_matches(self, dp, direct_vm):
        line = challenge(dp)["challenge_line"]
        serve(direct_vm, "other\r\n   " + line + "   \r\nmore\r\n")
        assert dp.verify(DOMAIN)["status"] == "VERIFIED"


class TestCannotBeFaked:
    def test_line_for_another_address_does_not_verify(self, dp, direct_vm, direct_bob):
        line = challenge(dp)["challenge_line"]
        direct_vm.sender = direct_bob
        challenge(dp)
        serve(direct_vm, line)                                     # alice's line, bob verifying
        v = dp.verify(DOMAIN)
        assert v["status"] == "PENDING" and v["last_outcome"] == "LINE_MISSING"

    def test_address_merely_mentioned_on_the_site_is_not_proof(self, dp, direct_vm, direct_alice):
        challenge(dp)
        serve(direct_vm, f"Our wallet is {direct_alice.as_hex if hasattr(direct_alice, 'as_hex') else direct_alice}")
        assert dp.verify(DOMAIN)["last_outcome"] == "LINE_MISSING"

    def test_html_catch_all_page_is_refused_even_if_it_contains_the_line(self, dp, direct_vm):
        line = challenge(dp)["challenge_line"]
        serve(direct_vm, f"<!doctype html><html><body><p>{line}</p></body></html>", ctype="text/html")
        assert dp.verify(DOMAIN)["last_outcome"] == "FILE_NOT_TEXT"

    def test_html_body_served_as_text_plain_is_refused(self, dp, direct_vm):
        line = challenge(dp)["challenge_line"]
        serve(direct_vm, f"<html><body>{line}</body></html>")
        assert dp.verify(DOMAIN)["last_outcome"] == "FILE_NOT_TEXT"

    def test_reissued_challenge_kills_the_old_line(self, dp, direct_vm):
        old = challenge(dp)["challenge_line"]
        set_tx_time(direct_vm, "2026-11-23T13:00:00Z")
        new = challenge(dp)["challenge_line"]
        assert new != old
        serve(direct_vm, old)
        assert dp.verify(DOMAIN)["last_outcome"] == "LINE_MISSING"

    def test_prefix_or_partial_line_does_not_match(self, dp, direct_vm):
        line = challenge(dp)["challenge_line"]
        serve(direct_vm, line[:-1] + "\n" + line + "x\n")
        assert dp.verify(DOMAIN)["last_outcome"] == "LINE_MISSING"

    @pytest.mark.parametrize("status,outcome", [(404, "FILE_NOT_FOUND"), (500, "FILE_NOT_FOUND"), (301, "FILE_NOT_FOUND")])
    def test_missing_file(self, dp, direct_vm, status, outcome):
        challenge(dp)
        serve(direct_vm, "nope", status=status)
        assert dp.verify(DOMAIN)["last_outcome"] == outcome

    def test_oversized_file(self, dp, direct_vm):
        line = challenge(dp)["challenge_line"]
        serve(direct_vm, line + "\n" + "x" * 9000)
        assert dp.verify(DOMAIN)["last_outcome"] == "FILE_TOO_BIG"


class TestLifecycle:
    def test_challenge_expires_after_72h(self, dp, direct_vm):
        line = challenge(dp)["challenge_line"]
        serve(direct_vm, line)
        set_tx_time(direct_vm, "2026-11-26T12:00:01Z")
        assert dp.verify(DOMAIN)["status"] == "FAILED"
        with direct_vm.expect_revert("request a new challenge"):
            dp.verify(DOMAIN)

    def test_verified_proof_expires_after_90_days(self, dp, direct_vm, direct_alice):
        serve(direct_vm, challenge(dp)["challenge_line"])
        dp.verify(DOMAIN)
        set_tx_time(direct_vm, "2027-02-21T12:00:01Z")
        assert dp.is_verified(DOMAIN, direct_alice) is False
        assert dp.verified_addresses(DOMAIN) == []

    def test_anyone_can_recheck_and_a_removed_line_revokes(self, dp, direct_vm, direct_alice, direct_bob):
        line = challenge(dp)["challenge_line"]
        serve(direct_vm, line)
        dp.verify(DOMAIN)
        direct_vm.clear_mocks()
        serve(direct_vm, "site changed hands")
        direct_vm.sender = direct_bob
        r = dp.recheck(DOMAIN, direct_alice)
        assert r["status"] == "REVOKED" and r["last_outcome"] == "LINE_MISSING"
        assert dp.is_verified(DOMAIN, direct_alice) is False

    def test_recheck_with_line_still_there_restarts_the_window(self, dp, direct_vm, direct_alice):
        line = challenge(dp)["challenge_line"]
        serve(direct_vm, line)
        dp.verify(DOMAIN)
        set_tx_time(direct_vm, "2027-01-01T00:00:00Z")
        r = dp.recheck(DOMAIN, direct_alice)
        assert r["status"] == "VERIFIED" and r["valid_until"] == "2027-04-01T00:00:00Z" and r["checks"] == 2

    def test_owner_can_revoke_and_must_rechallenge(self, dp, direct_vm, direct_alice):
        serve(direct_vm, challenge(dp)["challenge_line"])
        dp.verify(DOMAIN)
        assert dp.revoke(DOMAIN)["status"] == "REVOKED"
        assert dp.is_verified(DOMAIN, direct_alice) is False
        with direct_vm.expect_revert("request a new challenge"):
            dp.verify(DOMAIN)

    def test_verify_twice_is_refused_while_valid(self, dp, direct_vm):
        serve(direct_vm, challenge(dp)["challenge_line"])
        dp.verify(DOMAIN)
        with direct_vm.expect_revert("already verified"):
            dp.verify(DOMAIN)

    def test_two_addresses_can_both_prove_one_domain(self, dp, direct_vm, direct_alice, direct_bob):
        a = challenge(dp)["challenge_line"]
        direct_vm.sender = direct_bob
        b = challenge(dp)["challenge_line"]
        serve(direct_vm, a + "\n" + b + "\n")
        dp.verify(DOMAIN)
        direct_vm.sender = direct_alice
        dp.verify(DOMAIN)
        assert len(dp.verified_addresses(DOMAIN)) == 2


class TestInputs:
    @pytest.mark.parametrize("bad", [
        "https://shop.acme-bakery.com", "shop.acme-bakery.com/path", "shop.acme-bakery.com:8443", "user@acme.com",
        "localhost", "acme", "10.0.0.1", "intranet.corp", "box.local", "my.site.test", "a b.com", "-bad.com",
        "xn--caf-dma.com/x", "", 7,
    ])
    def test_bad_domains_rejected(self, dp, direct_vm, bad):
        with direct_vm.expect_revert("[EXPECTED]"):
            dp.request_challenge(bad)

    def test_verify_without_challenge(self, dp, direct_vm):
        with direct_vm.expect_revert("request a challenge"):
            dp.verify(DOMAIN)

    def test_recheck_unknown_and_unverified(self, dp, direct_vm, direct_alice):
        with direct_vm.expect_revert("no proof"):
            dp.recheck(DOMAIN, direct_alice)
        challenge(dp)
        with direct_vm.expect_revert("only a verified proof"):
            dp.recheck(DOMAIN, direct_alice)

    def test_unknown_pair_is_simply_not_verified(self, dp, direct_bob):
        assert dp.is_verified(DOMAIN, direct_bob) is False

    def test_config(self, dp):
        cfg = dp.get_config()
        assert cfg["proof_path"] == "/.well-known/genlayer-proof.txt" and cfg["proof_days"] == 90


class TestConsensus:
    def test_validator_agrees_on_same_file(self, dp, direct_vm):
        serve(direct_vm, challenge(dp)["challenge_line"])
        dp.verify(DOMAIN)
        assert direct_vm.run_validator() is True

    def test_validator_disagrees_if_its_fetch_differs(self, dp, direct_vm):
        serve(direct_vm, challenge(dp)["challenge_line"])
        dp.verify(DOMAIN)
        direct_vm.clear_mocks()
        serve(direct_vm, "nothing here")
        assert direct_vm.run_validator() is False

    def test_validator_agrees_on_a_shared_failure_code(self, dp, direct_vm):
        challenge(dp)
        serve(direct_vm, "nope", status=404)
        dp.verify(DOMAIN)
        assert direct_vm.run_validator() is True

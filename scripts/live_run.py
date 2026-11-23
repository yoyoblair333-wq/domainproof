#!/usr/bin/env python3
"""
live_run.py - deploy DomainProof to GenLayer studionet and prove control of a real site.

    pip install "genlayer-py>=0.19" "glkit @ git+https://github.com/yoyoblair333-wq/glkit"
    python scripts/live_run.py challenge     # deploy + issue alice's challenge; prints the line to publish
    # publish that line at https://<DOMAIN>/.well-known/genlayer-proof.txt, wait for the site to update
    python scripts/live_run.py verify        # alice verifies; bob (no line) and a 404 domain fail
    # remove the line from the site, wait for the site to update
    python scripts/live_run.py revoke        # bob rechecks alice's proof -> REVOKED

Resumable (glkit.LiveRun): every tx hash is saved to docs/live/run.json before waiting.
Throwaway keys live in docs/live/.keys.json, which is gitignored.
"""

import os
import sys

from glkit import LiveRun

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOMAIN = os.environ.get("DOMAINPROOF_DOMAIN", "yoyoblair333-wq.github.io")
NO_FILE_DOMAIN = "github.com"          # serves no proof file at /.well-known/genlayer-proof.txt


def main():
    phase = sys.argv[1] if len(sys.argv) > 1 else "challenge"
    run = LiveRun(os.path.join(ROOT, "docs", "live", "run.json"), roles=["alice", "bob"],
                  keys_path=os.path.join(ROOT, "docs", "live", ".keys.json")).connect()
    dp = run.deploy("deploy_domain_proof", "alice", os.path.join(ROOT, "contracts", "domain_proof.py"))
    alice, bob = run.accounts["alice"].address, run.accounts["bob"].address
    run.s["domain"] = DOMAIN

    run.write("alice_requests_challenge", "alice", dp, "request_challenge", [DOMAIN])
    proof = run.note("alice_challenge", run.read(dp, "get_proof", [DOMAIN, alice]))
    print("\nPublish this exact line at", proof["proof_url"], "\n\n", proof["challenge_line"], "\n")
    if phase == "challenge":
        return

    run.write("alice_verifies", "alice", dp, "verify", [DOMAIN], fee="llm")
    run.note("alice_after_verify", run.read(dp, "get_proof", [DOMAIN, alice]))
    run.note("is_verified_alice", run.read(dp, "is_verified", [DOMAIN, alice]))

    # bob claims the same domain but never publishes his line: must stay unverified
    run.write("bob_requests_challenge", "bob", dp, "request_challenge", [DOMAIN])
    run.write("bob_verifies_without_publishing", "bob", dp, "verify", [DOMAIN], fee="llm")
    run.note("bob_after_verify", run.read(dp, "get_proof", [DOMAIN, bob]))
    run.note("is_verified_bob", run.read(dp, "is_verified", [DOMAIN, bob]))

    # a domain that serves no proof file at all
    run.write("bob_challenges_github_com", "bob", dp, "request_challenge", [NO_FILE_DOMAIN])
    run.write("bob_verifies_github_com", "bob", dp, "verify", [NO_FILE_DOMAIN], fee="llm")
    run.note("bob_github_com", run.read(dp, "get_proof", [NO_FILE_DOMAIN, bob]))

    # input gate: a URL is not a domain
    run.write("url_instead_of_domain_must_revert", "bob", dp, "request_challenge", ["https://" + DOMAIN + "/"])

    # anyone may recheck a verified proof; the line is still there, so the window restarts
    run.write("bob_rechecks_alice_line_present", "bob", dp, "recheck", [DOMAIN, alice], fee="llm")
    run.note("alice_after_recheck_1", run.read(dp, "get_proof", [DOMAIN, alice]))
    run.note("verified_addresses_after_verify", run.read(dp, "verified_addresses", [DOMAIN]))
    if phase == "verify":
        run.save()
        return

    # the line has been removed from the site: a recheck by anyone revokes the proof
    run.write("bob_rechecks_alice_line_removed", "bob", dp, "recheck", [DOMAIN, alice], fee="llm")
    run.note("alice_after_recheck_2", run.read(dp, "get_proof", [DOMAIN, alice]))
    run.note("is_verified_alice_final", run.read(dp, "is_verified", [DOMAIN, alice]))
    run.note("verified_addresses_final", run.read(dp, "verified_addresses", [DOMAIN]))
    run.note("config", run.read(dp, "get_config"))
    run.finish()


if __name__ == "__main__":
    main()

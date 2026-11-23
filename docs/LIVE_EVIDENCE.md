# DomainProof live evidence (studionet, 2026-11-23)

Rendered by `glkit evidence` from the live-run JSON, which the run script wrote from chain data. Test-network GEN has no value; all keys are throwaway test keys.

Network: Genlayer Studio Network

## Contracts

| Deploy step | Address |
|---|---|
| deploy_domain_proof | [`0xb287E34b4779f23b6A88A206eB0514eEE40D8639`](https://explorer-studio.genlayer.com/address/0xb287E34b4779f23b6A88A206eB0514eEE40D8639) |

## Roles (throwaway keys)

| Role | Address |
|---|---|
| alice | `0x9CE25091b75968759A68290b1B4dB6d173aC205A` |
| bob | `0x23F38Ef6E76AC4655FE12B9844319b98269E7084` |

## Transactions

| # | Step | Tx | Status | Consensus | Leader execution | Votes | Contract error |
|---|---|---|---|---|---|---|---|
| 1 | deploy_domain_proof | [`0x574d4763…5c5c9b`](https://explorer-studio.genlayer.com/tx/0x574d47638409b0324a071506467609e5c04ea0c5ab00e58a1463f074c35c5c9b) | finalized/accepted | MAJORITY_AGREE | SUCCESS | agree 3, idle 2 |  |
| 2 | alice_requests_challenge | [`0xc3928312…fc85bd`](https://explorer-studio.genlayer.com/tx/0xc3928312b27d42bda6a26e463ffd7ad5d41f502e0b4b86d29fc0c43650fc85bd) | finalized/accepted | MAJORITY_AGREE | SUCCESS | agree 4, idle 1 |  |
| 3 | alice_verifies | [`0xb78f6bce…0deee3`](https://explorer-studio.genlayer.com/tx/0xb78f6bcefc7109a03b6e9f67855a1f4bb3394f90d95ac5c952f31b8e740deee3) | finalized/accepted | MAJORITY_AGREE | SUCCESS | agree 3, idle 2 |  |
| 4 | bob_requests_challenge | [`0x4f2d2c20…b17a73`](https://explorer-studio.genlayer.com/tx/0x4f2d2c20f5fd60099fe01f7963d411c8b974c033d501c514b46decad2ab17a73) | finalized/accepted | MAJORITY_AGREE | SUCCESS | agree 4, idle 1 |  |
| 5 | bob_verifies_without_publishing | [`0xc2a9eacb…4e55fa`](https://explorer-studio.genlayer.com/tx/0xc2a9eacb161195a153643d896727b46fa9a1f718de7d9364630d182db84e55fa) | finalized/accepted | MAJORITY_AGREE | SUCCESS | agree 4, idle 1 |  |
| 6 | bob_challenges_github_com | [`0x1aadefcb…c98b6e`](https://explorer-studio.genlayer.com/tx/0x1aadefcb80bb43f311d7b98df344bf361950c790d3140924120f79150bc98b6e) | finalized/accepted | MAJORITY_AGREE | SUCCESS | agree 3, idle 2 |  |
| 7 | bob_verifies_github_com | [`0x7afde503…a9d03d`](https://explorer-studio.genlayer.com/tx/0x7afde5035b49a2283a38cf2ce26be21cf64c7cc6f14403a3de4aa27161a9d03d) | finalized/accepted | MAJORITY_AGREE | SUCCESS | agree 4, idle 1 |  |
| 8 | url_instead_of_domain_must_revert | [`0xdd8b61af…db2bd1`](https://explorer-studio.genlayer.com/tx/0xdd8b61af8c1e5a2e87d03768aa62fcd6aa0271ce6675bced7b475d54a4db2bd1) | finalized/accepted | MAJORITY_AGREE | ERROR | agree 4, idle 1 | [EXPECTED] give a bare domain like shop.example.com (no scheme, path, port or spaces; punycode for IDNs) |
| 9 | bob_rechecks_alice_line_present | [`0xd4cee444…77e0cc`](https://explorer-studio.genlayer.com/tx/0xd4cee444156c08327385fca76db0f0413b3b5d046123c01f665283189177e0cc) | finalized/accepted | MAJORITY_AGREE | SUCCESS | agree 5 |  |
| 10 | bob_rechecks_alice_line_removed | [`0xe6c82d93…c93ff7`](https://explorer-studio.genlayer.com/tx/0xe6c82d931c2433b4f65a8d57768c23479492f648e4b96e10bf8bf51560c93ff7) | finalized/accepted | MAJORITY_AGREE | SUCCESS | agree 3, idle 2 |  |

## State read back from the contracts

### alice_challenge

```json
{
 "address": "0x9CE25091b75968759A68290b1B4dB6d173aC205A",
 "challenge_line": "genlayer-domain-proof v1 domain=yoyoblair333-wq.github.io address=0x9ce25091b75968759a68290b1b4db6d173ac205a nonce=b62f2cf6244ff78e68edc15b",
 "challenged_at": "2026-11-23T19:11:30Z",
 "checks": 2,
 "domain": "yoyoblair333-wq.github.io",
 "last_checked_at": "2026-11-23T19:21:32Z",
 "last_outcome": "OK",
 "proof_url": "https://yoyoblair333-wq.github.io/.well-known/genlayer-proof.txt",
 "status": "VERIFIED",
 "valid_until": "2027-02-21T19:21:32Z",
 "verified_at": "2026-11-23T19:21:32Z",
 "verified_now": true
}
```

### alice_after_verify

```json
{
 "address": "0x9CE25091b75968759A68290b1B4dB6d173aC205A",
 "challenge_line": "genlayer-domain-proof v1 domain=yoyoblair333-wq.github.io address=0x9ce25091b75968759a68290b1b4db6d173ac205a nonce=b62f2cf6244ff78e68edc15b",
 "challenged_at": "2026-11-23T19:11:30Z",
 "checks": 2,
 "domain": "yoyoblair333-wq.github.io",
 "last_checked_at": "2026-11-23T19:21:32Z",
 "last_outcome": "OK",
 "proof_url": "https://yoyoblair333-wq.github.io/.well-known/genlayer-proof.txt",
 "status": "VERIFIED",
 "valid_until": "2027-02-21T19:21:32Z",
 "verified_at": "2026-11-23T19:21:32Z",
 "verified_now": true
}
```

### is_verified_alice

```json
true
```

### bob_after_verify

```json
{
 "address": "0x23F38Ef6E76AC4655FE12B9844319b98269E7084",
 "challenge_line": "genlayer-domain-proof v1 domain=yoyoblair333-wq.github.io address=0x23f38ef6e76ac4655fe12b9844319b98269e7084 nonce=a8985f0ba7349c03025b07c9",
 "challenged_at": "2026-11-23T19:20:17Z",
 "checks": 1,
 "domain": "yoyoblair333-wq.github.io",
 "last_checked_at": "2026-11-23T19:20:31Z",
 "last_outcome": "LINE_MISSING",
 "proof_url": "https://yoyoblair333-wq.github.io/.well-known/genlayer-proof.txt",
 "status": "PENDING",
 "valid_until": "",
 "verified_at": "",
 "verified_now": false
}
```

### is_verified_bob

```json
false
```

### bob_github_com

```json
{
 "address": "0x23F38Ef6E76AC4655FE12B9844319b98269E7084",
 "challenge_line": "genlayer-domain-proof v1 domain=github.com address=0x23f38ef6e76ac4655fe12b9844319b98269e7084 nonce=3864899c290208b7fd8aa9ce",
 "challenged_at": "2026-11-23T19:20:49Z",
 "checks": 1,
 "domain": "github.com",
 "last_checked_at": "2026-11-23T19:21:02Z",
 "last_outcome": "FILE_NOT_FOUND",
 "proof_url": "https://github.com/.well-known/genlayer-proof.txt",
 "status": "PENDING",
 "valid_until": "",
 "verified_at": "",
 "verified_now": false
}
```

### alice_after_recheck_1

```json
{
 "address": "0x9CE25091b75968759A68290b1B4dB6d173aC205A",
 "challenge_line": "genlayer-domain-proof v1 domain=yoyoblair333-wq.github.io address=0x9ce25091b75968759a68290b1b4db6d173ac205a nonce=b62f2cf6244ff78e68edc15b",
 "challenged_at": "2026-11-23T19:11:30Z",
 "checks": 2,
 "domain": "yoyoblair333-wq.github.io",
 "last_checked_at": "2026-11-23T19:21:32Z",
 "last_outcome": "OK",
 "proof_url": "https://yoyoblair333-wq.github.io/.well-known/genlayer-proof.txt",
 "status": "VERIFIED",
 "valid_until": "2027-02-21T19:21:32Z",
 "verified_at": "2026-11-23T19:21:32Z",
 "verified_now": true
}
```

### verified_addresses_after_verify

```json
[
 "0x9CE25091b75968759A68290b1B4dB6d173aC205A"
]
```

### alice_after_recheck_2

```json
{
 "address": "0x9CE25091b75968759A68290b1B4dB6d173aC205A",
 "challenge_line": "genlayer-domain-proof v1 domain=yoyoblair333-wq.github.io address=0x9ce25091b75968759a68290b1b4db6d173ac205a nonce=b62f2cf6244ff78e68edc15b",
 "challenged_at": "2026-11-23T19:11:30Z",
 "checks": 3,
 "domain": "yoyoblair333-wq.github.io",
 "last_checked_at": "2026-11-23T19:31:30Z",
 "last_outcome": "LINE_MISSING",
 "proof_url": "https://yoyoblair333-wq.github.io/.well-known/genlayer-proof.txt",
 "status": "REVOKED",
 "valid_until": "",
 "verified_at": "2026-11-23T19:21:32Z",
 "verified_now": false
}
```

### is_verified_alice_final

```json
false
```

### verified_addresses_final

```json
[]
```

### config

```json
{
 "challenge_hours": 72,
 "challenges_issued": 3,
 "max_addresses_per_domain": 16,
 "max_file_bytes": 8192,
 "outcomes": [
  "OK",
  "FILE_NOT_FOUND",
  "FILE_NOT_TEXT",
  "FILE_TOO_BIG",
  "LINE_MISSING"
 ],
 "proof_days": 90,
 "proof_path": "/.well-known/genlayer-proof.txt",
 "proof_tag": "genlayer-domain-proof v1"
}
```

## Run metadata

```json
{
 "domain": "yoyoblair333-wq.github.io"
}
```

Run finished at 2026-11-23T19:31:46Z.

# DecoyTell — Implementation Summary

Live audit notes for the DecoyTell build. One file per implemented ticket, kept up
to date as each ticket lands. Each file explains, in both coding terms and plain
language: **the problem** that ticket attacked, **what we built**, **why we built it
that way**, **what we deliberately did not do (and why)**, and **exactly how to check
it works**.

## How to read this for a judge

- Hand the judge `PRD.md` (the problem) and then this folder.
- The demo that proves the whole thing: `python demo.py` from the repo root.
- The tests that back it: `python -m unittest discover tests`.

## Tickets

| # | Ticket | Verdict it demos | File |
|---|--------|------------------|------|
| T1 | Engine + harmless PASS path | `PASS` (and `INSUFFICIENT_DATA` guard) | [01-t1-engine-and-pass-path.md](01-t1-engine-and-pass-path.md) |
| T2 | Scoped auto-correction + single-drift repair | `CORRECTED` (individual check) | [02-t2-auto-correction.md](02-t2-auto-correction.md) |
| T3 | Pair-fingerprint path (the "aha") | `CORRECTED` (joint check only) | [03-t3-pair-fingerprint.md](03-t3-pair-fingerprint.md) |
| T4 | Unsafe / insufficient-data + scriptable CLI + proof | `UNSAFE` | _pending_ |
| T5 | Test hardening + README + Docker | — | _pending_ |

## The core idea in one breath

An attacker fingerprints a fake (decoy) server by checking small observable
attributes against what a real server of that type looks like. DecoyTell compares
a decoy against a matched real asset on a **fixed, declared surface of 5
attributes**, flags anything outside tolerance — **individually or as a pair** —
and either **fixes just that attribute** or marks the decoy **unsafe to expose**.
# DecoyTell

DecoyTell verifies that a deception asset (a decoy) convincingly resembles the real asset it impersonates across a fixed, declared set of observable attributes, and certifies whether the decoy is safe to expose.

## Language

**Decoy**:
A simulated deception asset that impersonates a real asset; it is useful only while its observable properties remain consistent with the asset it mimics.
_Avoid_: honeypot, fake server

**Real asset**:
The genuine asset a decoy impersonates; the comparison reference, modeled as a time-ordered observation history.
_Avoid_: target, reference box

**Observation**:
One time-stamped reading of every attribute of the real asset. The history is the collection of observations.
_Avoid_: sample, record, datapoint

**Declared surface**:
The fixed, finite set of observable attributes the comparison covers; never an open-ended guess. Defined in the schema.
_Avoid_: feature set, fingerprint space

**Attribute**:
One observable property in the declared surface (exactly five: service_banner, patch_cadence_days, timing_band, account_age_days, monitoring_behavior), each with a kind, a tolerance, a correctability flag, and a fix action.
_Avoid_: field, signal, dimension

**Tolerance**:
The allowed deviation an attribute may show before it counts as drift, expressed per kind (numeric percentile band or categorical minimum frequency).
_Avoid_: slack, margin

**Drift**:
An attribute value, or combination of values, that falls outside the declared comparison model of the real asset.
_Avoid_: deviation, anomaly, mismatch

**Marginal check**:
The per-attribute tolerance comparison of the decoy against the real asset's recent window.
_Avoid_: individual check, single check

**Joint check**:
The pairwise check that catches two individually in-tolerance attributes whose exact combination the real asset never exhibits.
_Avoid_: combination check, interaction test

**Fingerprint**:
A decoy combination the real asset never exhibits; what makes the decoy uniquely identifiable to an attacker.
_Avoid_: signature, tell

**Correction**:
A scoped repair of a drifted attribute to the real asset's conditional mode given the decoy's passing attributes; never a full rebuild.
_Avoid_: fix, patch (when referring to the decoy)

**Correction budget**:
The maximum number of correction attempts allowed before a decoy is declared unsafe to expose.
_Avoid_: retry limit, cap

**Verdict**:
The certification of a verification run: PASS, CORRECTED, UNSAFE, or INSUFFICIENT_DATA.
_Avoid_: result, status, score

**Recent window**:
The last N days of the real asset's observation history over which all statistics are computed; the decoy is judged against the asset as it is now.
_Avoid_: current period, slice

**Matched real asset**:
The real asset a decoy claims to impersonate; pairing is declared, not discovered.
_Avoid_: pair, peer

**Loop event**:
One persisted cycle of the live loop: timestamp, the real and decoy observations, the
verdict, and any fixes applied with their reasoning.
_Avoid_: log line, cycle record

**Loop control**:
The running flag (PostgreSQL row) the API toggles and the loop process polls each
cycle; it is how the dashboard starts and stops the loop without owning it.
_Avoid_: flag, switch
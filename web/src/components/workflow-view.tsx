import { useEffect, useState } from "react"
import { Check, ShieldAlert, ShieldCheck, Terminal } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Pipeline, type StageStatus } from "@/components/pipeline"
import { VerdictBadge, verdictExplanation } from "@/components/verdict-badge"
import { api } from "@/lib/api"
import type { ScenarioReport, Verdict } from "@/lib/types"

const DECLARED_SURFACE = [
  { name: "service_banner", kind: "categorical", tolerance: "seen in window, count ≥ 2", correctable: true, fix: "reconfigure server header/banner" },
  { name: "patch_cadence_days", kind: "numeric", tolerance: "inside window [Q05, Q95] band", correctable: true, fix: "apply upstream security patch" },
  { name: "timing_band", kind: "categorical", tolerance: "seen in window, count ≥ 2", correctable: true, fix: "adjust response throttling" },
  { name: "account_age_days", kind: "numeric", tolerance: "inside window [Q05, Q95] band", correctable: true, fix: "update cert/account-age metadata" },
  { name: "monitoring_behavior", kind: "categorical", tolerance: "seen in window, count ≥ 2", correctable: false, fix: "host-level, not editable" },
]

const VERDICTS: Verdict[] = ["PASS", "CORRECTED", "UNSAFE", "INSUFFICIENT_DATA"]

const COMMANDS = [
  { cmd: "docker compose up -d", what: "start the live stack: real asset (:8443), decoy (:8444), postgres (:5433)" },
  { cmd: "pip install -r requirements-live.txt", what: "install psycopg — the only live-layer dependency" },
  { cmd: "python collect_live.py --seed", what: "seed the store with the real asset's observation history" },
  { cmd: "python loop_service.py", what: "start the live loop process (polls the loop-control row, waits for Start)" },
  { cmd: "python -m uvicorn decoytell.api:app --port 8000", what: "serve the API + this dashboard at http://localhost:8000" },
  { cmd: "open http://localhost:8000 → press \"Verify now\" or \"Start loop\"", what: "run one verification cycle or start continuous operation" },
]

function stageStatus(verdict: Verdict | undefined): StageStatus {
  switch (verdict) {
    case "PASS":
      return "done"
    case "CORRECTED":
      return "warn"
    case "UNSAFE":
      return "error"
    default:
      return "idle"
  }
}

export function WorkflowView() {
  const [reports, setReports] = useState<ScenarioReport[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    api
      .scenarios()
      .then((result) => {
        if (!cancelled) setReports(result)
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err))
      })
    return () => {
      cancelled = true
    }
  }, [])

  if (error) return <p className="text-destructive">API error: {error}</p>

  const driftCount =
    reports?.reduce(
      (sum, report) =>
        sum + report.attributes.filter((attr) => attr.in_tolerance === false).length,
      0
    ) ?? null
  const fingerprintCount =
    reports?.reduce((sum, report) => sum + report.pairs.filter((pair) => pair.fingerprint).length, 0) ?? null
  const correctionCount =
    reports?.reduce((sum, report) => sum + report.corrections.length, 0) ?? null
  const windowSize = reports?.length ? reports[0].window_size : null

  return (
    <div className="space-y-6">
      <section>
        <h2 className="mb-1 text-lg font-semibold">How DecoyTell works</h2>
        <p className="mb-4 max-w-3xl text-sm text-muted-foreground">
          An attacker fingerprints a decoy by comparing its observable properties against what a
          real server looks like. DecoyTell makes that believability check automatic: every cycle
          it probes both servers, compares the decoy against the real asset&apos;s recent window,
          repairs any drift in place, and certifies the result.
        </p>
        <Pipeline
          stages={[
            {
              key: "probe",
              title: "1 · Probe",
              description: "Measure the real asset and the decoy with the same collector — the 5 declared attributes, as they are now.",
              status: "done",
            },
            {
              key: "marginal",
              title: "2 · Marginal checks",
              description: "Compare each decoy attribute against the real asset's recent 90-day window: percentile band for numerics, minimum frequency for categoricals.",
              status: "done",
              value: driftCount !== null ? `${driftCount} drifting attributes found across the demo set` : undefined,
            },
            {
              key: "joint",
              title: "3 · Joint check",
              description: "All 10 attribute pairs: a combination the real asset should have shown but never did is a fingerprint — a unique tell.",
              status: "done",
              value: fingerprintCount !== null ? `${fingerprintCount} fingerprint(s) caught` : undefined,
            },
            {
              key: "correct",
              title: "4 · Correct",
              description: "Drifted attributes are repaired in place, one at a time, to the real window's conditional mode — never a full rebuild.",
              status: "done",
              value: correctionCount !== null ? `${correctionCount} scoped correction(s) demonstrated` : undefined,
            },
            {
              key: "reverify",
              title: "5 · Re-verify",
              description: "The full check set runs again after every fix. Only then is the decoy certified safe to expose.",
              status: "done",
              value: windowSize !== null ? `${windowSize} observations in the recent window` : undefined,
            },
          ]}
        />
      </section>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">The declared surface</CardTitle>
            <CardDescription>
              The fixed set of observable attributes the comparison covers — never an open-ended
              guess. All tolerances live in <code className="font-mono">decoytell/schema.py</code>.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="divide-y divide-border">
              {DECLARED_SURFACE.map((attr) => (
                <div key={attr.name} className="grid grid-cols-[9rem_1fr_auto] items-center gap-2 py-2 text-sm">
                  <span className="font-mono text-xs font-semibold">{attr.name}</span>
                  <span className="text-xs text-muted-foreground">{attr.tolerance}</span>
                  <Badge variant={attr.correctable ? "secondary" : "destructive"} className="w-fit justify-self-end text-[10px]">
                    {attr.correctable ? "correctable" : "fixed"}
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Verdicts</CardTitle>
            <CardDescription>What each certification means — and what the operator must do.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {VERDICTS.map((verdict) => (
                <div key={verdict} className="flex items-start gap-3">
                  <VerdictBadge verdict={verdict} />
                  <p className="text-sm text-muted-foreground">{verdictExplanation(verdict)}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <section>
        <h2 className="mb-1 text-lg font-semibold">The five demo stories</h2>
        <p className="mb-3 text-sm text-muted-foreground">
          Each scenario is a declared decoy state against the same real asset. The expected verdict
          is what the design promises; the actual verdict is what the engine produced.
        </p>
        {!reports ? (
          <p className="text-muted-foreground">Loading scenarios…</p>
        ) : (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-5">
            {reports.map((report) => {
              const match = report.verdict === report.expected_verdict
              const status = stageStatus(report.verdict)
              return (
                <Card key={report.scenario_id} className="py-4">
                  <CardHeader className="px-4">
                    <CardTitle className="font-mono text-sm">{report.scenario_id}</CardTitle>
                    <CardDescription className="text-xs">{report.note}</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-2 px-4">
                    <div className="flex items-center gap-2">
                      <VerdictBadge verdict={report.verdict} />
                      {report.expected_verdict && (
                        <span className="text-xs text-muted-foreground">
                          expected: {report.expected_verdict}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-1.5 text-xs">
                      {match ? (
                        <>
                          <ShieldCheck className="size-3.5 text-green-600" />
                          <span className="text-green-700">behaves as designed</span>
                        </>
                      ) : (
                        <>
                          <ShieldAlert className="size-3.5 text-red-600" />
                          <span className="text-red-700">mismatch — investigate</span>
                        </>
                      )}
                      {status === "warn" && <span className="ml-auto font-mono text-[11px] text-muted-foreground">{report.corrections.length} fix(es)</span>}
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>
        )}
      </section>

      <section>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Terminal className="size-4" /> Run the full workflow
            </CardTitle>
            <CardDescription>
              The exact commands, in order, that bring up the live stack and this dashboard.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {COMMANDS.map((step, index) => (
                <div key={step.cmd} className="flex items-start gap-3 rounded-lg border bg-muted/30 px-3 py-2">
                  <span className="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full bg-primary text-[11px] font-semibold text-primary-foreground">
                    {index + 1}
                  </span>
                  <div className="min-w-0">
                    <code className="block break-all font-mono text-sm font-semibold">{step.cmd}</code>
                    <span className="text-xs text-muted-foreground">{step.what}</span>
                  </div>
                </div>
              ))}
            </div>
            <p className="mt-3 flex items-center gap-1.5 text-xs text-muted-foreground">
              <Check className="size-3.5 text-green-600" />
              One-click alternatives: <code className="font-mono">docker compose up -d --build</code> runs
              everything containerized, or use <span className="font-mono">Verify now</span> above for a
              single cycle without the loop service.
            </p>
          </CardContent>
        </Card>
      </section>
    </div>
  )
}
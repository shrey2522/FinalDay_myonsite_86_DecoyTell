import { useState } from "react"
import { Crosshair, FlaskConical, LoaderCircle, Radar, RotateCw, ShieldAlert, Target } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { api } from "@/lib/api"
import { ATTRIBUTE_LABELS, OBSERVABLE_KEYS, type ReconResult } from "@/lib/types"
import { cn } from "@/lib/utils"

import { AttributeComparison } from "./attribute-comparison"
import { CorrectionChain } from "./correction-chain"
import { VerdictBadge } from "./verdict-badge"

function PhaseHeader({ step, title, subtitle }: { step: string; title: string; subtitle: string }) {
  return (
    <div className="flex items-start gap-3">
      <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-primary font-mono text-xs font-semibold text-primary-foreground">
        {step}
      </span>
      <div>
        <h3 className="text-sm font-semibold">{title}</h3>
        <p className="text-xs text-muted-foreground">{subtitle}</p>
      </div>
    </div>
  )
}

function CandidateTable({ result }: { result: ReconResult }) {
  return (
    <div className="overflow-x-auto rounded-lg border">
      <table className="w-full min-w-[52rem] text-sm">
        <thead>
          <tr className="border-b bg-muted/50 text-left text-[11px] uppercase tracking-wide text-muted-foreground">
            <th className="px-3 py-2">candidate</th>
            <th className="px-3 py-2">banner</th>
            <th className="px-3 py-2">patch age</th>
            <th className="px-3 py-2">reach</th>
            <th className="px-3 py-2">auth</th>
            <th className="px-3 py-2">style</th>
            <th className="px-3 py-2 text-right">score</th>
            <th className="px-3 py-2">reasons</th>
          </tr>
        </thead>
        <tbody>
          {result.ranked.map(({ candidate, score, reasons }) => {
            const isSelected = result.selected?.name === candidate.name
            return (
              <tr
                key={candidate.name}
                className={cn(
                  "border-b last:border-b-0",
                  candidate.is_decoy && "bg-amber-50/70",
                  isSelected && "ring-2 ring-inset ring-amber-400"
                )}
              >
                <td className="px-3 py-2">
                  <span className="flex items-center gap-1.5 font-mono text-xs font-semibold">
                    {candidate.name}
                    {candidate.is_decoy && (
                      <Badge className="border-transparent bg-amber-100 text-amber-800">the decoy</Badge>
                    )}
                  </span>
                </td>
                <td className="px-3 py-2 font-mono text-xs">
                  {candidate.banner_visible ? (
                    <span className="text-red-700">exposed</span>
                  ) : (
                    <span className="text-green-700">hidden</span>
                  )}
                </td>
                <td className="px-3 py-2 font-mono text-xs">
                  {candidate.patch_age_days === null ? "—" : `${candidate.patch_age_days}d`}
                </td>
                <td className="px-3 py-2 font-mono text-xs">
                  {candidate.reachable ? "yes" : "no"}
                </td>
                <td className="px-3 py-2 font-mono text-xs">
                  {candidate.has_auth ? (
                    <span className="text-green-700">required</span>
                  ) : (
                    <span className="text-red-700">none</span>
                  )}
                </td>
                <td className="px-3 py-2 font-mono text-xs">{candidate.subdomain_style}</td>
                <td className="px-3 py-2 text-right">
                  <span className={cn("font-mono text-sm font-bold", candidate.is_decoy ? "text-amber-700" : "text-muted-foreground")}>
                    {score}
                  </span>
                </td>
                <td className="px-3 py-2 text-xs text-muted-foreground">
                  <ul className="list-disc space-y-0.5 pl-4">
                    {reasons.map((reason) => (
                      <li key={reason}>{reason}</li>
                    ))}
                  </ul>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function ObservationTable({ observation }: { observation: Record<string, unknown> }) {
  return (
    <div className="overflow-hidden rounded-lg border">
      {OBSERVABLE_KEYS.map((key) => (
        <div key={key} className="grid grid-cols-[12rem_1fr] border-b last:border-b-0">
          <div className="bg-muted/50 px-3 py-1.5 text-xs">
            <span className="font-medium">{ATTRIBUTE_LABELS[key]}</span>
            <span className="ml-1 font-mono text-[10px] text-muted-foreground">{key}</span>
          </div>
          <div className="px-3 py-1.5 font-mono text-xs">
            {observation[key] === undefined || observation[key] === null ? "—" : String(observation[key])}
          </div>
        </div>
      ))}
    </div>
  )
}

export function ReconView() {
  const [result, setResult] = useState<ReconResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [injected, setInjected] = useState(false)
  const [injecting, setInjecting] = useState(false)

  const runRecon = async () => {
    setLoading(true)
    setError(null)
    try {
      setResult(await api.recon())
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }

  const injectAndRerun = async () => {
    setInjecting(true)
    setError(null)
    try {
      const response = await api.controlInject()
      setInjected(Boolean(response.applied))
      await runRecon()
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setInjecting(false)
    }
  }

  const fingerprints = result?.analysis?.pairs.filter((pair) => pair.fingerprint) ?? []

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-2 text-lg font-semibold">
            <Crosshair className="size-5 text-red-600" /> Attacker recon
          </h2>
          <p className="max-w-3xl text-sm text-muted-foreground">
            Act 1 of the demo: why an attacker would pick the decoy out of a candidate pool, what
            they measure once they do, and what DecoyTell catches. Same code path as{" "}
            <code className="font-mono">python recon/demo_recon.py</code>, against the live decoy.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="outline" disabled={loading || injecting} onClick={() => void runRecon()}>
            {loading ? <LoaderCircle className="size-3.5 animate-spin" /> : <RotateCw className="size-3.5" />}
            {loading ? "Running…" : "Run recon"}
          </Button>
          <Button size="sm" disabled={loading || injecting} onClick={() => void injectAndRerun()}>
            {injecting ? <LoaderCircle className="size-3.5 animate-spin" /> : <FlaskConical className="size-3.5" />}
            {injecting ? "Injecting…" : "Inject drift + re-run"}
          </Button>
        </div>
      </div>

      {injected && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-800">
          Drift injected through the control plane (old banner + slow timing) — the recon below is
          the fresh run against the re-broken decoy.
        </div>
      )}

      {error && <p className="text-sm text-destructive">API error: {error}</p>}
      {loading && !result && <p className="text-muted-foreground">Running the attack simulation…</p>}

      {!result && !loading && !error && (
        <div className="rounded-lg border border-dashed px-4 py-10 text-center">
          <Crosshair className="mx-auto size-8 text-muted-foreground" />
          <p className="mt-2 text-sm font-medium">Ready to run the attack simulation</p>
          <p className="mx-auto mt-1 max-w-md text-xs text-muted-foreground">
            Press <span className="font-semibold text-foreground">Run recon</span> to score the candidate
            pool, pick the target, and verify it against the real asset — it takes a few seconds of
            live probing.
          </p>
        </div>
      )}

      {result && (
        <>
          <Card>
            <CardHeader>
              <PhaseHeader
                step="1"
                title="Reconnaissance — score the candidate pool"
                subtitle="Every point is earned by a named rule: exposed banner, no auth layer, stale patches. The decoy is the most attractive reachable target by design."
              />
            </CardHeader>
            <CardContent>
              <CandidateTable result={result} />
              <p className="mt-3 flex items-center gap-1.5 text-xs text-muted-foreground">
                <Target className="size-3.5 text-amber-600" />
                Selected target:{" "}
                <span className="font-mono font-semibold text-foreground">
                  {result.selected?.name ?? "—"}
                </span>
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <PhaseHeader
                step="2"
                title="Pre-attack observation — the attacker measures the target"
                subtitle="Exactly the 5 declared attributes DecoyTell tracks, probed the same way an attacker would."
              />
            </CardHeader>
            <CardContent>
              {result.observation ? (
                <ObservationTable observation={result.observation} />
              ) : (
                <p className="text-sm text-muted-foreground">Target unreachable — nothing to observe.</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <PhaseHeader
                step="3"
                title="DecoyTell verification — existing engine, called as-is"
                subtitle="The attacker's observation is verified against the real asset's recent window from the store."
              />
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex flex-wrap items-center gap-2">
                <VerdictBadge verdict={result.verdict ?? "UNREACHABLE"} />
                <span className="text-sm text-muted-foreground">{result.result_text}</span>
                {result.analysis?.window_size !== undefined && (
                  <Badge variant="secondary" className="font-mono">
                    window: {result.analysis.window_size} obs
                  </Badge>
                )}
              </div>

              {result.analysis?.insufficient ? (
                <p className="text-sm text-muted-foreground">
                  Baseline window too small to certify (insufficient data).
                </p>
              ) : result.analysis ? (
                <>
                  <AttributeComparison attributes={result.analysis.attributes} title="decoy vs real window" />
                  {fingerprints.length > 0 && (
                    <div className="space-y-1.5">
                      {fingerprints.map((pair) => (
                        <div
                          key={`${pair.attr_a}-${pair.attr_b}`}
                          className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm"
                        >
                          <ShieldAlert className="mt-0.5 size-4 shrink-0 text-red-600" />
                          <span className="font-mono">
                            JOINT fingerprint: {pair.attr_a}={String(pair.value_a)} + {pair.attr_b}=
                            {String(pair.value_b)} — observed {pair.observed}, expected {pair.expected}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                  {result.corrections.length > 0 && (
                    <div>
                      <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                        Scheduled repair (the loop&apos;s job, not a response to this probe)
                      </h4>
                      <CorrectionChain fixes={result.corrections} />
                    </div>
                  )}
                </>
              ) : (
                <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
                  <Radar className="size-4" /> No verification run — the selected target could not be
                  certified.
                </p>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
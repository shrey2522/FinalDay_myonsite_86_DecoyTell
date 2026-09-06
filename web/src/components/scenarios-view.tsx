import { useState } from "react"
import { CheckCircle2, ShieldAlert } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { usePolling } from "@/hooks/usePolling"
import { api } from "@/lib/api"
import type { ScenarioReport } from "@/lib/types"

import { AttributeComparison } from "./attribute-comparison"
import { CorrectionChain } from "./correction-chain"
import { PairHeatmap } from "./pair-heatmap"
import { VerdictBadge } from "./verdict-badge"

function ThresholdsTable({ report }: { report: ScenarioReport }) {
  const rows = [
    { label: "Recent window", value: `${report.thresholds.recent_window_days} days` },
    { label: "Min window observations", value: String(report.thresholds.min_window_observations) },
    { label: "Numeric band", value: `[Q${report.thresholds.numeric_lower_percentile * 100}, Q${report.thresholds.numeric_upper_percentile * 100}]` },
    { label: "Categorical minimum", value: String(report.thresholds.categorical_min_count) },
    { label: "Joint expected minimum", value: String(report.thresholds.joint_expected_min) },
    { label: "Correction budget", value: String(report.thresholds.correction_budget) },
  ]
  return (
    <div className="grid grid-cols-2 gap-x-6 gap-y-1.5 sm:grid-cols-3">
      {rows.map((row) => (
        <div key={row.label} className="flex items-baseline justify-between gap-2 border-b border-dashed pb-1 text-xs">
          <span className="text-muted-foreground">{row.label}</span>
          <span className="font-mono font-semibold">{row.value}</span>
        </div>
      ))}
    </div>
  )
}

function ReportDialog({ report, onClose }: { report: ScenarioReport; onClose: () => void }) {
  const fingerprints = report.pairs.filter((pair) => pair.fingerprint)
  const final = report.final
  const finalFailures = final
    ? final.attributes.filter((attr) => attr.in_tolerance === false).length +
      final.pairs.filter((pair) => pair.fingerprint).length
    : null
  const match = report.verdict === report.expected_verdict

  return (
    <Dialog open onOpenChange={(open) => { if (!open) onClose() }}>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-3xl">
        <DialogHeader>
          <div className="flex flex-wrap items-center gap-2">
            <DialogTitle className="font-mono">{report.scenario_id}</DialogTitle>
            <VerdictBadge verdict={report.verdict} />
            {report.expected_verdict && (
              <Badge variant="secondary">expected: {report.expected_verdict}</Badge>
            )}
            {!match && <Badge className="border-transparent bg-red-100 text-red-800">mismatch</Badge>}
          </div>
          <DialogDescription>{report.note}</DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-xs text-muted-foreground sm:grid-cols-4">
            <span>
              history: <span className="font-mono font-semibold text-foreground">{report.history_size}</span> obs
            </span>
            <span>
              window: <span className="font-mono font-semibold text-foreground">{report.window_size}</span> obs
            </span>
            <span>
              seed: <span className="font-mono font-semibold text-foreground">{report.seed}</span>
            </span>
            <span>
              schema: <span className="font-mono font-semibold text-foreground">{report.schema_version}</span>
            </span>
          </div>

          <section>
            <h4 className="mb-2 text-sm font-semibold">1 · Marginal checks — decoy vs real window</h4>
            <AttributeComparison attributes={report.attributes} title="as probed (before any correction)" />
          </section>

          <section>
            <h4 className="mb-2 text-sm font-semibold">2 · Joint check — all 10 attribute pairs</h4>
            <PairHeatmap pairs={report.pairs} />
            {fingerprints.length > 0 && (
              <div className="mt-3 space-y-1.5">
                {fingerprints.map((pair) => (
                  <div key={`${pair.attr_a}-${pair.attr_b}`} className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm">
                    <ShieldAlert className="mt-0.5 size-4 shrink-0 text-red-600" />
                    <span>
                      <span className="font-mono font-semibold">
                        {pair.attr_a}={String(pair.value_a)} × {pair.attr_b}={String(pair.value_b)}
                      </span>
                      : the real asset should have shown this combination (expected {pair.expected}) but
                      never did (observed {pair.observed}) — an attacker could use it to identify the decoy.
                    </span>
                  </div>
                ))}
              </div>
            )}
          </section>

          {report.corrections.length > 0 && (
            <section>
              <h4 className="mb-2 text-sm font-semibold">3 · Scoped corrections — one attribute at a time, re-verified after each fix</h4>
              <CorrectionChain fixes={report.corrections} />
            </section>
          )}

          {report.blocked_attributes.length > 0 && (
            <section className="rounded-lg border border-red-200 bg-red-50 px-4 py-3">
              <h4 className="flex items-center gap-2 text-sm font-semibold text-red-800">
                <ShieldAlert className="size-4" /> Blocked — not correctable into tolerance
              </h4>
              <p className="mt-1 text-sm text-red-700">
                {report.blocked_attributes.join(", ")} — no scoped repair exists, so the decoy cannot be
                certified safe to expose.
              </p>
            </section>
          )}

          {final && (
            <section>
              <h4 className="mb-2 text-sm font-semibold">4 · Re-verification — the state after corrections</h4>
              <AttributeComparison attributes={final.attributes} title="final state (full check set re-run)" />
              <div className="mt-3 flex items-center gap-2 text-sm">
                {finalFailures === 0 ? (
                  <>
                    <CheckCircle2 className="size-4 text-green-600" />
                    <span className="font-medium text-green-700">
                      All {final.attributes.length} individual checks and all {final.pairs.length} pairs pass —
                      the decoy is safe to expose.
                    </span>
                  </>
                ) : (
                  <>
                    <ShieldAlert className="size-4 text-red-600" />
                    <span className="font-medium text-red-700">
                      {finalFailures} check(s) still failing after corrections.
                    </span>
                  </>
                )}
              </div>
            </section>
          )}

          <section>
            <h4 className="mb-2 text-sm font-semibold">Thresholds in force</h4>
            <ThresholdsTable report={report} />
          </section>
        </div>
      </DialogContent>
    </Dialog>
  )
}

export function ScenariosView() {
  const { data, error, loading } = usePolling<ScenarioReport[]>(() => api.scenarios(), 5000)
  const [selected, setSelected] = useState<ScenarioReport | null>(null)

  if (loading) return <p className="text-muted-foreground">Loading…</p>
  if (error) return <p className="text-destructive">API error: {error}</p>
  if (!data) return null

  return (
    <div className="space-y-3">
      <p className="text-sm text-muted-foreground">
        Every scenario runs the same engine against the same real asset. Open a report to see the
        exact attributes that drifted, the fingerprints found, and the corrections applied.
      </p>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {data.map((report) => {
          const match = report.verdict === report.expected_verdict
          const driftCount = report.attributes.filter((attr) => attr.in_tolerance === false).length
          const fingerprintCount = report.pairs.filter((pair) => pair.fingerprint).length
          return (
            <div key={report.scenario_id} className="flex flex-col rounded-lg border px-4 py-3">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="font-mono text-sm font-medium">{report.scenario_id}</div>
                  <div className="mt-0.5 line-clamp-2 text-xs text-muted-foreground">{report.note}</div>
                </div>
                <VerdictBadge verdict={report.verdict} />
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px]">
                {report.expected_verdict && (
                  <Badge variant="secondary">expected {report.expected_verdict}</Badge>
                )}
                {driftCount > 0 && <Badge className="border-transparent bg-red-100 text-red-800">{driftCount} drift(s)</Badge>}
                {fingerprintCount > 0 && <Badge className="border-transparent bg-red-100 text-red-800">{fingerprintCount} fingerprint(s)</Badge>}
                {report.corrections.length > 0 && (
                  <Badge className="border-transparent bg-amber-100 text-amber-800">{report.corrections.length} fix(es)</Badge>
                )}
                {!match && <Badge className="border-transparent bg-red-100 text-red-800">mismatch</Badge>}
              </div>
              <div className="mt-3 flex items-center justify-between">
                <span className="font-mono text-[11px] text-muted-foreground">
                  {report.window_size} obs in window
                </span>
                <Button variant="outline" size="sm" onClick={() => setSelected(report)}>
                  Open report
                </Button>
              </div>
            </div>
          )
        })}
      </div>

      {selected && <ReportDialog report={selected} onClose={() => setSelected(null)} />}
    </div>
  )
}
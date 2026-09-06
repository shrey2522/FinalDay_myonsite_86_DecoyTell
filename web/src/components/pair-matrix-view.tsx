import { useState } from "react"
import { ShieldAlert } from "lucide-react"

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { usePolling } from "@/hooks/usePolling"
import { api } from "@/lib/api"
import type { PairFinding } from "@/lib/types"

import { PairHeatmap } from "./pair-heatmap"

const SCENARIOS = ["s1_harmless", "s2_single_drift", "s3_pair_fingerprint", "s4_uncorrectable", "s5_insufficient_data"]

export function PairMatrixView() {
  const [scenario, setScenario] = useState("s3_pair_fingerprint")
  const { data, error, loading } = usePolling<{ scenario: string; pairs: PairFinding[] }>(
    () => api.pairs(scenario),
    5000,
    [scenario]
  )

  const fingerprints = data?.pairs.filter((pair) => pair.fingerprint) ?? []
  const judged = data?.pairs.filter((pair) => pair.expected >= 1) ?? []

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <span className="text-sm font-medium">Scenario:</span>
        <Select value={scenario} onValueChange={setScenario}>
          <SelectTrigger className="w-64">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {SCENARIOS.map((id) => (
              <SelectItem key={id} value={id}>
                {id}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <span className="text-sm text-muted-foreground">
          {data ? `${judged.length}/10 pairs judged · ${fingerprints.length} fingerprint(s)` : "…"}
        </span>
      </div>

      <p className="max-w-3xl text-sm text-muted-foreground">
        The joint check examines all 10 attribute pairs. A pair is a <span className="font-semibold">fingerprint</span>{" "}
        when the real asset should have exhibited the decoy&apos;s combination (expected ≥ 1) but never did —
        two individually-fine attributes whose exact combination gives the decoy away.
      </p>

      {loading ? (
        <p className="text-muted-foreground">Loading…</p>
      ) : error ? (
        <p className="text-destructive">API error: {error}</p>
      ) : (
        <>
          {data && <PairHeatmap pairs={data.pairs} />}

          {fingerprints.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-sm font-semibold">Fingerprints detected</h4>
              {fingerprints.map((pair) => (
                <div
                  key={`${pair.attr_a}-${pair.attr_b}`}
                  className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm"
                >
                  <ShieldAlert className="mt-0.5 size-4 shrink-0 text-red-600" />
                  <span className="font-mono">
                    {pair.attr_a}={String(pair.value_a)} × {pair.attr_b}={String(pair.value_b)} — observed{" "}
                    {pair.observed}, expected {pair.expected}
                  </span>
                </div>
              ))}
            </div>
          )}

          {fingerprints.length === 0 && data && (
            <div className="rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800">
              No fingerprints — every judged combination the decoy exhibits also occurs in the real
              asset&apos;s window.
            </div>
          )}
        </>
      )}
    </div>
  )
}
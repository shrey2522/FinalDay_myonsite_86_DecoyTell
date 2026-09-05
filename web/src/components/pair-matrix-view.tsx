import { useState } from "react"

import { Badge } from "@/components/ui/badge"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { usePolling } from "@/hooks/usePolling"
import { api } from "@/lib/api"
import type { PairFinding } from "@/lib/types"

const SCENARIOS = ["s1_harmless", "s2_single_drift", "s3_pair_fingerprint", "s4_uncorrectable", "s5_insufficient_data"]

export function PairMatrixView() {
  const [scenario, setScenario] = useState("s3_pair_fingerprint")
  const { data, error, loading } = usePolling<{ scenario: string; pairs: PairFinding[] }>(
    () => api.pairs(scenario),
    5000,
    [scenario]
  )

  const fingerprints = data?.pairs.filter((pair) => pair.fingerprint) ?? []

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
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
        <span className="text-muted-foreground text-sm">
          {fingerprints.length > 0
            ? `${fingerprints.length} fingerprint(s): ${fingerprints
                .map((f) => `${f.attr_a} x ${f.attr_b}`)
                .join(", ")}`
            : "no fingerprints"}
        </span>
      </div>

      {loading ? (
        <p className="text-muted-foreground">Loading…</p>
      ) : error ? (
        <p className="text-destructive">API error: {error}</p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Pair</TableHead>
              <TableHead>Values</TableHead>
              <TableHead>Observed</TableHead>
              <TableHead>Expected</TableHead>
              <TableHead>Verdict</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data?.pairs.map((pair) => (
              <TableRow key={`${pair.attr_a}-${pair.attr_b}`}>
                <TableCell className="font-mono text-xs">
                  {pair.attr_a} × {pair.attr_b}
                </TableCell>
                <TableCell className="font-mono text-xs">
                  {String(pair.value_a)} / {String(pair.value_b)}
                </TableCell>
                <TableCell>{pair.observed}</TableCell>
                <TableCell>{pair.expected}</TableCell>
                <TableCell>
                  {pair.fingerprint ? (
                    <Badge className="bg-red-100 text-red-800">fingerprint</Badge>
                  ) : (
                    <Badge variant="secondary">OK</Badge>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      <p className="text-muted-foreground text-xs">
        The 10 pairwise joint checks ("the 10 possible drifts"): a fingerprint means the real asset
        should have exhibited this combination (expected ≥ 1) but never did (observed = 0).
      </p>
    </div>
  )
}
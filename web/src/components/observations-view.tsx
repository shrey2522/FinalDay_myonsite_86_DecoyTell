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
import { ATTRIBUTE_LABELS, type ObservationRow } from "@/lib/types"
import { cn } from "@/lib/utils"

const TARGETS = ["real-asset", "decoy"]
const NUMERIC = ["patch_cadence_days", "account_age_days"] as const
const CATEGORICAL = ["service_banner", "timing_band", "monitoring_behavior"] as const

function percentile(sorted: number[], p: number) {
  if (sorted.length === 0) return null
  const k = (sorted.length - 1) * p
  const f = Math.floor(k)
  const c = Math.ceil(k)
  return f === c ? sorted[k] : sorted[f] * (c - k) + sorted[c] * (k - f)
}

function NumericStat({ label, values }: { label: string; values: number[] }) {
  const sorted = [...values].sort((a, b) => a - b)
  const lo = percentile(sorted, 0.05)
  const hi = percentile(sorted, 0.95)
  const median = percentile(sorted, 0.5)
  return (
    <div className="rounded-lg border px-3 py-2">
      <div className="text-xs font-medium">{label}</div>
      <div className="mt-1 flex flex-wrap gap-x-3 gap-y-0.5 font-mono text-[11px] text-muted-foreground">
        <span>min <span className="font-semibold text-foreground">{sorted[0]?.toFixed(1)}</span></span>
        <span>Q05 <span className="font-semibold text-foreground">{lo?.toFixed(1)}</span></span>
        <span>med <span className="font-semibold text-foreground">{median?.toFixed(1)}</span></span>
        <span>Q95 <span className="font-semibold text-foreground">{hi?.toFixed(1)}</span></span>
        <span>max <span className="font-semibold text-foreground">{sorted[sorted.length - 1]?.toFixed(1)}</span></span>
      </div>
    </div>
  )
}

function CategoricalStat({ label, rows, valueOf }: { label: string; rows: ObservationRow[]; valueOf: (row: ObservationRow) => string }) {
  const counts = new Map<string, number>()
  for (const row of rows) {
    const value = valueOf(row)
    counts.set(value, (counts.get(value) ?? 0) + 1)
  }
  const total = rows.length
  const entries = [...counts.entries()].sort((a, b) => b[1] - a[1])
  const maxCount = entries[0]?.[1] ?? 1
  return (
    <div className="rounded-lg border px-3 py-2">
      <div className="text-xs font-medium">{label}</div>
      <div className="mt-1.5 space-y-1">
        {entries.map(([value, count]) => (
          <div key={value} className="flex items-center gap-2">
            <span className="w-28 truncate font-mono text-[11px] text-muted-foreground" title={value}>
              {value}
            </span>
            <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-secondary">
              <div
                className="h-full rounded-full bg-primary/60"
                style={{ width: `${(count / maxCount) * 100}%` }}
              />
            </div>
            <span className="w-14 text-right font-mono text-[11px] text-muted-foreground">
              {count} ({((count / total) * 100).toFixed(0)}%)
            </span>
          </div>
        ))}
        {entries.length === 0 && <span className="text-xs text-muted-foreground">no data</span>}
      </div>
    </div>
  )
}

export function ObservationsView() {
  const [target, setTarget] = useState("real-asset")
  const { data, error, loading } = usePolling(
    () => api.observations(target, 90),
    5000,
    [target]
  )

  const rows = data?.observations ?? []
  const numericStats: Record<string, number[]> = { patch_cadence_days: [], account_age_days: [] }
  for (const row of rows) {
    numericStats.patch_cadence_days.push(row.patch_cadence_days)
    numericStats.account_age_days.push(row.account_age_days)
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <span className="text-sm font-medium">Target:</span>
        <Select value={target} onValueChange={setTarget}>
          <SelectTrigger className="w-48">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {TARGETS.map((id) => (
              <SelectItem key={id} value={id}>
                {id}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <span className="text-sm text-muted-foreground">
          {data ? `${data.count} observations in the last ${data.days} days` : "…"}
        </span>
      </div>

      {loading ? (
        <p className="text-muted-foreground">Loading…</p>
      ) : error ? (
        <p className="text-destructive">API error: {error}</p>
      ) : (
        <>
          <div>
            <h4 className="mb-2 text-sm font-semibold">Distribution over the recent window</h4>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              {NUMERIC.map((key) => (
                <NumericStat key={key} label={ATTRIBUTE_LABELS[key]} values={numericStats[key]} />
              ))}
              {CATEGORICAL.map((key) => (
                <CategoricalStat
                  key={key}
                  label={ATTRIBUTE_LABELS[key]}
                  rows={rows}
                  valueOf={key === "service_banner" ? (row) => row.service_banner : key === "timing_band" ? (row) => row.timing_band : (row) => row.monitoring_behavior}
                />
              ))}
            </div>
          </div>

          <div>
            <h4 className="mb-2 text-sm font-semibold">Recent stream (last 50)</h4>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Days ago</TableHead>
                    <TableHead>Banner</TableHead>
                    <TableHead>Patch cadence</TableHead>
                    <TableHead>Timing</TableHead>
                    <TableHead>Account age</TableHead>
                    <TableHead>Monitoring</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rows.slice(-50).map((row, index) => (
                    <TableRow key={index}>
                      <TableCell className={cn("font-mono text-xs", row.days_ago <= 1 && "font-semibold text-foreground")}>
                        {row.days_ago}
                      </TableCell>
                      <TableCell className="font-mono text-xs">{row.service_banner}</TableCell>
                      <TableCell className="font-mono text-xs">{row.patch_cadence_days}</TableCell>
                      <TableCell>
                        <Badge variant="secondary">{row.timing_band}</Badge>
                      </TableCell>
                      <TableCell className="font-mono text-xs">{row.account_age_days}</TableCell>
                      <TableCell>
                        <Badge variant="secondary">{row.monitoring_behavior}</Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                  {rows.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={6} className="text-muted-foreground">
                        No observations yet — seed the store:{" "}
                        <code className="font-mono">python collect_live.py --seed</code>
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
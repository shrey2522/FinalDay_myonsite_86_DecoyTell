import { useEffect, useState } from "react"

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
import type { ObservationRow } from "@/lib/types"

const TARGETS = ["real-asset", "decoy"]

export function ObservationsView() {
  const [target, setTarget] = useState("real-asset")
  const { data, error, loading } = usePolling(
    () => api.observations(target, 90),
    5000,
    [target]
  )
  const [rows, setRows] = useState<ObservationRow[]>([])

  useEffect(() => {
    if (data) setRows(data.observations.slice(-50))
  }, [data])

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
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
        <span className="text-muted-foreground text-sm">
          {data ? `${data.count} observations in the last ${data.days} days (showing last 50)` : "…"}
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
              <TableHead>Days ago</TableHead>
              <TableHead>Banner</TableHead>
              <TableHead>Patch cadence</TableHead>
              <TableHead>Timing</TableHead>
              <TableHead>Account age</TableHead>
              <TableHead>Monitoring</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((row, index) => (
              <TableRow key={index}>
                <TableCell className="font-mono text-xs">{row.days_ago}</TableCell>
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
                  No observations yet — seed the store: <code className="font-mono">python collect_live.py --seed</code>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      )}
    </div>
  )
}
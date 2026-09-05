import { useEffect, useState } from "react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
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
import type { LoopEvent } from "@/lib/types"

import { VerdictBadge } from "./verdict-badge"

const OBSERVABLE_KEYS = [
  "service_banner",
  "patch_cadence_days",
  "timing_band",
  "account_age_days",
  "monitoring_behavior",
] as const

function ObservationTable({ label, observation }: { label: string; observation: Record<string, unknown> }) {
  return (
    <div>
      <h4 className="mb-1 text-xs font-semibold text-muted-foreground">{label}</h4>
      <Table>
        <TableBody>
          {OBSERVABLE_KEYS.map((key) => (
            <TableRow key={key}>
              <TableCell className="font-mono text-xs">{key}</TableCell>
              <TableCell className="font-mono text-xs">{String(observation[key] ?? "—")}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}

export function LiveLoopView() {
  const { data, error, loading } = usePolling<{ events: LoopEvent[] }>(
    () => api.loopEvents(0, 50),
    3000
  )
  const [expanded, setExpanded] = useState<number | null>(null)

  useEffect(() => {
    if (data?.events.length) setExpanded(data.events[data.events.length - 1].id)
  }, [data])

  if (loading) return <p className="text-muted-foreground">Loading…</p>
  if (error) return <p className="text-destructive">API error: {error}</p>
  if (!data) return null

  const events = [...data.events].reverse()

  return (
    <div className="space-y-3">
      {events.length === 0 && (
        <p className="text-muted-foreground">
          No loop events yet — run <code className="font-mono">python loop_service.py</code> and start the loop
          from the dashboard, or press "Verify now".
        </p>
      )}
      {events.map((event) => (
        <Card key={event.id}>
          <CardHeader className="py-3">
            <div className="flex flex-wrap items-center gap-3">
              <CardTitle className="font-mono text-sm">cycle #{event.cycle}</CardTitle>
              <span className="text-muted-foreground font-mono text-xs">{event.timestamp}</span>
              <VerdictBadge verdict={event.verdict} />
              <span className="text-muted-foreground text-xs">→</span>
              <VerdictBadge verdict={event.recheck} />
              <Button variant="ghost" size="sm" className="ml-auto" onClick={() => setExpanded(expanded === event.id ? null : event.id)}>
                {expanded === event.id ? "hide" : "details"}
              </Button>
            </div>
          </CardHeader>
          {expanded === event.id && (
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <ObservationTable label="Real asset probe" observation={event.real_obs} />
                <ObservationTable label="Decoy probe" observation={event.decoy_obs} />
              </div>
              {event.fixes.length > 0 ? (
                <div>
                  <h4 className="mb-1 text-xs font-semibold text-muted-foreground">Fixes applied (reasoning)</h4>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Attribute</TableHead>
                        <TableHead>Before</TableHead>
                        <TableHead>After</TableHead>
                        <TableHead>Action</TableHead>
                        <TableHead>Status</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {event.fixes.map((fix, index) => (
                        <TableRow key={index}>
                          <TableCell className="font-mono text-xs">{fix.attribute}</TableCell>
                          <TableCell className="font-mono text-xs">{String(fix.before)}</TableCell>
                          <TableCell className="font-mono text-xs">{String(fix.after)}</TableCell>
                          <TableCell className="text-xs">{fix.action}</TableCell>
                          <TableCell>
                            {fix.applied ? (
                              <Badge className="bg-green-100 text-green-800">applied</Badge>
                            ) : (
                              <Badge className="bg-red-100 text-red-800">{fix.reason ?? "cannot apply"}</Badge>
                            )}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              ) : (
                <p className="text-muted-foreground text-xs">No corrections needed this cycle.</p>
              )}
            </CardContent>
          )}
        </Card>
      ))}
    </div>
  )
}
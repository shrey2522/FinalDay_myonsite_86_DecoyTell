import { useEffect, useState } from "react"
import { ArrowRight, ChevronDown, ChevronUp, Radio } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { usePolling } from "@/hooks/usePolling"
import { api } from "@/lib/api"
import { ATTRIBUTE_LABELS, OBSERVABLE_KEYS, type LoopEvent } from "@/lib/types"
import { cn } from "@/lib/utils"

import { CorrectionChain } from "./correction-chain"
import { LoopControlBar } from "./loop-control-bar"
import { VerdictBadge } from "./verdict-badge"

function ProbeComparison({ event }: { event: LoopEvent }) {
  const drifted = OBSERVABLE_KEYS.filter(
    (key) => event.real_obs[key] !== undefined && event.real_obs[key] !== event.decoy_obs[key]
  )
  const cells = (key: string) =>
    cn(
      "px-3 py-1.5 font-mono text-xs",
      drifted.includes(key as (typeof OBSERVABLE_KEYS)[number])
        ? "bg-red-50 text-red-700"
        : "text-muted-foreground"
    )

  return (
    <div className="overflow-hidden rounded-lg border">
      <div className="grid grid-cols-[10rem_1fr_1fr] border-b bg-muted/50 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        <div className="px-3 py-1.5">attribute</div>
        <div className="px-3 py-1.5">real asset (as probed)</div>
        <div className="px-3 py-1.5">decoy (as probed)</div>
      </div>
      {OBSERVABLE_KEYS.map((key) => (
        <div key={key} className="grid grid-cols-[10rem_1fr_1fr] border-b last:border-b-0">
          <div className="px-3 py-1.5 text-xs">
            <span className="font-medium">{ATTRIBUTE_LABELS[key]}</span>
            <span className="ml-1 font-mono text-[10px] text-muted-foreground">{key}</span>
          </div>
          <div className={cells(key)}>{String(event.real_obs[key] ?? "—")}</div>
          <div className={cn(cells(key), "font-semibold")}>{String(event.decoy_obs[key] ?? "—")}</div>
        </div>
      ))}
      {drifted.length > 0 && (
        <div className="bg-red-50 px-3 py-1.5 text-xs text-red-700">
          {drifted.length} attribute(s) differ from the real asset: {drifted.join(", ")}
        </div>
      )}
      {drifted.length === 0 && (
        <div className="bg-green-50 px-3 py-1.5 text-xs text-green-700">
          decoy matches the real asset on every probed attribute
        </div>
      )}
    </div>
  )
}

function EventCard({ event }: { event: LoopEvent }) {
  const [expanded, setExpanded] = useState(false)
  const corrected = event.verdict !== event.recheck

  return (
    <Card className="py-3">
      <CardHeader className="px-4">
        <div className="flex flex-wrap items-center gap-3">
          <span className="flex items-center gap-1.5 font-mono text-sm font-semibold">
            <Radio className="size-4 text-muted-foreground" />
            cycle #{event.cycle}
          </span>
          <span className="font-mono text-xs text-muted-foreground">{event.timestamp}</span>
          <div className="flex items-center gap-1.5">
            <VerdictBadge verdict={event.verdict} />
            <ArrowRight className="size-3.5 text-muted-foreground" />
            <VerdictBadge verdict={event.recheck} />
          </div>
          {corrected && (
            <Badge className="border-transparent bg-green-100 text-green-800">
              corrected & re-verified clean
            </Badge>
          )}
          {event.fixes.length > 0 && (
            <Badge variant="secondary" className="font-mono">
              {event.fixes.length} fix(es) attempted
            </Badge>
          )}
          <Button
            variant="ghost"
            size="sm"
            className="ml-auto"
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
            {expanded ? "hide details" : "show details"}
          </Button>
        </div>
      </CardHeader>
      {expanded && (
        <CardContent className="space-y-4 px-4">
          <ProbeComparison event={event} />
          {event.fixes.length > 0 ? (
            <div>
              <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Corrections applied through the control plane
              </h4>
              <CorrectionChain fixes={event.fixes} />
            </div>
          ) : (
            <p className="text-xs text-muted-foreground">No corrections needed this cycle.</p>
          )}
        </CardContent>
      )}
    </Card>
  )
}

export function LiveLoopView() {
  const { data, error, loading } = usePolling<{ events: LoopEvent[] }>(
    () => api.loopEvents(0, 50),
    3000
  )
  const [expandedId, setExpandedId] = useState<number | null>(null)

  useEffect(() => {
    if (data?.events.length) setExpandedId(data.events[data.events.length - 1].id)
  }, [data])

  if (loading) return <p className="text-muted-foreground">Loading…</p>
  if (error) return <p className="text-destructive">API error: {error}</p>
  if (!data) return null

  const events = [...data.events].reverse()

  return (
    <div className="space-y-4">
      <LoopControlBar />

      <p className="text-sm text-muted-foreground">
        Each cycle: probe the real asset and the decoy → append to the store → verify against the
        recent window → apply fixes through the control plane → re-probe → re-verify → persist the
        event. The loop process survives API restarts and vice versa.
      </p>

      {events.length === 0 && (
        <div className="rounded-lg border border-dashed px-4 py-8 text-center text-muted-foreground">
          <p>
            No loop events yet. Run <code className="font-mono">python loop_service.py</code>, then press{" "}
            <span className="font-medium">Start loop</span> above — or press{" "}
            <span className="font-medium">Verify now</span> for a single cycle.
          </p>
        </div>
      )}

      <div className="space-y-3">
        {events.map((event) => (
          <div
            key={event.id}
            className={cn("rounded-xl", expandedId === event.id && "ring-2 ring-primary/20")}
          >
            <EventCard event={event} />
          </div>
        ))}
      </div>
    </div>
  )
}
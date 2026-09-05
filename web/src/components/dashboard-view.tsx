import { useState } from "react"

import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { usePolling } from "@/hooks/usePolling"
import { api } from "@/lib/api"
import type { Status } from "@/lib/types"

import { VerdictBadge } from "./verdict-badge"

export function DashboardView() {
  const { data, error, loading } = usePolling<Status>(() => api.status(), 3000)
  const [busy, setBusy] = useState(false)

  const toggleLoop = async () => {
    setBusy(true)
    try {
      if (data?.loop.running) await api.loopStop()
      else await api.loopStart()
    } finally {
      setBusy(false)
    }
  }

  const verifyNow = async () => {
    setBusy(true)
    try {
      await api.verify()
    } finally {
      setBusy(false)
    }
  }

  if (loading) return <p className="text-muted-foreground">Loading…</p>
  if (error) return <p className="text-destructive">API error: {error}</p>
  if (!data) return null

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Button disabled={busy} onClick={() => void toggleLoop()}>
          {data.loop.running ? "Stop loop" : "Start loop"}
        </Button>
        <Button variant="outline" disabled={busy} onClick={() => void verifyNow()}>
          Verify now
        </Button>
        <span className="text-muted-foreground text-sm">
          Loop: {data.loop.running ? "running" : "stopped"}
        </span>
        {data.loop.latest_event && (
          <span className="text-muted-foreground text-sm">
            Latest cycle #{data.loop.latest_event.cycle} @ {data.loop.latest_event.timestamp}
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {data.scenarios.map((scenario) => (
          <Card key={scenario.id}>
            <CardHeader>
              <CardTitle className="font-mono text-sm">{scenario.id}</CardTitle>
              <CardDescription>{scenario.expected ?? "—"}</CardDescription>
            </CardHeader>
            <CardContent>
              <VerdictBadge verdict={scenario.verdict} />
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
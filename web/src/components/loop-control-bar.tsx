import { useState } from "react"
import { Play, RotateCw, Square } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { usePolling } from "@/hooks/usePolling"
import { api } from "@/lib/api"
import type { Status } from "@/lib/types"

export function LoopControlBar() {
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

  const latest = data?.loop.latest_event

  return (
    <div className="flex flex-wrap items-center gap-3 rounded-lg border bg-muted/30 px-4 py-3">
      <div className="flex items-center gap-2">
        <span
          className={`size-2.5 rounded-full ${data?.loop.running ? "animate-pulse bg-green-600" : "bg-slate-400"}`}
        />
        <span className="text-sm font-medium">
          Loop: {loading ? "…" : data?.loop.running ? "running" : "stopped"}
        </span>
      </div>
      <div className="flex items-center gap-2">
        <Button size="sm" disabled={busy} onClick={() => void toggleLoop()}>
          {data?.loop.running ? (
            <>
              <Square className="size-3.5" /> Stop loop
            </>
          ) : (
            <>
              <Play className="size-3.5" /> Start loop
            </>
          )}
        </Button>
        <Button size="sm" variant="outline" disabled={busy} onClick={() => void verifyNow()}>
          <RotateCw className="size-3.5" /> Verify now
        </Button>
      </div>
      {latest && (
        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          <span className="font-mono">latest cycle #{latest.cycle}</span>
          <span className="font-mono">{latest.timestamp}</span>
          <Badge variant="secondary" className="font-mono">
            {latest.verdict} → {latest.recheck}
          </Badge>
        </div>
      )}
      {!latest && !error && (
        <span className="text-xs text-muted-foreground">
          no cycles yet — press <span className="font-mono">Verify now</span> to run one
        </span>
      )}
      {error && <span className="text-xs text-destructive">API error: {error}</span>}
    </div>
  )
}
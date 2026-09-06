import { ArrowRight } from "lucide-react"

import { cn } from "@/lib/utils"

export type StageStatus = "done" | "active" | "warn" | "error" | "idle"

export interface PipelineStage {
  key: string
  title: string
  description: string
  status: StageStatus
  value?: string
}

const statusStyles: Record<StageStatus, { ring: string; dot: string; value: string }> = {
  done: { ring: "border-green-300 bg-green-50", dot: "bg-green-600", value: "text-green-700" },
  active: { ring: "border-blue-300 bg-blue-50", dot: "bg-blue-600", value: "text-blue-700" },
  warn: { ring: "border-amber-300 bg-amber-50", dot: "bg-amber-500", value: "text-amber-700" },
  error: { ring: "border-red-300 bg-red-50", dot: "bg-red-600", value: "text-red-700" },
  idle: { ring: "border-border bg-muted/50", dot: "bg-slate-400", value: "text-muted-foreground" },
}

export function Pipeline({ stages }: { stages: PipelineStage[] }) {
  return (
    <div className="flex flex-col gap-2 lg:flex-row lg:items-stretch lg:gap-0">
      {stages.map((stage, index) => {
        const style = statusStyles[stage.status]
        return (
          <div key={stage.key} className="flex flex-1 flex-col lg:flex-row">
            <div className={cn("flex flex-1 flex-col gap-1.5 rounded-xl border p-3", style.ring)}>
              <div className="flex items-center gap-2">
                <span className={cn("size-2.5 rounded-full", style.dot)} />
                <span className="text-sm font-semibold">{stage.title}</span>
              </div>
              <p className="text-xs leading-relaxed text-muted-foreground">{stage.description}</p>
              {stage.value && (
                <p className={cn("font-mono text-xs font-semibold", style.value)}>{stage.value}</p>
              )}
            </div>
            {index < stages.length - 1 && (
              <div className="flex items-center justify-center py-1 lg:px-1 lg:py-0">
                <ArrowRight className="size-4 rotate-90 text-muted-foreground lg:rotate-0" />
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
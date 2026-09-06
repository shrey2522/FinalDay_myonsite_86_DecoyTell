import { ArrowRight, Check, Wrench } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { ATTRIBUTE_LABELS, type Fix } from "@/lib/types"
import { cn } from "@/lib/utils"

export function CorrectionChain({ fixes }: { fixes: Fix[] }) {
  if (fixes.length === 0) return null
  return (
    <div className="space-y-0">
      {fixes.map((fix, index) => (
        <div key={index} className="relative flex gap-3 pb-4 last:pb-0">
          {index < fixes.length - 1 && <div className="absolute left-[13px] top-7 bottom-0 w-px bg-border" />}
          <div
            className={cn(
              "flex size-7 shrink-0 items-center justify-center rounded-full border",
              fix.applied === false
                ? "border-red-200 bg-red-50 text-red-600"
                : "border-amber-200 bg-amber-50 text-amber-700"
            )}
          >
            <Wrench className="size-3.5" />
          </div>
          <div className="min-w-0 flex-1 rounded-lg border bg-muted/30 px-3 py-2">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm font-semibold">{ATTRIBUTE_LABELS[fix.attribute] ?? fix.attribute}</span>
              <Badge variant="secondary" className="font-mono">
                {fix.action}
              </Badge>
            </div>
            <div className="mt-1 flex flex-wrap items-center gap-2 font-mono text-sm">
              <span className="text-muted-foreground line-through">{String(fix.before)}</span>
              <ArrowRight className="size-3.5 text-muted-foreground" />
              <span className="font-semibold">{String(fix.after)}</span>
              {fix.applied === false ? (
                <Badge className="border-transparent bg-red-100 text-red-800">
                  cannot apply{fix.reason ? `: ${fix.reason}` : ""}
                </Badge>
              ) : fix.re_verified ? (
                <Badge className="border-transparent bg-green-100 text-green-800">
                  <Check className="size-3" /> re-verified
                </Badge>
              ) : fix.applied === true ? (
                <Badge className="border-transparent bg-green-100 text-green-800">
                  <Check className="size-3" /> applied
                </Badge>
              ) : (
                <Badge variant="secondary">scheduled</Badge>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
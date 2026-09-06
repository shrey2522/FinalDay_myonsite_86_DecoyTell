import { Badge } from "@/components/ui/badge"
import { ATTRIBUTE_DESCRIPTIONS, ATTRIBUTE_LABELS, type AttributeResult } from "@/lib/types"
import { cn } from "@/lib/utils"

function StatusBadge({ attribute }: { attribute: AttributeResult }) {
  if (attribute.in_tolerance === null) {
    return <Badge variant="secondary">no window data</Badge>
  }
  return attribute.in_tolerance ? (
    <Badge className="border-transparent bg-green-100 text-green-800">in tolerance</Badge>
  ) : (
    <Badge className="border-transparent bg-red-100 text-red-800">DRIFT</Badge>
  )
}

function BandGauge({ attribute }: { attribute: AttributeResult }) {
  const [lo, hi] = attribute.band ?? [0, 1]
  const value = Number(attribute.decoy_value)
  const unit = attribute.unit ? ` ${attribute.unit}` : ""

  const min = Math.min(lo, value)
  const max = Math.max(hi, value)
  const span = max - min || 1
  const pad = span * 0.08
  const from = min - pad
  const to = max + pad
  const range = to - from || 1

  const bandLeft = ((lo - from) / range) * 100
  const bandWidth = ((hi - lo) / range) * 100
  const markerLeft = ((value - from) / range) * 100
  const outside = value < lo || value > hi

  return (
    <div className="space-y-1.5">
      <div className="relative h-6 rounded-md border border-border bg-secondary/40">
        <div
          className="absolute top-0 h-full bg-green-200/80"
          style={{ left: `${bandLeft}%`, width: `${bandWidth}%` }}
          title={`real window band [${lo}, ${hi}]${unit}`}
        />
        <div
          className={cn(
            "absolute top-0 h-full w-1 -translate-x-1/2 rounded-sm",
            outside ? "bg-red-500" : "bg-green-700"
          )}
          style={{ left: `${markerLeft}%` }}
          title={`decoy value ${value}${unit}`}
        />
      </div>
      <div className="flex justify-between font-mono text-[11px] text-muted-foreground">
        <span>
          band [{lo}–{hi}]{unit}
        </span>
        <span className={outside ? "font-semibold text-red-600" : "text-green-700"}>
          decoy = {value}
          {unit}
        </span>
      </div>
    </div>
  )
}

function FrequencyBar({ attribute }: { attribute: AttributeResult }) {
  const count = attribute.count ?? 0
  const window = attribute.window_size ?? 0
  const minCount = Math.max(2, Math.ceil(window * 0.05))
  const pct = window > 0 ? Math.min(100, (count / window) * 100) : 0
  const thresholdPct = window > 0 ? Math.min(100, (minCount / window) * 100) : 0
  const ok = Boolean(attribute.in_tolerance)

  return (
    <div className="space-y-1.5">
      <div className="relative h-6 overflow-hidden rounded-md border border-border bg-secondary/40">
        <div
          className={cn("absolute inset-y-0 left-0", ok ? "bg-green-200/80" : "bg-red-200/80")}
          style={{ width: `${pct}%` }}
        />
        <div
          className="absolute inset-y-0 w-0.5 bg-slate-600"
          style={{ left: `${thresholdPct}%` }}
          title={`minimum frequency: ${minCount}/${window}`}
        />
      </div>
      <div className="flex justify-between font-mono text-[11px] text-muted-foreground">
        <span>
          seen {count}/{window} in window
        </span>
        <span className={ok ? "text-green-700" : "font-semibold text-red-600"}>
          threshold {minCount}
        </span>
      </div>
    </div>
  )
}

export function AttributeRow({ attribute }: { attribute: AttributeResult }) {
  return (
    <div className="grid grid-cols-1 gap-2 py-2 sm:grid-cols-[16rem_1fr_auto] sm:items-center">
      <div>
        <div className="text-sm font-medium">{ATTRIBUTE_LABELS[attribute.name] ?? attribute.name}</div>
        <div className="font-mono text-[11px] text-muted-foreground">
          {attribute.name} · {ATTRIBUTE_DESCRIPTIONS[attribute.name] ?? attribute.kind}
        </div>
        <div className="mt-0.5 font-mono text-sm font-semibold">{String(attribute.decoy_value)}</div>
      </div>
      <div>
        {attribute.no_window ? (
          <p className="text-xs text-muted-foreground">no window data — cannot certify</p>
        ) : attribute.kind === "numeric" && attribute.band ? (
          <BandGauge attribute={attribute} />
        ) : (
          <FrequencyBar attribute={attribute} />
        )}
      </div>
      <div className="sm:text-right">
        <StatusBadge attribute={attribute} />
      </div>
    </div>
  )
}

export function AttributeComparison({
  attributes,
  title = "Decoy vs real window",
}: {
  attributes: AttributeResult[]
  title?: string
}) {
  return (
    <div className="divide-y divide-border rounded-lg border">
      <div className="bg-muted/50 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        {title}
      </div>
      <div className="divide-y divide-border px-4">
        {attributes.map((attribute) => (
          <AttributeRow key={attribute.name} attribute={attribute} />
        ))}
      </div>
    </div>
  )
}
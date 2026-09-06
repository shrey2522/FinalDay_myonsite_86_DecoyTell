import { ATTRIBUTE_LABELS, type PairFinding } from "@/lib/types"
import { cn } from "@/lib/utils"

export function PairHeatmap({ pairs }: { pairs: PairFinding[] }) {
  const attrs = ["service_banner", "patch_cadence_days", "timing_band", "account_age_days", "monitoring_behavior"]
  const byPair = new Map<string, PairFinding>()
  for (const pair of pairs) {
    byPair.set(`${pair.attr_a}::${pair.attr_b}`, pair)
    byPair.set(`${pair.attr_b}::${pair.attr_a}`, pair)
  }

  const cellClass = (pair: PairFinding | undefined) => {
    if (!pair) return "bg-transparent"
    if (pair.fingerprint) return "bg-red-200/80 text-red-900"
    if (pair.expected >= 1) return "bg-green-100/80 text-green-900"
    return "bg-slate-100 text-slate-500"
  }

  const cellTitle = (pair: PairFinding | undefined) => {
    if (!pair) return ""
    const a = ATTRIBUTE_LABELS[pair.attr_a] ?? pair.attr_a
    const b = ATTRIBUTE_LABELS[pair.attr_b] ?? pair.attr_b
    if (pair.fingerprint) {
      return `FINGERPRINT: ${a}=${pair.value_a} + ${b}=${pair.value_b} — the real asset should have shown this (expected ${pair.expected}) but never did (observed ${pair.observed}).`
    }
    if (pair.expected < 1) {
      return `${a} × ${b}: combination out of the real asset's range (expected ${pair.expected}) — not judged.`
    }
    return `${a} × ${b}: observed ${pair.observed} of expected ${pair.expected} — consistent with the real asset.`
  }

  return (
    <div className="space-y-2">
      <div className="inline-block rounded-lg border">
        <table className="border-collapse">
          <thead>
            <tr>
              <th className="p-1.5" />
              {attrs.map((attr) => (
                <th key={attr} className="px-1.5 pb-1.5 text-center">
                  <span className="block max-w-16 truncate font-mono text-[10px] font-medium text-muted-foreground" title={ATTRIBUTE_LABELS[attr]}>
                    {attr.split("_").slice(0, -1).join(" ") || attr}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {attrs.map((rowAttr, rowIndex) => (
              <tr key={rowAttr}>
                <td className="pr-1.5 text-right">
                  <span className="font-mono text-[10px] text-muted-foreground" title={ATTRIBUTE_LABELS[rowAttr]}>
                    {rowAttr.split("_")[0]}
                  </span>
                </td>
                {attrs.map((colAttr, colIndex) => {
                  const pair = byPair.get(`${rowAttr}::${colAttr}`)
                  const isSelf = rowAttr === colAttr
                  return (
                    <td key={colAttr} className="p-0.5">
                      {isSelf || colIndex < rowIndex ? (
                        <div className={cn("size-8 rounded", isSelf ? "bg-muted" : "bg-transparent")} />
                      ) : (
                        <div
                          className={cn("flex size-8 items-center justify-center rounded font-mono text-[10px] font-semibold", cellClass(pair))}
                          title={cellTitle(pair)}
                        >
                          {pair?.fingerprint ? "!" : pair && pair.expected >= 1 ? "✓" : "·"}
                        </div>
                      )}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
        <span className="flex items-center gap-1.5">
          <span className="inline-block size-3 rounded bg-green-100/80" /> combination occurs as expected
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block size-3 rounded bg-red-200/80" /> fingerprint (never shown by real asset)
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block size-3 rounded bg-slate-100" /> out of range — not judged
        </span>
      </div>
    </div>
  )
}
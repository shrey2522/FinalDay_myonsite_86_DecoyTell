import { Badge } from "@/components/ui/badge"
import type { Verdict } from "@/lib/types"

const styles: Record<Verdict, string> = {
  PASS: "border-transparent bg-green-100 text-green-800",
  CORRECTED: "border-transparent bg-amber-100 text-amber-800",
  UNSAFE: "border-transparent bg-red-100 text-red-800",
  INSUFFICIENT_DATA: "border-transparent bg-slate-200 text-slate-700",
  UNREACHABLE: "border-transparent bg-slate-200 text-slate-700",
}

export function VerdictBadge({ verdict }: { verdict: Verdict }) {
  return (
    <Badge className={styles[verdict] ?? styles.UNREACHABLE}>{verdict}</Badge>
  )
}
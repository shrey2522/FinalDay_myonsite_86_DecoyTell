import { Badge } from "@/components/ui/badge"
import type { Verdict } from "@/lib/types"
import { cn } from "@/lib/utils"

const styles: Record<Verdict, string> = {
  PASS: "border-transparent bg-green-100 text-green-800",
  CORRECTED: "border-transparent bg-amber-100 text-amber-800",
  CORRECTED_PARTIAL: "border-transparent bg-orange-100 text-orange-800",
  UNSAFE: "border-transparent bg-red-100 text-red-800",
  INSUFFICIENT_DATA: "border-transparent bg-slate-200 text-slate-700",
  STALE_DATA: "border-transparent bg-violet-100 text-violet-800",
  MIRRORING_REQUIRED: "border-transparent bg-purple-100 text-purple-800",
  UNREACHABLE: "border-transparent bg-slate-200 text-slate-700",
}

const dotStyles: Record<Verdict, string> = {
  PASS: "bg-green-600",
  CORRECTED: "bg-amber-500",
  CORRECTED_PARTIAL: "bg-orange-500",
  UNSAFE: "bg-red-600",
  INSUFFICIENT_DATA: "bg-slate-400",
  STALE_DATA: "bg-violet-500",
  MIRRORING_REQUIRED: "bg-purple-500",
  UNREACHABLE: "bg-slate-400",
}

export function VerdictBadge({ verdict, dot = false }: { verdict: Verdict; dot?: boolean }) {
  return (
    <Badge className={styles[verdict] ?? styles.UNREACHABLE}>
      {dot && <span className={cn("size-1.5 rounded-full", dotStyles[verdict] ?? dotStyles.UNREACHABLE)} />}
      {verdict}
    </Badge>
  )
}

const explanations: Record<Verdict, string> = {
  PASS: "No drift: the decoy matches the real asset within every tolerance.",
  CORRECTED: "Drift was found, scoped corrections were applied, and the decoy re-verified clean.",
  CORRECTED_PARTIAL: "Drift was corrected, but at least one fix could not be applied on the live decoy.",
  UNSAFE: "Drift cannot be corrected (non-correctable attribute or budget exhausted). Do not expose.",
  INSUFFICIENT_DATA: "Too few recent observations to certify — the tool refuses to guess.",
  STALE_DATA: "The real asset has not been observed recently; the window is stale.",
  MIRRORING_REQUIRED: "The real asset is dark while the decoy answers — differential availability is itself a fingerprint.",
  UNREACHABLE: "The decoy could not be probed.",
}

export function verdictExplanation(verdict: Verdict): string {
  return explanations[verdict] ?? "Unknown verdict."
}
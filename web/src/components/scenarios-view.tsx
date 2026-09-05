import { useState } from "react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
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
import type { Fix, ScenarioReport } from "@/lib/types"

import { VerdictBadge } from "./verdict-badge"

function FixRow({ fix }: { fix: Fix }) {
  return (
    <TableRow>
      <TableCell className="font-mono">{fix.attribute}</TableCell>
      <TableCell className="font-mono">{String(fix.before)}</TableCell>
      <TableCell className="font-mono">{String(fix.after)}</TableCell>
      <TableCell>{fix.action}</TableCell>
      <TableCell>
        {fix.applied === undefined ? (
          <Badge variant="secondary">{fix.re_verified ? "re-verified" : "applied"}</Badge>
        ) : fix.applied ? (
          <Badge className="bg-green-100 text-green-800">applied</Badge>
        ) : (
          <Badge className="bg-red-100 text-red-800">cannot apply{fix.reason ? `: ${fix.reason}` : ""}</Badge>
        )}
      </TableCell>
    </TableRow>
  )
}

export function ScenariosView() {
  const { data, error, loading } = usePolling<ScenarioReport[]>(() => api.scenarios(), 5000)
  const [selected, setSelected] = useState<ScenarioReport | null>(null)

  if (loading) return <p className="text-muted-foreground">Loading…</p>
  if (error) return <p className="text-destructive">API error: {error}</p>
  if (!data) return null

  return (
    <div className="space-y-4">
      {data.map((report) => (
        <div key={report.scenario_id} className="flex items-center justify-between rounded-lg border px-4 py-3">
          <div>
            <div className="font-mono text-sm font-medium">{report.scenario_id}</div>
            <div className="text-muted-foreground text-xs">{report.note}</div>
          </div>
          <div className="flex items-center gap-3">
            <VerdictBadge verdict={report.verdict} />
            <Button variant="outline" size="sm" onClick={() => setSelected(report)}>
              Report
            </Button>
          </div>
        </div>
      ))}

      <Dialog open={selected !== null} onOpenChange={(open) => { if (!open) setSelected(null) }}>
        <DialogContent className="max-h-[80vh] overflow-y-auto sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle className="font-mono">{selected?.scenario_id}</DialogTitle>
            <DialogDescription>{selected?.note}</DialogDescription>
          </DialogHeader>
          {selected && (
            <div className="space-y-6">
              <div>
                <h4 className="mb-2 text-sm font-semibold">Attributes (decoy vs real window)</h4>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Attribute</TableHead>
                      <TableHead>Decoy value</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Real reference</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {selected.attributes.map((attribute) => (
                      <TableRow key={attribute.name}>
                        <TableCell className="font-mono">{attribute.name}</TableCell>
                        <TableCell className="font-mono">{String(attribute.decoy_value)}</TableCell>
                        <TableCell>
                          {attribute.in_tolerance === null ? (
                            <Badge variant="secondary">no data</Badge>
                          ) : attribute.in_tolerance ? (
                            <Badge className="bg-green-100 text-green-800">OK</Badge>
                          ) : (
                            <Badge className="bg-red-100 text-red-800">DRIFT</Badge>
                          )}
                        </TableCell>
                        <TableCell className="text-muted-foreground text-xs">
                          {attribute.kind === "numeric"
                            ? `in [${attribute.band?.[0]}, ${attribute.band?.[1]}] ${attribute.unit ?? ""}`
                            : `seen ${attribute.count}/${attribute.window_size}`}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              <div>
                <h4 className="mb-2 text-sm font-semibold">Joint check (pairs)</h4>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Pair</TableHead>
                      <TableHead>Observed</TableHead>
                      <TableHead>Expected</TableHead>
                      <TableHead>Fingerprint</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {selected.pairs.map((pair) => (
                      <TableRow key={`${pair.attr_a}-${pair.attr_b}`}>
                        <TableCell className="font-mono">
                          {pair.attr_a}={String(pair.value_a)}, {pair.attr_b}={String(pair.value_b)}
                        </TableCell>
                        <TableCell>{pair.observed}</TableCell>
                        <TableCell>{pair.expected}</TableCell>
                        <TableCell>
                          {pair.fingerprint ? (
                            <Badge className="bg-red-100 text-red-800">structurally absent</Badge>
                          ) : (
                            <Badge variant="secondary">—</Badge>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              {selected.corrections.length > 0 && (
                <div>
                  <h4 className="mb-2 text-sm font-semibold">Corrections (with reasoning)</h4>
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
                      {selected.corrections.map((fix, index) => (
                        <FixRow key={index} fix={fix} />
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}

              {selected.blocked_attributes.length > 0 && (
                <p className="text-destructive text-sm">
                  Blocked (not correctable): {selected.blocked_attributes.join(", ")}
                </p>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
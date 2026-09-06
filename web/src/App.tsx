import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

import { LiveLoopView } from "@/components/live-loop-view"
import { LoopControlBar } from "@/components/loop-control-bar"
import { ObservationsView } from "@/components/observations-view"
import { PairMatrixView } from "@/components/pair-matrix-view"
import { ReconView } from "@/components/recon-view"
import { ScenariosView } from "@/components/scenarios-view"
import { WorkflowView } from "@/components/workflow-view"

export default function App() {
  return (
    <div className="min-h-screen bg-background p-6">
      <header className="mb-4">
        <h1 className="text-2xl font-bold tracking-tight">DecoyTell</h1>
        <p className="text-muted-foreground text-sm">
          Bounded deception-surface consistency verification — keeps a decoy statistically
          indistinguishable from the real asset it impersonates
        </p>
      </header>

      <div className="mb-4">
        <LoopControlBar />
      </div>

      <Tabs defaultValue="workflow">
        <TabsList className="mb-4">
          <TabsTrigger value="workflow">Workflow</TabsTrigger>
          <TabsTrigger value="recon">Attacker recon</TabsTrigger>
          <TabsTrigger value="scenarios">Scenarios</TabsTrigger>
          <TabsTrigger value="loop">Live loop</TabsTrigger>
          <TabsTrigger value="pairs">Pair matrix</TabsTrigger>
          <TabsTrigger value="observations">Observations</TabsTrigger>
        </TabsList>
        <TabsContent value="workflow">
          <WorkflowView />
        </TabsContent>
        <TabsContent value="recon">
          <ReconView />
        </TabsContent>
        <TabsContent value="scenarios">
          <ScenariosView />
        </TabsContent>
        <TabsContent value="loop">
          <LiveLoopView />
        </TabsContent>
        <TabsContent value="pairs">
          <PairMatrixView />
        </TabsContent>
        <TabsContent value="observations">
          <ObservationsView />
        </TabsContent>
      </Tabs>
    </div>
  )
}
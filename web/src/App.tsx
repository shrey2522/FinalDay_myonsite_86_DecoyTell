import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

import { DashboardView } from "@/components/dashboard-view"
import { LiveLoopView } from "@/components/live-loop-view"
import { ObservationsView } from "@/components/observations-view"
import { PairMatrixView } from "@/components/pair-matrix-view"
import { ScenariosView } from "@/components/scenarios-view"

export default function App() {
  return (
    <div className="min-h-screen bg-background p-6">
      <header className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight">DecoyTell Dashboard</h1>
        <p className="text-muted-foreground text-sm">
          Bounded deception-surface consistency verification — monitoring, documentation, and
          drift tracking
        </p>
      </header>

      <Tabs defaultValue="dashboard">
        <TabsList className="mb-4">
          <TabsTrigger value="dashboard">Dashboard</TabsTrigger>
          <TabsTrigger value="scenarios">Scenarios</TabsTrigger>
          <TabsTrigger value="loop">Live loop</TabsTrigger>
          <TabsTrigger value="pairs">Pair matrix</TabsTrigger>
          <TabsTrigger value="observations">Observations</TabsTrigger>
        </TabsList>
        <TabsContent value="dashboard">
          <DashboardView />
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
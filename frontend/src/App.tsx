import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import Index from "./pages/Index.tsx";
import DocumentsPage from "./pages/DocumentsPage.tsx";
import NotFound from "./pages/NotFound.tsx";
import SalesAgent from "./pages/SalesAgent.tsx";
import SimulationLive from "./pages/SimulationLive.tsx";
import SupplyChainAgent from "./pages/SupplyChainAgent.tsx";
import DeepSimulationLive from "./pages/DeepSimulationLive.tsx";
import NetworkSimulationLive from "./pages/NetworkSimulationLive.tsx";
import SalesSupplyDebateSimulator from "./pages/SalesSupplyDebateSimulator.tsx";
import SimulatorsHub from "./pages/SimulatorsHub.tsx";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Index />} />
          <Route path="/documents" element={<DocumentsPage />} />
          {/* feature/salesAgent + simulator: standalone UIs (not embedded in main decision view) */}
          <Route path="/simulators" element={<SimulatorsHub />} />
          <Route path="/simulation-live" element={<SimulationLive />} />
          <Route path="/agents/sales" element={<SalesAgent />} />
          <Route path="/agents/supply-chain" element={<SupplyChainAgent />} />
          <Route path="/simulation-deep" element={<DeepSimulationLive />} />
          <Route path="/simulation-network" element={<NetworkSimulationLive />} />
          <Route path="/simulation-sales-supply-debate" element={<SalesSupplyDebateSimulator />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;

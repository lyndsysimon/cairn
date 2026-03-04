import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Layout } from "./components/Layout";
import { AgentListPage } from "./pages/AgentListPage";
import { CreateAgentPage } from "./pages/CreateAgentPage";
import { AgentDetailPage } from "./pages/AgentDetailPage";
import { ProviderListPage } from "./pages/ProviderListPage";
import { CreateProviderPage } from "./pages/CreateProviderPage";
import { ProviderDetailPage } from "./pages/ProviderDetailPage";

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<AgentListPage />} />
          <Route path="agents/new" element={<CreateAgentPage />} />
          <Route path="agents/:id" element={<AgentDetailPage />} />
          <Route path="providers" element={<ProviderListPage />} />
          <Route path="providers/new" element={<CreateProviderPage />} />
          <Route path="providers/:id" element={<ProviderDetailPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

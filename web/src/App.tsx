import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Layout } from "./components/Layout";
import { AgentListPage } from "./pages/AgentListPage";
import { CreateAgentPage } from "./pages/CreateAgentPage";
import { AgentDetailPage } from "./pages/AgentDetailPage";
import { ProviderListPage } from "./pages/ProviderListPage";
import { CreateProviderPage } from "./pages/CreateProviderPage";
import { ProviderDetailPage } from "./pages/ProviderDetailPage";
import { CredentialListPage } from "./pages/CredentialListPage";
import { CreateCredentialPage } from "./pages/CreateCredentialPage";
import { CredentialDetailPage } from "./pages/CredentialDetailPage";
import { RunDetailPage } from "./pages/RunDetailPage";

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
          <Route path="credentials" element={<CredentialListPage />} />
          <Route path="credentials/new" element={<CreateCredentialPage />} />
          <Route path="credentials/:id" element={<CredentialDetailPage />} />
          <Route path="runs/:runId" element={<RunDetailPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

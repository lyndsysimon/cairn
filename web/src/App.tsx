import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Layout } from "./components/Layout";
import { AgentListPage } from "./pages/AgentListPage";
import { CreateAgentPage } from "./pages/CreateAgentPage";
import { AgentDetailPage } from "./pages/AgentDetailPage";

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<AgentListPage />} />
          <Route path="agents/new" element={<CreateAgentPage />} />
          <Route path="agents/:id" element={<AgentDetailPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

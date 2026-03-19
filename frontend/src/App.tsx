import { NavLink, Outlet, Route, Routes, useLocation } from "react-router-dom";
import { HomePage } from "./pages/HomePage";
import { UploadRunPage } from "./pages/UploadRunPage";
import { RunLayout } from "./pages/RunLayout";
import { InputAnalysisPage } from "./pages/InputAnalysisPage";
import { ValidationPage } from "./pages/ValidationPage";
import { SummaryPage } from "./pages/SummaryPage";
import { PlaceholderPage } from "./pages/PlaceholderPage";
import { MapPage } from "./pages/MapPage";
import { WarehousePage } from "./pages/WarehousePage";
import { CustomerPage } from "./pages/CustomerPage";
import { RoutePage } from "./pages/RoutePage";
import { GraphPage } from "./pages/GraphPage";

const runNav = [
  { to: "", label: "Summary" },
  { to: "input", label: "Input" },
  { to: "validation", label: "Validation" },
  { to: "map", label: "Map" },
  { to: "graph", label: "Graph" },
  { to: "warehouse", label: "Warehouse" },
  { to: "customer", label: "Customer" },
  { to: "route", label: "Route" },
  { to: "compare", label: "Compare" },
  { to: "explain", label: "Explain" },
];

function Shell() {
  const location = useLocation();
  const runMatch = location.pathname.match(/^\/runs\/([^/]+)/);
  const runBase = runMatch ? `/runs/${runMatch[1]}` : null;
  const inRun = Boolean(runBase);
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">Network 3-Tier</div>
        <nav className="nav-group">
          <NavLink to="/" end className="nav-link">
            Home
          </NavLink>
          <NavLink to="/runs/new" className="nav-link">
            Upload & Run
          </NavLink>
        </nav>
        {inRun ? (
          <nav className="nav-group secondary">
            {runNav.map((item) => (
              <NavLink
                key={item.label}
                to={item.to === "" ? runBase! : `${runBase!}/${item.to}`}
                end={item.to === ""}
                className="nav-link"
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        ) : null}
      </aside>
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}

export function App() {
  return (
    <Routes>
      <Route element={<Shell />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/runs/new" element={<UploadRunPage />} />
        <Route path="/runs/:runId" element={<RunLayout />}>
          <Route index element={<SummaryPage />} />
          <Route path="input" element={<InputAnalysisPage />} />
          <Route path="validation" element={<ValidationPage />} />
          <Route path="map" element={<MapPage />} />
          <Route path="graph" element={<GraphPage />} />
          <Route path="warehouse" element={<WarehousePage />} />
          <Route path="customer" element={<CustomerPage />} />
          <Route path="route" element={<RoutePage />} />
          <Route path="compare" element={<PlaceholderPage title="Scenario Compare" />} />
          <Route path="explain" element={<PlaceholderPage title="Explain" />} />
        </Route>
      </Route>
    </Routes>
  );
}

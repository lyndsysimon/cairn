import { NavLink, Outlet } from "react-router-dom";

export function Layout() {
  return (
    <div className="layout">
      <aside className="sidebar">
        <NavLink to="/" className="sidebar-logo">
          Cairn
        </NavLink>
        <nav className="sidebar-nav">
          <NavLink
            to="/chat"
            className={({ isActive }) =>
              `sidebar-link${isActive ? " active" : ""}`
            }
          >
            Chat
          </NavLink>
          <NavLink
            to="/"
            end
            className={({ isActive }) =>
              `sidebar-link${isActive ? " active" : ""}`
            }
          >
            Agents
          </NavLink>
          <NavLink
            to="/providers"
            className={({ isActive }) =>
              `sidebar-link${isActive ? " active" : ""}`
            }
          >
            Model Providers
          </NavLink>
          <NavLink
            to="/credentials"
            className={({ isActive }) =>
              `sidebar-link${isActive ? " active" : ""}`
            }
          >
            Credentials
          </NavLink>
        </nav>
      </aside>
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}

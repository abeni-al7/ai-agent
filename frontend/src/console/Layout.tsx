import { NavLink, Navigate, Outlet } from "react-router-dom";
import { token } from "../api";
import { CommandBar } from "./CommandBar";

export function Layout() {
  if (!token.get()) return <Navigate to="/login" replace />;
  return (
    <div className="console">
      <a className="skip" href="#main">Skip to content</a>
      <header className="rail">
        <NavLink to="/" className="brand" aria-label="Wekil, today">
          <span className="brand__word">Wekil</span>
          <span className="brand__am" lang="am">ወኪል</span>
        </NavLink>
        <nav aria-label="Console">
          <NavLink to="/" end>Today</NavLink>
          <NavLink to="/queue">Applications</NavLink>
          <NavLink to="/monitoring">Monitoring</NavLink>
        </nav>
        <button className="rail__out" onClick={() => { token.set(null); location.assign("/login"); }}>Sign out</button>
      </header>
      <div className="console__body">
        <CommandBar />
        <main id="main" tabIndex={-1}><Outlet /></main>
      </div>
    </div>
  );
}

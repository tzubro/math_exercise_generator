import { useEffect, useState } from "react";
import { getApiHealth } from "./lib/api";
import ExerciseBank from "./features/exercises/ExerciseBank";
import TestBuilder from "./features/tests/TestBuilder";

type ConnectionState = "checking" | "connected" | "unavailable";

export default function App() {
  const [connection, setConnection] = useState<ConnectionState>("checking");
  const [activeView, setActiveView] = useState<"bank" | "builder">("bank");

  useEffect(() => {
    let active = true;

    getApiHealth()
      .then(() => {
        if (active) setConnection("connected");
      })
      .catch(() => {
        if (active) setConnection("unavailable");
      });

    return () => {
      active = false;
    };
  }, []);

  return (
    <main className="app-shell">
      <header className="top-bar">
        <span className="brand-mark" aria-hidden="true">∑</span>
        <span className="brand-name">Math Test Generator</span>
        <nav className="main-nav" aria-label="Main navigation">
          <button
            aria-current={activeView === "bank" ? "page" : undefined}
            className={activeView === "bank" ? "nav-button nav-button-active" : "nav-button"}
            onClick={() => setActiveView("bank")}
            type="button"
          >
            Exercise bank
          </button>
          <button
            aria-current={activeView === "builder" ? "page" : undefined}
            className={activeView === "builder" ? "nav-button nav-button-active" : "nav-button"}
            onClick={() => setActiveView("builder")}
            type="button"
          >
            Create a test
          </button>
        </nav>
        <span className={`connection connection-${connection}`}>
          <span className="connection-dot" />
          {connection === "checking"
            ? "Connecting"
            : connection === "connected"
              ? "Local app ready"
              : "Backend unavailable"}
        </span>
      </header>

      {activeView === "bank" ? <ExerciseBank /> : <TestBuilder />}
    </main>
  );
}

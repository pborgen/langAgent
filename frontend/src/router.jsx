import { Link, Outlet, createRootRoute, createRoute, createRouter, redirect } from "@tanstack/react-router";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { SupportProvider, useSupport } from "./supportContext";

function RootLayout() {
  return (
    <SupportProvider>
      <main className="app-shell">
        <div className="bg-grid" aria-hidden="true" />

        <section className="panel hero">
          <p className="eyebrow">React + TanStack + FastAPI</p>
          <h1>SupportPilot Console</h1>
          <p className="subtitle">
            Customer support agent demo with LangGraph routing, tools, and human-in-the-loop approval.
          </p>
          <nav className="tabs" aria-label="Primary">
            <Link to="/chat" className="tab" activeProps={{ className: "tab active" }}>
              Chat
            </Link>
            <Link to="/settings" className="tab" activeProps={{ className: "tab active" }}>
              Settings
            </Link>
            <Link to="/analytics" className="tab" activeProps={{ className: "tab active" }}>
              Analytics
            </Link>
          </nav>
        </section>

        <Outlet />
      </main>
    </SupportProvider>
  );
}

function MessageBubble({ kind, text }) {
  return <div className={`msg ${kind}`}>{text}</div>;
}

function ChatPage() {
  const {
    sessionId,
    setSessionId,
    customerId,
    setCustomerId,
    status,
    handoffSummary,
    messages,
    canApprove,
    isSending,
    isApproving,
    sendMessage,
    approveEscalation,
  } = useSupport();
  const [input, setInput] = useState("");

  const onSubmit = (event) => {
    event.preventDefault();
    if (sendMessage(input)) {
      setInput("");
    }
  };

  return (
    <>
      <section className="panel controls">
        <div className="field-row">
          <label>
            Session ID
            <input value={sessionId} onChange={(e) => setSessionId(e.target.value)} />
          </label>
          <label>
            Customer ID
            <input value={customerId} onChange={(e) => setCustomerId(e.target.value)} />
          </label>
        </div>

        <div className="status-row">
          <span className="label">Agent Status</span>
          <span className={`badge ${status}`}>{status}</span>
        </div>

        {handoffSummary ? <div className="handoff">Handoff Summary: {handoffSummary}</div> : null}
      </section>

      <section className="panel chat">
        <div className="chat-log">
          {messages.map((msg) => (
            <MessageBubble key={msg.id} kind={msg.kind} text={msg.text} />
          ))}
        </div>

        <form className="composer" onSubmit={onSubmit}>
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            rows={3}
            required
            placeholder="Ask about orders, shipping, returns, appointments, or escalation..."
          />

          <div className="actions">
            <button type="submit" disabled={isSending}>
              {isSending ? "Sending..." : "Send"}
            </button>
            {canApprove ? (
              <button type="button" className="secondary" onClick={approveEscalation} disabled={isApproving}>
                {isApproving ? "Approving..." : "Approve Escalation"}
              </button>
            ) : null}
          </div>
        </form>
      </section>
    </>
  );
}

function SettingsPage() {
  const { sessionId, setSessionId, customerId, setCustomerId, resetConversation } = useSupport();

  return (
    <section className="panel settings">
      <h2>Session Settings</h2>
      <p className="subtitle">Update defaults used for API payloads in this browser session.</p>
      <div className="field-row">
        <label>
          Session ID
          <input value={sessionId} onChange={(e) => setSessionId(e.target.value)} />
        </label>
        <label>
          Customer ID
          <input value={customerId} onChange={(e) => setCustomerId(e.target.value)} />
        </label>
      </div>
      <div className="actions left">
        <button type="button" className="secondary" onClick={resetConversation}>
          Reset Conversation
        </button>
      </div>
    </section>
  );
}

function AnalyticsPage() {
  const { stats, sessionId, apiBase } = useSupport();
  const summaryQuery = useQuery({
    queryKey: ["analytics-summary", sessionId, apiBase],
    queryFn: async () => {
      const params = new URLSearchParams({ session_id: sessionId });
      const res = await fetch(`${apiBase}/v1/analytics/summary?${params.toString()}`);
      if (!res.ok) {
        throw new Error(`Analytics request failed: ${res.status}`);
      }
      return res.json();
    },
  });

  const summary = summaryQuery.data;

  return (
    <section className="panel analytics">
      <h2>Conversation Analytics</h2>
      <p className="subtitle">Quick support-agent metrics from frontend state + backend API.</p>
      <div className="stats-grid">
        <article className="stat-card">
          <h3>Total Messages</h3>
          <p>{stats.totalMessages}</p>
        </article>
        <article className="stat-card">
          <h3>User Messages</h3>
          <p>{stats.userMessages}</p>
        </article>
        <article className="stat-card">
          <h3>Agent Messages</h3>
          <p>{stats.agentMessages}</p>
        </article>
        <article className="stat-card">
          <h3>Escalations (API)</h3>
          <p>{summary ? summary.escalations : "-"}</p>
        </article>
        <article className="stat-card">
          <h3>Awaiting Approval (API)</h3>
          <p>{summary ? summary.awaiting_approval : "-"}</p>
        </article>
        <article className="stat-card">
          <h3>Tool Calls (API)</h3>
          <p>{summary ? summary.tool_calls : "-"}</p>
        </article>
      </div>
      {summaryQuery.isError ? <p className="subtitle">Analytics API unavailable. Showing local stats only.</p> : null}
    </section>
  );
}

const rootRoute = createRootRoute({ component: RootLayout });

const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  beforeLoad: () => {
    throw redirect({ to: "/chat" });
  },
});

const chatRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/chat",
  component: ChatPage,
});

const settingsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/settings",
  component: SettingsPage,
});

const analyticsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/analytics",
  component: AnalyticsPage,
});

const routeTree = rootRoute.addChildren([indexRoute, chatRoute, settingsRoute, analyticsRoute]);

export const router = createRouter({ routeTree });

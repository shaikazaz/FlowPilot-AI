
import { useCallback, useEffect, useState } from "react";
import "./App.css";

const API = (
  import.meta.env.VITE_API_BASE_URL ||
  "http://127.0.0.1:8000/api/requests"
).replace(/\/+$/, "");

const STATUSES = ["Pending", "In Progress", "Completed"];
const PRIORITIES = ["Low", "Medium", "High"];

async function api(path = "", options = {}) {
  const token = localStorage.getItem("token");
  let response;

  try {
    response = await fetch(`${API}/${path}`, {
      ...options,
      headers: {
        Accept: "application/json",
        ...(options.body ? { "Content-Type": "application/json" } : {}),
        ...(token ? { Authorization: `Token ${token}` } : {}),
        ...options.headers,
      },
    });
  } catch {
    throw new Error(
      "Cannot connect to Django. Check that the backend is running."
    );
  }

  if (response.status === 204) {
    if (!response.ok) throw new Error("Request failed.");
    return {};
  }

  const text = await response.text();
  let data = {};

  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = { detail: text };
  }

  if (!response.ok) {
    throw new Error(
      data.error ||
        data.detail ||
        data.message ||
        Object.values(data).flat().join(" ") ||
        `Request failed (${response.status}).`
    );
  }

  return data;
}

function normalizeList(data) {
  if (Array.isArray(data)) {
    return {
      results: data,
      count: data.length,
      next: null,
      previous: null,
    };
  }

  return {
    results: data?.results || [],
    count: data?.count ?? data?.results?.length ?? 0,
    next: data?.next ?? null,
    previous: data?.previous ?? null,
  };
}

function priorityClass(value) {
  return String(value || "Medium")
    .toLowerCase()
    .replace(/\s+/g, "-");
}

function dateText(value) {
  if (!value) return "Date unavailable";

  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "Date unavailable"
    : date.toLocaleDateString();
}

function ticketSolution(ticket) {
  return String(ticket.resolution ?? ticket.solution ?? "").trim();
}

export default function App() {
  const [token, setToken] = useState(
    () => localStorage.getItem("token") || ""
  );
  const [role, setRole] = useState(
    () => localStorage.getItem("role") || "User"
  );
  const [username, setUsername] = useState(
    () => localStorage.getItem("username") || ""
  );

  const [page, setPage] = useState("My Requests");
  const [authMode, setAuthMode] = useState("login");
  const [authForm, setAuthForm] = useState({
    username: "",
    email: "",
    name: "",
    password: "",
    confirm_password: "",
  });

  const [issue, setIssue] = useState("");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");

  const [tickets, setTickets] = useState([]);
  const [analytics, setAnalytics] = useState({});
  const [pagination, setPagination] = useState({
    count: 0,
    next: null,
    previous: null,
  });
  const [currentPage, setCurrentPage] = useState(1);

  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [ordering, setOrdering] = useState("-updated_at");

  const [solutionDrafts, setSolutionDrafts] = useState({});
  const [statusDrafts, setStatusDrafts] = useState({});
  const [priorityDrafts, setPriorityDrafts] = useState({});

  const [loading, setLoading] = useState(false);
  const [dataLoading, setDataLoading] = useState(false);
  const [busyId, setBusyId] = useState(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const owner = role === "Owner";

  function clearNotices() {
    setError("");
    setMessage("");
  }

  const loadData = useCallback(
    async (pageNumber = 1) => {
      if (!token) return;

      setDataLoading(true);
      setError("");

      try {
        const query = new URLSearchParams();
        query.set("page", String(pageNumber));
        query.set("ordering", ordering);

        if (search.trim()) query.set("search", search.trim());
        if (statusFilter) query.set("status", statusFilter);

        if (owner && priorityFilter) {
          query.set("priority", priorityFilter);
        }

        const listPromise = api(`?${query.toString()}`);
        const analyticsPromise = owner
          ? api("analytics/")
          : Promise.resolve(null);

        const [listData, analyticsData] = await Promise.all([
          listPromise,
          analyticsPromise,
        ]);

        const normalized = normalizeList(listData);

        setTickets(normalized.results);
        setPagination({
          count: normalized.count,
          next: normalized.next,
          previous: normalized.previous,
        });
        setCurrentPage(pageNumber);

        if (analyticsData) setAnalytics(analyticsData);
      } catch (err) {
        setError(err.message || "Could not load requests.");
      } finally {
        setDataLoading(false);
      }
    },
    [
      token,
      owner,
      search,
      statusFilter,
      priorityFilter,
      ordering,
    ]
  );

  useEffect(() => {
    if (token) loadData(1);
  }, [token, loadData]);

  function updateAuthForm(event) {
    const { name, value } = event.target;
    setAuthForm((previous) => ({ ...previous, [name]: value }));
  }

  async function authenticate(event) {
    event.preventDefault();
    clearNotices();
    setLoading(true);

    try {
      const endpoint =
        authMode === "register" ? "register/" : "login/";

      const payload =
        authMode === "register"
          ? authForm
          : {
              username: authForm.username,
              password: authForm.password,
            };

      const result = await api(endpoint, {
        method: "POST",
        body: JSON.stringify(payload),
      });

      if (authMode === "register") {
        setMessage("Account created. Please sign in.");
        setAuthMode("login");
        setAuthForm((previous) => ({
          ...previous,
          password: "",
          confirm_password: "",
        }));
        return;
      }

      localStorage.setItem("token", result.token);
      localStorage.setItem("username", result.username);
      localStorage.setItem("role", result.role || "User");

      setToken(result.token);
      setUsername(result.username);
      setRole(result.role || "User");
      setPage(result.role === "Owner" ? "Overview" : "My Requests");
      setMessage("Signed in successfully.");
    } catch (err) {
      setError(err.message || "Authentication failed.");
    } finally {
      setLoading(false);
    }
  }

  async function logout() {
    clearNotices();

    try {
      await api("logout/", { method: "POST" });
    } catch {
      // Clear the local session even if the backend is unavailable.
    }

    localStorage.removeItem("token");
    localStorage.removeItem("username");
    localStorage.removeItem("role");

    setToken("");
    setUsername("");
    setRole("User");
    setTickets([]);
    setAnalytics({});
    setAnswer("");
    setQuestion("");
    setPage("My Requests");
    setMessage("You have been signed out.");
  }

  async function createTicket(event) {
    event.preventDefault();
    clearNotices();

    if (!issue.trim()) {
      setError("Please describe your issue.");
      return;
    }

    setLoading(true);

    try {
      const result = await api("", {
        method: "POST",
        body: JSON.stringify({ issue: issue.trim() }),
      });

      setIssue("");
      setMessage(
        result.message || "Your AI-generated request was created."
      );
      setPage("My Requests");
      await loadData(1);
    } catch (err) {
      setError(err.message || "Could not create the request.");
    } finally {
      setLoading(false);
    }
  }

  async function updateTicket(id, changes) {
    clearNotices();
    setBusyId(id);

    try {
      await api(`${id}/`, {
        method: "PATCH",
        body: JSON.stringify(changes),
      });

      setMessage(`Request #${id} updated successfully.`);
      await loadData(currentPage);
    } catch (err) {
      setError(err.message || "Could not update the request.");
    } finally {
      setBusyId(null);
    }
  }

  async function deleteTicket(id) {
    if (!window.confirm(`Delete request #${id}? This cannot be undone.`)) {
      return;
    }

    clearNotices();
    setBusyId(id);

    try {
      await api(`${id}/`, { method: "DELETE" });
      setMessage(`Request #${id} deleted.`);
      await loadData(currentPage);
    } catch (err) {
      setError(err.message || "Could not delete the request.");
    } finally {
      setBusyId(null);
    }
  }

  async function askPolicy(event) {
    event.preventDefault();
    clearNotices();

    if (!question.trim()) return;

    setLoading(true);
    setAnswer("");

    try {
      const result = await api("chat/", {
        method: "POST",
        body: JSON.stringify({ question: question.trim() }),
      });

      setAnswer(
        result.answer || "No answer was returned by the policy assistant."
      );
    } catch (err) {
      setError(err.message || "Policy AI could not respond.");
    } finally {
      setLoading(false);
    }
  }

  function applyFilters(event) {
    event.preventDefault();
    setSearch(searchInput.trim());
  }

  function clearFilters() {
    setSearchInput("");
    setSearch("");
    setStatusFilter("");
    setPriorityFilter("");
    setOrdering("-updated_at");
  }

  if (!token) {
    return (
      <main className="auth-page">
        <section className="auth-card">
          <div className="brand-mark">F</div>
          <p className="eyebrow">BUSINESS WORKSPACE</p>
          <h1>FlowPilot AI</h1>
          <p className="muted">
            Clearer business requests, powered by AI.
          </p>

          {error && <div className="notice error">{error}</div>}
          {message && <div className="notice success">{message}</div>}

          <div className="auth-tabs">
            <button
              type="button"
              className={authMode === "login" ? "active" : ""}
              onClick={() => {
                clearNotices();
                setAuthMode("login");
              }}
            >
              Sign in
            </button>
            <button
              type="button"
              className={authMode === "register" ? "active" : ""}
              onClick={() => {
                clearNotices();
                setAuthMode("register");
              }}
            >
              Register
            </button>
          </div>

          <form className="stack-form" onSubmit={authenticate}>
            {authMode === "register" && (
              <>
                <label>
                  Full name
                  <input
                    name="name"
                    value={authForm.name}
                    onChange={updateAuthForm}
                    placeholder="Your name"
                    required
                  />
                </label>
                <label>
                  Email
                  <input
                    name="email"
                    type="email"
                    value={authForm.email}
                    onChange={updateAuthForm}
                    placeholder="you@company.com"
                    required
                  />
                </label>
              </>
            )}

            <label>
              Username
              <input
                name="username"
                value={authForm.username}
                onChange={updateAuthForm}
                autoComplete="username"
                required
              />
            </label>

            <label>
              Password
              <input
                name="password"
                type="password"
                value={authForm.password}
                onChange={updateAuthForm}
                autoComplete={
                  authMode === "login"
                    ? "current-password"
                    : "new-password"
                }
                required
              />
            </label>

            {authMode === "register" && (
              <label>
                Confirm password
                <input
                  name="confirm_password"
                  type="password"
                  value={authForm.confirm_password}
                  onChange={updateAuthForm}
                  autoComplete="new-password"
                  required
                />
              </label>
            )}

            <button className="primary full-width" disabled={loading}>
              {loading
                ? "Please wait..."
                : authMode === "login"
                  ? "Sign in"
                  : "Create account"}
            </button>
          </form>
        </section>
      </main>
    );
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">F</div>
          <div>
            <strong>FlowPilot AI</strong>
            <small>BUSINESS WORKSPACE</small>
          </div>
        </div>

        <p className="nav-label">WORKSPACE</p>

        {(owner
          ? ["Overview", "Requests", "Analytics"]
          : ["My Requests", "Create Request", "Policy AI"]
        ).map((item) => (
          <button
            key={item}
            className={`nav-link ${page === item ? "selected" : ""}`}
            onClick={() => {
              clearNotices();
              setPage(item);
            }}
          >
            <span>
              {item === "Overview"
                ? "▦"
                : item === "Requests" || item === "My Requests"
                  ? "☷"
                  : item === "Create Request"
                    ? "+"
                    : item === "Policy AI"
                      ? "✳"
                      : "▥"}
            </span>
            {item}
          </button>
        ))}

        <div className="sidebar-bottom">
          <div className="avatar">
            {(username[0] || "U").toUpperCase()}
          </div>
          <div className="user-meta">
            <strong>{username}</strong>
            <small>{role}</small>
          </div>
          <button className="secondary" onClick={logout}>
            Logout
          </button>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <span>Workspace / {page}</span>
          <span className="connection">● Connected</span>
        </header>

        <div className="content">
          {error && (
            <div className="notice error">
              {error}
              <button onClick={() => setError("")}>×</button>
            </div>
          )}

          {message && (
            <div className="notice success">
              {message}
              <button onClick={() => setMessage("")}>×</button>
            </div>
          )}

          {page === "Overview" && owner && (
            <>
              <p className="eyebrow">OWNER WORKSPACE</p>
              <h1>Overview</h1>
              <p className="muted">
                Monitor and manage all business requests.
              </p>

              <div className="stats-grid">
                <Stat label="All requests" value={analytics.total_requests ?? "—"} />
                <Stat label="Pending" value={analytics.pending_requests ?? "—"} />
                <Stat label="In progress" value={analytics.in_progress_requests ?? "—"} />
                <Stat label="Completed" value={analytics.completed_requests ?? "—"} />
                <Stat label="High priority" value={analytics.high_priority_requests ?? "—"} />
              </div>

              <button
                className="primary"
                onClick={() => setPage("Requests")}
              >
                Manage requests →
              </button>
            </>
          )}

          {page === "My Requests" && !owner && (
            <>
              <div className="page-heading">
                <div>
                  <p className="eyebrow">YOUR WORKSPACE</p>
                  <h1>My Requests</h1>
                  <p className="muted">
                    Track your requests, AI-generated priority, status, and
                    the Owner's solution.
                  </p>
                </div>
                <button
                  className="primary"
                  onClick={() => setPage("Create Request")}
                >
                  + New request
                </button>
              </div>

              <RequestFilters
                searchInput={searchInput}
                setSearchInput={setSearchInput}
                statusFilter={statusFilter}
                setStatusFilter={setStatusFilter}
                ordering={ordering}
                setOrdering={setOrdering}
                applyFilters={applyFilters}
                clearFilters={clearFilters}
                owner={false}
                priorityFilter={priorityFilter}
                setPriorityFilter={setPriorityFilter}
              />

              <p className="muted">
                {pagination.count} matching request(s)
              </p>

              {dataLoading ? (
                <p className="muted">Loading requests...</p>
              ) : tickets.length === 0 ? (
                <EmptyState
                  title="No requests found"
                  description="Create a request or clear your filters."
                />
              ) : (
                <div className="ticket-list">
                  {tickets.map((ticket) => (
                    <article className="ticket-card" key={ticket.id}>
                      <div className="ticket-heading">
                        <div>
                          <p className="ticket-number">
                            REQUEST #{ticket.id}
                          </p>
                          <h3>{ticket.title}</h3>
                          <p className="muted small">
                            {ticket.category || "General"} · Created{" "}
                            {dateText(ticket.created_at)}
                          </p>
                        </div>

                        <div className="priority-display">
                          <span className="field-label">
                            AI-GENERATED PRIORITY
                          </span>
                          <span
                            className={`priority-badge ${priorityClass(
                              ticket.priority
                            )}`}
                          >
                            {ticket.priority || "Medium"}
                          </span>
                        </div>
                      </div>

                      <div className="ticket-description">
                        {ticket.description}
                      </div>

                      <div className="ticket-meta">
                        <div>
                          <span className="field-label">STATUS</span>
                          <span
                            className={`status-badge ${priorityClass(
                              ticket.status
                            )}`}
                          >
                            {ticket.status || "Pending"}
                          </span>
                        </div>
                        <div>
                          <span className="field-label">LAST UPDATED</span>
                          <strong>{dateText(ticket.updated_at)}</strong>
                        </div>
                      </div>

                      <div className="solution-view">
                        <span className="field-label">
                          OWNER RESPONSE / SOLUTION
                        </span>
                        {ticketSolution(ticket) ? (
                          <p>{ticketSolution(ticket)}</p>
                        ) : (
                          <p className="muted">
                            The Owner has not provided a solution yet.
                          </p>
                        )}
                      </div>
                    </article>
                  ))}
                </div>
              )}

              <Pagination
                currentPage={currentPage}
                pagination={pagination}
                dataLoading={dataLoading}
                loadData={loadData}
              />
            </>
          )}

          {page === "Requests" && owner && (
            <>
              <p className="eyebrow">OWNER WORKSPACE</p>
              <h1>Manage requests</h1>
              <p className="muted">
                Review AI-generated tickets and manage their resolution.
              </p>

              <RequestFilters
                searchInput={searchInput}
                setSearchInput={setSearchInput}
                statusFilter={statusFilter}
                setStatusFilter={setStatusFilter}
                ordering={ordering}
                setOrdering={setOrdering}
                applyFilters={applyFilters}
                clearFilters={clearFilters}
                owner
                priorityFilter={priorityFilter}
                setPriorityFilter={setPriorityFilter}
              />

              <p className="muted">
                {pagination.count} matching request(s)
              </p>

              {dataLoading ? (
                <p className="muted">Loading requests...</p>
              ) : tickets.length === 0 ? (
                <EmptyState
                  title="No requests found"
                  description="Try clearing the filters."
                />
              ) : (
                <div className="ticket-list">
                  {tickets.map((ticket) => (
                    <article className="ticket-card" key={ticket.id}>
                      <div className="ticket-heading">
                        <div>
                          <p className="ticket-number">
                            REQUEST #{ticket.id}
                          </p>
                          <h3>{ticket.title}</h3>
                          <p className="muted small">
                            {ticket.username || "User"} · {ticket.category} ·{" "}
                            {dateText(ticket.created_at)}
                          </p>
                        </div>
                        <span className="priority-badge">
                          Current: {ticket.priority}
                        </span>
                      </div>

                      <p className="ticket-description">
                        {ticket.description}
                      </p>

                      <div className="owner-controls">
                        <label>
                          Priority
                          <select
                            value={
                              priorityDrafts[ticket.id] ?? ticket.priority
                            }
                            onChange={(event) =>
                              setPriorityDrafts((previous) => ({
                                ...previous,
                                [ticket.id]: event.target.value,
                              }))
                            }
                          >
                            {PRIORITIES.map((priority) => (
                              <option key={priority} value={priority}>
                                {priority}
                              </option>
                            ))}
                          </select>
                        </label>

                        <label>
                          Status
                          <select
                            value={statusDrafts[ticket.id] ?? ticket.status}
                            onChange={(event) =>
                              setStatusDrafts((previous) => ({
                                ...previous,
                                [ticket.id]: event.target.value,
                              }))
                            }
                          >
                            {STATUSES.map((status) => (
                              <option key={status} value={status}>
                                {status}
                              </option>
                            ))}
                          </select>
                        </label>

                        <button
                          className="primary"
                          disabled={busyId === ticket.id}
                          onClick={() =>
                            updateTicket(ticket.id, {
                              priority:
                                priorityDrafts[ticket.id] ?? ticket.priority,
                              status:
                                statusDrafts[ticket.id] ?? ticket.status,
                            })
                          }
                        >
                          Save status / priority
                        </button>
                      </div>

                      <label className="solution-editor">
                        Owner response / solution
                        <textarea
                          rows={3}
                          value={
                            solutionDrafts[ticket.id] ??
                            ticketSolution(ticket)
                          }
                          onChange={(event) =>
                            setSolutionDrafts((previous) => ({
                              ...previous,
                              [ticket.id]: event.target.value,
                            }))
                          }
                          placeholder="Explain the resolution for the user..."
                        />
                      </label>

                      <div className="button-row">
                        <button
                          className="primary"
                          disabled={busyId === ticket.id}
                          onClick={() =>
                            updateTicket(ticket.id, {
                              resolution:
                                solutionDrafts[ticket.id] ??
                                ticketSolution(ticket),
                            })
                          }
                        >
                          Save solution
                        </button>
                        <button
                          className="danger-button"
                          disabled={busyId === ticket.id}
                          onClick={() => deleteTicket(ticket.id)}
                        >
                          Delete request
                        </button>
                      </div>
                    </article>
                  ))}
                </div>
              )}

              <Pagination
                currentPage={currentPage}
                pagination={pagination}
                dataLoading={dataLoading}
                loadData={loadData}
              />
            </>
          )}

          {page === "Create Request" && !owner && (
            <section className="form-card">
              <p className="eyebrow">AI REQUEST GENERATOR</p>
              <h1>Describe your issue</h1>
              <p className="muted">
                Describe the problem. AI generates the title, organized
                description, category, and recommended priority.
              </p>

              <form className="stack-form" onSubmit={createTicket}>
                <label>
                  Issue description
                  <textarea
                    rows={7}
                    value={issue}
                    onChange={(event) => setIssue(event.target.value)}
                    placeholder="Example: I cannot access the company dashboard after resetting my password..."
                    required
                  />
                </label>

                <button
                  className="primary"
                  disabled={loading || !issue.trim()}
                >
                  {loading ? "Generating ticket..." : "Generate request →"}
                </button>
              </form>
            </section>
          )}

          {page === "Policy AI" && !owner && (
            <section className="form-card">
              <p className="eyebrow">RAG POLICY ASSISTANT</p>
              <h1>Ask company policy</h1>
              <p className="muted">
                Answers are based on information retrieved from the available
                company policy documents.
              </p>

              <div className="suggestions">
                {[
                  "How many annual leave days do employees receive?",
                  "What is the RAM requirement for the application server?",
                ].map((suggestion) => (
                  <button
                    key={suggestion}
                    className="secondary"
                    type="button"
                    onClick={() => setQuestion(suggestion)}
                  >
                    {suggestion}
                  </button>
                ))}
              </div>

              <form className="stack-form" onSubmit={askPolicy}>
                <label>
                  Your question
                  <textarea
                    rows={3}
                    value={question}
                    onChange={(event) => setQuestion(event.target.value)}
                    placeholder="Ask a question about company policy..."
                    required
                  />
                </label>
                <button className="primary" disabled={loading}>
                  {loading ? "Thinking..." : "Ask assistant →"}
                </button>
              </form>

              {answer && (
                <div className="solution-view">
                  <strong>✦ FlowPilot AI</strong>
                  <p>{answer}</p>
                </div>
              )}
            </section>
          )}

          {page === "Analytics" && owner && (
            <>
              <p className="eyebrow">ORGANIZATION INSIGHTS</p>
              <h1>Request analytics</h1>

              <div className="stats-grid">
                <Stat label="All requests" value={analytics.total_requests ?? 0} />
                <Stat label="Pending" value={analytics.pending_requests ?? 0} />
                <Stat label="In progress" value={analytics.in_progress_requests ?? 0} />
                <Stat label="Completed" value={analytics.completed_requests ?? 0} />
                <Stat label="High priority" value={analytics.high_priority_requests ?? 0} />
              </div>

              <section className="form-card">
                <h3>Requests by category</h3>
                {(analytics.category_distribution || []).length === 0 ? (
                  <p className="muted">No category data available yet.</p>
                ) : (
                  (analytics.category_distribution || []).map((item) => (
                    <div className="category-row" key={item.category}>
                      <span>{item.category || "Uncategorized"}</span>
                      <strong>{item.count}</strong>
                    </div>
                  ))
                )}
              </section>
            </>
          )}

          <footer className="footer">
            FlowPilot AI · Django REST Framework · RAG policy assistant
          </footer>
        </div>
      </main>
    </div>
  );
}

function RequestFilters({
  searchInput,
  setSearchInput,
  statusFilter,
  setStatusFilter,
  ordering,
  setOrdering,
  applyFilters,
  clearFilters,
  owner,
  priorityFilter,
  setPriorityFilter,
}) {
  return (
    <form className="filter-card" onSubmit={applyFilters}>
      <input
        value={searchInput}
        onChange={(event) => setSearchInput(event.target.value)}
        placeholder="Search title or request..."
        aria-label="Search requests"
      />

      <div className="filter-grid">
        <label>
          Status
          <select
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value)}
          >
            <option value="">All statuses</option>
            {STATUSES.map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </select>
        </label>

        {owner && (
          <label>
            Priority
            <select
              value={priorityFilter}
              onChange={(event) => setPriorityFilter(event.target.value)}
            >
              <option value="">All priorities</option>
              {PRIORITIES.map((priority) => (
                <option key={priority} value={priority}>
                  {priority}
                </option>
              ))}
            </select>
          </label>
        )}

        <label>
          Sort by
          <select
            value={ordering}
            onChange={(event) => setOrdering(event.target.value)}
          >
            <option value="-updated_at">Recently updated</option>
            <option value="updated_at">Least recently updated</option>
            <option value="-created_at">Newest created</option>
            <option value="created_at">Oldest created</option>
          </select>
        </label>
      </div>

      <div className="button-row">
        <button className="primary" type="submit">
          Apply filters
        </button>
        <button
          className="secondary"
          type="button"
          onClick={clearFilters}
        >
          Clear filters
        </button>
      </div>
    </form>
  );
}

function Pagination({
  currentPage,
  pagination,
  dataLoading,
  loadData,
}) {
  return (
    <div className="pagination">
      <button
        className="secondary"
        disabled={!pagination.previous || dataLoading || currentPage <= 1}
        onClick={() => loadData(currentPage - 1)}
      >
        ← Previous
      </button>
      <span>
        Page {currentPage} · {pagination.count} requests
      </span>
      <button
        className="secondary"
        disabled={!pagination.next || dataLoading}
        onClick={() => loadData(currentPage + 1)}
      >
        Next →
      </button>
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <article className="stat-card">
      <span className="muted">{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

function EmptyState({ title, description }) {
  return (
    <div className="empty-state">
      <h3>{title}</h3>
      <p className="muted">{description}</p>
    </div>
  );
}

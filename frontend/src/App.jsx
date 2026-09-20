import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, compactDate, money, relativeTime } from "./api.js";

/* ── Helpers ─────────────────────────────────────────────── */

function stockMeta(value) {
  if (value === true)  return { label: "In stock",     icon: "●", tone: "ok" };
  if (value === false) return { label: "Out of stock",  icon: "○", tone: "bad" };
  return                       { label: "Unknown",       icon: "◌", tone: "muted" };
}

const KPI_ICONS = { tracked: "📡", inStock: "✅", outOfStock: "⚠️", lastSweep: "🕒" };

const OUTCOME_ICONS = { success: "✓", retried: "↻", failed: "✕" };

/* ── Toast System ────────────────────────────────────────── */

let toastId = 0;

function useToasts() {
  const [toasts, setToasts] = useState([]);

  const push = useCallback((message, type = "info") => {
    const id = ++toastId;
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.map((t) => (t.id === id ? { ...t, exit: true } : t)));
      setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 350);
    }, 3500);
  }, []);

  return { toasts, push };
}

function ToastContainer({ toasts }) {
  if (!toasts.length) return null;
  return (
    <div className="toast-container">
      {toasts.map((t) => (
        <div key={t.id} className={`toast ${t.type} ${t.exit ? "toast-exit" : ""}`}>
          {t.message}
        </div>
      ))}
    </div>
  );
}

/* ── Skeleton Components ─────────────────────────────────── */

function SkeletonLines({ lines = 3 }) {
  const widths = ["w-80", "w-full", "w-60", "w-40"];
  return (
    <div>
      {Array.from({ length: lines }, (_, i) => (
        <div key={i} className={`skeleton skeleton-line ${widths[i % widths.length]}`} />
      ))}
    </div>
  );
}

function SkeletonCards({ count = 4 }) {
  return (
    <div className="skeleton-row">
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className="skeleton skeleton-card" />
      ))}
    </div>
  );
}

/* ── App ─────────────────────────────────────────────────── */

function App() {
  const [products, setProducts] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [loadingProducts, setLoadingProducts] = useState(true);
  const [error, setError] = useState("");
  const { toasts, push: pushToast } = useToasts();

  async function loadProducts(nextSelectedId) {
    setLoadingProducts(true);
    setError("");
    try {
      const data = await api("/api/products/");
      setProducts(data);
      setSelectedId((current) => {
        if (nextSelectedId) return nextSelectedId;
        if (current && data.some((item) => item.id === current)) return current;
        return data[0]?.id || null;
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingProducts(false);
    }
  }

  useEffect(() => {
    loadProducts();
  }, []);

  const selected = products.find((p) => p.id === selectedId) || null;
  const inStockCount = products.filter((p) => p.currently_in_stock === true).length;
  const outCount = products.filter((p) => p.currently_in_stock === false).length;
  const lastSweep = products
    .map((p) => p.last_scrape_at)
    .filter(Boolean)
    .sort()
    .at(-1);

  return (
    <div className="shell">
      <div className="glow glow-a" />
      <div className="glow glow-b" />
      <div className="glow glow-c" />

      <ToastContainer toasts={toasts} />

      <header className="nav">
        <div className="brand">
          <span className="mark">◉</span>
          <div>
            <strong>Watchboard</strong>
            <small>INE mock store · price &amp; stock observatory</small>
          </div>
        </div>
        <div className="nav-actions">
          <span className="live-pill">
            <i /> Live watch
          </span>
          <button className="ghost" type="button" onClick={() => loadProducts()}>
            Refresh
          </button>
        </div>
      </header>

      {error && <div className="banner error">{error}</div>}

      <section className="kpis stagger">
        <Kpi icon={KPI_ICONS.tracked}    label="Tracked"      value={String(products.length)} hint="Products on watch" />
        <Kpi icon={KPI_ICONS.inStock}    label="In stock"     value={String(inStockCount)}    hint="Last known good scrape" />
        <Kpi icon={KPI_ICONS.outOfStock} label="Out of stock" value={String(outCount)}        hint="Needs restock alert" />
        <Kpi icon={KPI_ICONS.lastSweep}  label="Last sweep"   value={relativeTime(lastSweep)} hint="Across the watchlist" />
      </section>

      <main className="workspace">
        <aside className="rail">
          <SearchPanel
            trackedIds={new Set(products.map((p) => String(p.store_product_id)))}
            onTracked={(id) => loadProducts(id)}
            pushToast={pushToast}
          />
          <TrackedList
            products={products}
            selectedId={selectedId}
            loading={loadingProducts}
            onSelect={setSelectedId}
          />
        </aside>
        <section className="stage">
          {selected ? (
            <ProductDetail
              product={selected}
              onChanged={() => loadProducts(selected.id)}
              onRemoved={() => loadProducts()}
              pushToast={pushToast}
            />
          ) : (
            <EmptyStage />
          )}
        </section>
      </main>
    </div>
  );
}

/* ── KPI Card ────────────────────────────────────────────── */

function Kpi({ icon, label, value, hint }) {
  return (
    <article className="kpi animate-in">
      <span className="kpi-icon">{icon}</span>
      <span className="kpi-label">{label}</span>
      <strong>{value}</strong>
      <small>{hint}</small>
    </article>
  );
}

/* ── Search Panel ────────────────────────────────────────── */

function SearchPanel({ trackedIds, onTracked, pushToast }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [trackingId, setTrackingId] = useState(null);
  const [message, setMessage] = useState("");

  async function search(event) {
    event.preventDefault();
    if (query.trim().length < 2) {
      setMessage("Type at least two characters to search the store.");
      return;
    }
    setLoading(true);
    setMessage("");
    try {
      const data = await api(`/api/store/search/?q=${encodeURIComponent(query)}`);
      setResults(data);
      setMessage(data.length ? `${data.length} match${data.length === 1 ? "" : "es"}` : "No products matched.");
    } catch (err) {
      setMessage(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function track(product) {
    setTrackingId(product.id);
    setMessage("");
    try {
      const tracked = await api("/api/products/track/", {
        method: "POST",
        body: JSON.stringify({ store_product_id: product.id }),
      });
      pushToast(`Now tracking ${tracked.name}`, "success");
      await onTracked(tracked.id);
    } catch (err) {
      pushToast(err.message, "error");
    } finally {
      setTrackingId(null);
    }
  }

  return (
    <section className="card search-card">
      <div className="card-head">
        <h2>Find a product</h2>
        <p>Search the INE mock store</p>
      </div>
      <form className="search-form" onSubmit={search}>
        <input
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setResults([]);
            setMessage("");
          }}
          placeholder="Name, brand, category, or SKU…"
          aria-label="Search mock store"
        />
        <button type="submit" disabled={loading}>
          {loading ? <><span className="spinner spinner-dark" />Searching</> : "Search"}
        </button>
      </form>
      {message && <p className="soft-note">{message}</p>}
      <div className="result-list">
        {results.map((product) => {
          const already = trackedIds.has(String(product.id));
          return (
            <article className="result" key={product.id}>
              <div>
                <span className="chip">{product.category}</span>
                <h3>{product.name}</h3>
                <p>
                  {product.brand} · {product.sku}
                </p>
              </div>
              <button
                type="button"
                disabled={already || trackingId === product.id}
                onClick={() => track(product)}
              >
                {already
                  ? "✓ Watching"
                  : trackingId === product.id
                    ? <><span className="spinner spinner-dark" />Adding</>
                    : "Track"}
              </button>
            </article>
          );
        })}
      </div>
    </section>
  );
}

/* ── Tracked List ────────────────────────────────────────── */

function TrackedList({ products, selectedId, loading, onSelect }) {
  return (
    <section className="card list-card">
      <div className="card-head">
        <h2>Watchlist</h2>
        <p>{products.length} tracked</p>
      </div>
      {loading ? (
        <SkeletonLines lines={4} />
      ) : products.length === 0 ? (
        <p className="muted">Search the store and track a product to start history.</p>
      ) : (
        <div className="watch-list">
          {products.map((product) => {
            const stock = stockMeta(product.currently_in_stock);
            return (
              <button
                className={`watch-row ${product.id === selectedId ? "active" : ""}`}
                key={product.id}
                type="button"
                onClick={() => onSelect(product.id)}
              >
                <span className="watch-copy">
                  <strong>{product.name}</strong>
                  <small>
                    {product.metadata?.brand || "INE Store"} ·{" "}
                    <em className={stock.tone}>{stock.icon} {stock.label}</em>
                  </small>
                </span>
                <span className="watch-price">{money(product.current_price, product.currency)}</span>
              </button>
            );
          })}
        </div>
      )}
    </section>
  );
}

/* ── Empty Stage ─────────────────────────────────────────── */

function EmptyStage() {
  return (
    <div className="empty-stage">
      <div className="empty-inner">
        <div className="empty-rings">
          <div className="empty-ring" />
          <div className="empty-ring" />
          <div className="empty-ring" />
          <span className="empty-glyph">◎</span>
        </div>
        <h2>Nothing on the board yet</h2>
        <p>
          Search the INE mock store, track a product, then watch price, stock,
          and every scrape attempt land here.
        </p>
      </div>
    </div>
  );
}

/* ── Product Detail ──────────────────────────────────────── */

function ProductDetail({ product, onChanged, onRemoved, pushToast }) {
  const [history, setHistory] = useState([]);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [tab, setTab] = useState("history");
  const [busy, setBusy] = useState("");

  async function loadDetail() {
    setLoading(true);
    setError("");
    try {
      const [historyData, logsData] = await Promise.all([
        api(`/api/products/${product.id}/price-history/`),
        api(`/api/products/${product.id}/scrape-logs/`),
      ]);
      setHistory(historyData);
      setLogs(logsData);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDetail();
  }, [product.id]);

  const sortedHistory = useMemo(
    () => [...history].sort((a, b) => new Date(a.scraped_at) - new Date(b.scraped_at)),
    [history]
  );

  const stock = stockMeta(product.currently_in_stock);
  const latest = sortedHistory.at(-1);
  const previous = sortedHistory.at(-2);
  const delta = latest && previous ? Number(latest.price) - Number(previous.price) : null;

  async function scrapeNow() {
    setBusy("scrape");
    setError("");
    try {
      await api("/api/scrape/run/", {
        method: "POST",
        body: JSON.stringify({ product_id: product.id }),
      });
      pushToast("Scrape completed successfully", "success");
      await onChanged();
      await loadDetail();
    } catch (err) {
      pushToast(`Scrape failed: ${err.message}`, "error");
      setError(err.message);
    } finally {
      setBusy("");
    }
  }

  async function untrack() {
    setBusy("remove");
    setError("");
    try {
      await api(`/api/products/${product.id}/`, { method: "DELETE" });
      pushToast(`Stopped tracking ${product.name}`, "info");
      await onRemoved();
    } catch (err) {
      pushToast(err.message, "error");
      setError(err.message);
    } finally {
      setBusy("");
    }
  }

  return (
    <div className="detail">
      <div className="hero">
        <div className="hero-info">
          <span className="eyebrow">{product.metadata?.category || "Tracked product"}</span>
          <h1>{product.name}</h1>
          <p>{product.description}</p>
          <div className="meta-row">
            <span className="meta-tag">{product.metadata?.brand || "INE Store"}</span>
            <span className="meta-tag">{product.metadata?.sku || product.store_product_id}</span>
            <span className={`stock-badge ${stock.tone}`}>
              {stock.icon} {stock.label}
            </span>
          </div>
        </div>
        <div className="hero-price">
          <small>Latest price</small>
          <strong>{money(product.current_price, product.currency)}</strong>
          {delta !== null && (
            <em className={delta < 0 ? "ok" : delta > 0 ? "bad" : "muted"}>
              {delta === 0
                ? "No change"
                : `${delta > 0 ? "▲" : "▼"} ${Math.abs(delta).toFixed(2)} vs last`}
            </em>
          )}
        </div>
      </div>

      <div className="facts stagger">
        <Fact label="Store ID" value={product.store_product_id || "—"} />
        <Fact label="Last scrape" value={compactDate(product.last_scrape_at)} />
        <Fact label="Last success" value={compactDate(product.last_successful_scrape_at)} />
        <Fact label="Cadence" value={`Every ${product.scrape_interval_minutes} min`} />
      </div>

      <div className="actions">
        <a className="ghost linkish" href={product.url} target="_blank" rel="noreferrer">
          Open store page ↗
        </a>
        <button type="button" onClick={scrapeNow} disabled={Boolean(busy)}>
          {busy === "scrape" ? <><span className="spinner spinner-dark" />Scraping…</> : "⚡ Scrape now"}
        </button>
        <button className="danger" type="button" onClick={untrack} disabled={Boolean(busy)}>
          {busy === "remove" ? <><span className="spinner" />Removing…</> : "Stop tracking"}
        </button>
      </div>

      {error && <div className="banner error" style={{ marginTop: 16 }}>{error}</div>}

      <div className="tabs">
        <button
          className={tab === "history" ? "tab on" : "tab"}
          type="button"
          onClick={() => setTab("history")}
        >
          📊 Price & stock
        </button>
        <button
          className={tab === "logs" ? "tab on" : "tab"}
          type="button"
          onClick={() => setTab("logs")}
        >
          📋 Scrape log
        </button>
      </div>

      {loading ? (
        <div style={{ marginTop: 18 }}>
          <SkeletonLines lines={2} />
          <SkeletonCards count={4} />
        </div>
      ) : tab === "history" ? (
        <>
          <HistoryChart history={sortedHistory} currency={product.currency} />
          <HistoryTable history={sortedHistory} currency={product.currency} />
        </>
      ) : (
        <ScrapeLogTable logs={logs} />
      )}
    </div>
  );
}

/* ── Fact ─────────────────────────────────────────────────── */

function Fact({ label, value }) {
  return (
    <div className="fact animate-in">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

/* ── History Chart ───────────────────────────────────────── */

function HistoryChart({ history, currency }) {
  const [hover, setHover] = useState(null);

  if (history.length === 0) {
    return (
      <div className="empty-block">
        No price points yet. Run a scrape or wait for the two-hour schedule.
      </div>
    );
  }

  const width = 760;
  const height = 220;
  const pad = { l: 54, r: 18, t: 18, b: 36 };
  const prices = history.map((p) => Number(p.price));
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const spread = max - min || 1;
  const innerW = width - pad.l - pad.r;
  const innerH = height - pad.t - pad.b;

  const coords = history.map((point, index) => {
    const x = pad.l + (index / Math.max(history.length - 1, 1)) * innerW;
    const y = pad.t + innerH - ((Number(point.price) - min) / spread) * innerH;
    return { x, y, point };
  });

  const line = coords.map((c) => `${c.x},${c.y}`).join(" ");
  const area = `${pad.l},${pad.t + innerH} ${line} ${coords.at(-1).x},${pad.t + innerH}`;

  return (
    <div className="chart-card">
      <div className="card-head compact">
        <h3>Price over time</h3>
        <p>
          {money(min, currency)} — {money(max, currency)}
        </p>
      </div>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label="Price history chart"
        onMouseLeave={() => setHover(null)}
      >
        <defs>
          <linearGradient id="priceFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#7CFFB2" stopOpacity="0.25" />
            <stop offset="100%" stopColor="#7CFFB2" stopOpacity="0" />
          </linearGradient>
          <linearGradient id="lineGrad" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#4de890" />
            <stop offset="50%" stopColor="#7CFFB2" />
            <stop offset="100%" stopColor="#b8ffd5" />
          </linearGradient>
        </defs>

        {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
          const y = pad.t + innerH * (1 - ratio);
          const label = min + spread * ratio;
          return (
            <g key={ratio}>
              <line className="grid" x1={pad.l} y1={y} x2={width - pad.r} y2={y} />
              <text className="axis" x="4" y={y + 4}>
                {label.toFixed(0)}
              </text>
            </g>
          );
        })}

        <polygon className="area" points={area} fill="url(#priceFill)" />
        <polyline className="line" points={line} />

        {coords.map((c) => (
          <circle
            key={c.point.id}
            cx={c.x}
            cy={c.y}
            r={hover?.point.id === c.point.id ? 7 : 4}
            onMouseEnter={() => setHover(c)}
          />
        ))}
      </svg>

      {hover && (
        <div className="tooltip">
          {compactDate(hover.point.scraped_at)} ·{" "}
          {money(hover.point.price, hover.point.currency || currency)} ·{" "}
          {hover.point.in_stock ? "● In stock" : "○ Out of stock"}
          {hover.point.stock_quantity != null && ` · Qty: ${hover.point.stock_quantity}`}
        </div>
      )}
    </div>
  );
}

/* ── History Table ───────────────────────────────────────── */

function HistoryTable({ history, currency }) {
  if (history.length === 0) return null;

  return (
    <div className="table-wrap">
      <h3>Recorded price points</h3>
      <table>
        <thead>
          <tr>
            <th>Scraped</th>
            <th>Price</th>
            <th>Qty</th>
            <th>Stock</th>
          </tr>
        </thead>
        <tbody>
          {[...history].reverse().map((point) => (
            <tr key={point.id}>
              <td>{compactDate(point.scraped_at)}</td>
              <td style={{ fontFamily: "'IBM Plex Mono', monospace", color: "var(--accent)" }}>
                {money(point.price, point.currency || currency)}
              </td>
              <td>{point.stock_quantity ?? "—"}</td>
              <td>
                <span className={`stock-badge ${point.in_stock ? "ok" : "bad"}`}>
                  {point.in_stock ? "● In stock" : "○ Out of stock"}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ── Scrape Log Table ────────────────────────────────────── */

function ScrapeLogTable({ logs }) {
  if (logs.length === 0) {
    return (
      <div className="empty-block">
        No scrape attempts yet. Failures will appear here honestly — never hidden.
      </div>
    );
  }

  const maxDuration = Math.max(...logs.map((l) => l.duration_ms || 0), 1);

  return (
    <div className="table-wrap">
      <h3>Every scrape attempt</h3>
      <table>
        <thead>
          <tr>
            <th>When</th>
            <th>Outcome</th>
            <th>#</th>
            <th>HTTP</th>
            <th>Duration</th>
            <th>Note</th>
          </tr>
        </thead>
        <tbody>
          {logs.map((log) => (
            <tr key={log.id}>
              <td>{compactDate(log.attempted_at)}</td>
              <td>
                <span className={`outcome ${log.outcome}`}>
                  {OUTCOME_ICONS[log.outcome] || "?"} {log.outcome}
                </span>
              </td>
              <td>{log.attempt_number}</td>
              <td style={{ fontFamily: "'IBM Plex Mono', monospace" }}>
                {log.http_status || "—"}
              </td>
              <td>
                {log.duration_ms ? (
                  <span className="duration-bar">
                    <span
                      className="duration-fill"
                      style={{ width: `${Math.max((log.duration_ms / maxDuration) * 80, 8)}px` }}
                    />
                    {log.duration_ms} ms
                  </span>
                ) : (
                  "—"
                )}
              </td>
              <td className="note">{log.error_message || log.notes || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default App;

import { useParams, Link } from "react-router-dom";
import { useData } from "../lib/useData";
import { ThemeToggle } from "../components/ThemeToggle";
import { ImpactRadar } from "../components/ImpactRadar";
import type { Engineer } from "../types";

export function EngineerDetail() {
  const { login } = useParams();
  const state = useData();

  if (state.status === "loading")
    return <div className="app"><div className="state-box">Loading…</div></div>;
  if (state.status === "error")
    return <div className="app"><div className="state-box">Couldn’t load data.</div></div>;

  const e = state.data.engineers.find((x) => x.login === login);
  if (!e)
    return (
      <div className="app">
        <Link to="/" className="back">← Back</Link>
        <div className="state-box">No engineer “{login}” in the active pool.</div>
      </div>
    );

  return (
    <div className="app">
      <Link to="/" className="back">← All engineers</Link>
      <div className="header">
        <div className="detail-head">
          <h1>{e.name}</h1>
          <span className="handle">@{e.login}</span>
          {e.association && <span className="pill">{e.association.toLowerCase()}</span>}
        </div>
        <ThemeToggle />
      </div>
      <p className="rank-known" style={{ marginTop: 6 }}>
        Rank #{e.rank} of {state.data.meta.active_engineers} · {e.known_for}
      </p>

      <div className="detail-grid">
        {/* left: radar + score */}
        <div>
          <div className="panel panel-pad">
            <h4 style={{ marginBottom: 2 }}>Impact dimensions</h4>
            <p className="methodology" style={{ margin: "2px 0 0" }}>Percentile vs. active pool</p>
            <ImpactRadar percentiles={e.percentiles} height={250} />
            <div style={{ textAlign: "center", marginTop: 4 }}>
              <div className="score-num" style={{ color: "var(--accent)", fontSize: "2.2rem" }}>{e.score}</div>
              <div className="score-label">blended impact score (0–100)</div>
            </div>
          </div>

          <ReviewedFor engineer={e} />
        </div>

        {/* right: what they did */}
        <div>
          <Scored engineer={e} />
          <Context engineer={e} />
        </div>
      </div>
    </div>
  );
}

function Scored({ engineer: e }: { engineer: Engineer }) {
  const m = e.metrics;
  return (
    <div className="panel panel-pad" style={{ marginBottom: 16 }}>
      <h4 style={{ marginBottom: 4 }}>What they did for the team <span style={{ color: "var(--text-dim)", fontWeight: 400, fontSize: "0.78rem" }}>(scored)</span></h4>
      <div className="stat-grid">
        <Stat v={m.distinct_unblocked} k="Distinct engineers unblocked" sub="reviewed their PRs" accent />
        <Stat v={m.reviews_given} k="Reviews given" sub={`${m.substantive_given} substantive (${Math.round(m.substantive_ratio * 100)}%)`} />
        <Stat v={`${m.reciprocity}×`} k="Review reciprocity" sub={`gave ${m.reviews_given} · received ${m.reviews_received}`} />
        <Stat v={m.median_ttfr_hours == null ? "—" : `${m.median_ttfr_hours}h`} k="Median time to first review" sub="responsiveness on others’ PRs" />
        <Stat v={m.involvement_comments} k="Comments on others’ PRs" sub="involvement" />
        <Stat v={`${Math.round(m.substantive_ratio * 100)}%`} k="Substantive reviews" sub="not rubber-stamps" />
      </div>
    </div>
  );
}

function Context({ engineer: e }: { engineer: Engineer }) {
  const c = e.context;
  const mix = Object.entries(c.work_type_mix);
  return (
    <div className="panel panel-pad">
      <h4 style={{ marginBottom: 4 }}>Authorship context <span style={{ color: "var(--text-dim)", fontWeight: 400, fontSize: "0.78rem" }}>(not scored)</span></h4>
      <div className="stat-grid">
        <Stat v={c.throughput} k="Merged PRs (throughput)" sub={`${c.authored_total} authored total`} />
        <Stat v={c.merge_rate == null ? "—" : `${Math.round(c.merge_rate * 100)}%`} k="Merge rate" sub={`${c.merged} merged · ${c.closed_unmerged} closed unmerged`} />
        <Stat v={`${c.ai_authored_pct}%`} k="AI-assisted PRs" sub={c.ai_tools.length ? c.ai_tools.join(", ") : "no AI tools detected"} />
        <Stat v={c.median_pr_size} k="Median PR size" sub="lines changed (context only)" />
      </div>

      <div style={{ marginTop: 12 }}>
        <div className="score-label" style={{ marginBottom: 6 }}>Work-type mix</div>
        <div className="chips">
          {mix.map(([t, n]) => <span key={t} className="chip muted">{t} · {n}</span>)}
        </div>
      </div>

      {c.ai_tools.length > 0 && (
        <div style={{ marginTop: 12 }}>
          <div className="score-label" style={{ marginBottom: 6 }}>AI tools used</div>
          <div className="chips">
            {c.ai_tools.map((t) => <span key={t} className="chip">{t}</span>)}
          </div>
        </div>
      )}

      {c.reverts.length > 0 && (
        <div className="revert-warn" style={{ marginTop: 14 }}>
          <h4>⚑ {c.reverts.length} PR{c.reverts.length > 1 ? "s" : ""} reverted within 48h</h4>
          <p className="methodology" style={{ margin: "4px 0 0" }}>
            A rare red flag, shown for context — not part of the score.
          </p>
          {c.reverts.slice(0, 3).map((r) => (
            <div className="attn-item" key={r.number}>
              <span>#{r.number} {r.title.slice(0, 54)}</span>
              <span className="meta">reverted in {r.hours}h</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ReviewedFor({ engineer: e }: { engineer: Engineer }) {
  if (!e.reviewed_for.length) return null;
  return (
    <div className="panel panel-pad" style={{ marginTop: 16 }}>
      <h4 style={{ marginBottom: 4 }}>Who they unblocked</h4>
      <p className="methodology" style={{ margin: "0 0 10px" }}>
        Engineers whose PRs {e.name.split(" ")[0]} reviewed (count).
      </p>
      <div className="reviewed-for">
        {e.reviewed_for.map((r) => (
          <Link to={`/engineer/${r.login}`} className="rf" key={r.login}>
            @{r.login} <b>{r.count}</b>
          </Link>
        ))}
      </div>
    </div>
  );
}

function Stat({ v, k, sub, accent }: { v: React.ReactNode; k: string; sub?: string; accent?: boolean }) {
  return (
    <div className="stat">
      <div className={"v" + (accent ? " accent" : "")}>{v}</div>
      <div className="k">{k}</div>
      {sub && <div className="sub">{sub}</div>}
    </div>
  );
}

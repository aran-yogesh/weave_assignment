import { useData } from "../lib/useData";
import { ThemeToggle } from "../components/ThemeToggle";
import { RankRow } from "../components/RankRow";
import { EffortScatter } from "../components/EffortScatter";
import { AttentionPanel } from "../components/AttentionPanel";
import { CategoryLeaderboard } from "../components/CategoryLeaderboard";
import type { Meta } from "../types";

const fmt = (iso: string) =>
  new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric" });

export function Home() {
  const state = useData();

  if (state.status === "loading")
    return <Shell><div className="state-box">Loading impact data…</div></Shell>;
  if (state.status === "error")
    return (
      <Shell>
        <div className="state-box">
          Couldn’t load data.json.<br />
          <span style={{ fontSize: "0.8rem" }}>{state.message}</span>
        </div>
      </Shell>
    );

  const { meta, engineers, scatter, team } = state.data;
  const top5 = engineers.slice(0, 5);

  return (
    <Shell meta={meta}>
      <div className="section">
        <div className="section-title">
          Top 5 most impactful engineers
          <span className="hint">ranked by review-influence score · hover for dimensions · click for detail</span>
        </div>
        <p className="caveat">
          Measures provable force-multiplication via the review graph; heads-down IC work on
          hard systems is under-credited here — see context stats.
        </p>
        <div className="rank-list">
          {top5.map((e) => <RankRow key={e.login} engineer={e} />)}
        </div>
      </div>

      <div className="section">
        <div className="section-title">
          Effort vs. impact
          <span className="hint">PR size doesn’t equal impact — the people who matter sit off the diagonal</span>
        </div>
        <div className="panel panel-pad">
          <EffortScatter points={scatter} />
          <p className="methodology" style={{ marginTop: 8 }}>
            Each dot is an active engineer ({meta.active_engineers} total). <b style={{ color: "var(--accent)" }}>Orange</b> = top 5.
            A big-PR engineer low on the y-axis ships lots of code but little leverage; a small-PR engineer high up is a force multiplier.
          </p>
        </div>
      </div>

      <div className="section">
        <div className="section-title">Team picture &amp; what needs attention</div>
        <div className="grid-2">
          <div className="panel panel-pad">
            <CategoryLeaderboard engineers={engineers} />
          </div>
          <div className="panel panel-pad">
            <AttentionPanel team={team} />
          </div>
        </div>
      </div>

      <div className="section">
        <div className="panel panel-pad methodology">
          <h4 style={{ color: "var(--text)", marginBottom: 8 }}>How the score works (and what it doesn’t measure)</h4>
          <p>
            <b>Thesis: impact = force multiplication.</b> The most impactful engineer isn’t the one with the most commits —
            it’s the one who makes the whole team faster and whose absence would slow everyone down. The one thing GitHub
            data can <b>cleanly prove</b> about this is <b>review &amp; unblocking influence</b>: one person measurably helping
            another, with names and timestamps.
          </p>
          <p style={{ marginTop: 8 }}>
            The <b>impact score (0–100)</b> blends six review-graph dimensions, each turned into a percentile against the active pool:
            distinct people unblocked (30%), review reciprocity (20%), substantive-review ratio (15%), responsiveness (15%),
            involvement (10%), and review volume (10%). Bots are excluded everywhere; chore &amp; generated PRs are excluded from scoring.
          </p>
          <p style={{ marginTop: 8 }}>
            <b>Honest limits:</b> this measures the <i>provable</i> dimension of impact. Whether the work itself <i>matters</i>,
            and who owns the hardest systems, need human context — shown here as context stats (throughput, AI leverage,
            merge rate, reverts), never folded into the score.
          </p>
          <p style={{ marginTop: 10, fontSize: "0.74rem", color: "var(--text-dim)" }}>
            <b style={{ color: "var(--text-muted)" }}>Footnotes.</b> Review and comment counts are scoped by PR <i>close</i> date,
            so a PR opened before the window but closed inside it contributes reviews that may predate the 90-day window, while a
            PR closed just before the window contributes none — a minor edge effect on the review-graph counts.
          </p>
          <p style={{ marginTop: 6, fontSize: "0.74rem", color: "var(--text-dim)" }}>
            Reviews and files are fetched with a cap (first 30), so the most heavily-reviewed PRs may slightly undercount review
            and comment volume.
          </p>
        </div>
      </div>

      <footer className="methodology" style={{ marginTop: 24, textAlign: "center", fontSize: "0.75rem" }}>
        {meta.repo} · {meta.prs_total.toLocaleString()} PRs analyzed ({meta.prs_merged.toLocaleString()} merged,{" "}
        {meta.prs_closed_unmerged.toLocaleString()} closed-unmerged) · generated {fmt(meta.generated_at)}
      </footer>
    </Shell>
  );
}

function Shell({ children, meta }: { children: React.ReactNode; meta?: Meta }) {
  return (
    <div className="app">
      <header className="header">
        <div>
          <h1>PostHog <span className="accent">Engineering Impact</span></h1>
          <div className="subtitle">
            Who makes the team faster — measured by review &amp; unblocking influence, the one dimension of impact
            GitHub data can cleanly prove.
          </div>
          {meta && (
            <div className="pill-row">
              <span className="pill accent">{fmt(meta.since)} – {fmt(meta.until)} · {meta.days} days</span>
              <span className="pill">{meta.active_engineers} active engineers</span>
              <span className="pill">bots &amp; chores filtered</span>
            </div>
          )}
        </div>
        <ThemeToggle />
      </header>
      {children}
    </div>
  );
}

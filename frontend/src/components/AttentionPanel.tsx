import type { Team } from "../types";

// Team-level "where the work is + where it waits" panel: PR volume by codebase
// area (team activity) and directory review chokepoints (where work waits).
export function AttentionPanel({ team }: { team: Team }) {
  const maxArea = Math.max(1, ...team.areas.map((a) => a.pr_count));
  return (
    <div className="attn">
      <div className="attn-block">
        <h4>📍 Where the work is</h4>
        <p className="desc">
          PR volume by top-level codebase area this quarter. A team-activity
          view of the busiest areas — not a per-person judgment.
        </p>
        {team.areas.length === 0 ? (
          <div className="attn-item"><span className="meta">No area data.</span></div>
        ) : (
          team.areas.map((a) => (
            <div className="area-row" key={a.dir}>
              <code className="area-name"><span>{a.dir}/</span></code>
              <div className="area-bar">
                <div className="area-fill" style={{ width: `${(a.pr_count / maxArea) * 100}%` }} />
              </div>
              <span className="area-count">{a.pr_count}</span>
            </div>
          ))
        )}
      </div>

      <div className="attn-block">
        <h4>🐢 Review chokepoints</h4>
        <p className="desc">
          Directories with the slowest median time-to-first-review. Where work
          waits longest — candidates for more reviewers or clearer ownership.
        </p>
        {team.chokepoints.length === 0 ? (
          <div className="attn-item"><span className="meta">No standout chokepoints.</span></div>
        ) : (
          team.chokepoints.map((c) => (
            <div className="attn-item" key={c.dir}>
              <span><code>{c.dir}/</code></span>
              <span className="meta">
                <b className="tag-bad">{c.median_ttfr_hours}h</b> median · {c.pr_count} PRs
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ZAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { useNavigate } from "react-router-dom";
import type { ScatterPoint } from "../types";

// Effort-vs-impact scatter: x = median PR size (LOC), y = impact percentile.
// Visually shows that lines of code don't equal impact — the interesting
// people sit off the diagonal.
export function EffortScatter({ points }: { points: ScatterPoint[] }) {
  const navigate = useNavigate();
  const accent = "#ff6a00";

  return (
    <ResponsiveContainer width="100%" height={320}>
      <ScatterChart margin={{ top: 12, right: 20, bottom: 32, left: 6 }}>
        <CartesianGrid stroke="var(--radar-grid)" strokeDasharray="3 3" />
        <XAxis
          type="number"
          dataKey="size"
          name="Median PR size"
          scale="sqrt"
          tick={{ fill: "var(--text-muted)", fontSize: 11 }}
          label={{ value: "Median PR size (lines changed) →", position: "bottom", offset: 14, fill: "var(--text-dim)", fontSize: 11 }}
        />
        <YAxis
          type="number"
          dataKey="score"
          name="Impact"
          domain={[0, 100]}
          tick={{ fill: "var(--text-muted)", fontSize: 11 }}
          label={{ value: "Impact score →", angle: -90, position: "insideLeft", fill: "var(--text-dim)", fontSize: 11 }}
        />
        <ZAxis range={[60, 60]} />
        <Tooltip
          cursor={{ strokeDasharray: "3 3" }}
          content={({ payload }) => {
            if (!payload || !payload.length) return null;
            const p = payload[0].payload as ScatterPoint;
            return (
              <div style={{ background: "var(--bg-elev)", border: "1px solid var(--border)", borderRadius: 10, padding: "8px 10px", fontSize: 12 }}>
                <b>{p.name}</b> <span style={{ color: "var(--text-dim)" }}>#{p.rank}</span>
                <div style={{ color: "var(--text-muted)" }}>Impact {p.score} · {p.size} lines/PR</div>
              </div>
            );
          }}
        />
        <Scatter
          data={points}
          onClick={(p: any) => p && navigate(`/engineer/${p.login}`)}
          cursor="pointer"
          isAnimationActive={false}
        >
          {points.map((p) => (
            <Cell
              key={p.login}
              fill={p.is_top5 ? accent : "var(--text-dim)"}
              fillOpacity={p.is_top5 ? 0.95 : 0.5}
            />
          ))}
        </Scatter>
      </ScatterChart>
    </ResponsiveContainer>
  );
}

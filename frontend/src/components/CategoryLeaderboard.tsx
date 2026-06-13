import { useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Cell,
  ResponsiveContainer,
} from "recharts";
import type { Engineer } from "../types";

// "Who's best at each thing" — a tabbed leaderboard. Each tab is ONE raw
// dimension (never a blended score), shown as a horizontal bar of the top 8.
// Values are read straight from the engineer list, so they always match the
// detail pages.

type Row = { login: string; name: string; value: number };

interface Category {
  key: string;
  label: string;
  unit: string;
  // Pull the raw value for an engineer (null = exclude from this board).
  pick: (e: Engineer) => number | null;
  // Lower is better (e.g. response time)? Default false = higher is better.
  ascending?: boolean;
  // Minimum reviews given to qualify — guards rate metrics (e.g. median
  // time-to-first-review) against being topped by 1-review noise.
  minReviews?: number;
}

const CATEGORIES: Category[] = [
  {
    key: "unblocked",
    label: "Most engineers unblocked",
    unit: "engineers",
    pick: (e) => e.metrics.distinct_unblocked,
  },
  {
    key: "fastest",
    label: "Fastest to reply",
    unit: "h median",
    pick: (e) => e.metrics.median_ttfr_hours,
    ascending: true,
    minReviews: 3,
  },
  {
    key: "substantive",
    label: "Most substantive reviews",
    unit: "reviews",
    pick: (e) => e.metrics.substantive_given,
  },
];

const accent = "#ff6a00";

/** Top 8 engineers for one category, sorted by that single raw value. */
function leaderboard(engineers: Engineer[], cat: Category): Row[] {
  const rows: Row[] = [];
  for (const e of engineers) {
    if (cat.minReviews != null && e.metrics.reviews_given < cat.minReviews) continue;
    const v = cat.pick(e);
    if (v == null) continue;
    rows.push({ login: e.login, name: e.name, value: v });
  }
  rows.sort((a, b) => (cat.ascending ? a.value - b.value : b.value - a.value));
  return rows.slice(0, 8);
}

export function CategoryLeaderboard({ engineers }: { engineers: Engineer[] }) {
  const [active, setActive] = useState(0);
  const navigate = useNavigate();
  const cat = CATEGORIES[active];
  const rows = leaderboard(engineers, cat);

  return (
    <div>
      <h4 style={{ marginBottom: 4 }}>Who’s best at each thing</h4>
      <p className="methodology" style={{ margin: "2px 0 10px" }}>
        Top 8 on one raw dimension at a time — not a blended score.
      </p>

      <div className="tab-row" role="tablist" aria-label="Leaderboard category">
        {CATEGORIES.map((c, i) => (
          <button
            key={c.key}
            role="tab"
            aria-selected={i === active}
            className={"tab" + (i === active ? " on" : "")}
            onClick={() => setActive(i)}
          >
            {c.label}
          </button>
        ))}
      </div>

      <ResponsiveContainer width="100%" height={Math.max(rows.length * 34, 80)}>
        <BarChart
          data={rows}
          layout="vertical"
          margin={{ top: 4, right: 56, bottom: 4, left: 8 }}
          barCategoryGap={6}
        >
          <XAxis type="number" hide domain={[0, "dataMax"]} />
          <YAxis
            type="category"
            dataKey="name"
            width={132}
            tickLine={false}
            axisLine={false}
            tick={{ fill: "var(--text-muted)", fontSize: 12 }}
          />
          <Bar
            dataKey="value"
            radius={[0, 5, 5, 0]}
            isAnimationActive={false}
            cursor="pointer"
            onClick={(d: any) => d && navigate(`/engineer/${d.login}`)}
            label={{
              position: "right",
              formatter: (v: ReactNode) => `${v} ${cat.unit}`,
              fill: "var(--text-dim)",
              fontSize: 11,
            }}
          >
            {rows.map((r, i) => (
              <Cell
                key={r.login}
                fill={accent}
                fillOpacity={1 - (i / rows.length) * 0.55}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

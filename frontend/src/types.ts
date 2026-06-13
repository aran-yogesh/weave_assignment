// Typed shapes for public/data.json (produced by the Python pipeline).

export interface Meta {
  repo: string;
  since: string;
  until: string;
  days: number;
  prs_total: number;
  prs_merged: number;
  prs_closed_unmerged: number;
  generated_at: string;
  active_engineers: number;
  weights: Record<string, number>;
  filters_note: string;
}

export interface EngineerMetrics {
  distinct_unblocked: number;
  reviews_given: number;
  reviews_received: number;
  reciprocity: number;
  substantive_given: number;
  substantive_ratio: number;
  median_ttfr_hours: number | null;
  involvement_comments: number;
}

// Percentile (0-100) per scored dimension.
export interface Percentiles {
  unblocking: number;
  reciprocity: number;
  review_depth: number;
  responsiveness: number;
  involvement: number;
  volume: number;
}

export interface Revert {
  number: number;
  title: string;
  reverted_by: number;
  hours: number;
}

export interface EngineerContext {
  authored_total: number;
  merged: number;
  closed_unmerged: number;
  merge_rate: number | null;
  throughput: number;
  ai_authored_pct: number;
  ai_tools: string[];
  work_type_mix: Record<string, number>;
  median_pr_size: number;
  reverts: Revert[];
}

export interface Engineer {
  login: string;
  name: string;
  association: string | null;
  score: number;
  rank: number;
  known_for: string;
  metrics: EngineerMetrics;
  percentiles: Percentiles;
  context: EngineerContext;
  reviewed_for: { login: string; count: number }[];
}

export interface ScatterPoint {
  login: string;
  name: string;
  size: number;
  score: number;
  rank: number;
  is_top5: boolean;
}

export interface Area {
  dir: string;
  pr_count: number;
}

export interface Chokepoint {
  dir: string;
  median_ttfr_hours: number;
  pr_count: number;
}

export interface Team {
  areas: Area[];
  chokepoints: Chokepoint[];
}

export interface DashboardData {
  meta: Meta;
  engineers: Engineer[];
  scatter: ScatterPoint[];
  team: Team;
}

// The five radar axes (label -> percentile key), shared by all radar charts.
export const RADAR_AXES: { label: string; key: keyof Percentiles }[] = [
  { label: "Unblocking", key: "unblocking" },
  { label: "Reciprocity", key: "reciprocity" },
  { label: "Review depth", key: "review_depth" },
  { label: "Responsiveness", key: "responsiveness" },
  { label: "Involvement", key: "involvement" },
];

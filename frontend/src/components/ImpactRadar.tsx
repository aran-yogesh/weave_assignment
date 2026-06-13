import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
} from "recharts";
import { RADAR_AXES, type Percentiles } from "../types";

// Radar/spider plot of an engineer's five impact dimensions (percentiles 0-100).
export function ImpactRadar({
  percentiles,
  height = 230,
  showTicks = true,
}: {
  percentiles: Percentiles;
  height?: number;
  showTicks?: boolean;
}) {
  const data = RADAR_AXES.map((a) => ({
    axis: a.label,
    value: percentiles[a.key],
  }));
  const accent = "#ff6a00";

  return (
    <ResponsiveContainer width="100%" height={height}>
      <RadarChart data={data} outerRadius="62%" margin={{ top: 6, right: 30, bottom: 6, left: 30 }}>
        <PolarGrid stroke="var(--radar-grid)" />
        <PolarAngleAxis
          dataKey="axis"
          tick={{ fill: "var(--text-muted)", fontSize: 11 }}
        />
        <PolarRadiusAxis
          domain={[0, 100]}
          tick={showTicks ? { fill: "var(--text-dim)", fontSize: 9 } : false}
          axisLine={false}
          tickCount={3}
        />
        <Radar
          dataKey="value"
          stroke={accent}
          fill={accent}
          fillOpacity={0.35}
          isAnimationActive={false}
        />
      </RadarChart>
    </ResponsiveContainer>
  );
}

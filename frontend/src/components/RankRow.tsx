import { useState } from "react";
import { useNavigate } from "react-router-dom";
import type { Engineer } from "../types";
import { ImpactRadar } from "./ImpactRadar";

// A single ranked engineer row. Hover reveals a radar popover; click/Enter
// navigates to the detail page.
export function RankRow({ engineer }: { engineer: Engineer }) {
  const [hover, setHover] = useState(false);
  const navigate = useNavigate();
  const go = () => navigate(`/engineer/${engineer.login}`);

  return (
    <div
      className="rank-row"
      role="button"
      tabIndex={0}
      onClick={go}
      onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), go())}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      aria-label={`${engineer.name}, impact score ${engineer.score}. ${engineer.known_for}`}
    >
      <div className="rank-num">{engineer.rank}</div>
      <div className="rank-main">
        <div className="rank-name">
          {engineer.name}
          <span className="rank-handle">@{engineer.login}</span>
        </div>
        <div className="rank-known">{engineer.known_for}</div>
      </div>
      <div className="rank-score">
        <div className="score-num">{engineer.score}</div>
        <div className="score-label">impact</div>
      </div>

      {hover && (
        <div className="radar-pop">
          <h4>Impact dimensions (percentile)</h4>
          <ImpactRadar percentiles={engineer.percentiles} height={210} showTicks={false} />
        </div>
      )}
    </div>
  );
}

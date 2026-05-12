"use client";

import { useEffect, useState } from "react";
import axios from "axios";
import styles from "./page.module.css";

interface Odds {
  away_ml: number | null;
  home_ml: number | null;
  ou_total: number | null;
  over_odds: number | null;
  under_odds: number | null;
}

interface MLBPrediction {
  game_id: number;
  away_team: string;
  home_team: string;
  away_pitcher: string | null;
  home_pitcher: string | null;
  away_bullpen_era: number | null;
  home_bullpen_era: number | null;
  odds: Odds;
  nrfi_prob?: number | null;
  f5_away_score?: number | null;
  f5_home_score?: number | null;
  full_away_score?: number | null;
  full_home_score?: number | null;
  model_away_win_prob?: number | null;
  model_home_win_prob?: number | null;
  model_total?: number | null;
  total_play?: string | null;
  confidence?: number | null;
  spread_adv?: number | null;
  f5_pick?: string | null;
  ou_play?: string | null;
  ml_edge?: number | null;
}

const safeFormat = (value: number | null | undefined, decimals: number = 2, suffix: string = "") => {
  if (value === null || value === undefined || isNaN(value)) return "N/A";
  return `${Number(value).toFixed(decimals)}${suffix}`;
};

export default function Home() {
  const [matches, setMatches] = useState<MLBPrediction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      const response = await axios.get("http://localhost:8000/api/v1/predictions/latest");
      setMatches(response.data.data || []);
      setError(null);
    } catch (err) {
      console.error("Fetch error:", err);
      setError("Failed to fetch data from engine.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const renderStars = (confidence: number | null | undefined) => {
    if (!confidence) return "N/A";
    // 10 üzerinden olan skoru yıldıza çeviriyoruz (max 5 yıldız görseli için bölebiliriz veya direkt 10 yıldıza kadar yazdırabiliriz. Şık durması için ★ kullanacağız)
    const starCount = Math.min(10, Math.max(1, Math.round(confidence)));
    return "★".repeat(starCount);
  };

  if (loading) return <div className={styles.page}><h2>Loading Analytics Engine...</h2></div>;
  if (error) return <div className={styles.page}><h2>Error: {error}</h2></div>;

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Tyler's Value Hunter</h1>
          <p style={{ color: "#64748b", marginTop: "0.5rem", fontWeight: 500 }}>
            Advanced Pythagorean Win Probs & F5 Analytics
          </p>
        </div>
        <button className={styles.refreshBtn} onClick={fetchData}>
          Run Engine Sync
        </button>
      </header>

      <main className={styles.grid}>
        {matches.map((match) => {
          const edge = match.ml_edge ?? 0;
          const isValue = edge >= 0.05;
          const isSuperValue = edge >= 0.15; // %15 Edge tam bir Super Value!

          let cardClass = styles.card;
          if (isSuperValue) cardClass = `${styles.card} ${styles.cardSuperValue}`;
          else if (isValue) cardClass = `${styles.card} ${styles.cardValue}`;

          const totalPlay = match.total_play || "PASS";

          return (
            <div key={match.game_id} className={cardClass}>
              {isSuperValue && <div className={styles.superBadge}>TOP EDGE</div>}

              {/* HEADER: TEAMS & PITCHERS */}
              <div className={styles.matchupHeader}>
                <div className={styles.teams}>
                  {match.away_team} @ {match.home_team}
                </div>
                <div className={styles.pitchers}>
                  {match.away_pitcher || "TBD"} (BP: {safeFormat(match.away_bullpen_era)})
                  {" vs "}
                  {match.home_pitcher || "TBD"} (BP: {safeFormat(match.home_bullpen_era)})
                </div>
              </div>

              {/* TYLER'S CORE ANALYTICS */}
              <div>
                <div className={styles.sectionTitle}>Engine Projections</div>
                <div className={styles.statsRow}>
                  <div className={styles.statItem}>
                    <span className={styles.statLabel}>F5 Model Score</span>
                    <span className={styles.statValue}>
                      {safeFormat(match.f5_away_score, 1)} - {safeFormat(match.f5_home_score, 1)}
                    </span>
                  </div>
                  <div className={styles.statItem}>
                    <span className={styles.statLabel}>Full Game Score</span>
                    <span className={styles.statValue}>
                      {safeFormat(match.full_away_score, 1)} - {safeFormat(match.full_home_score, 1)}
                    </span>
                  </div>
                  <div className={styles.statItem}>
                    <span className={styles.statLabel}>1.83 Win Prob (Away)</span>
                    <span className={styles.statValue}>
                      {safeFormat((match.model_away_win_prob || 0) * 100, 1, "%")}
                    </span>
                  </div>
                  <div className={styles.statItem}>
                    <span className={styles.statLabel}>1.83 Win Prob (Home)</span>
                    <span className={styles.statValue}>
                      {safeFormat((match.model_home_win_prob || 0) * 100, 1, "%")}
                    </span>
                  </div>
                </div>
              </div>

              {/* BETTING METRICS */}
              <div>
                <div className={styles.sectionTitle}>Market Advantage</div>
                <div className={styles.statsRow}>
                  <div className={styles.statItem}>
                    <span className={styles.statLabel}>NRFI Probability</span>
                    <span className={styles.statValue}>
                      {safeFormat((match.nrfi_prob || 0) * 100, 1, "%")}
                    </span>
                  </div>
                  <div className={styles.statItem}>
                    <span className={styles.statLabel}>ML Edge</span>
                    <span className={`${styles.statValue} ${isValue ? styles.statValueHighlight : ""}`}>
                      {match.ml_edge !== null ? `+${safeFormat(edge * 100, 1, "%")}` : "AWAITING ODDS"}
                    </span>
                  </div>
                  <div className={styles.statItem}>
                    <span className={styles.statLabel}>Spread Adv</span>
                    <span className={styles.statValue}>{safeFormat(match.spread_adv, 1)}</span>
                  </div>
                  <div className={styles.statItem}>
                    <span className={styles.statLabel}>Model Confidence</span>
                    <span className={styles.confidenceStars}>{renderStars(match.confidence)}</span>
                  </div>
                </div>
              </div>

              {/* ACTION ROW (BOTTOM) */}
              <div className={styles.actionRow}>
                <div className={styles.actionItem}>
                  <div className={styles.actionLabel}>F5 Pick</div>
                  <div className={styles.actionValue}>{match.f5_pick || "N/A"}</div>
                </div>
                <div className={styles.actionItem}>
                  <div className={styles.actionLabel}>O/U ({match.odds?.ou_total || "?"})</div>
                  <div className={`
                    ${styles.actionValue} 
                    ${totalPlay === "BET UNDER" ? styles.badgeUnder : ""} 
                    ${totalPlay === "BET OVER" ? styles.badgeOver : ""} 
                    ${totalPlay === "PASS" ? styles.badgePass : ""}
                  `}>
                    {totalPlay}
                  </div>
                </div>
              </div>

            </div>
          );
        })}
      </main>

      {/* ... main içeriği bittikten sonra ... */}

      <footer className={styles.footer}>
        <div className={styles.signature}>
          Created with precision by <a href="mailto:ozzencben@gmail.com">Ozenc</a>
        </div>

        <div className={styles.footerLinks}>
          <a
            href="https://www.upwork.com/freelancers/~01bd880efba1b95a83"
            target="_blank"
            rel="noopener noreferrer"
          >
            Hire me on Upwork
          </a>
          <span>•</span>
          <a href="#">Documentation</a>
          <span>•</span>
          <span>© 2026 MLB Predictor Engine v2.0</span>
        </div>
      </footer>

    </div >
  );
}
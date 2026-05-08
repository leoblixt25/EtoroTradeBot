import { useEffect, useState } from 'react';

interface Props {
  overall: number;
  breakdown: {
    diversification: number;
    risk_management: number;
    returns: number;
    stability: number;
    trader_quality: number;
  };
}

const scoreColors = (score: number) => {
  if (score >= 80) return { text: 'text-success-500', stroke: '#10b981', ring: '#10b981' };
  if (score >= 60) return { text: 'text-primary-500', stroke: '#059669', ring: '#059669' };
  if (score >= 40) return { text: 'text-warning-500', stroke: '#f59e0b', ring: '#f59e0b' };
  return { text: 'text-danger-500', stroke: '#ef4444', ring: '#ef4444' };
};

export default function HealthScore({ overall, breakdown }: Props) {
  const [animatedScore, setAnimatedScore] = useState(0);

  useEffect(() => {
    const timer = setTimeout(() => setAnimatedScore(overall), 100);
    return () => clearTimeout(timer);
  }, [overall]);

  const colors = scoreColors(overall);
  const circumference = 2 * Math.PI * 60;
  const offset = circumference - (animatedScore / 100) * circumference;

  const bars = [
    { label: 'Diversification', score: breakdown.diversification },
    { label: 'Risk Management', score: breakdown.risk_management },
    { label: 'Returns', score: breakdown.returns },
    { label: 'Stability', score: breakdown.stability },
    { label: 'Trader Quality', score: breakdown.trader_quality },
  ];

  return (
    <div>
      <div className="flex flex-col items-center mb-4">
        <div className="relative w-40 h-40">
          <svg className="w-full h-full -rotate-90" viewBox="0 0 140 140">
            <circle
              cx="70"
              cy="70"
              r="60"
              fill="none"
              stroke="var(--border-color)"
              strokeWidth="10"
            />
            <circle
              cx="70"
              cy="70"
              r="60"
              fill="none"
              stroke={colors.stroke}
              strokeWidth="10"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={offset}
              className="gauge-ring"
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className={`text-3xl font-bold ${colors.text}`}>
              {animatedScore.toFixed(0)}
            </span>
            <span className="text-[10px] text-[var(--text-secondary)]">Health Score</span>
          </div>
        </div>
      </div>

      <div className="space-y-2.5">
        {bars.map((bar) => {
          const barColors = scoreColors(bar.score);
          return (
            <div key={bar.label}>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-[var(--text-secondary)]">{bar.label}</span>
                <span className={`font-medium ${barColors.text}`}>
                  {bar.score.toFixed(0)}%
                </span>
              </div>
              <div className="h-2 rounded-full bg-[var(--border-color)] overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-1000 ease-out"
                  style={{
                    width: `${bar.score}%`,
                    backgroundColor: barColors.stroke,
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

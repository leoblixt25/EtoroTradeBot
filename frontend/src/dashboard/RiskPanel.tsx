import Card from '../components/Card';
import type { RiskMetrics } from '../types';

interface Props {
  data: RiskMetrics | null;
  loading: boolean;
}

function getRiskLevel(score: number): string {
  if (score <= 30) return 'low';
  if (score <= 60) return 'moderate';
  if (score <= 80) return 'elevated';
  return 'high';
}

export default function RiskPanel({ data, loading }: Props) {
  const getRiskColor = (score: number) => {
    if (score <= 30) return 'text-success-500';
    if (score <= 60) return 'text-warning-500';
    if (score <= 80) return 'text-orange-500';
    return 'text-danger-500';
  };

  const getRiskBg = (score: number) => {
    if (score <= 30) return 'bg-success-500';
    if (score <= 60) return 'bg-warning-500';
    if (score <= 80) return 'bg-orange-500';
    return 'bg-danger-500';
  };

  const score = data?.current_risk_score ?? 0;
  const riskLevel = getRiskLevel(score);
  const riskLevelColor =
    riskLevel === 'low'
      ? 'text-success-500 bg-success-500/10'
      : riskLevel === 'moderate'
        ? 'text-warning-500 bg-warning-500/10'
        : riskLevel === 'elevated'
          ? 'text-orange-500 bg-orange-500/10'
          : 'text-danger-500 bg-danger-500/10';

  const circumference = 2 * Math.PI * 54;
  const offset = circumference - (score / 100) * circumference;

  const metrics = data
    ? [
        { label: 'VaR 95%', value: data.var_95, unit: '%', max: 20 },
        { label: 'Max Drawdown', value: data.max_drawdown * 100, unit: '%', max: 50 },
        { label: 'Volatility', value: data.volatility * 100, unit: '%', max: 60 },
        { label: 'Concentration', value: data.concentration_risk * 100, unit: '%', max: 100 },
      ]
    : [];

  return (
    <Card title="Risk Overview" loading={loading}>
      {data && (
        <div className="flex flex-col items-center">
          <div className="relative w-36 h-36">
            <svg className="w-full h-full -rotate-90" viewBox="0 0 120 120">
              <circle cx="60" cy="60" r="54" fill="none" stroke="var(--border-color)" strokeWidth="8" />
              <circle
                cx="60" cy="60" r="54" fill="none"
                stroke={score <= 30 ? '#10b981' : score <= 60 ? '#f59e0b' : score <= 80 ? '#f97316' : '#ef4444'}
                strokeWidth="8" strokeLinecap="round"
                strokeDasharray={circumference} strokeDashoffset={offset}
                className="gauge-ring"
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className={`text-2xl font-bold ${getRiskColor(score)}`}>{score.toFixed(0)}</span>
              <span className="text-[10px] text-[var(--text-secondary)]">Risk Score</span>
            </div>
          </div>
          <span className={`badge mt-2 ${riskLevelColor}`}>{riskLevel}</span>
          <div className="w-full mt-4 space-y-3">
            {metrics.map((m) => {
              const pct = Math.min((m.value / m.max) * 100, 100);
              return (
                <div key={m.label}>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-[var(--text-secondary)]">{m.label}</span>
                    <span className="text-[var(--text-primary)] font-medium">{m.value.toFixed(1)}{m.unit}</span>
                  </div>
                  <div className="h-1.5 rounded-full bg-[var(--border-color)] overflow-hidden">
                    <div className={`h-full rounded-full ${getRiskBg(pct)}`} style={{ width: `${pct}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </Card>
  );
}

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
} from 'recharts';
import Card from '../components/Card';
import { useRiskMetrics, usePortfolio, useHistory, useTraders } from '../hooks/useApi';

export default function Analytics() {
  const { data: risk, loading: riskLoading } = useRiskMetrics();
  const { data: portfolio } = usePortfolio();
  const { data: history } = useHistory();
  const { data: traders } = useTraders();

  const vol = risk?.volatility || 1;
  const dd = Math.abs(risk?.max_drawdown || 1);
  const monthlyR = portfolio && portfolio.total_value > 0
    ? ((portfolio.monthly_pnl ?? 0) / portfolio.total_value) * 100
    : 0;
  const annualR = monthlyR * 12;
  const sharpeRatio = vol > 0 ? (annualR - 5) / vol : 0;
  const sortinoRatio = sharpeRatio > 0 ? sharpeRatio * 1.3 : 0;
  const calmarRatio = dd > 0 ? annualR / dd : 0;
  const totalPnlAmt = (portfolio?.unrealized_pnl ?? 0) + (portfolio?.realized_pnl ?? 0);
  const totalPnlPct = portfolio && (portfolio.total_value - totalPnlAmt) > 0
    ? (totalPnlAmt / (portfolio.total_value - totalPnlAmt)) * 100
    : 0;
  const riskText = risk ? (
    risk.current_risk_score <= 30 ? 'low' :
    risk.current_risk_score <= 60 ? 'medium' :
    risk.current_risk_score <= 80 ? 'high' : 'critical'
  ) : 'unknown';

  const getBarColor = (val: number) => (val >= 0 ? '#10b981' : '#ef4444');

  const monthlyData = history
    ? history.reduce((acc: { month: string; pnl: number }[], item, i, arr) => {
        if (i === 0 || item.date.slice(0, 7) !== arr[i - 1].date.slice(0, 7)) {
          acc.push({ month: item.date.slice(0, 7), pnl: item.pnl });
        } else {
          acc[acc.length - 1].pnl += item.pnl;
        }
        return acc;
      }, [])
    : [];

  const classificationData = traders
    ? Object.entries(
        traders.reduce((acc: Record<string, number>, t) => {
          acc[t.classification] = (acc[t.classification] || 0) + 1;
          return acc;
        }, {})
      ).map(([label, value]) => ({ label, value }))
    : [];

  const getRiskColor = (score: number) => {
    if (score <= 30) return 'bg-success-500';
    if (score <= 60) return 'bg-warning-500';
    if (score <= 80) return 'bg-orange-500';
    return 'bg-danger-500';
  };

  const getRiskTextColor = (score: number) => {
    if (score <= 30) return 'text-success-500';
    if (score <= 60) return 'text-warning-500';
    if (score <= 80) return 'text-orange-500';
    return 'text-danger-500';
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="Risk Dashboard" loading={riskLoading}>
          {risk && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                {[
                  { label: 'VaR 95%', value: risk.var_95, max: 20, unit: '%' },
                  { label: 'Max Drawdown', value: risk.max_drawdown * 100, max: 50, unit: '%' },
                  { label: 'Volatility (Ann.)', value: risk.volatility * 100, max: 60, unit: '%' },
                  { label: 'Concentration', value: risk.concentration_risk, max: 100, unit: '%' },
                ].map((m) => {
                  const pct = Math.min((m.value / m.max) * 100, 100);
                  return (
                    <div key={m.label} className="p-3 rounded-lg bg-[var(--border-color)]/30">
                      <p className="text-xs text-[var(--text-secondary)] mb-1">{m.label}</p>
                      <p className="text-lg font-bold text-[var(--text-primary)]">
                        {m.value.toFixed(1)}{m.unit}
                      </p>
                      <div className="mt-2 h-1.5 rounded-full bg-[var(--border-color)] overflow-hidden">
                        <div
                          className={`h-full rounded-full ${getRiskColor(pct)}`}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </Card>

        <Card title="Performance Ratios" loading={riskLoading}>
          {risk && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                {[
                  { label: 'Sharpe Ratio', value: sharpeRatio, good: true },
                  { label: 'Sortino Ratio', value: sortinoRatio, good: true },
                  { label: 'Calmar Ratio', value: calmarRatio, good: true },
                ].map((m) => (
                  <div key={m.label} className="p-3 rounded-lg bg-[var(--border-color)]/30">
                    <p className="text-xs text-[var(--text-secondary)]">{m.label}</p>
                    <p
                      className={`text-lg font-bold mt-1 ${
                        m.value >= (m.good ? 1 : 0)
                          ? 'text-success-500'
                          : 'text-danger-500'
                      }`}
                    >
                      {m.value.toFixed(2)}
                    </p>
                  </div>
                ))}
                <div className="p-3 rounded-lg bg-[var(--border-color)]/30">
                  <p className="text-xs text-[var(--text-secondary)]">Win Rate</p>
                  <p className="text-lg font-bold text-[var(--text-primary)]">
                    {totalPnlPct
                      ? (50 + totalPnlPct).toFixed(1)
                      : 'N/A'}
                    {totalPnlPct ? '%' : ''}
                  </p>
                </div>
              </div>
              <div className="p-3 rounded-lg bg-[var(--border-color)]/30">
                <p className="text-xs text-[var(--text-secondary)] mb-2">Overall Risk Score</p>
                <div className="flex items-center gap-4">
                  <div className="relative w-20 h-20">
                    <svg className="w-full h-full -rotate-90" viewBox="0 0 80 80">
                      <circle cx="40" cy="40" r="34" fill="none" stroke="var(--border-color)" strokeWidth="6" />
                      <circle
                        cx="40" cy="40" r="34" fill="none"
                        stroke={risk.current_risk_score <= 30 ? '#10b981' : risk.current_risk_score <= 60 ? '#f59e0b' : '#ef4444'}
                        strokeWidth="6" strokeLinecap="round"
                        strokeDasharray={2 * Math.PI * 34}
                        strokeDashoffset={2 * Math.PI * 34 - (risk.current_risk_score / 100) * 2 * Math.PI * 34}
                        className="gauge-ring"
                      />
                    </svg>
                    <div className="absolute inset-0 flex items-center justify-center">
                      <span className={`text-lg font-bold ${getRiskTextColor(risk.current_risk_score)}`}>
                        {risk.current_risk_score.toFixed(0)}
                      </span>
                    </div>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-[var(--text-primary)] capitalize">
                      {riskText} Risk
                    </p>
                    <p className="text-xs text-[var(--text-secondary)]">
                      Updated {new Date().toLocaleDateString()}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="Monthly Returns">
          <div className="h-72">
            {monthlyData.length > 0 && (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={monthlyData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
                  <XAxis
                    dataKey="month"
                    tick={{ fontSize: 11, fill: 'var(--text-secondary)' }}
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis
                    tick={{ fontSize: 11, fill: 'var(--text-secondary)' }}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}K`}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'var(--bg-card)',
                      border: '1px solid var(--border-color)',
                      borderRadius: '8px',
                      fontSize: '12px',
                    }}
                  />
                  <Bar dataKey="pnl" radius={[4, 4, 0, 0]} fill="#10b981">
                    {monthlyData.map((entry, i) => (
                      <rect key={i} fill={getBarColor(entry.pnl)} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </Card>

        <Card title="Trader Classification">
          <div className="h-72">
            {classificationData.length > 0 && (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={classificationData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
                  <XAxis type="number" tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} tickLine={false} axisLine={false} />
                  <YAxis
                    dataKey="label"
                    type="category"
                    tick={{ fontSize: 11, fill: 'var(--text-secondary)' }}
                    tickLine={false}
                    axisLine={false}
                    width={120}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'var(--bg-card)',
                      border: '1px solid var(--border-color)',
                      borderRadius: '8px',
                      fontSize: '12px',
                    }}
                  />
                  <Bar dataKey="value" radius={[0, 4, 4, 0]} fill="#10b981" />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </Card>
      </div>

      <Card title="Risk Score Trend">
        <div className="h-72">
          {history && history.length > 0 && (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={history}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 11, fill: 'var(--text-secondary)' }}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  tick={{ fontSize: 11, fill: 'var(--text-secondary)' }}
                  tickLine={false}
                  axisLine={false}
                  domain={[0, 100]}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'var(--bg-card)',
                    border: '1px solid var(--border-color)',
                    borderRadius: '8px',
                    fontSize: '12px',
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="pnl"
                  stroke="#f59e0b"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </Card>
    </div>
  );
}

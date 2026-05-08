import { TrendingUp, TrendingDown, DollarSign, BarChart3, LineChart } from 'lucide-react';
import Card from '../components/Card';
import type { PortfolioSummary as PortfolioSummaryType } from '../types';

interface Props {
  data: PortfolioSummaryType | null;
  loading: boolean;
}

export default function PortfolioSummary({ data, loading }: Props) {
  if (loading || !data) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <Card key={i} loading />
        ))}
      </div>
    );
  }

  const metrics = [
    {
      label: 'Total Value',
      value: data.total_value,
      change: data.day_change_percent,
      isUp: data.daily_pnl >= 0,
      icon: DollarSign,
      color: 'text-primary-500',
      bg: 'bg-primary-500/10',
    },
    {
      label: 'Daily P&L',
      value: data.daily_pnl,
      change: data.day_change_percent,
      isUp: data.daily_pnl >= 0,
      icon: TrendingUp,
      color: data.daily_pnl >= 0 ? 'text-success-500' : 'text-danger-500',
      bg: data.daily_pnl >= 0 ? 'bg-success-500/10' : 'bg-danger-500/10',
    },
    {
      label: 'Weekly P&L',
      value: data.weekly_pnl,
      change: data.total_value > 0 ? (data.weekly_pnl / (data.total_value - data.weekly_pnl)) * 100 : 0,
      isUp: data.weekly_pnl >= 0,
      icon: BarChart3,
      color: data.weekly_pnl >= 0 ? 'text-success-500' : 'text-danger-500',
      bg: data.weekly_pnl >= 0 ? 'bg-success-500/10' : 'bg-danger-500/10',
    },
    {
      label: 'Monthly P&L',
      value: data.monthly_pnl,
      change: data.total_value > 0 ? (data.monthly_pnl / (data.total_value - data.monthly_pnl)) * 100 : 0,
      isUp: data.monthly_pnl >= 0,
      icon: LineChart,
      color: data.monthly_pnl >= 0 ? 'text-success-500' : 'text-danger-500',
      bg: data.monthly_pnl >= 0 ? 'bg-success-500/10' : 'bg-danger-500/10',
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {metrics.map((m) => (
        <Card key={m.label}>
          <div className="flex items-start justify-between">
            <div className="space-y-2">
              <p className="text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wider">
                {m.label}
              </p>
              <p className="text-2xl font-bold text-[var(--text-primary)]">
                {formatCurrency(m.value)}
              </p>
              <div
                className={`flex items-center gap-1 text-xs font-medium ${
                  m.isUp ? 'metric-up' : 'metric-down'
                }`}
              >
                {m.isUp ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                <span>{Math.abs(m.change).toFixed(2)}%</span>
              </div>
            </div>
            <div className={`p-3 rounded-xl ${m.bg}`}>
              <m.icon size={20} className={m.color} />
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
}

function formatCurrency(value: number): string {
  const abs = Math.abs(value);
  const sign = value < 0 ? '-' : '';
  if (abs >= 1_000_000) return `${sign}$${(abs / 1_000_000).toFixed(2)}M`;
  if (abs >= 1_000) return `${sign}$${(abs / 1_000).toFixed(1)}K`;
  return `${sign}$${abs.toFixed(2)}`;
}

import { useNavigate } from 'react-router-dom';
import { TrendingUp, TrendingDown, User, PauseCircle, PlayCircle } from 'lucide-react';
import Card from '../components/Card';
import type { CopiedTrader } from '../types';

interface Props {
  traders: CopiedTrader[] | null;
  loading: boolean;
}

export default function TraderOverview({ traders, loading }: Props) {
  const navigate = useNavigate();

  if (loading || !traders) {
    return (
      <Card title="Top Traders" loading>
        <div className="flex gap-3 overflow-x-auto pb-2">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="skeleton h-32 w-48 shrink-0 rounded-xl" />
          ))}
        </div>
      </Card>
    );
  }

  return (
    <Card title="Top Traders" subtitle="Your copied traders">
      <div className="flex gap-3 overflow-x-auto pb-2 -mx-1 px-1">
        {traders.slice(0, 5).map((trader) => {
          const riskScore = Math.min(Math.max(Math.abs(trader.total_roi) * 5, 10), 90);
          return (
          <div
            key={trader.id}
            onClick={() => navigate('/traders')}
            className="card p-4 min-w-[200px] shrink-0 cursor-pointer hover:border-primary-500/30 transition-colors"
          >
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center text-white font-semibold text-sm">
                {trader.trader_name.charAt(0)}
              </div>
              <div className="min-w-0">
                <p className="text-sm font-medium text-[var(--text-primary)] truncate">
                  {trader.trader_name}
                </p>
                <span className={`badge mt-0.5 ${
                  trader.classification === 'conservative'
                    ? 'bg-success-500/10 text-success-500'
                    : trader.classification === 'balanced'
                      ? 'bg-primary-500/10 text-primary-500'
                      : trader.classification === 'aggressive'
                        ? 'bg-warning-500/10 text-warning-500'
                        : 'bg-danger-500/10 text-danger-500'
                }`}>
                  {trader.classification}
                </span>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <p className="text-[10px] text-[var(--text-secondary)] uppercase">Allocation</p>
                <p className="text-sm font-semibold text-[var(--text-primary)]">
                  {trader.allocation_percent.toFixed(1)}%
                </p>
              </div>
              <div>
                <p className="text-[10px] text-[var(--text-secondary)] uppercase">PnL</p>
                <div className="flex items-center gap-1">
                  {trader.total_pnl >= 0 ? (
                    <TrendingUp size={12} className="text-success-500" />
                  ) : (
                    <TrendingDown size={12} className="text-danger-500" />
                  )}
                  <span className={`text-sm font-semibold ${
                    trader.total_pnl >= 0 ? 'text-success-500' : 'text-danger-500'
                  }`}>
                    ${Math.abs(trader.total_pnl).toFixed(0)}
                  </span>
                </div>
              </div>
            </div>
            <div className="mt-2">
              <div className="flex items-center justify-between text-[10px] text-[var(--text-secondary)]">
                <span>Risk</span>
                <span>{riskScore.toFixed(0)}%</span>
              </div>
              <div className="mt-1 h-1.5 rounded-full bg-[var(--border-color)] overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${
                    riskScore > 70
                      ? 'bg-danger-500'
                      : riskScore > 40
                        ? 'bg-warning-500'
                        : 'bg-success-500'
                  }`}
                  style={{ width: `${riskScore}%` }}
                />
              </div>
            </div>
            <div className="mt-2 flex items-center gap-1">
              {trader.status === 'active' ? (
                <PlayCircle size={12} className="text-success-500" />
              ) : (
                <PauseCircle size={12} className="text-warning-500" />
              )}
              <span className="text-[10px] text-[var(--text-secondary)] capitalize">{trader.status}</span>
            </div>
          </div>
          );
        })}
      </div>
    </Card>
  );
}

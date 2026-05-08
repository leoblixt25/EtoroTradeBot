import { useState, useMemo } from 'react';
import {
  TrendingUp,
  TrendingDown,
  Play,
  Pause,
  Filter,
  X,
  AlertTriangle,
  BarChart3,
} from 'lucide-react';
import Card from '../components/Card';
import { useTraders, useRiskMetrics } from '../hooks/useApi';
import type { CopiedTrader } from '../types';

export default function Traders() {
  const { data: traders, loading } = useTraders();
  const [filterClass, setFilterClass] = useState<string>('all');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [selectedTrader, setSelectedTrader] = useState<CopiedTrader | null>(null);
  const [compareIds, setCompareIds] = useState<number[]>([]);

  const filtered = useMemo(() => {
    if (!traders) return [];
    return traders.filter((t) => {
      if (filterClass !== 'all' && t.classification !== filterClass) return false;
      if (filterStatus !== 'all' && t.status !== filterStatus) return false;
      return true;
    });
  }, [traders, filterClass, filterStatus]);

  const toggleCompare = (id: number) => {
    setCompareIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-wrap items-center gap-3">
        <select
          value={filterClass}
          onChange={(e) => setFilterClass(e.target.value)}
          className="px-3 py-2 rounded-lg border border-[var(--border-color)] bg-[var(--bg-card)] text-sm text-[var(--text-primary)] focus:outline-none focus:border-primary-500"
        >
          <option value="all">All Classifications</option>
          <option value="conservative">Conservative</option>
          <option value="balanced">Balanced</option>
          <option value="growth">Growth</option>
          <option value="aggressive">Aggressive</option>
          <option value="very_aggressive">Very Aggressive</option>
        </select>

        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="px-3 py-2 rounded-lg border border-[var(--border-color)] bg-[var(--bg-card)] text-sm text-[var(--text-primary)] focus:outline-none focus:border-primary-500"
        >
          <option value="all">All Statuses</option>
          <option value="active">Active</option>
          <option value="paused">Paused</option>
          <option value="stopped">Stopped</option>
        </select>

        <div className="flex items-center gap-2 ml-auto">
          {compareIds.length > 0 && (
            <span className="text-xs text-[var(--text-secondary)]">
              {compareIds.length} selected
            </span>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
        {filtered.map((trader) => (
          <TraderCard
            key={trader.id}
            trader={trader}
            selected={selectedTrader?.id === trader.id}
            comparing={compareIds.includes(trader.id)}
            onSelect={() => setSelectedTrader(trader)}
            onCompare={() => toggleCompare(trader.id)}
          />
        ))}
      </div>

      {selectedTrader && (
        <TraderDetailModal
          trader={selectedTrader}
          onClose={() => setSelectedTrader(null)}
        />
      )}
    </div>
  );
}

function TraderCard({
  trader,
  selected,
  comparing,
  onSelect,
  onCompare,
}: {
  trader: CopiedTrader;
  selected: boolean;
  comparing: boolean;
  onSelect: () => void;
  onCompare: () => void;
}) {
  const statusColor = {
    active: 'bg-success-500',
    paused: 'bg-warning-500',
    stopped: 'bg-danger-500',
  };

  const classColor = {
    conservative: 'bg-success-500/10 text-success-500 border-success-500/20',
    balanced: 'bg-primary-500/10 text-primary-500 border-primary-500/20',
    growth: 'bg-warning-500/10 text-warning-500 border-warning-500/20',
    aggressive: 'bg-orange-500/10 text-orange-500 border-orange-500/20',
    very_aggressive: 'bg-danger-500/10 text-danger-500 border-danger-500/20',
  };

  return (
    <div
      className={`card p-4 cursor-pointer transition-all hover:border-primary-500/30 ${
        selected ? 'ring-2 ring-primary-500' : ''
      } ${comparing ? 'ring-2 ring-warning-500' : ''}`}
      onClick={onSelect}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-full bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center text-white font-bold text-lg">
              {trader.trader_name.charAt(0)}
          </div>
          <div>
            <p className="text-sm font-semibold text-[var(--text-primary)]">
              {trader.trader_name}
            </p>
            <span
              className={`badge mt-1 border ${classColor[trader.classification as keyof typeof classColor] || 'bg-primary-500/10 text-primary-500 border-primary-500/20'}`}
            >
              {trader.classification.replace('_', ' ')}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className={`w-2.5 h-2.5 rounded-full ${statusColor[trader.status]}`} />
          <button
            onClick={(e) => {
              e.stopPropagation();
              onCompare();
            }}
            className={`p-1.5 rounded-lg ${
              comparing
                ? 'bg-warning-500/10 text-warning-500'
                : 'hover:bg-[var(--border-color)] text-[var(--text-secondary)]'
            }`}
          >
            <BarChart3 size={14} />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3 mb-3">
        <div>
          <p className="text-[10px] text-[var(--text-secondary)] uppercase">Allocation</p>
          <p className="text-sm font-semibold text-[var(--text-primary)]">
            {trader.allocation_percent.toFixed(1)}%
          </p>
        </div>
        <div>
          <p className="text-[10px] text-[var(--text-secondary)] uppercase">Value</p>
          <p className="text-sm font-semibold text-[var(--text-primary)]">
            ${trader.current_value.toLocaleString()}
          </p>
        </div>
        <div>
          <p className="text-[10px] text-[var(--text-secondary)] uppercase">ROI</p>
          <div className="flex items-center gap-1">
            {trader.total_roi >= 0 ? (
              <TrendingUp size={14} className="text-success-500" />
            ) : (
              <TrendingDown size={14} className="text-danger-500" />
            )}
            <span
              className={`text-sm font-semibold ${
                trader.total_roi >= 0 ? 'text-success-500' : 'text-danger-500'
              }`}
            >
              {trader.total_roi.toFixed(1)}%
            </span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <p className="text-[10px] text-[var(--text-secondary)] uppercase">P&L</p>
          <p className={`text-sm font-medium ${trader.total_pnl >= 0 ? 'metric-up' : 'metric-down'}`}>
            ${Math.abs(trader.total_pnl).toLocaleString()}
          </p>
        </div>
        <div>
          <p className="text-[10px] text-[var(--text-secondary)] uppercase">Value</p>
          <p className="text-sm font-medium text-[var(--text-primary)]">
            ${trader.current_value.toLocaleString()}
          </p>
        </div>
      </div>
    </div>
  );
}

function TraderDetailModal({
  trader,
  onClose,
}: {
  trader: CopiedTrader;
  onClose: () => void;
}) {
  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div
        className="w-full max-w-lg rounded-xl border border-[var(--border-color)] bg-[var(--bg-card)] shadow-xl animate-slide-up"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-4 border-b border-[var(--border-color)]">
          <h2 className="text-lg font-semibold text-[var(--text-primary)]">
            {trader.trader_name}
          </h2>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-[var(--border-color)]"
          >
            <X size={18} className="text-[var(--text-secondary)]" />
          </button>
        </div>
        <div className="p-4 space-y-4">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-full bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center text-white font-bold text-2xl">
            {trader.trader_name.charAt(0)}
            </div>
            <div>
              <span className="badge bg-primary-500/10 text-primary-500">
                {trader.classification.replace('_', ' ')}
              </span>
              <div className="flex items-center gap-2 mt-2">
                <div
                  className={`w-2.5 h-2.5 rounded-full ${
                    trader.status === 'active'
                      ? 'bg-success-500'
                      : trader.status === 'paused'
                        ? 'bg-warning-500'
                        : 'bg-danger-500'
                  }`}
                />
                <span className="text-sm text-[var(--text-secondary)] capitalize">
                  {trader.status}
                </span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="p-3 rounded-lg bg-[var(--border-color)]/30">
              <p className="text-xs text-[var(--text-secondary)]">Total ROI</p>
              <p
                className={`text-lg font-bold ${
                  trader.total_roi >= 0 ? 'metric-up' : 'metric-down'
                }`}
              >
                {trader.total_roi.toFixed(2)}%
              </p>
            </div>
            <div className="p-3 rounded-lg bg-[var(--border-color)]/30">
              <p className="text-xs text-[var(--text-secondary)]">Total P&L</p>
              <p className={`text-lg font-bold ${trader.total_pnl >= 0 ? 'metric-up' : 'metric-down'}`}>
                ${Math.abs(trader.total_pnl).toLocaleString()}
              </p>
            </div>
            <div className="p-3 rounded-lg bg-[var(--border-color)]/30">
              <p className="text-xs text-[var(--text-secondary)]">Allocation</p>
              <p className="text-lg font-bold text-[var(--text-primary)]">
                {trader.allocation_percent.toFixed(1)}%
              </p>
            </div>
            <div className="p-3 rounded-lg bg-[var(--border-color)]/30">
              <p className="text-xs text-[var(--text-secondary)]">Current Value</p>
              <p className="text-lg font-bold text-[var(--text-primary)]">
                ${trader.current_value.toLocaleString()}
              </p>
            </div>
          </div>

          <div>
            <p className="text-xs text-[var(--text-secondary)] mb-2">Total ROI</p>
            <p className={`text-lg font-bold ${trader.total_roi >= 0 ? 'metric-up' : 'metric-down'}`}>
              {trader.total_roi.toFixed(2)}%
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

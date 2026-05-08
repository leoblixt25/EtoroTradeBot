import { useState, useMemo } from 'react';
import {
  Search,
  TrendingUp,
  TrendingDown,
  ArrowUpDown,
  ExternalLink,
} from 'lucide-react';
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  CartesianGrid,
  Area,
  AreaChart,
} from 'recharts';
import Card from '../components/Card';
import { usePortfolio, usePositions, useHistory } from '../hooks/useApi';

type SortKey = 'instrument_name' | 'instrument_type' | 'allocated_amount' | 'pnl' | 'pnl_percent';

const COLORS = ['#10b981', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6'];

export default function Portfolio() {
  const { data: portfolio } = usePortfolio();
  const { data: positions, loading: positionsLoading } = usePositions();
  const { data: history } = useHistory();

  const [search, setSearch] = useState('');
  const [sortKey, setSortKey] = useState<SortKey>('allocated_amount');
  const [sortAsc, setSortAsc] = useState(false);
  const [chartPeriod, setChartPeriod] = useState('1M');

  const periods = ['1W', '1M', '3M', '6M', '1Y', 'ALL'];

  const filteredPositions = useMemo(() => {
    if (!positions) return [];
    let filtered = positions;
    if (search) {
      const q = search.toLowerCase();
      filtered = positions.filter(
        (p) =>
          p.instrument_name.toLowerCase().includes(q) ||
          p.instrument_type.toLowerCase().includes(q)
      );
    }
    return [...filtered].sort((a, b) => {
      const aVal = a[sortKey] ?? 0;
      const bVal = b[sortKey] ?? 0;
      if (typeof aVal === 'string') {
        return sortAsc
          ? (aVal as string).localeCompare(bVal as string)
          : (bVal as string).localeCompare(aVal as string);
      }
      return sortAsc ? (aVal as number) - (bVal as number) : (bVal as number) - (aVal as number);
    });
  }, [positions, search, sortKey, sortAsc]);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortAsc(!sortAsc);
    } else {
      setSortKey(key);
      setSortAsc(false);
    }
  };

  const allocationData = useMemo(() => {
    if (!positions) return [];
    const map = new Map<string, number>();
    positions.forEach((p) => {
      map.set(p.instrument_type, (map.get(p.instrument_type) || 0) + p.allocated_amount);
    });
    return Array.from(map.entries()).map(([label, value]) => ({
      label,
      value,
    }));
  }, [positions]);

  const summaryCards = [
    {
      label: 'Total Value',
      value: portfolio?.total_value ?? 0,
    },
    {
      label: 'Cash',
      value: portfolio?.cash_balance ?? 0,
    },
    {
      label: 'Invested',
      value: portfolio?.invested_amount ?? 0,
    },
    {
      label: 'Unrealized P&L',
      value: portfolio?.unrealized_pnl ?? 0,
      isUp: (portfolio?.unrealized_pnl ?? 0) >= 0,
    },
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {summaryCards.map((c) => (
          <Card key={c.label}>
            <p className="text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wider">
              {c.label}
            </p>
            <p className={`text-xl font-bold mt-1 ${c.isUp !== undefined ? (c.isUp ? 'metric-up' : 'metric-down') : 'text-[var(--text-primary)]'}`}>
              {formatCurrency(c.value)}
            </p>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        <div className="lg:col-span-2">
          <Card title="Allocation">
            <div className="h-64">
              {allocationData.length > 0 && (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={allocationData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={90}
                      paddingAngle={3}
                      dataKey="value"
                    >
                      {allocationData.map((_, i) => (
                        <Cell key={i} fill={COLORS[i % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'var(--bg-card)',
                        border: '1px solid var(--border-color)',
                        borderRadius: '8px',
                        fontSize: '12px',
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              )}
            </div>
            <div className="mt-2 space-y-1.5">
              {allocationData.map((d, i) => (
                <div key={d.label} className="flex items-center gap-2 text-xs">
                  <div
                    className="w-2.5 h-2.5 rounded-full shrink-0"
                    style={{ backgroundColor: COLORS[i % COLORS.length] }}
                  />
                  <span className="text-[var(--text-secondary)]">{d.label}</span>
                </div>
              ))}
            </div>
          </Card>
        </div>

        <div className="lg:col-span-3">
          <Card title="Performance">
            <div className="flex gap-1 mb-4">
              {periods.map((p) => (
                <button
                  key={p}
                  onClick={() => setChartPeriod(p)}
                  className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                    chartPeriod === p
                      ? 'bg-primary-500 text-white'
                      : 'bg-[var(--border-color)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
            <div className="h-64">
              {history && history.length > 0 && (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={history}>
                    <defs>
                      <linearGradient id="perfGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                      </linearGradient>
                    </defs>
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
                    <Area
                      type="monotone"
                      dataKey="value"
                      stroke="#10b981"
                      strokeWidth={2}
                      fill="url(#perfGrad)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              )}
            </div>
          </Card>
        </div>
      </div>

      <Card title="Positions" loading={positionsLoading}>
        <div className="mb-4 relative">
          <Search
            size={16}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-secondary)]"
          />
          <input
            type="text"
            placeholder="Search instruments..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] text-sm text-[var(--text-primary)] placeholder:text-[var(--text-secondary)] focus:outline-none focus:border-primary-500 transition-colors"
          />
        </div>

        <div className="overflow-x-auto -mx-1">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--border-color)]">
                {[
                  { key: 'instrument_name' as SortKey, label: 'Instrument' },
                  { key: 'instrument_type' as SortKey, label: 'Type' },
                  { label: 'Amount' },
                  { label: 'Entry' },
                  { label: 'Current' },
                  { key: 'allocated_amount' as SortKey, label: 'Allocated' },
                  { key: 'pnl' as SortKey, label: 'P&L' },
                  { key: 'pnl_percent' as SortKey, label: 'P&L%' },
                  { label: '' },
                ].map((col) => (
                  <th
                    key={col.label}
                    className={`px-3 py-3 text-left text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wider ${
                      col.key ? 'cursor-pointer hover:text-[var(--text-primary)]' : ''
                    }`}
                    onClick={() => col.key && toggleSort(col.key)}
                  >
                    <div className="flex items-center gap-1">
                      {col.label}
                      {col.key && (
                        <ArrowUpDown
                          size={12}
                          className={
                            sortKey === col.key
                              ? 'text-primary-500'
                              : 'text-[var(--text-secondary)]'
                          }
                        />
                      )}
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border-color)]">
              {filteredPositions.map((pos) => (
                <tr
                  key={pos.id}
                  className="hover:bg-[var(--border-color)]/30 transition-colors"
                >
                  <td className="px-3 py-3 font-medium text-[var(--text-primary)]">
                    {pos.instrument_name}
                  </td>
                  <td className="px-3 py-3">
                    <span className="badge bg-primary-500/10 text-primary-500">
                      {pos.instrument_type}
                    </span>
                  </td>
                  <td className="px-3 py-3 text-[var(--text-secondary)]">
                    {pos.amount.toFixed(2)}
                  </td>
                  <td className="px-3 py-3 text-[var(--text-secondary)]">
                    ${pos.entry_price.toFixed(2)}
                  </td>
                  <td className="px-3 py-3 text-[var(--text-primary)]">
                    ${pos.current_price.toFixed(2)}
                  </td>
                  <td className="px-3 py-3 text-[var(--text-primary)] font-medium">
                    ${pos.allocated_amount.toLocaleString()}
                  </td>
                  <td
                    className={`px-3 py-3 font-medium ${
                      pos.pnl >= 0 ? 'metric-up' : 'metric-down'
                    }`}
                  >
                    <div className="flex items-center gap-1">
                      {pos.pnl >= 0 ? (
                        <TrendingUp size={14} />
                      ) : (
                        <TrendingDown size={14} />
                      )}
                      ${Math.abs(pos.pnl).toLocaleString()}
                    </div>
                  </td>
                  <td
                    className={`px-3 py-3 font-medium ${
                      pos.pnl_percent >= 0 ? 'metric-up' : 'metric-down'
                    }`}
                  >
                    {pos.pnl_percent.toFixed(2)}%
                  </td>
                  <td className="px-3 py-3">
                    <button className="btn btn-ghost p-1.5 rounded-lg">
                      <ExternalLink size={14} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
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

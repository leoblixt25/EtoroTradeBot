import { useState } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import Card from '../components/Card';
import type { PerformanceData } from '../types';

interface Props {
  data: PerformanceData[] | null;
  loading: boolean;
}

const periods = ['1W', '1M', '3M', '6M', '1Y', 'ALL'];

export default function PerformanceChart({ data, loading }: Props) {
  const [period, setPeriod] = useState('1M');

  return (
    <Card title="Portfolio Performance" subtitle={`Over the ${period} period`} loading={loading}>
      <div className="flex gap-1 mb-4">
        {periods.map((p) => (
          <button
            key={p}
            onClick={() => setPeriod(p)}
            className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
              period === p
                ? 'bg-primary-500 text-white'
                : 'bg-[var(--border-color)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            {p}
          </button>
        ))}
      </div>
      <div className="h-64 sm:h-80">
        {data && data.length > 0 && (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 5, right: 5, left: 0, bottom: 5 }}>
              <defs>
                <linearGradient id="valueGradient" x1="0" y1="0" x2="0" y2="1">
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
                formatter={(value: number) => [`$${value.toLocaleString()}`, 'Value']}
              />
              <Area
                type="monotone"
                dataKey="value"
                stroke="#10b981"
                strokeWidth={2}
                fill="url(#valueGradient)"
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
        {(!data || data.length === 0) && !loading && (
          <div className="h-full flex items-center justify-center text-sm text-[var(--text-secondary)]">
            No performance data available
          </div>
        )}
      </div>
    </Card>
  );
}

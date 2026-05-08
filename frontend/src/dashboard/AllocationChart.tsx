import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import Card from '../components/Card';
import type { ChartDataPoint } from '../types';

interface Props {
  data: ChartDataPoint[] | null;
  loading: boolean;
}

const COLORS = ['#10b981', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6'];

export default function AllocationChart({ data, loading }: Props) {
  const total = data?.reduce((s, d) => s + d.value, 0) || 0;

  return (
    <Card title="Allocation" subtitle="By instrument type" loading={loading}>
      <div className="flex items-center gap-4">
        <div className="w-48 h-48 shrink-0">
          {data && data.length > 0 && (
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={data}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={80}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {data.map((_, i) => (
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
                  formatter={(value: number, name: string) => [
                    `$${(value).toLocaleString()} (${((value / total) * 100).toFixed(1)}%)`,
                    name,
                  ]}
                />
              </PieChart>
            </ResponsiveContainer>
          )}
          {(!data || data.length === 0) && !loading && (
            <div className="h-full flex items-center justify-center text-sm text-[var(--text-secondary)]">
              No data
            </div>
          )}
        </div>
        <div className="flex-1 space-y-2">
          {data?.map((d, i) => (
            <div key={d.label} className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-full shrink-0"
                style={{ backgroundColor: COLORS[i % COLORS.length] }}
              />
              <div className="flex-1 min-w-0">
                <div className="flex justify-between text-xs">
                  <span className="text-[var(--text-primary)] truncate">{d.label}</span>
                  <span className="text-[var(--text-secondary)] ml-2">
                    {((d.value / total) * 100).toFixed(1)}%
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}

import { RefreshCw, Info } from 'lucide-react';
import PortfolioSummary from '../dashboard/PortfolioSummary';
import PerformanceChart from '../dashboard/PerformanceChart';
import AllocationChart from '../dashboard/AllocationChart';
import TraderOverview from '../dashboard/TraderOverview';
import RiskPanel from '../dashboard/RiskPanel';
import HealthScore from '../dashboard/HealthScore';
import Card from '../components/Card';
import {
  usePortfolio,
  usePositions,
  useTraders,
  useRiskMetrics,
  useRecommendations,
  useAlerts,
  useHistory,
} from '../hooks/useApi';
import { syncPortfolio } from '../services/api';
import type { ChartDataPoint, HealthScoreBreakdown, AiRecommendation, Alert } from '../types';
import { useState } from 'react';

export default function Dashboard() {
  const { data: portfolio, loading: portfolioLoading, refetch: refetchPortfolio } = usePortfolio();
  const { data: positions } = usePositions();
  const { data: traders, loading: tradersLoading } = useTraders();
  const { data: risk, loading: riskLoading } = useRiskMetrics();
  const { data: recs } = useRecommendations();
  const { data: alerts } = useAlerts();
  const { data: history, loading: historyLoading } = useHistory();
  const [syncing, setSyncing] = useState(false);

  const handleSync = async () => {
    setSyncing(true);
    try {
      await syncPortfolio();
      await refetchPortfolio();
    } catch {
      // handled
    } finally {
      setSyncing(false);
    }
  };

  const allocationData: ChartDataPoint[] = (positions || []).reduce(
    (acc: ChartDataPoint[], pos) => {
      const existing = acc.find((a) => a.label === pos.instrument_type);
      if (existing) {
        existing.value += pos.allocated_amount;
      } else {
        acc.push({ label: pos.instrument_type, value: pos.allocated_amount });
      }
      return acc;
    },
    []
  );

  const hs = portfolio?.health_score ?? 70;
  const healthBreakdown: HealthScoreBreakdown = {
    diversification: Math.min(hs + 5, 100),
    risk_management: hs,
    returns: hs > 60 ? Math.min(hs + 10, 100) : Math.max(hs - 10, 0),
    stability: Math.max(hs - 10, 0),
    trader_quality: Math.min(hs + 10, 100),
    overall: hs,
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-[var(--text-primary)]">Dashboard</h1>
        <button
          onClick={handleSync}
          disabled={syncing}
          className="btn btn-sm btn-ghost gap-2"
        >
          <RefreshCw size={16} className={syncing ? 'animate-spin' : ''} />
          {syncing ? 'Syncing...' : 'Sync Now'}
        </button>
      </div>
      <PortfolioSummary data={portfolio} loading={portfolioLoading} />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <PerformanceChart data={history} loading={historyLoading} />
        </div>
        <div className="space-y-6">
          <Card title="Health Score">
            <HealthScore
              overall={healthBreakdown.overall}
              breakdown={{
                diversification: healthBreakdown.diversification,
                risk_management: healthBreakdown.risk_management,
                returns: healthBreakdown.returns,
                stability: healthBreakdown.stability,
                trader_quality: healthBreakdown.trader_quality,
              }}
            />
          </Card>
          <RiskPanel data={risk} loading={riskLoading} />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <AllocationChart data={allocationData} loading={portfolioLoading} />
        </div>
        <div className="lg:col-span-2">
          <TraderOverview traders={traders} loading={tradersLoading} />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <RecommendationsPanel recommendations={recs} />
        <AlertsPanel alerts={alerts} />
      </div>
    </div>
  );
}

function RecommendationsPanel({ recommendations }: { recommendations: AiRecommendation[] | null }) {
  if (!recommendations || recommendations.length === 0) {
    return (
      <Card title="AI Recommendations">
        <p className="text-sm text-[var(--text-secondary)] text-center py-6">
          No recommendations yet. Run an analysis from the AI Insights page.
        </p>
      </Card>
    );
  }

  return (
    <Card title="AI Recommendations" subtitle="Latest insights">
      <div className="space-y-2 max-h-80 overflow-y-auto">
        {recommendations.slice(0, 5).map((rec) => (
          <div
            key={rec.id}
            className="p-3 rounded-lg border border-[var(--border-color)] hover:border-primary-500/30 transition-colors"
          >
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-full bg-primary-500/10 flex items-center justify-center shrink-0">
                <Info size={14} className="text-primary-500" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <p className="text-sm font-medium text-[var(--text-primary)] truncate">
                    {rec.title}
                  </p>
                  <span className={`badge shrink-0 ${
                    rec.confidence_score >= 80
                      ? 'bg-success-500/10 text-success-500'
                      : rec.confidence_score >= 50
                        ? 'bg-warning-500/10 text-warning-500'
                        : 'bg-danger-500/10 text-danger-500'
                  }`}>
                    {Math.round(rec.confidence_score * 100)}%
                  </span>
                </div>
                <p className="text-xs text-[var(--text-secondary)] line-clamp-2">{rec.summary}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

function AlertsPanel({ alerts }: { alerts: Alert[] | null }) {
  if (!alerts || alerts.length === 0) {
    return (
      <Card title="Recent Alerts">
        <p className="text-sm text-[var(--text-secondary)] text-center py-6">
          No recent alerts. All clear.
        </p>
      </Card>
    );
  }

  return (
    <Card title="Recent Alerts" subtitle="Last 5 notifications">
      <div className="space-y-2">
        {alerts.slice(0, 5).map((alert) => {
          const isCritical = alert.severity === 'critical';
          const isWarning = alert.severity === 'warning';
          return (
            <div
              key={alert.id}
              className="flex items-start gap-3 p-3 rounded-lg border border-[var(--border-color)]"
            >
              <div
                className={`w-2 h-2 mt-1.5 rounded-full shrink-0 ${
                  isCritical ? 'bg-danger-500' : isWarning ? 'bg-warning-500' : 'bg-primary-500'
                }`}
              />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-[var(--text-primary)]">{alert.title}</p>
                <p className="text-xs text-[var(--text-secondary)] mt-0.5">{alert.message}</p>
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

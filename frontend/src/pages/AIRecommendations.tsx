import { useState } from 'react';
import {
  Brain,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  Info,
  Lightbulb,
  TrendingUp,
} from 'lucide-react';
import Card from '../components/Card';
import { useRecommendations, useTraders } from '../hooks/useApi';
import { triggerAnalysis } from '../services/api';
import type { AiRecommendation } from '../types';

export default function AIRecommendations() {
  const { data: recommendations, loading, refetch } = useRecommendations();
  const { data: traders } = useTraders();
  const [analyzing, setAnalyzing] = useState(false);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [selectedTrader, setSelectedTrader] = useState<string>('');

  const handleAnalyze = async () => {
    setAnalyzing(true);
    try {
      await triggerAnalysis();
      refetch();
    } catch {
      // error handled
    } finally {
      setAnalyzing(false);
    }
  };

  const sorted = (recommendations || []).sort(
    (a, b) => b.confidence_score - a.confidence_score
  );

  const riskLevel = (score: number): 'low' | 'medium' | 'high' => {
    if (score >= 80) return 'low';
    if (score >= 50) return 'medium';
    return 'high';
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center">
            <Brain size={20} className="text-white" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-[var(--text-primary)]">
              AI Insights
            </h2>
            <p className="text-xs text-[var(--text-secondary)]">
              Machine learning analysis and recommendations
            </p>
          </div>
        </div>
        <button
          onClick={handleAnalyze}
          disabled={analyzing}
          className="btn btn-primary"
        >
          <RefreshCw
            size={16}
            className={analyzing ? 'animate-spin' : ''}
          />
          {analyzing ? 'Analyzing...' : 'Trigger Analysis'}
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <Card title="Recommendations" subtitle="Sorted by confidence" loading={loading}>
            {sorted.length === 0 && !loading && (
              <div className="text-center py-8 text-sm text-[var(--text-secondary)]">
                No recommendations yet. Click "Trigger Analysis" to generate insights.
              </div>
            )}
            <div className="space-y-3">
              {sorted.map((rec) => (
                <div
                  key={rec.id}
                  className="rounded-lg border border-[var(--border-color)] overflow-hidden hover:border-primary-500/30 transition-colors"
                >
                  <div
                    className="p-4 cursor-pointer"
                    onClick={() =>
                      setExpandedId(expandedId === rec.id ? null : rec.id)
                    }
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex items-start gap-3 min-w-0 flex-1">
                        <div
                          className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
                            rec.recommendation_type === 'risk'
                              ? 'bg-danger-500/10'
                              : rec.recommendation_type === 'opportunity'
                                ? 'bg-success-500/10'
                                : 'bg-primary-500/10'
                          }`}
                        >
                          {rec.recommendation_type === 'risk' ? (
                            <AlertTriangle size={16} className="text-danger-500" />
                          ) : rec.recommendation_type === 'opportunity' ? (
                            <TrendingUp size={16} className="text-success-500" />
                          ) : (
                            <Lightbulb size={16} className="text-primary-500" />
                          )}
                        </div>
                        <div className="min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <p className="text-sm font-medium text-[var(--text-primary)]">
                              {rec.title}
                            </p>
                            <span
                              className={`badge ${
                                rec.confidence_score >= 80
                                  ? 'bg-success-500/10 text-success-500'
                                  : rec.confidence_score >= 50
                                    ? 'bg-warning-500/10 text-warning-500'
                                    : 'bg-danger-500/10 text-danger-500'
                              }`}
                            >
                              {rec.confidence_score}%
                            </span>
                            {!rec.applied && (
                              <span className="badge bg-danger-500/10 text-danger-500">
                                Action Required
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-[var(--text-secondary)] mt-1">
                            {rec.summary}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <RiskBadge level={riskLevel(rec.confidence_score)} />
                        {expandedId === rec.id ? (
                          <ChevronUp size={16} className="text-[var(--text-secondary)]" />
                        ) : (
                          <ChevronDown size={16} className="text-[var(--text-secondary)]" />
                        )}
                      </div>
                    </div>
                  </div>
                  {expandedId === rec.id && (
                    <div className="px-4 pb-4 pt-0 border-t border-[var(--border-color)] animate-fade-in">
                      <div className="mt-3 p-3 rounded-lg bg-[var(--border-color)]/30">
                        <p className="text-xs font-medium text-[var(--text-secondary)] mb-1">
                          Reasoning
                        </p>
                        <p className="text-sm text-[var(--text-primary)]">
                          {rec.summary}
                        </p>
                      </div>
                      <div className="flex items-center justify-between mt-3 text-xs text-[var(--text-secondary)]">
                        <span>
                          {(rec.details as Record<string, string>)?.trader_name && `Trader: ${(rec.details as Record<string, string>).trader_name}`}
                        </span>
                        <span>
                          {new Date(rec.created_at).toLocaleDateString('en-US', {
                            month: 'short',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </Card>
        </div>

        <div className="space-y-6">
          <Card title="Weekly Summary">
            <div className="p-4 rounded-lg bg-gradient-to-br from-primary-500/5 to-primary-500/10 border border-primary-500/20">
              <div className="flex items-center gap-2 mb-2">
                <Brain size={16} className="text-primary-500" />
                <p className="text-sm font-semibold text-[var(--text-primary)]">
                  AI Overview
                </p>
              </div>
              <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
                {recommendations && recommendations.length > 0
                  ? `${recommendations.length} active recommendations. ${recommendations.filter((r) => !r.applied).length} require your attention. Portfolio health is being monitored.`
                  : 'Run an analysis to get your weekly AI summary with portfolio health insights, risk assessment, and actionable recommendations.'}
              </p>
            </div>
            <div className="mt-4 space-y-3">
              {[
                { label: 'Total Insights', value: recommendations?.length ?? 0, icon: Lightbulb, color: 'text-primary-500' },
                { label: 'Action Required', value: recommendations?.filter((r) => !r.applied).length ?? 0, icon: AlertTriangle, color: 'text-danger-500' },
                { label: 'High Confidence', value: recommendations?.filter((r) => r.confidence_score >= 80).length ?? 0, icon: TrendingUp, color: 'text-success-500' },
              ].map((s) => (
                <div key={s.label} className="flex items-center justify-between p-2">
                  <div className="flex items-center gap-2">
                    <s.icon size={14} className={s.color} />
                    <span className="text-xs text-[var(--text-secondary)]">{s.label}</span>
                  </div>
                  <span className="text-sm font-semibold text-[var(--text-primary)]">{s.value}</span>
                </div>
              ))}
            </div>
          </Card>

          <Card title="Trader Analysis">
            <select
              value={selectedTrader}
              onChange={(e) => setSelectedTrader(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] text-sm text-[var(--text-primary)] focus:outline-none focus:border-primary-500 mb-4"
            >
              <option value="">Select a trader...</option>
              {(traders || []).map((t) => (
                <option key={t.id} value={String(t.id)}>
                  {t.trader_name}
                </option>
              ))}
            </select>
            {selectedTrader ? (
              <div className="text-sm text-[var(--text-secondary)]">
                <p>Analysis available for selected trader.</p>
              </div>
            ) : (
              <p className="text-xs text-[var(--text-secondary)]">
                Select a trader above to view AI-powered behavior analysis, risk
                assessment, and performance predictions.
              </p>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}

function RiskBadge({ level }: { level: 'low' | 'medium' | 'high' }) {
  const colors = {
    low: 'bg-success-500/10 text-success-500',
    medium: 'bg-warning-500/10 text-warning-500',
    high: 'bg-danger-500/10 text-danger-500',
  };

  return <span className={`badge ${colors[level]}`}>{level} risk</span>;
}

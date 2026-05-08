import { useState, useEffect, useCallback, useRef } from 'react';
import type {
  PortfolioSummary,
  Position,
  CopiedTrader,
  RiskMetrics,
  RiskLimits,
  AutomationRule,
  AiRecommendation,
  Alert,
  PerformanceData,
  AppSettings,
} from '../types';
import {
  getPortfolio,
  getPositions,
  getHistory,
  getTraders,
  getRiskSummary,
  getRiskLimits,
  getAutomationRules,
  getRecommendations,
  getAlerts,
  getSettings,
} from '../services/api';

interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

function useAsync<T>(fetchFn: () => Promise<T>): AsyncState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const fetchRef = useRef(fetchFn);
  fetchRef.current = fetchFn;

  const [version, setVersion] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchRef.current()
      .then(result => { if (!cancelled) setData(result); })
      .catch((e: Error) => { if (!cancelled) setError(e.message); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [version]);

  const refetch = useCallback(() => setVersion(v => v + 1), []);

  return { data, loading, error, refetch };
}

export function usePortfolio() {
  return useAsync(getPortfolio);
}

export function usePositions() {
  return useAsync(getPositions);
}

export function useHistory(period?: string) {
  return useAsync(() => getHistory(period));
}

export function useTraders() {
  return useAsync(getTraders);
}

export function useRiskMetrics() {
  return useAsync(getRiskSummary);
}

export function useRiskLimits() {
  return useAsync(getRiskLimits);
}

export function useRecommendations() {
  return useAsync(getRecommendations);
}

export function useAlerts() {
  return useAsync(getAlerts);
}

export function useAutomationRules() {
  return useAsync(getAutomationRules);
}

export function useSettings() {
  return useAsync(getSettings);
}

import axios, { AxiosError } from 'axios';
import type {
  PortfolioSummary,
  Position,
  CopiedTrader,
  TraderAnalysis,
  RiskMetrics,
  RiskLimits,
  AutomationRule,
  AutomationRuleConfig,
  AutomationLog,
  AiRecommendation,
  Alert,
  PerformanceData,
  PaginatedResponse,
  AppSettings,
} from '../types';

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('etoro_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

function handleError(error: unknown): string {
  if (error instanceof AxiosError && error.response?.data) {
    const data = error.response.data as { detail?: string; message?: string };
    return data.detail || data.message || 'An error occurred';
  }
  if (error instanceof Error) return error.message;
  return 'Unknown error';
}

// Portfolio
export async function getPortfolio(): Promise<PortfolioSummary> {
  try {
    const { data } = await api.get('/portfolio');
    return data.summary || data;
  } catch (error) {
    throw new Error(handleError(error));
  }
}

export async function getPositions(): Promise<Position[]> {
  try {
    const { data } = await api.get('/portfolio/positions');
    return Array.isArray(data) ? data : [];
  } catch (error) {
    throw new Error(handleError(error));
  }
}

export async function getHistory(period?: string): Promise<PerformanceData[]> {
  try {
    const { data } = await api.get('/portfolio/history', { params: { period: period || '1m' } });
    return Array.isArray(data) ? data : [];
  } catch (error) {
    throw new Error(handleError(error));
  }
}

// Traders
export async function getTraders(): Promise<CopiedTrader[]> {
  try {
    const { data } = await api.get('/traders');
    return Array.isArray(data) ? data : [];
  } catch (error) {
    throw new Error(handleError(error));
  }
}

export async function getTrader(id: number): Promise<TraderAnalysis> {
  try {
    const { data } = await api.get(`/traders/${id}`);
    return data;
  } catch (error) {
    throw new Error(handleError(error));
  }
}

export async function getTraderPerformance(id: number): Promise<PerformanceData[]> {
  try {
    const { data } = await api.get(`/traders/${id}/performance`);
    return Array.isArray(data) ? data : [];
  } catch (error) {
    throw new Error(handleError(error));
  }
}

export async function pauseTrader(id: number): Promise<CopiedTrader> {
  try {
    const { data } = await api.post(`/traders/${id}/pause`);
    return data;
  } catch (error) {
    throw new Error(handleError(error));
  }
}

export async function resumeTrader(id: number): Promise<CopiedTrader> {
  try {
    const { data } = await api.post(`/traders/${id}/resume`);
    return data;
  } catch (error) {
    throw new Error(handleError(error));
  }
}

// Risk
export async function getRiskSummary(): Promise<RiskMetrics> {
  try {
    const { data } = await api.get('/risk/summary');
    return data;
  } catch (error) {
    throw new Error(handleError(error));
  }
}

export async function getRiskLimits(): Promise<RiskLimits> {
  try {
    const { data } = await api.get('/risk/limits');
    return data;
  } catch (error) {
    throw new Error(handleError(error));
  }
}

export async function updateRiskLimits(limits: Partial<RiskLimits>): Promise<RiskLimits> {
  try {
    const { data } = await api.put('/risk/limits', limits);
    return data;
  } catch (error) {
    throw new Error(handleError(error));
  }
}

export async function emergencyStop(): Promise<void> {
  try {
    await api.post('/risk/emergency-stop');
  } catch (error) {
    throw new Error(handleError(error));
  }
}

// Automation
export async function getAutomationRules(): Promise<AutomationRule[]> {
  try {
    const { data } = await api.get('/automation/rules');
    return Array.isArray(data) ? data : [];
  } catch (error) {
    throw new Error(handleError(error));
  }
}

export async function createRule(rule: Partial<AutomationRule>): Promise<AutomationRule> {
  try {
    const { data } = await api.post('/automation/rules', rule);
    return data;
  } catch (error) {
    throw new Error(handleError(error));
  }
}

export async function updateRule(id: number, rule: Partial<AutomationRule>): Promise<AutomationRule> {
  try {
    const { data } = await api.put(`/automation/rules/${id}`, rule);
    return data;
  } catch (error) {
    throw new Error(handleError(error));
  }
}

export async function deleteRule(id: number): Promise<void> {
  try {
    await api.delete(`/automation/rules/${id}`);
  } catch (error) {
    throw new Error(handleError(error));
  }
}

export async function toggleRule(id: number): Promise<AutomationRule> {
  try {
    const { data } = await api.put(`/automation/rules/${id}/toggle`);
    return data;
  } catch (error) {
    throw new Error(handleError(error));
  }
}

export async function getAutomationLogs(): Promise<AutomationLog[]> {
  try {
    const { data } = await api.get('/automation/logs');
    return Array.isArray(data) ? data : [];
  } catch (error) {
    throw new Error(handleError(error));
  }
}

// AI / Recommendations
export async function getRecommendations(): Promise<AiRecommendation[]> {
  try {
    const { data } = await api.get('/ai/recommendations');
    return Array.isArray(data) ? data : [];
  } catch (error) {
    throw new Error(handleError(error));
  }
}

export async function triggerAnalysis(): Promise<AiRecommendation[]> {
  try {
    const { data } = await api.post('/ai/analyze', { force: true });
    return Array.isArray(data) ? data : [];
  } catch (error) {
    throw new Error(handleError(error));
  }
}

export async function getWeeklySummary(): Promise<AiRecommendation | null> {
  try {
    const { data } = await api.get('/ai/weekly-summary');
    return data;
  } catch (error) {
    return null;
  }
}

// Alerts
export async function getAlerts(): Promise<Alert[]> {
  try {
    const { data } = await api.get('/alerts');
    return Array.isArray(data) ? data : [];
  } catch (error) {
    throw new Error(handleError(error));
  }
}

export async function markAlertRead(id: number): Promise<Alert> {
  try {
    const { data } = await api.put(`/alerts/${id}/read`);
    return data;
  } catch (error) {
    throw new Error(handleError(error));
  }
}

export async function deleteAlert(id: number): Promise<void> {
  try {
    await api.delete(`/alerts/${id}`);
  } catch (error) {
    throw new Error(handleError(error));
  }
}

// Audit
export async function getAuditLogs(page = 1): Promise<PaginatedResponse<unknown>> {
  try {
    const { data } = await api.get('/audit', { params: { page, page_size: 20 } });
    return data;
  } catch (error) {
    throw new Error(handleError(error));
  }
}

// Settings
export async function getSettings(): Promise<AppSettings> {
  try {
    const { data } = await api.get('/settings');
    return data;
  } catch (error) {
    throw new Error(handleError(error));
  }
}

export async function updateEtoroDemoMode(enabled: boolean): Promise<AppSettings> {
  try {
    const { data } = await api.put('/settings/etoro/demo-mode', { etoro_demo_mode: enabled });
    return data;
  } catch (error) {
    throw new Error(handleError(error));
  }
}

export async function updatePaperTrading(enabled: boolean): Promise<AppSettings> {
  try {
    const { data } = await api.put('/settings/paper-trading', { paper_trading: enabled });
    return data;
  } catch (error) {
    throw new Error(handleError(error));
  }
}

export async function updateEtoroKeys(keys: { public_api_key?: string; user_key?: string }): Promise<AppSettings> {
  try {
    const { data } = await api.put('/settings/etoro', keys);
    return data;
  } catch (error) {
    throw new Error(handleError(error));
  }
}

export async function updateTelegramConfig(config: { bot_token?: string; chat_id?: string }): Promise<AppSettings> {
  try {
    const { data } = await api.put('/settings/telegram', config);
    return data;
  } catch (error) {
    throw new Error(handleError(error));
  }
}

export async function syncPortfolio(): Promise<{ status: string; message: string; positions_synced: number; traders_synced: number }> {
  try {
    const { data } = await api.post('/portfolio/sync');
    return data;
  } catch (error) {
    throw new Error(handleError(error));
  }
}

export async function testEtoroConnection(): Promise<{ message: string; status: string }> {
  try {
    const { data } = await api.post('/settings/etoro/test');
    return data;
  } catch (error) {
    throw new Error(handleError(error));
  }
}

export async function testTelegram(): Promise<{ message: string }> {
  try {
    const { data } = await api.post('/telegram/test');
    return data;
  } catch (error) {
    throw new Error(handleError(error));
  }
}

export default api;

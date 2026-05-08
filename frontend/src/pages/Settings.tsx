import { useState, useEffect } from 'react';
import {
  Save,
  AlertTriangle,
  Send,
  Power,
  Eye,
  EyeOff,
  CheckCircle,
  XCircle,
  Loader2,
} from 'lucide-react';
import Card from '../components/Card';
import { useRiskLimits, useAutomationRules, useSettings } from '../hooks/useApi';
import {
  updateRiskLimits,
  toggleRule,
  emergencyStop,
  updatePaperTrading,
  updateEtoroKeys,
  updateTelegramConfig,
  testTelegram,
  testEtoroConnection,
  updateEtoroDemoMode,
  syncPortfolio,
} from '../services/api';
import { useTheme } from '../context/ThemeContext';
import type { RiskLimits, AutomationRule } from '../types';

export default function Settings() {
  const { data: limits, loading: limitsLoading, refetch: refetchLimits } = useRiskLimits();
  const { data: rules, loading: rulesLoading, refetch: refetchRules } = useAutomationRules();
  const { data: settings, loading: settingsLoading, refetch: refetchSettings } = useSettings();
  const { theme, toggleTheme } = useTheme();

  const [limitsForm, setLimitsForm] = useState<Partial<RiskLimits>>({});
  const [saving, setSaving] = useState(false);
  const [showStopConfirm, setShowStopConfirm] = useState(false);

  // Paper trading
  const [paperTrading, setPaperTrading] = useState(true);
  const [togglingPaper, setTogglingPaper] = useState(false);

  // eToro keys
  const [showEtoroPublic, setShowEtoroPublic] = useState(false);
  const [showEtoroUser, setShowEtoroUser] = useState(false);
  const [etoroPublicKey, setEtoroPublicKey] = useState('');
  const [etoroUserKey, setEtoroUserKey] = useState('');
  const [savingEtoro, setSavingEtoro] = useState(false);
  const [testingEtoro, setTestingEtoro] = useState(false);
  const [etoroTestResult, setEtoroTestResult] = useState<string | null>(null);
  const [etoroDemoMode, setEtoroDemoMode] = useState(false);
  const [togglingDemoMode, setTogglingDemoMode] = useState(false);

  // Telegram
  const [showBotToken, setShowBotToken] = useState(false);
  const [botToken, setBotToken] = useState('');
  const [chatId, setChatId] = useState('');
  const [savingTelegram, setSavingTelegram] = useState(false);
  const [testingTelegram, setTestingTelegram] = useState(false);
  const [testResult, setTestResult] = useState<string | null>(null);

  useEffect(() => {
    if (settings) {
      setPaperTrading(settings.paper_trading);
      setEtoroDemoMode(settings.etoro_demo_mode);
    }
  }, [settings]);

  const currentLimits = { ...limits, ...limitsForm } as RiskLimits;

  const handleSaveLimits = async () => {
    setSaving(true);
    try {
      await updateRiskLimits(limitsForm);
      refetchLimits();
    } catch {
      // handled
    } finally {
      setSaving(false);
    }
  };

  const handleToggleRule = async (id: number) => {
    try {
      await toggleRule(id);
      refetchRules();
    } catch {
      // handled
    }
  };

  const handleTogglePaperTrading = async () => {
    setTogglingPaper(true);
    try {
      const result = await updatePaperTrading(!paperTrading);
      setPaperTrading(result.paper_trading);
      refetchSettings();
      if (!result.paper_trading && result.etoro_configured) {
        syncPortfolio().catch(() => {});
      }
    } catch {
      // handled
    } finally {
      setTogglingPaper(false);
    }
  };

  const handleSaveEtoroKeys = async () => {
    setSavingEtoro(true);
    try {
      const result = await updateEtoroKeys({
        public_api_key: etoroPublicKey || undefined,
        user_key: etoroUserKey || undefined,
      });
      refetchSettings();
      if (!paperTrading && result.etoro_configured) {
        syncPortfolio().catch(() => {});
      }
    } catch {
      // handled
    } finally {
      setSavingEtoro(false);
    }
  };

  const handleTestEtoro = async () => {
    setTestingEtoro(true);
    setEtoroTestResult(null);
    try {
      await testEtoroConnection();
      setEtoroTestResult('success');
    } catch (e) {
      setEtoroTestResult(e instanceof Error ? e.message : 'error');
    } finally {
      setTestingEtoro(false);
    }
  };

  const handleToggleDemoMode = async () => {
    setTogglingDemoMode(true);
    try {
      const result = await updateEtoroDemoMode(!etoroDemoMode);
      setEtoroDemoMode(result.etoro_demo_mode);
      refetchSettings();
    } catch {
      // handled
    } finally {
      setTogglingDemoMode(false);
    }
  };

  const handleSaveTelegram = async () => {
    setSavingTelegram(true);
    try {
      await updateTelegramConfig({
        bot_token: botToken || undefined,
        chat_id: chatId || undefined,
      });
      refetchSettings();
    } catch {
      // handled
    } finally {
      setSavingTelegram(false);
    }
  };

  const handleTestTelegram = async () => {
    setTestingTelegram(true);
    setTestResult(null);
    try {
      await testTelegram();
      setTestResult('success');
    } catch {
      setTestResult('error');
    } finally {
      setTestingTelegram(false);
    }
  };

  const handleEmergencyStop = async () => {
    try {
      await emergencyStop();
      setShowStopConfirm(false);
    } catch {
      // handled
    }
  };

  const limitSliders = [
    { key: 'max_drawdown' as keyof RiskLimits, label: 'Max Drawdown', max: 50, unit: '%' },
    { key: 'max_allocation_per_trader' as keyof RiskLimits, label: 'Max Allocation Per Trader', max: 100, unit: '%' },
    { key: 'min_diversification' as keyof RiskLimits, label: 'Min Diversification', max: 20, unit: ' assets' },
    { key: 'volatility_exposure_reduction' as keyof RiskLimits, label: 'Volatility Reduction', max: 100, unit: '%' },
    { key: 'cooldown_days_after_loss' as keyof RiskLimits, label: 'Cooldown Days', max: 30, unit: ' days' },
  ];

  return (
    <div className="space-y-6 animate-fade-in max-w-4xl">
      <Card
        title="Risk Limits"
        subtitle="Configure your risk management parameters"
        loading={limitsLoading}
      >
        <div className="space-y-4">
          {limitSliders.map((slider) => {
            const value = currentLimits[slider.key] as number || 0;
            return (
              <div key={slider.key}>
                <div className="flex justify-between text-sm mb-1">
                  <label className="text-[var(--text-primary)] font-medium">
                    {slider.label}
                  </label>
                  <span className="text-[var(--text-secondary)]">
                    {value}
                    {slider.unit}
                  </span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={slider.max}
                  step={slider.key === 'cooldown_days_after_loss' ? 1 : 0.5}
                  value={value}
                  onChange={(e) =>
                    setLimitsForm((f) => ({
                      ...f,
                      [slider.key]: parseFloat(e.target.value),
                    }))
                  }
                  className="w-full h-2 rounded-full appearance-none cursor-pointer bg-[var(--border-color)] accent-primary-500"
                />
              </div>
            );
          })}
          <button
            onClick={handleSaveLimits}
            disabled={saving}
            className="btn btn-primary mt-2"
          >
            <Save size={16} />
            {saving ? 'Saving...' : 'Save Limits'}
          </button>
        </div>
      </Card>

      <Card
        title="Automation Rules"
        subtitle="Manage automated trading rules"
        loading={rulesLoading}
      >
        {rules && rules.length > 0 ? (
          <div className="space-y-3">
            {rules.map((rule: AutomationRule) => (
              <div
                key={rule.id}
                className="flex items-center justify-between p-3 rounded-lg border border-[var(--border-color)]"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-medium text-[var(--text-primary)]">
                      {rule.name}
                    </p>
                    <span
                      className={`badge ${
                        rule.enabled
                          ? 'bg-success-500/10 text-success-500'
                          : 'bg-[var(--border-color)] text-[var(--text-secondary)]'
                      }`}
                    >
                      {rule.enabled ? 'Active' : 'Disabled'}
                    </span>
                  </div>
                  <p className="text-xs text-[var(--text-secondary)] mt-0.5">
                    {rule.rule_type}
                  </p>
                </div>
                <button
                  onClick={() => handleToggleRule(rule.id)}
                  className={`p-2 rounded-lg transition-colors ${
                    rule.enabled
                      ? 'bg-success-500/10 text-success-500 hover:bg-success-500/20'
                      : 'bg-[var(--border-color)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                  }`}
                >
                  <Power size={16} />
                </button>
              </div>
            ))}
          </div>
        ) : (
          !rulesLoading && (
            <p className="text-sm text-[var(--text-secondary)] text-center py-4">
              No automation rules configured yet.
            </p>
          )
        )}
      </Card>

      <Card title="Preferences" loading={settingsLoading}>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-[var(--text-primary)]">
                Dark Mode
              </p>
              <p className="text-xs text-[var(--text-secondary)]">
                Toggle dark/light theme
              </p>
            </div>
            <Toggle enabled={theme === 'dark'} onClick={toggleTheme} />
          </div>

          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-[var(--text-primary)]">
                Paper Trading Mode
              </p>
              <p className="text-xs text-[var(--text-secondary)]">
                Simulate trades without real money
              </p>
            </div>
            <Toggle enabled={paperTrading} onClick={handleTogglePaperTrading} loading={togglingPaper} />
          </div>
        </div>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card title="eToro API Keys" loading={settingsLoading}>
          <div className="space-y-4">
            <div>
              <p className="text-sm font-medium text-[var(--text-primary)] mb-1">
                Public API Key
              </p>
              <div className="relative">
                <input
                  type={showEtoroPublic ? 'text' : 'password'}
                  value={etoroPublicKey}
                  placeholder={settings?.etoro_public_key_masked || 'Not configured'}
                  onChange={(e) => setEtoroPublicKey(e.target.value)}
                  className="w-full px-3 py-2 pr-10 rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] text-sm text-[var(--text-primary)]"
                />
                <button
                  onClick={() => setShowEtoroPublic(!showEtoroPublic)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                >
                  {showEtoroPublic ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>
            <div>
              <p className="text-sm font-medium text-[var(--text-primary)] mb-1">
                User Key
              </p>
              <div className="relative">
                <input
                  type={showEtoroUser ? 'text' : 'password'}
                  value={etoroUserKey}
                  placeholder={settings?.etoro_user_key_masked || 'Not configured'}
                  onChange={(e) => setEtoroUserKey(e.target.value)}
                  className="w-full px-3 py-2 pr-10 rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] text-sm text-[var(--text-primary)]"
                />
                <button
                  onClick={() => setShowEtoroUser(!showEtoroUser)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                >
                  {showEtoroUser ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>
            <button onClick={handleSaveEtoroKeys} disabled={savingEtoro} className="btn btn-primary w-full">
              <Save size={16} />
              {savingEtoro ? 'Saving...' : 'Save Keys'}
            </button>
            <button
              onClick={handleTestEtoro}
              disabled={testingEtoro || !settings?.etoro_configured}
              className="btn btn-ghost w-full"
            >
              {testingEtoro ? <Loader2 size={16} className="animate-spin" /> : <CheckCircle size={16} />}
              {testingEtoro ? 'Testing...' : 'Test Connection'}
            </button>
            {etoroTestResult === 'success' && (
              <p className="text-xs text-success-500 flex items-center gap-1">
                <CheckCircle size={12} /> Connection successful
              </p>
            )}
            {etoroTestResult && etoroTestResult !== 'success' && (
              <p className="text-xs text-danger-500 flex items-center gap-1">
                <XCircle size={12} /> {etoroTestResult}
              </p>
            )}
            <div className="flex items-center justify-between pt-2 border-t border-[var(--border-color)]">
              <div>
                <p className="text-sm font-medium text-[var(--text-primary)]">
                  Demo (Virtual) Mode
                </p>
                <p className="text-xs text-[var(--text-secondary)]">
                  Use /demo/ endpoints for Virtual environment keys
                </p>
              </div>
              <Toggle enabled={etoroDemoMode} onClick={handleToggleDemoMode} loading={togglingDemoMode} />
            </div>
          </div>
        </Card>

        <Card title="Telegram Integration" loading={settingsLoading}>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-[var(--text-primary)]">Status</p>
                <p className="text-xs text-[var(--text-secondary)]">
                  {settings?.telegram_configured ? 'Connected' : 'Not connected'}
                </p>
              </div>
              <span className={`badge ${
                settings?.telegram_configured
                  ? 'bg-success-500/10 text-success-500'
                  : 'bg-warning-500/10 text-warning-500'
              }`}>
                {settings?.telegram_configured ? 'Active' : 'Inactive'}
              </span>
            </div>
            <div>
              <p className="text-sm font-medium text-[var(--text-primary)] mb-1">
                Bot Token
              </p>
              <div className="relative">
                <input
                  type={showBotToken ? 'text' : 'password'}
                  value={botToken}
                  placeholder={settings?.telegram_bot_token_masked || 'Enter bot token'}
                  onChange={(e) => setBotToken(e.target.value)}
                  className="w-full px-3 py-2 pr-10 rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] text-sm text-[var(--text-primary)]"
                />
                <button
                  onClick={() => setShowBotToken(!showBotToken)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                >
                  {showBotToken ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>
            <div>
              <p className="text-sm font-medium text-[var(--text-primary)] mb-1">
                Chat ID
              </p>
              <input
                type="text"
                value={chatId}
                placeholder={settings?.telegram_chat_id_masked || 'Enter chat ID'}
                onChange={(e) => setChatId(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] text-sm text-[var(--text-primary)]"
              />
            </div>
            <button onClick={handleSaveTelegram} disabled={savingTelegram} className="btn btn-primary w-full">
              <Save size={16} />
              {savingTelegram ? 'Saving...' : 'Save Telegram'}
            </button>
            <button
              onClick={handleTestTelegram}
              disabled={testingTelegram || !settings?.telegram_configured}
              className="btn btn-ghost w-full"
            >
              {testingTelegram ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
              {testingTelegram ? 'Sending...' : 'Test Notification'}
            </button>
            {testResult === 'success' && (
              <p className="text-xs text-success-500 flex items-center gap-1">
                <CheckCircle size={12} /> Test notification sent
              </p>
            )}
            {testResult === 'error' && (
              <p className="text-xs text-danger-500 flex items-center gap-1">
                <XCircle size={12} /> Test failed — check bot token and chat ID
              </p>
            )}
          </div>
        </Card>
      </div>

      <Card variant="danger" title="Danger Zone">
        {!showStopConfirm ? (
          <button
            onClick={() => setShowStopConfirm(true)}
            className="btn btn-danger w-full"
          >
            <AlertTriangle size={16} />
            Emergency Stop All Trading
          </button>
        ) : (
          <div className="space-y-3 animate-fade-in">
            <p className="text-sm font-medium text-danger-600 dark:text-danger-400">
              Are you sure? This will immediately close all positions and pause all traders.
            </p>
            <div className="flex gap-3">
              <button
                onClick={handleEmergencyStop}
                className="btn btn-danger flex-1"
              >
                <AlertTriangle size={16} />
                Confirm Stop
              </button>
              <button
                onClick={() => setShowStopConfirm(false)}
                className="btn btn-ghost flex-1"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}

function Toggle({ enabled, onClick, loading }: { enabled: boolean; onClick: () => void; loading?: boolean }) {
  return (
    <button
      onClick={onClick}
      disabled={loading}
      className={`relative w-12 h-6 rounded-full transition-colors ${
        enabled ? 'bg-primary-500' : 'bg-[var(--border-color)]'
      } ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
    >
      <div
        className={`absolute top-1 w-4 h-4 rounded-full bg-white shadow transition-transform ${
          enabled ? 'translate-x-7' : 'translate-x-1'
        }`}
      />
    </button>
  );
}

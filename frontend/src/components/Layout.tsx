import { useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import Sidebar from './Sidebar';
import Header from './Header';
import { useAlerts } from '../hooks/useApi';
import { useWebSocket } from '../hooks/useWebSocket';
import { markAlertRead } from '../services/api';

const pageTitles: Record<string, string> = {
  '/': 'Dashboard',
  '/portfolio': 'Portfolio',
  '/traders': 'Traders',
  '/analytics': 'Analytics',
  '/recommendations': 'AI Insights',
  '/settings': 'Settings',
};

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();
  const { data: alerts, refetch: refetchAlerts } = useAlerts();
  const { connected } = useWebSocket('1');

  const title = pageTitles[location.pathname] || 'Dashboard';

  const handleAlertRead = async (id: number) => {
    try {
      await markAlertRead(id);
      refetchAlerts();
    } catch {
      // ignore
    }
  };

  return (
    <div className="flex h-screen overflow-hidden bg-[var(--bg-primary)]">
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="flex-1 flex flex-col min-w-0">
        <Header
          title={title}
          connected={connected}
          alerts={alerts || []}
          onMenuToggle={() => setSidebarOpen(!sidebarOpen)}
          onAlertRead={handleAlertRead}
        />
        <main className="flex-1 overflow-y-auto p-4 sm:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

import { Bell, Menu, Wifi, WifiOff } from 'lucide-react';
import { useState, useRef, useEffect } from 'react';
import ThemeToggle from './ThemeToggle';
import type { Alert } from '../types';

interface HeaderProps {
  title: string;
  connected: boolean;
  alerts: Alert[];
  onMenuToggle: () => void;
  onAlertRead: (id: number) => void;
}

export default function Header({
  title,
  connected,
  alerts,
  onMenuToggle,
  onAlertRead,
}: HeaderProps) {
  const [showNotifications, setShowNotifications] = useState(false);
  const notifRef = useRef<HTMLDivElement>(null);

  const unread = alerts.filter((a) => !a.read).length;

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setShowNotifications(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <header className="h-16 border-b border-[var(--border-color)] bg-[var(--bg-card)] flex items-center justify-between px-4 sm:px-6">
      <div className="flex items-center gap-4">
        <button
          onClick={onMenuToggle}
          className="lg:hidden p-2 rounded-lg hover:bg-[var(--border-color)]"
        >
          <Menu size={20} className="text-[var(--text-secondary)]" />
        </button>
        <h1 className="text-lg font-semibold text-[var(--text-primary)]">
          {title}
        </h1>
      </div>

      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5 px-2 py-1 rounded-full bg-[var(--border-color)]/50">
          {connected ? (
            <>
              <Wifi size={14} className="text-success-500" />
              <span className="text-xs text-[var(--text-secondary)] hidden sm:inline">
                Live
              </span>
            </>
          ) : (
            <>
              <WifiOff size={14} className="text-danger-500" />
              <span className="text-xs text-[var(--text-secondary)] hidden sm:inline">
                Offline
              </span>
            </>
          )}
        </div>

        <ThemeToggle />

        <div className="relative" ref={notifRef}>
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            className="relative p-2 rounded-lg hover:bg-[var(--border-color)]"
          >
            <Bell size={18} className="text-[var(--text-secondary)]" />
            {unread > 0 && (
              <span className="absolute top-1 right-1 w-4 h-4 rounded-full bg-danger-500 text-white text-[10px] font-bold flex items-center justify-center">
                {unread > 9 ? '9+' : unread}
              </span>
            )}
          </button>

          {showNotifications && (
            <div className="absolute right-0 mt-2 w-80 rounded-xl border border-[var(--border-color)] bg-[var(--bg-card)] shadow-xl z-50 animate-fade-in">
              <div className="p-3 border-b border-[var(--border-color)]">
                <p className="text-sm font-semibold text-[var(--text-primary)]">
                  Notifications
                </p>
              </div>
              <div className="max-h-64 overflow-y-auto">
                {alerts.length === 0 ? (
                  <p className="p-4 text-sm text-[var(--text-secondary)] text-center">
                    No notifications
                  </p>
                ) : (
                  alerts.slice(0, 5).map((alert) => (
                    <div
                      key={alert.id}
                      className={`p-3 border-b border-[var(--border-color)] last:border-b-0 cursor-pointer hover:bg-[var(--border-color)]/30 transition-colors ${
                        !alert.read ? 'bg-primary-500/5' : ''
                      }`}
                      onClick={() => {
                        if (!alert.read) onAlertRead(alert.id);
                        setShowNotifications(false);
                      }}
                    >
                      <div className="flex items-start gap-2">
                        <div
                          className={`w-2 h-2 mt-1.5 rounded-full shrink-0 ${
                            alert.severity === 'danger'
                              ? 'bg-danger-500'
                              : alert.severity === 'warning'
                                ? 'bg-warning-500'
                                : 'bg-primary-500'
                          }`}
                        />
                        <div className="min-w-0">
                          <p className="text-xs font-medium text-[var(--text-primary)] truncate">
                            {alert.title}
                          </p>
                          <p className="text-xs text-[var(--text-secondary)] mt-0.5 line-clamp-2">
                            {alert.message}
                          </p>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  PieChart,
  Users,
  BarChart3,
  Brain,
  Settings,
  X,
} from 'lucide-react';
import clsx from 'clsx';

interface SidebarProps {
  open: boolean;
  onClose: () => void;
}

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/portfolio', icon: PieChart, label: 'Portfolio' },
  { to: '/traders', icon: Users, label: 'Traders' },
  { to: '/analytics', icon: BarChart3, label: 'Analytics' },
  { to: '/recommendations', icon: Brain, label: 'AI Insights' },
  { to: '/settings', icon: Settings, label: 'Settings' },
];

export default function Sidebar({ open, onClose }: SidebarProps) {
  return (
    <>
      {open && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={onClose}
        />
      )}
      <aside
        className={clsx(
          'fixed lg:static inset-y-0 left-0 z-50 w-64',
          'bg-[var(--bg-sidebar)] border-r border-[var(--border-color)]',
          'transform transition-transform duration-200 ease-in-out',
          'flex flex-col',
          open ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        )}
      >
        <div className="flex items-center justify-between h-16 px-6 border-b border-[var(--border-color)]">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center">
              <span className="text-white font-bold text-sm">eT</span>
            </div>
            <span className="font-semibold text-sm text-[var(--text-primary)]">
              eToro Manager
            </span>
          </div>
          <button
            onClick={onClose}
            className="lg:hidden p-1 rounded hover:bg-[var(--border-color)]"
          >
            <X size={18} className="text-[var(--text-secondary)]" />
          </button>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              onClick={onClose}
              className={({ isActive }) =>
                clsx('sidebar-item', isActive && 'active')
              }
            >
              <item.icon size={18} />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="px-4 py-3 border-t border-[var(--border-color)]">
          <p className="text-xs text-[var(--text-secondary)]">
            v1.0.0 &middot; Capital Preservation
          </p>
        </div>
      </aside>
    </>
  );
}

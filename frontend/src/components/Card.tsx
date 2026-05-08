import clsx from 'clsx';
import type { ReactNode } from 'react';

interface CardProps {
  title?: string;
  subtitle?: string;
  children?: ReactNode;
  className?: string;
  loading?: boolean;
  variant?: 'default' | 'success' | 'warning' | 'danger';
}

export default function Card({
  title,
  subtitle,
  children,
  className,
  loading = false,
  variant = 'default',
}: CardProps) {
  const variantBorder = {
    default: '',
    success: 'border-l-4 border-l-success-500',
    warning: 'border-l-4 border-l-warning-500',
    danger: 'border-l-4 border-l-danger-500',
  };

  return (
    <div
      className={clsx(
        'card p-4 sm:p-6',
        variantBorder[variant],
        className
      )}
    >
      {(title || subtitle) && (
        <div className="mb-4">
          {title && (
            <h3 className="text-sm font-semibold text-[var(--text-primary)]">
              {title}
            </h3>
          )}
          {subtitle && (
            <p className="text-xs text-[var(--text-secondary)] mt-0.5">
              {subtitle}
            </p>
          )}
        </div>
      )}
      {loading ? (
        <div className="space-y-3">
          <div className="skeleton h-4 w-3/4" />
          <div className="skeleton h-4 w-1/2" />
          <div className="skeleton h-4 w-2/3" />
        </div>
      ) : (
        children
      )}
    </div>
  );
}

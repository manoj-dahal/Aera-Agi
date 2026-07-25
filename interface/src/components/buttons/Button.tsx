import type { ButtonHTMLAttributes, ReactNode } from 'react';
import { cn } from '@utils/cn';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'subtle';
export type ButtonSize = 'sm' | 'md' | 'lg';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  icon?: ReactNode;
  loading?: boolean;
  fullWidth?: boolean;
}

const VARIANTS: Record<ButtonVariant, string> = {
  primary:
    'bg-gradient-to-br from-[var(--aera-accent-primary)] to-[var(--aera-accent-secondary)] text-[var(--aera-accent-ink)] hover:brightness-110',
  secondary:
    'bg-[var(--aera-bg-overlay)] text-[var(--aera-text-primary)] border border-[var(--aera-line-default)] hover:border-[var(--aera-accent-primary)]',
  ghost:
    'bg-transparent text-[var(--aera-text-muted)] border border-[var(--aera-line-default)] hover:text-[var(--aera-text-primary)] hover:border-[var(--aera-accent-primary)]',
  subtle:
    'bg-transparent text-[var(--aera-text-muted)] hover:bg-[var(--aera-bg-overlay)] hover:text-[var(--aera-text-primary)]',
  danger: 'bg-[var(--aera-danger)] text-white hover:brightness-110',
};

const SIZES: Record<ButtonSize, string> = {
  sm: 'text-[11.5px] px-2.5 py-1.5 gap-1.5 rounded-md',
  md: 'text-[13px] px-3.5 py-2 gap-2 rounded-lg',
  lg: 'text-[14px] px-5 py-2.5 gap-2 rounded-lg',
};

export function Button({
  variant = 'secondary',
  size = 'md',
  icon,
  loading = false,
  fullWidth = false,
  className,
  children,
  disabled,
  ...rest
}: ButtonProps) {
  return (
    <button
      className={cn(
        'inline-flex items-center justify-center font-medium transition-all duration-150 disabled:opacity-45',
        VARIANTS[variant],
        SIZES[size],
        fullWidth && 'w-full',
        className,
      )}
      disabled={disabled || loading}
      {...rest}
    >
      {loading ? <span className="animate-spin-slow">◌</span> : icon}
      {children}
    </button>
  );
}

export function IconButton({
  className,
  ...props
}: Omit<ButtonProps, 'children' | 'fullWidth'> & { 'aria-label': string }) {
  return <Button className={cn('!px-2', className)} {...props} />;
}

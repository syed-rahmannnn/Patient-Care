import {
  useEffect,
  type ButtonHTMLAttributes,
  type InputHTMLAttributes,
  type ReactNode,
} from 'react'
import { X } from 'lucide-react'
import { initials } from '../lib/format'

export function cn(...parts: (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(' ')
}

/* ===== Button ===== */
type Variant = 'primary' | 'secondary' | 'ghost' | 'danger'
interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: 'sm' | 'md'
}
const VARIANTS: Record<Variant, string> = {
  primary: 'bg-white text-black hover:bg-zinc-200 font-semibold',
  secondary: 'glass border border-white/10 text-fg hover:border-white/25',
  ghost: 'text-muted hover:text-fg hover:bg-white/5',
  danger: 'text-danger hover:bg-red-400/10',
}
export function Button({ variant = 'secondary', size = 'md', className, ...rest }: ButtonProps) {
  return (
    <button
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded-[10px] transition active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50',
        size === 'sm' ? 'h-8 px-3 text-[13px]' : 'h-10 px-4 text-sm',
        VARIANTS[variant],
        className,
      )}
      {...rest}
    />
  )
}

export function IconButton({ className, ...rest }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className={cn(
        'grid h-9 w-9 place-items-center rounded-lg text-muted transition hover:bg-white/5 hover:text-fg disabled:opacity-40',
        className,
      )}
      {...rest}
    />
  )
}

/* ===== Card ===== */
export function Card({
  className,
  hover,
  children,
}: {
  className?: string
  hover?: boolean
  children: ReactNode
}) {
  return (
    <div
      className={cn(
        'card p-6',
        hover && 'transition hover:border-white/15 hover:bg-cardhover',
        className,
      )}
    >
      {children}
    </div>
  )
}

export function Overline({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cn('text-[11px] font-semibold uppercase tracking-[0.1em] text-muted', className)}>
      {children}
    </div>
  )
}

/* ===== Input ===== */
export function Input({ className, ...rest }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        'h-10 w-full rounded-[10px] border border-line bg-card px-3 text-sm text-fg placeholder:text-faint',
        'transition focus:border-white/25 focus:outline-none focus:ring-2 focus:ring-white/15',
        className,
      )}
      {...rest}
    />
  )
}

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-[13px] font-medium text-fg2">{label}</span>
      {children}
    </label>
  )
}

/* ===== Spinner ===== */
export function Spinner({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        'h-5 w-5 animate-spin rounded-full border-2 border-white/20 border-t-white/80',
        className,
      )}
    />
  )
}

export function Loading({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-3 py-20 text-sm text-muted">
      <Spinner /> {label}
    </div>
  )
}

/* ===== Avatar ===== */
export function Avatar({ name, size = 32 }: { name: string; size?: number }) {
  return (
    <div
      className="grid shrink-0 place-items-center rounded-full bg-white/8 font-semibold text-fg2"
      style={{ width: size, height: size, fontSize: size * 0.38 }}
    >
      {initials(name)}
    </div>
  )
}

/* ===== Status pill ===== */
type Tone = 'active' | 'inactive' | 'pending' | 'acked' | 'danger'
const TONES: Record<Tone, string> = {
  active: 'text-activefg border-active/25 bg-active/10',
  inactive: 'text-fg2 border-inactive/25 bg-inactive/12',
  pending: 'text-warn border-warn/25 bg-warn/10',
  acked: 'text-activefg border-active/25 bg-active/10',
  danger: 'text-[#fca5a5] border-danger/30 bg-danger/10',
}
export function StatusPill({
  tone,
  children,
  dot,
  pulse,
}: {
  tone: Tone
  children: ReactNode
  dot?: boolean
  pulse?: boolean
}) {
  const dotColor =
    tone === 'active' || tone === 'acked'
      ? 'bg-active'
      : tone === 'pending'
        ? 'bg-warn'
        : tone === 'danger'
          ? 'bg-danger'
          : 'bg-inactive'
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[12px] font-semibold',
        TONES[tone],
      )}
    >
      {dot && <span className={cn('h-1.5 w-1.5 rounded-full', dotColor, pulse && 'animate-pulse-dot')} />}
      {children}
    </span>
  )
}

/* ===== Modal ===== */
export function Modal({
  open,
  onClose,
  title,
  children,
  footer,
}: {
  open: boolean
  onClose: () => void
  title: string
  children: ReactNode
  footer?: ReactNode
}) {
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 grid place-items-center p-4">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="animate-fade-up relative w-full max-w-md rounded-[20px] border border-white/10 bg-elevated p-6 shadow-2xl">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">{title}</h2>
          <IconButton onClick={onClose} aria-label="Close">
            <X size={18} />
          </IconButton>
        </div>
        {children}
        {footer && <div className="mt-6 flex justify-end gap-2">{footer}</div>}
      </div>
    </div>
  )
}

/* ===== Empty state ===== */
export function EmptyState({
  icon,
  title,
  hint,
  action,
}: {
  icon: ReactNode
  title: string
  hint?: string
  action?: ReactNode
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
      <div className="grid h-14 w-14 place-items-center rounded-2xl border border-line bg-card text-muted">
        {icon}
      </div>
      <div>
        <div className="font-semibold">{title}</div>
        {hint && <div className="mt-1 text-sm text-muted">{hint}</div>}
      </div>
      {action}
    </div>
  )
}

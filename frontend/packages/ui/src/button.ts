export type ButtonVariant = 'primary' | 'dark' | 'outline' | 'ghost' | 'danger' | 'on-graphite'
export type ButtonSize = 'sm' | 'md' | 'lg'

const base =
  'inline-flex items-center justify-center gap-2 font-semibold select-none transition-colors disabled:opacity-40 no-underline'

const variants: Record<ButtonVariant, string> = {
  primary: 'bg-primary text-on-primary hover:bg-primary-hover',
  dark: 'bg-ink text-white hover:bg-black',
  outline: 'bg-surface text-ink border border-line-strong hover:bg-ground',
  ghost: 'bg-transparent text-ink hover:bg-black/5',
  danger: 'bg-surface text-danger border border-line-strong hover:bg-danger-bg',
  'on-graphite': 'bg-transparent text-primary hover:bg-white/10',
}

const sizes: Record<ButtonSize, string> = {
  sm: 'h-9 px-3 text-sm rounded-[10px]',
  md: 'h-11 px-4 text-[15px] rounded-control',
  lg: 'h-[52px] px-5 text-[17px] rounded-control',
}

/** Same look for <button> and <RouterLink>. */
export function buttonClass(variant: ButtonVariant = 'primary', size: ButtonSize = 'md', block = false) {
  return [base, variants[variant], sizes[size], block ? 'w-full' : ''].join(' ')
}

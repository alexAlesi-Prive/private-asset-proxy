import type { ButtonHTMLAttributes } from 'react'

type Variant = 'primary' | 'secondary' | 'inverted' | 'outlined'

const VARIANTS: Record<Variant, string> = {
  primary: 'bg-primary text-white hover:bg-primary-dark',
  secondary: 'bg-neutral text-primary border border-border hover:bg-white',
  inverted: 'bg-inverted text-white hover:opacity-90',
  outlined: 'bg-transparent text-primary border border-primary hover:bg-primary/5',
}

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
}

export function Button({ variant = 'primary', className = '', ...props }: Props) {
  return (
    <button
      className={`inline-flex items-center justify-center px-4 py-2 rounded-md text-sm font-medium transition
        disabled:opacity-40 disabled:pointer-events-none ${VARIANTS[variant]} ${className}`}
      {...props}
    />
  )
}

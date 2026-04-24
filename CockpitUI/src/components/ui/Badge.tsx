'use client';

import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/cn';

const badge = cva('chip', {
  variants: {
    size: {
      sm: 'h-4 min-h-0 px-1',
      md: 'h-5 min-h-0 px-1.5',
    },
    color: {
      violet: 'text-violet',
      amber:  'text-amber',
      accent: 'text-accent',
      sky:    'text-sky',
      bull:   'text-bull',
      bear:   'text-bear',
      ghost:  'text-ghost',
      dim:    'text-dim',
    },
  },
  defaultVariants: { size: 'md', color: 'ghost' },
});

interface BadgeProps extends VariantProps<typeof badge> {
  children: React.ReactNode;
  className?: string;
  title?: string;
}

export function Badge({ size, color, className, children, title }: BadgeProps) {
  return (
    <span className={cn(badge({ size, color }), className)} title={title}>
      {children}
    </span>
  );
}

import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

/** Merges Tailwind classes without conflicts, supports conditional inputs. */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

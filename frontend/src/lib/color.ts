// Shared color utilities.

// Return a readable ink color for text on a given hex background, using
// relative luminance to decide between ink-dark and paper-cream.
export function contrastInk(hex: string): string {
  const h = (hex ?? '').replace('#', '');
  if (h.length < 6) return '#0B1F3A';
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  const lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return lum > 0.6 ? '#0B1F3A' : '#FAF6E6';
}

// Team-secondary convenience: black secondaries look flat on dark primaries,
// so swap to white. Used in every team chip across the site.
export function secondaryInk(secondary: string): string {
  return secondary === '#000000' ? '#FFFFFF' : secondary;
}

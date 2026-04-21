/**
 * Tiny CSV export utility — turn any array of objects into a downloadable CSV.
 * No dependencies.
 */
export function downloadCsv(filename: string, rows: Record<string, any>[]) {
  if (!rows || rows.length === 0) return;
  const keys = Array.from(new Set(rows.flatMap(r => Object.keys(r))));

  const esc = (v: any): string => {
    if (v === null || v === undefined) return '';
    const s = String(v);
    if (s.includes(',') || s.includes('"') || s.includes('\n')) {
      return `"${s.replace(/"/g, '""')}"`;
    }
    return s;
  };

  const lines = [keys.join(',')];
  for (const row of rows) {
    lines.push(keys.map(k => esc(row[k])).join(','));
  }
  const csv = lines.join('\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

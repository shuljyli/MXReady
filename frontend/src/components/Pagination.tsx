export function Pagination({ label, offset, limit, total, onChange }: {
  label: string; offset: number; limit: number; total: number; onChange: (offset: number) => void;
}) {
  return <nav className="pagination" aria-label={label + "分页"}>
    <button type="button" className="secondary-button compact-button" disabled={offset === 0}
      aria-label={label + "上一页"} onClick={() => onChange(Math.max(0, offset - limit))}>上一页</button>
    <span role="status">{total ? offset + 1 : 0}–{Math.min(offset + limit, total)} / {total}</span>
    <button type="button" className="secondary-button compact-button" disabled={offset + limit >= total}
      aria-label={label + "下一页"} onClick={() => onChange(offset + limit)}>下一页</button>
  </nav>;
}

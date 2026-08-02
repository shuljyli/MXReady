/**
 * 报告加载骨架屏：在拉取报告期间展示占位块，避免空白闪烁。
 */
export function ReportSkeleton() {
  return (
    <div className="report-skeleton" aria-busy="true" aria-label="报告加载中">
      <section className="skeleton-block skeleton-hero">
        <div className="skeleton-line skeleton-line-lg" />
        <div className="skeleton-line" />
      </section>
      <section className="skeleton-block skeleton-summary">
        <div className="skeleton-line" />
        <div className="skeleton-line" />
        <div className="skeleton-line" />
      </section>
      <section className="skeleton-block">
        <div className="skeleton-line skeleton-line-lg" />
        {Array.from({ length: 3 }, (_, index) => (
          <div className="skeleton-card" key={index}>
            <div className="skeleton-line skeleton-line-sm" />
            <div className="skeleton-line" />
            <div className="skeleton-line skeleton-line-md" />
          </div>
        ))}
      </section>
    </div>
  );
}

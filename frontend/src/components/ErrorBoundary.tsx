import { Component, type ErrorInfo, type ReactNode } from "react";

type ErrorBoundaryProps = {
  children: ReactNode;
  label: string;
};

type ErrorBoundaryState = {
  hasError: boolean;
};

/**
 * 区域级错误边界：单一组件崩溃时只替换该区域，避免整页白屏。
 */
export class ErrorBoundary extends Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  state: ErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error(`[ErrorBoundary:${this.props.label}]`, error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <section className="error-panel" role="alert">
          <p className="eyebrow">组件异常</p>
          <h1>这个区域加载失败了</h1>
          <p>{this.props.label}渲染出错，请刷新页面后重试。</p>
          <button
            className="secondary-button"
            onClick={() => this.setState({ hasError: false })}
            type="button"
          >
            重试
          </button>
        </section>
      );
    }
    return this.props.children;
  }
}

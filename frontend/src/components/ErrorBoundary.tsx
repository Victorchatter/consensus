import React from 'react'
import { Copy, RotateCcw, AlertTriangle } from 'lucide-react'

interface Props {
  children: React.ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
  copied: boolean
}

export default class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null, copied: false }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, copied: false }
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('[ErrorBoundary]', error, info)
  }

  handleCopy = () => {
    const { error } = this.state
    const report = [
      `EchoTrader Crash Report`,
      `URL: ${window.location.href}`,
      `Time: ${new Date().toISOString()}`,
      `Message: ${error?.message || 'Unknown error'}`,
      `Stack: ${error?.stack || 'N/A'}`,
    ].join('\n')
    navigator.clipboard.writeText(report).then(() => {
      this.setState({ copied: true })
      setTimeout(() => this.setState({ copied: false }), 2000)
    })
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-bg text-text flex items-center justify-center p-8">
          <div className="bg-elevated border border-danger/30 rounded-lg p-8 max-w-lg w-full shadow-xl">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-danger/10 border border-danger/20 flex items-center justify-center">
                <AlertTriangle size={20} className="text-danger" />
              </div>
              <h2 className="text-xl font-bold text-danger">Something went wrong</h2>
            </div>
            <p className="text-sm text-muted mb-4">
              The application crashed unexpectedly. You can reload the page or copy a crash report to share with support.
            </p>
            <pre className="bg-bg border border-border rounded-md p-4 text-xs font-mono text-muted overflow-auto max-h-40">
              {this.state.error?.message || 'Unknown error'}
            </pre>
            <div className="mt-4 flex flex-wrap gap-3">
              <button
                onClick={() => window.location.reload()}
                className="bg-accent text-bg px-4 py-2 rounded-md text-sm font-semibold hover:bg-accent-light flex items-center gap-2"
              >
                <RotateCcw size={14} /> Reload Page
              </button>
              <button
                onClick={this.handleCopy}
                className="bg-elevated border border-border hover:border-border-hover text-muted hover:text-text px-4 py-2 rounded-md text-sm flex items-center gap-2 transition-colors"
              >
                <Copy size={14} />
                {this.state.copied ? 'Copied!' : 'Copy Report'}
              </button>
            </div>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

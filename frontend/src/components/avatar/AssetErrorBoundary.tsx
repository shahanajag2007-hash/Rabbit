import { Component, type ReactNode } from 'react'

interface Props {
  fallback: ReactNode
  onError?: (error: Error) => void
  children: ReactNode
}

/** Catches failures while loading optional 3D assets so a missing file never crashes the page. */
export class AssetErrorBoundary extends Component<Props, { failed: boolean }> {
  state = { failed: false }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  componentDidCatch(error: Error) {
    console.warn('[STYLEAI] 3D asset failed to load:', error.message)
    this.props.onError?.(error)
  }

  render() {
    return this.state.failed ? this.props.fallback : this.props.children
  }
}

import logger from '@/utils/logger';
import React, { Component } from 'react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';
class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null
    };
  }
  static getDerivedStateFromError(error) {
    return {
      hasError: true,
      error,
      errorInfo: null
    };
  }
  componentDidCatch(error, errorInfo) {
    logger.error('ErrorBoundary caught an error:', error, errorInfo);
    this.setState({
      error,
      errorInfo
    });
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }
  }
  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null
    });
  };
  handleGoHome = () => {
    window.location.href = '/';
  };
  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }
      return <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 p-4"><Card className="max-w-2xl w-full"><CardHeader><div className="flex items-center gap-3"><AlertTriangle className="h-8 w-8 text-destructive" /><CardTitle className="text-2xl">Something went wrong</CardTitle></div></CardHeader><CardContent className="space-y-4"><Alert variant="destructive"><AlertTriangle className="h-4 w-4" /><AlertTitle>Error Details</AlertTitle><AlertDescription><p className="font-semibold mt-2">{this.state.error?.name || 'Unknown Error'}</p><p className="text-sm mt-1">{this.state.error?.message || 'An unexpected error occurred'}</p></AlertDescription></Alert>{process.env.NODE_ENV === 'development' && this.state.errorInfo && <details className="mt-4 p-4 bg-gray-100 dark:bg-gray-800 rounded-md"><summary className="cursor-pointer font-semibold text-sm mb-2">Component Stack Trace (Development Only)</summary><pre className="text-xs overflow-auto whitespace-pre-wrap">{this.state.errorInfo.componentStack}</pre></details>}<div className="flex gap-3 pt-4"><Button onClick={this.handleReset} className="flex items-center gap-2"><RefreshCw className="h-4 w-4" />Try Again</Button><Button onClick={this.handleGoHome} variant="outline" className="flex items-center gap-2"><Home className="h-4 w-4" />Go to Home</Button></div><div className="text-sm text-muted-foreground pt-4 border-t"><p>If this problem persists, please contact support with the error details above.</p></div></CardContent></Card></div>;
    }
    return this.props.children;
  }
}
export default ErrorBoundary;

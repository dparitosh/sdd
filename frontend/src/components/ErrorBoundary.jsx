import logger from '@/utils/logger';
import React, { Component } from 'react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";













/**
 * ErrorBoundary Component
 * 
 * Catches React component errors and displays a user-friendly fallback UI
 * instead of crashing the entire application.
 * 
 * Usage:
 * <ErrorBoundary>
 *   <YourComponent />
 * </ErrorBoundary>
 */
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
    // Update state so the next render will show the fallback UI
    return {
      hasError: true,
      error,
      errorInfo: null
    };
  }

  componentDidCatch(error, errorInfo) {
    // Log error to console in development
    logger.error('ErrorBoundary caught an error:', error, errorInfo);

    // Update state with error details
    this.setState({
      error,
      errorInfo
    });

    // Call optional error handler prop
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }

    // In production, you might want to log to an error reporting service
    // Example: Sentry.captureException(error, { contexts: { react: { componentStack: errorInfo.componentStack } } });
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
      // Custom fallback provided by parent
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // Default error UI
      return (/*#__PURE__*/
        _jsx("div", { className: "min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 p-4", children: /*#__PURE__*/
          _jsxs(Card, { className: "max-w-2xl w-full", children: [/*#__PURE__*/
            _jsx(CardHeader, { children: /*#__PURE__*/
              _jsxs("div", { className: "flex items-center gap-3", children: [/*#__PURE__*/
                _jsx(AlertTriangle, { className: "h-8 w-8 text-destructive" }), /*#__PURE__*/
                _jsx(CardTitle, { className: "text-2xl", children: "Something went wrong" })] }
              ) }
            ), /*#__PURE__*/
            _jsxs(CardContent, { className: "space-y-4", children: [/*#__PURE__*/
              _jsxs(Alert, { variant: "destructive", children: [/*#__PURE__*/
                _jsx(AlertTriangle, { className: "h-4 w-4" }), /*#__PURE__*/
                _jsx(AlertTitle, { children: "Error Details" }), /*#__PURE__*/
                _jsxs(AlertDescription, { children: [/*#__PURE__*/
                  _jsx("p", { className: "font-semibold mt-2", children: this.state.error?.name || 'Unknown Error' }), /*#__PURE__*/
                  _jsx("p", { className: "text-sm mt-1", children: this.state.error?.message || 'An unexpected error occurred' })] }
                )] }
              ),

              process.env.NODE_ENV === 'development' && this.state.errorInfo && /*#__PURE__*/
              _jsxs("details", { className: "mt-4 p-4 bg-gray-100 dark:bg-gray-800 rounded-md", children: [/*#__PURE__*/
                _jsx("summary", { className: "cursor-pointer font-semibold text-sm mb-2", children: "Component Stack Trace (Development Only)" }

                ), /*#__PURE__*/
                _jsx("pre", { className: "text-xs overflow-auto whitespace-pre-wrap", children:
                  this.state.errorInfo.componentStack }
                )] }
              ), /*#__PURE__*/


              _jsxs("div", { className: "flex gap-3 pt-4", children: [/*#__PURE__*/
                _jsxs(Button, { onClick: this.handleReset, className: "flex items-center gap-2", children: [/*#__PURE__*/
                  _jsx(RefreshCw, { className: "h-4 w-4" }), "Try Again"] }

                ), /*#__PURE__*/
                _jsxs(Button, { onClick: this.handleGoHome, variant: "outline", className: "flex items-center gap-2", children: [/*#__PURE__*/
                  _jsx(Home, { className: "h-4 w-4" }), "Go to Home"] }

                )] }
              ), /*#__PURE__*/

              _jsx("div", { className: "text-sm text-muted-foreground pt-4 border-t", children: /*#__PURE__*/
                _jsx("p", { children: "If this problem persists, please contact support with the error details above." }) }
              )] }
            )] }
          ) }
        ));

    }

    return this.props.children;
  }
}

export default ErrorBoundary;

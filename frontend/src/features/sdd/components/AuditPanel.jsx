import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { runAudit, getAuditFindings } from '@/services/audit.service';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import {
  AlertCircle,
  CheckCircle2,
  AlertTriangle,
  Info,
  Play,
  RefreshCw,
  Shield,
} from 'lucide-react';

/** Severity config for badges and icons */
const SEVERITY_CONFIG = {
  Critical: {
    color: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
    icon: AlertCircle,
    ring: 'ring-red-500',
  },
  Warning: {
    color: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300',
    icon: AlertTriangle,
    ring: 'ring-yellow-500',
  },
  Pass: {
    color: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
    icon: CheckCircle2,
    ring: 'ring-green-500',
  },
};

/** Score color for gauge */
function scoreColor(score) {
  if (score >= 80) return 'text-green-600';
  if (score >= 50) return 'text-yellow-600';
  return 'text-red-600';
}

function progressColor(score) {
  if (score >= 80) return 'bg-green-600';
  if (score >= 50) return 'bg-yellow-600';
  return 'bg-red-600';
}

const AuditPanel = ({ dossierId }) => {
  const queryClient = useQueryClient();
  const [showAll, setShowAll] = useState(false);

  // Fetch existing audit findings
  const {
    data: auditResult,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['audit-findings', dossierId],
    queryFn: () => getAuditFindings(dossierId),
    enabled: !!dossierId,
  });

  // Run audit mutation
  const auditMutation = useMutation({
    mutationFn: () => runAudit(dossierId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['audit-findings', dossierId] });
    },
  });

  const findings = auditResult?.findings || [];
  const score = auditResult?.score ?? null;

  // Group findings by category
  const grouped = findings.reduce((acc, f) => {
    const cat = f.category || 'Other';
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(f);
    return acc;
  }, {});

  // Summary counts
  const criticalCount = findings.filter((f) => f.severity === 'Critical').length;
  const warningCount = findings.filter((f) => f.severity === 'Warning').length;
  const passCount = findings.filter((f) => f.severity === 'Pass').length;

  const visibleFindings = showAll ? findings : findings.slice(0, 10);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-32" />
        <Skeleton className="h-48" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Run Audit Action */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Shield className="h-5 w-5 text-muted-foreground" />
          <span className="text-sm text-muted-foreground">
            {auditResult?.ran_at
              ? `Last run: ${new Date(auditResult.ran_at).toLocaleString()}`
              : 'No audit run yet'}
          </span>
        </div>
        <Button
          onClick={() => auditMutation.mutate()}
          disabled={auditMutation.isPending}
        >
          {auditMutation.isPending ? (
            <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
          ) : (
            <Play className="h-4 w-4 mr-2" />
          )}
          {auditMutation.isPending ? 'Running…' : 'Run Audit'}
        </Button>
      </div>

      {auditMutation.isError && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Audit failed: {auditMutation.error?.message}
          </AlertDescription>
        </Alert>
      )}

      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Failed to load findings: {error.message}
          </AlertDescription>
        </Alert>
      )}

      {/* Health Score Gauge */}
      {score !== null && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Health Score</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-4">
              <div className={`text-4xl font-bold ${scoreColor(score)}`}>
                {score}
              </div>
              <div className="flex-1">
                <Progress
                  value={score}
                  className="h-3"
                  style={{
                    '--progress-foreground': score >= 80 ? '#16a34a' : score >= 50 ? '#ca8a04' : '#dc2626',
                  }}
                />
              </div>
              <span className="text-sm text-muted-foreground">/100</span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Summary Cards */}
      <div className="grid grid-cols-3 gap-3">
        <Card className="border-red-200 dark:border-red-800">
          <CardContent className="pt-4 pb-4 flex items-center gap-2">
            <AlertCircle className="h-4 w-4 text-red-600" />
            <div>
              <div className="text-xl font-bold text-red-600">{criticalCount}</div>
              <p className="text-xs text-muted-foreground">Critical</p>
            </div>
          </CardContent>
        </Card>
        <Card className="border-yellow-200 dark:border-yellow-800">
          <CardContent className="pt-4 pb-4 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-yellow-600" />
            <div>
              <div className="text-xl font-bold text-yellow-600">{warningCount}</div>
              <p className="text-xs text-muted-foreground">Warnings</p>
            </div>
          </CardContent>
        </Card>
        <Card className="border-green-200 dark:border-green-800">
          <CardContent className="pt-4 pb-4 flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-green-600" />
            <div>
              <div className="text-xl font-bold text-green-600">{passCount}</div>
              <p className="text-xs text-muted-foreground">Passed</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Findings by Category */}
      {Object.entries(grouped).map(([category, items]) => (
        <Card key={category}>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">{category}</CardTitle>
            <CardDescription>{items.length} finding(s)</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {items.map((finding) => {
              const config = SEVERITY_CONFIG[finding.severity] || SEVERITY_CONFIG.Pass;
              const Icon = config.icon;
              return (
                <div
                  key={finding.id}
                  className="flex items-start gap-3 p-2 rounded-md hover:bg-muted/50"
                >
                  <Icon className="h-4 w-4 mt-0.5 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm">{finding.message}</p>
                    {finding.element_id && (
                      <p className="text-xs text-muted-foreground mt-0.5">
                        Element: {finding.element_id}
                      </p>
                    )}
                  </div>
                  <Badge className={config.color}>{finding.severity}</Badge>
                </div>
              );
            })}
          </CardContent>
        </Card>
      ))}

      {findings.length === 0 && !isLoading && !error && (
        <div className="text-center py-8 text-muted-foreground">
          <Info className="h-8 w-8 mx-auto mb-2 opacity-50" />
          <p className="text-sm">No audit findings yet. Run an audit to check compliance.</p>
        </div>
      )}

      {findings.length > 10 && (
        <Button
          variant="outline"
          className="w-full"
          onClick={() => setShowAll((v) => !v)}
        >
          {showAll ? 'Show Less' : `Show All ${findings.length} Findings`}
        </Button>
      )}
    </div>
  );
};

export default AuditPanel;

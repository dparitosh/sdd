import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { submitApproval, getApprovalHistory } from '@/services/approval.service';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { Separator } from '@/components/ui/separator';
import {
  AlertCircle,
  CheckCircle2,
  XCircle,
  MessageSquare,
  User,
  Clock,
  Send,
} from 'lucide-react';

const DECISION_CONFIG = {
  approved: {
    color: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
    icon: CheckCircle2,
    label: 'Approved',
  },
  rejected: {
    color: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
    icon: XCircle,
    label: 'Rejected',
  },
};

const ReviewPanel = ({ dossierId, currentUser = 'Current User' }) => {
  const queryClient = useQueryClient();
  const [comment, setComment] = useState('');

  // Fetch approval history
  const {
    data: historyData,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['approval-history', dossierId],
    queryFn: () => getApprovalHistory(dossierId),
    enabled: !!dossierId,
  });

  // Submit approval/rejection
  const approvalMutation = useMutation({
    mutationFn: (decision) =>
      submitApproval(dossierId, {
        decision,
        approver: currentUser,
        rationale: comment,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['approval-history', dossierId] });
      queryClient.invalidateQueries({ queryKey: ['simulation-dossier', dossierId] });
      setComment('');
    },
  });

  const history = Array.isArray(historyData) ? historyData : historyData?.records || [];

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
      {/* Submit Review Form */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Submit Review Decision</CardTitle>
          <CardDescription>
            Approve or reject this dossier with a rationale comment
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div>
            <label className="text-sm font-medium text-muted-foreground mb-1 block">
              Rationale / Comment
            </label>
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="Enter your review rationale…"
              rows={3}
              className="flex min-h-20 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            />
          </div>

          <div className="flex gap-2">
            <Button
              onClick={() => approvalMutation.mutate('approved')}
              disabled={approvalMutation.isPending || !comment.trim()}
              className="bg-green-600 hover:bg-green-700 text-white"
            >
              <CheckCircle2 className="h-4 w-4 mr-2" />
              Approve
            </Button>
            <Button
              variant="destructive"
              onClick={() => approvalMutation.mutate('rejected')}
              disabled={approvalMutation.isPending || !comment.trim()}
            >
              <XCircle className="h-4 w-4 mr-2" />
              Reject
            </Button>
          </div>

          {approvalMutation.isError && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                {approvalMutation.error?.message || 'Failed to submit review'}
              </AlertDescription>
            </Alert>
          )}

          {approvalMutation.isSuccess && (
            <Alert>
              <CheckCircle2 className="h-4 w-4" />
              <AlertDescription>Review submitted successfully</AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* Decision History Timeline */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Decision History</CardTitle>
          <CardDescription>{history.length} decision(s) recorded</CardDescription>
        </CardHeader>
        <CardContent>
          {error && (
            <Alert variant="destructive" className="mb-4">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                Failed to load history: {error.message}
              </AlertDescription>
            </Alert>
          )}

          {history.length === 0 ? (
            <div className="text-center py-6 text-muted-foreground">
              <MessageSquare className="h-8 w-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">No review decisions yet</p>
            </div>
          ) : (
            <div className="relative">
              {/* Timeline line */}
              <div className="absolute left-4 top-0 bottom-0 w-px bg-border" />

              <div className="space-y-4">
                {history.map((record, idx) => {
                  const config =
                    DECISION_CONFIG[record.decision] || DECISION_CONFIG.approved;
                  const Icon = config.icon;
                  return (
                    <div key={record.id || idx} className="relative pl-10">
                      {/* Timeline dot */}
                      <div className="absolute left-2.5 top-1 h-3 w-3 rounded-full bg-background border-2 border-muted-foreground" />

                      <div className="rounded-md border p-3 space-y-2">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <Icon className="h-4 w-4" />
                            <Badge className={config.color}>
                              {config.label}
                            </Badge>
                          </div>
                          <div className="flex items-center gap-1 text-xs text-muted-foreground">
                            <Clock className="h-3 w-3" />
                            {record.decided_at
                              ? new Date(record.decided_at).toLocaleString()
                              : 'Unknown'}
                          </div>
                        </div>

                        <div className="flex items-center gap-1 text-sm">
                          <User className="h-3 w-3 text-muted-foreground" />
                          <span className="font-medium">{record.approver}</span>
                        </div>

                        {record.rationale && (
                          <>
                            <Separator />
                            <p className="text-sm text-muted-foreground">
                              {record.rationale}
                            </p>
                          </>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default ReviewPanel;

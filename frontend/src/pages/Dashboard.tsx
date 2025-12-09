import { useQuery } from '@tanstack/react-query';
import { apiService } from '@/services/api';
import { Card, CardContent, CardHeader, CardTitle } from '@ui/card';
import { Skeleton } from '@ui/skeleton';
import { Alert, AlertDescription } from '@ui/alert';
import { Database, GitBranch, Package, Activity } from 'lucide-react';

interface Statistics {
  node_types: Record<string, number>;
  relationship_types: Record<string, number>;
  total_nodes: number;
  total_relationships: number;
}

export default function Dashboard() {
  const { data: stats, isLoading, error } = useQuery<Statistics>({
    queryKey: ['statistics'],
    queryFn: apiService.getStatistics,
    retry: 1,
    staleTime: 30000,
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Card key={i}>
              <CardHeader className="pb-2">
                <Skeleton className="h-4 w-24" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-8 w-16" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <Alert variant="destructive">
          <AlertDescription>
            Failed to load statistics. Please check your connection and try again.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  const statCards = [
    {
      title: 'Total Nodes',
      value: stats?.total_nodes || 0,
      icon: Database,
      gradient: 'from-blue-500 to-cyan-500',
    },
    {
      title: 'Total Relationships',
      value: stats?.total_relationships || 0,
      icon: GitBranch,
      gradient: 'from-purple-500 to-pink-500',
    },
    {
      title: 'Node Types',
      value: Object.keys(stats?.node_types || {}).length,
      icon: Package,
      gradient: 'from-green-500 to-emerald-500',
    },
    {
      title: 'Relationship Types',
      value: Object.keys(stats?.relationship_types || {}).length,
      icon: Activity,
      gradient: 'from-orange-500 to-red-500',
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Overview of your MBSE Knowledge Graph
        </p>
      </div>

      {/* Stat Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {statCards.map((card) => (
          <Card key={card.title} className="overflow-hidden">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {card.title}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <div className="text-3xl font-bold">{card.value.toLocaleString()}</div>
                <div className={`rounded-full bg-gradient-to-br ${card.gradient} p-3`}>
                  <card.icon className="h-6 w-6 text-white" />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Node Types */}
      <Card>
        <CardHeader>
          <CardTitle>Node Types</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {Object.entries(stats?.node_types || {})
              .sort(([, a], [, b]) => (b as number) - (a as number))
              .slice(0, 10)
              .map(([type, count]) => (
                <div key={type} className="flex items-center justify-between">
                  <span className="text-sm font-medium">{type}</span>
                  <div className="flex items-center gap-2">
                    <div className="h-2 w-32 rounded-full bg-secondary">
                      <div
                        className="h-2 rounded-full bg-primary"
                        style={{
                          width: `${((count as number) / (stats?.total_nodes || 1)) * 100}%`,
                        }}
                      />
                    </div>
                    <span className="text-sm text-muted-foreground w-16 text-right">
                      {(count as number).toLocaleString()}
                    </span>
                  </div>
                </div>
              ))}
          </div>
        </CardContent>
      </Card>

      {/* Relationship Types */}
      <Card>
        <CardHeader>
          <CardTitle>Relationship Types</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {Object.entries(stats?.relationship_types || {})
              .sort(([, a], [, b]) => (b as number) - (a as number))
              .slice(0, 10)
              .map(([type, count]) => (
                <div key={type} className="flex items-center justify-between">
                  <span className="text-sm font-medium">{type}</span>
                  <div className="flex items-center gap-2">
                    <div className="h-2 w-32 rounded-full bg-secondary">
                      <div
                        className="h-2 rounded-full bg-purple-500"
                        style={{
                          width: `${((count as number) / (stats?.total_relationships || 1)) * 100}%`,
                        }}
                      />
                    </div>
                    <span className="text-sm text-muted-foreground w-16 text-right">
                      {(count as number).toLocaleString()}
                    </span>
                  </div>
                </div>
              ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

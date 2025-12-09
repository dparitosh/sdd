import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiService } from '@/services/api';
import { Card, CardContent, CardHeader, CardTitle } from '@ui/card';
import { Input } from '@ui/input';
import { Button } from '@ui/button';
import { Label } from '@ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@ui/select';
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@ui/tabs';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@ui/table';
import { Badge } from '@ui/badge';
import { Skeleton } from '@ui/skeleton';
import { Search, ExternalLink, List, Network } from 'lucide-react';

interface SearchResult {
  id: string;
  name: string;
  type: string;
  qualified_name?: string;
  comment?: string;
  [key: string]: any;
}

const ARTIFACT_TYPES = [
  'All',
  'Class',
  'Package',
  'Property',
  'Association',
  'Requirement',
  'Constraint',
  'Enumeration',
];

export default function AdvancedSearch() {
  const [searchParams, setSearchParams] = useState({
    type: 'All',
    name: '',
    comment: '',
  });
  const [viewMode, setViewMode] = useState<'table' | 'graph'>('table');

  const { data: results, isLoading, refetch } = useQuery<SearchResult[]>({
    queryKey: ['artifacts', searchParams],
    queryFn: () =>
      apiService.searchArtifacts({
        type: searchParams.type !== 'All' ? searchParams.type : undefined,
        name: searchParams.name || undefined,
        comment: searchParams.comment || undefined,
        limit: 100,
      }),
    enabled: false, // Only search when user clicks button
  });

  const handleSearch = () => {
    refetch();
  };

  const handleReset = () => {
    setSearchParams({ type: 'All', name: '', comment: '' });
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Advanced Search</h1>
        <p className="text-muted-foreground">
          Search for SysML/UML artifacts in the knowledge graph
        </p>
      </div>

      {/* Search Form */}
      <Card>
        <CardHeader>
          <CardTitle>Search Filters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            <div className="space-y-2">
              <Label htmlFor="type">Artifact Type</Label>
              <Select
                value={searchParams.type}
                onValueChange={(value) =>
                  setSearchParams({ ...searchParams, type: value })
                }
              >
                <SelectTrigger id="type">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {ARTIFACT_TYPES.map((type) => (
                    <SelectItem key={type} value={type}>
                      {type}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                placeholder="Enter artifact name..."
                value={searchParams.name}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                  setSearchParams({ ...searchParams, name: e.target.value })
                }
                onKeyDown={(e: React.KeyboardEvent) => e.key === 'Enter' && handleSearch()}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="comment">Comment</Label>
              <Input
                id="comment"
                placeholder="Search in comments..."
                value={searchParams.comment}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                  setSearchParams({ ...searchParams, comment: e.target.value })
                }
                onKeyDown={(e: React.KeyboardEvent) => e.key === 'Enter' && handleSearch()}
              />
            </div>
          </div>

          <div className="mt-4 flex gap-2">
            <Button onClick={handleSearch} className="flex gap-2">
              <Search className="h-4 w-4" />
              Search
            </Button>
            <Button variant="outline" onClick={handleReset}>
              Reset
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Results with Table/Graph View */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>
              Search Results
              {results && (
                <span className="ml-2 text-sm font-normal text-muted-foreground">
                  ({results.length} found)
                </span>
              )}
            </CardTitle>
            <Tabs value={viewMode} onValueChange={(v) => setViewMode(v as 'table' | 'graph')}>
              <TabsList>
                <TabsTrigger value="table" className="flex items-center gap-1">
                  <List className="h-4 w-4" />
                  Table
                </TabsTrigger>
                <TabsTrigger value="graph" className="flex items-center gap-1">
                  <Network className="h-4 w-4" />
                  Graph
                </TabsTrigger>
              </TabsList>
            </Tabs>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-2">
              {[...Array(5)].map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : results && results.length > 0 ? (
            <Tabs value={viewMode}>
              <TabsContent value="table" className="mt-0">
                <div className="rounded-md border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Type</TableHead>
                        <TableHead>Name</TableHead>
                        <TableHead>UID</TableHead>
                        <TableHead>Comment</TableHead>
                        <TableHead className="w-[100px]">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {results.map((artifact: SearchResult, index: number) => (
                        <TableRow key={artifact.uid || index}>
                          <TableCell>
                            <Badge variant="outline">{artifact.type}</Badge>
                          </TableCell>
                          <TableCell className="font-medium">
                            {artifact.name || '(unnamed)'}
                          </TableCell>
                          <TableCell>
                            <code className="text-xs">{artifact.uid}</code>
                          </TableCell>
                          <TableCell className="max-w-md truncate">
                            {artifact.comment || '-'}
                          </TableCell>
                          <TableCell>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() =>
                                window.open(
                                  `/api/${artifact.type.toLowerCase()}/${encodeURIComponent(
                                    artifact.uid
                                  )}`,
                                  '_blank'
                                )
                              }
                            >
                              <ExternalLink className="h-4 w-4" />
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </TabsContent>
              <TabsContent value="graph" className="mt-0">
                <div className="border rounded-lg p-8 bg-muted/20 min-h-[400px]">
                  <div className="flex flex-col items-center justify-center h-full text-center">
                    <Network className="h-16 w-16 text-muted-foreground mb-4" />
                    <h3 className="text-lg font-semibold mb-2">Graph Visualization</h3>
                    <p className="text-sm text-muted-foreground max-w-md">
                      Interactive graph view showing relationships between nodes. 
                      {results.length} nodes ready to visualize.
                    </p>
                    <div className="mt-6 grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                      {results.slice(0, 12).map((artifact: SearchResult, index: number) => (
                        <Card key={index} className="card-corporate">
                          <CardContent className="p-4 text-center">
                            <Badge variant="outline" className="mb-2">{artifact.type}</Badge>
                            <div className="text-sm font-medium truncate">{artifact.name || '(unnamed)'}</div>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                    <p className="text-xs text-muted-foreground mt-4">
                      Full graph visualization with D3.js coming soon
                    </p>
                  </div>
                </div>
              </TabsContent>
            </Tabs>
          ) : (
            <div className="flex h-32 items-center justify-center text-muted-foreground">
              {results ? 'No results found' : 'Enter search criteria and click Search'}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

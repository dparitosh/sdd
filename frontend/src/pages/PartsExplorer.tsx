import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useDebounce } from 'use-debounce';
import { apiService } from '@/services/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle, Box, Boxes, Layers, Loader2, Package, Search, Wrench } from 'lucide-react';
import { AP242Part, Material, BOMData, Assembly, AP242Statistics } from '@/types/api';
import ExportButton from '@/components/ExportButton';
import ExportButton from '@/components/ExportButton';

const PartsExplorer: React.FC = () => {
  const [selectedPart, setSelectedPart] = useState<AP242Part | null>(null);
  const [bomData, setBomData] = useState<BOMData | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [materialTypeFilter, setMaterialTypeFilter] = useState<string>('all');
  
  // Debounce search query to prevent excessive API calls
  const [debouncedSearchQuery] = useDebounce(searchQuery, 300);

  // Fetch parts using React Query
  const { data: partsData, isLoading: loadingParts, error: partsError, refetch: refetchParts } = useQuery({
    queryKey: ['ap242-parts', statusFilter, debouncedSearchQuery],
    queryFn: () => {
      const params: any = {};
      if (statusFilter !== 'all') params.status = statusFilter;
      if (debouncedSearchQuery) params.search = debouncedSearchQuery;
      return apiService.ap242.getParts(params);
    },
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  // Fetch materials
  const { data: materialsData, isLoading: loadingMaterials } = useQuery({
    queryKey: ['ap242-materials', materialTypeFilter],
    queryFn: () => {
      const params: any = {};
      if (materialTypeFilter !== 'all') params.type = materialTypeFilter;
      return apiService.ap242.getMaterials(params);
    },
    refetchInterval: 30000,
  });

  // Fetch assemblies
  const { data: assembliesData, isLoading: loadingAssemblies } = useQuery({
    queryKey: ['ap242-assemblies'],
    queryFn: () => apiService.ap242.getAssemblies(),
    refetchInterval: 60000,
  });

  // Fetch statistics
  const { data: statisticsData, isLoading: loadingStatistics } = useQuery({
    queryKey: ['ap242-statistics'],
    queryFn: () => apiService.ap242.getStatistics(),
    refetchInterval: 60000,
  });

  const parts = partsData?.parts || [];
  const materials = materialsData?.materials || [];
  const assemblies = assembliesData?.assemblies || [];
  const statistics = statisticsData?.statistics || null;

  const fetchPartDetail = async (partId: string) => {
    try {
      const partResponse = await apiService.ap242.getPart(partId);
      setSelectedPart(partResponse.part);

      // Fetch BOM for this part
      const bomResponse = await apiService.ap242.getPartBOM(partId);
      setBomData(bomResponse);
    } catch (error) {
      console.error('Error fetching part detail:', error);
    }
  };

  const getStatusColor = (status?: string) => {
    switch (status?.toLowerCase()) {
      case 'released':
        return 'default';
      case 'development':
        return 'secondary';
      case 'obsolete':
        return 'destructive';
      default:
        return 'outline';
    }
  };

  const getMaterialIcon = (type?: string) => {
    switch (type?.toLowerCase()) {
      case 'metal':
        return <Wrench className="h-4 w-4" />;
      case 'polymer':
        return <Box className="h-4 w-4" />;
      case 'composite':
        return <Layers className="h-4 w-4" />;
      default:
        return <Package className="h-4 w-4" />;
    }
  };

  const isLoading = loadingParts || loadingMaterials || loadingAssemblies || loadingStatistics;

  if (isLoading && !partsData) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Parts Explorer</h1>
          <p className="text-muted-foreground">AP242 3D Engineering - Parts, Materials, and CAD Geometry</p>
        </div>
        <Button variant="outline" onClick={() => refetchParts()} disabled={isLoading}>
          {isLoading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
          Refresh
        </Button>
      </div>

      {/* Error Alert */}
      {partsError && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Failed to load parts: {partsError instanceof Error ? partsError.message : 'Unknown error'}
          </AlertDescription>
        </Alert>
      )}

      {/* Statistics Cards */}
      {loadingStatistics ? (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i}>
              <CardHeader className="pb-2">
                <Skeleton className="h-4 w-32" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-8 w-16" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : statistics ? (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Parts</CardTitle>
              <Package className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {statistics.Part?.total || 0}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Materials</CardTitle>
              <Box className="h-4 w-4 text-blue-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {statistics.Material?.total || 0}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Assemblies</CardTitle>
              <Boxes className="h-4 w-4 text-green-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {statistics.Assembly?.total || 0}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">CAD Models</CardTitle>
              <Layers className="h-4 w-4 text-purple-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {statistics.GeometricModel?.total || 0}
              </div>
            </CardContent>
          </Card>
        </div>
      ) : null}

      {/* Main Content Tabs */}
      <Tabs defaultValue="parts" className="w-full">
        <TabsList>
          <TabsTrigger value="parts">Parts</TabsTrigger>
          <TabsTrigger value="materials">Materials</TabsTrigger>
          <TabsTrigger value="assemblies">Assemblies</TabsTrigger>
        </TabsList>

        {/* Parts Tab */}
        <TabsContent value="parts">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Parts Catalog</CardTitle>
                <ExportButton 
                  entityType="parts"
                  filters={{
                    status: statusFilter,
                    search: debouncedSearchQuery
                  }}
                />
              </div>
              <div className="flex gap-4 mt-4">
                <div className="relative flex-1">
                  <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Search parts..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-8"
                  />
                </div>
                <Select value={statusFilter} onValueChange={setStatusFilter}>
                  <SelectTrigger className="w-48">
                    <SelectValue placeholder="Status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Statuses</SelectItem>
                    <SelectItem value="Released">Released</SelectItem>
                    <SelectItem value="Development">Development</SelectItem>
                    <SelectItem value="Obsolete">Obsolete</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardHeader>
            <CardContent>
              {loadingParts ? (
                <div className="space-y-2">
                  {[1, 2, 3, 4, 5].map((i) => (
                    <Skeleton key={i} className="h-12 w-full" />
                  ))}
                </div>
              ) : parts.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  No parts found. Try adjusting your filters.
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Part Number</TableHead>
                      <TableHead>Name</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Materials</TableHead>
                      <TableHead>Requirements</TableHead>
                      <TableHead>Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {parts.map((part) => (
                      <TableRow key={part.id}>
                        <TableCell className="font-mono text-sm">{part.part_number}</TableCell>
                        <TableCell className="font-medium">{part.name}</TableCell>
                        <TableCell>
                          <Badge variant={getStatusColor(part.status)}>
                            {part.status || 'N/A'}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          {part.materials && part.materials.length > 0 ? (
                            <div className="flex flex-wrap gap-1">
                              {part.materials.slice(0, 2).map((mat, idx) => (
                                <Badge key={idx} variant="outline" className="text-xs">
                                  {mat.name}
                                </Badge>
                              ))}
                              {part.materials.length > 2 && (
                                <Badge variant="outline" className="text-xs">
                                  +{part.materials.length - 2}
                                </Badge>
                              )}
                            </div>
                          ) : (
                            <span className="text-muted-foreground text-sm">None</span>
                          )}
                        </TableCell>
                        <TableCell>
                          <Badge variant="secondary">
                            {part.satisfies_requirements?.length || 0} reqs
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => fetchPartDetail(part.id)}
                          >
                            View Details
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Materials Tab */}
        <TabsContent value="materials">
          <Card>
            <CardHeader>
              <CardTitle>Materials Library</CardTitle>
              <div className="flex gap-4 mt-4">
                <Select value={materialTypeFilter} onValueChange={setMaterialTypeFilter}>
                  <SelectTrigger className="w-48">
                    <SelectValue placeholder="Material Type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Types</SelectItem>
                    <SelectItem value="Metal">Metal</SelectItem>
                    <SelectItem value="Polymer">Polymer</SelectItem>
                    <SelectItem value="Composite">Composite</SelectItem>
                    <SelectItem value="Ceramic">Ceramic</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardHeader>
            <CardContent>
              {loadingMaterials ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {[1, 2, 3].map((i) => (
                    <Card key={i}>
                      <CardHeader>
                        <Skeleton className="h-6 w-48" />
                      </CardHeader>
                      <CardContent>
                        <Skeleton className="h-20 w-full" />
                      </CardContent>
                    </Card>
                  ))}
                </div>
              ) : materials.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  No materials found. Try adjusting your filters.
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {materials.map((material, idx) => (
                    <Card key={idx}>
                      <CardHeader>
                        <div className="flex items-start justify-between">
                          <div className="flex items-center gap-2">
                            {getMaterialIcon(material.material_type)}
                            <CardTitle className="text-base">{material.name}</CardTitle>
                          </div>
                          <Badge variant="outline">{material.material_type}</Badge>
                        </div>
                      </CardHeader>
                      <CardContent className="space-y-3">
                        {material.specification && (
                          <div>
                            <p className="text-sm font-medium">Specification</p>
                            <p className="text-sm text-muted-foreground">{material.specification}</p>
                          </div>
                        )}

                        {material.properties && material.properties.length > 0 && (
                          <div>
                            <p className="text-sm font-medium mb-2">Properties</p>
                            <div className="space-y-1">
                              {material.properties.map((prop, propIdx) => (
                                <div key={propIdx} className="text-xs flex justify-between">
                                  <span className="text-muted-foreground">{prop.name}:</span>
                                  <span className="font-mono">
                                    {prop.value} {prop.unit}
                                  </span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {material.used_in_parts && material.used_in_parts.length > 0 && (
                          <div>
                            <p className="text-sm font-medium">Used In</p>
                            <Badge variant="secondary" className="mt-1">
                              {material.used_in_parts.length} parts
                            </Badge>
                          </div>
                        )}

                        {material.ontology_classes && material.ontology_classes.length > 0 && (
                          <div>
                            <p className="text-sm font-medium">Ontology Classification</p>
                            <div className="flex flex-wrap gap-1 mt-1">
                              {material.ontology_classes.map((ont, ontIdx) => (
                                <Badge key={ontIdx} variant="outline" className="text-xs">
                                  {ont}
                                </Badge>
                              ))}
                            </div>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Assemblies Tab */}
        <TabsContent value="assemblies">
          <Card>
            <CardHeader>
              <CardTitle>Assembly Structures</CardTitle>
            </CardHeader>
            <CardContent>
              {loadingAssemblies ? (
                <div className="space-y-4">
                  {[1, 2, 3].map((i) => (
                    <Card key={i}>
                      <CardHeader>
                        <Skeleton className="h-6 w-48" />
                        <Skeleton className="h-4 w-32" />
                      </CardHeader>
                      <CardContent>
                        <Skeleton className="h-12 w-full" />
                      </CardContent>
                    </Card>
                  ))}
                </div>
              ) : assemblies.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  No assemblies found in the database.
                </div>
              ) : (
                <div className="space-y-4">
                  {assemblies.map((assembly, idx) => (
                    <Card key={idx}>
                      <CardHeader>
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <Boxes className="h-5 w-5 text-muted-foreground" />
                            <div>
                              <CardTitle className="text-base">{assembly.name}</CardTitle>
                              <p className="text-sm text-muted-foreground">
                                {assembly.component_count || 0} components
                              </p>
                            </div>
                          </div>
                          <Badge>{assembly.type}</Badge>
                        </div>
                      </CardHeader>
                      <CardContent>
                        {assembly.parts && assembly.parts.length > 0 && (
                          <div className="flex flex-wrap gap-2">
                            {assembly.parts.map((partName, partIdx) => (
                              <Badge key={partIdx} variant="outline">
                                {partName}
                              </Badge>
                            ))}
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Part Detail Panel */}
      {selectedPart && (
        <Card className="fixed right-4 top-20 w-96 max-h-[80vh] overflow-y-auto shadow-lg z-50">
          <CardHeader>
            <div className="flex justify-between items-start">
              <div>
                <CardTitle>{selectedPart.name}</CardTitle>
                <p className="text-sm text-muted-foreground">{selectedPart.part_number}</p>
              </div>
              <Button variant="ghost" size="sm" onClick={() => setSelectedPart(null)}>
                ✕
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <h4 className="font-semibold mb-2">Description</h4>
              <p className="text-sm text-muted-foreground">
                {selectedPart.description || 'No description available'}
              </p>
            </div>

            {selectedPart.versions && selectedPart.versions.length > 0 && (
              <div>
                <h4 className="font-semibold mb-2">Versions</h4>
                <div className="space-y-1">
                  {selectedPart.versions.map((v, idx) => (
                    <Badge key={idx} variant="outline" className="mr-1">
                      {v.version} ({v.status})
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {selectedPart.materials && selectedPart.materials.length > 0 && (
              <div>
                <h4 className="font-semibold mb-2">Materials</h4>
                <div className="space-y-2">
                  {selectedPart.materials.map((mat, idx) => (
                    <div key={idx} className="p-2 bg-muted rounded">
                      <div className="font-medium text-sm">{mat.name}</div>
                      <div className="text-xs text-muted-foreground">{mat.specification}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {bomData && bomData.components.length > 0 && (
              <div>
                <h4 className="font-semibold mb-2">Bill of Materials</h4>
                <div className="space-y-1">
                  {bomData.components.map((comp, idx) => (
                    <div key={idx} className="text-sm p-2 bg-muted rounded">
                      <div className="font-medium">{comp.name}</div>
                      <div className="text-xs text-muted-foreground">{comp.part_number}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {selectedPart.geometry && selectedPart.geometry.length > 0 && (
              <div>
                <h4 className="font-semibold mb-2">CAD Geometry</h4>
                <div className="space-y-1">
                  {selectedPart.geometry.map((geo, idx) => (
                    <div key={idx} className="text-sm">
                      <Badge variant="outline">{geo.type}</Badge> {geo.name}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default PartsExplorer;

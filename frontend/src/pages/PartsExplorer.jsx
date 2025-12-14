import logger from '@/utils/logger';
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

import ExportButton from '@/components/ExportButton';import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";

const PartsExplorer = () => {
  const [selectedPart, setSelectedPart] = useState(null);
  const [bomData, setBomData] = useState(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [materialTypeFilter, setMaterialTypeFilter] = useState('all');

  // Debounce search query to prevent excessive API calls
  const [debouncedSearchQuery] = useDebounce(searchQuery, 300);

  // Fetch parts using React Query
  const { data: partsData, isLoading: loadingParts, error: partsError, refetch: refetchParts } = useQuery({
    queryKey: ['ap242-parts', statusFilter, debouncedSearchQuery],
    queryFn: () => {
      const params = {};
      if (statusFilter !== 'all') params.status = statusFilter;
      if (debouncedSearchQuery) params.search = debouncedSearchQuery;
      return apiService.ap242.getParts(params);
    },
    refetchInterval: 30000 // Refresh every 30 seconds
  });

  // Fetch materials
  const { data: materialsData, isLoading: loadingMaterials } = useQuery({
    queryKey: ['ap242-materials', materialTypeFilter],
    queryFn: () => {
      const params = {};
      if (materialTypeFilter !== 'all') params.type = materialTypeFilter;
      return apiService.ap242.getMaterials(params);
    },
    refetchInterval: 30000
  });

  // Fetch assemblies
  const { data: assembliesData, isLoading: loadingAssemblies } = useQuery({
    queryKey: ['ap242-assemblies'],
    queryFn: () => apiService.ap242.getAssemblies(),
    refetchInterval: 60000
  });

  // Fetch statistics
  const { data: statisticsData, isLoading: loadingStatistics } = useQuery({
    queryKey: ['ap242-statistics'],
    queryFn: () => apiService.ap242.getStatistics(),
    refetchInterval: 60000
  });

  const parts = partsData?.parts || [];
  const materials = materialsData?.materials || [];
  const assemblies = assembliesData?.assemblies || [];
  const statistics = statisticsData?.statistics || null;

  const fetchPartDetail = async (partId) => {
    try {
      const partResponse = await apiService.ap242.getPart(partId);
      setSelectedPart(partResponse.part);

      // Fetch BOM for this part
      const bomResponse = await apiService.ap242.getPartBOM(partId);
      setBomData(bomResponse);
    } catch (error) {
      logger.error('Error fetching part detail:', error);
    }
  };

  const getStatusColor = (status) => {
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

  const getMaterialIcon = (type) => {
    switch (type?.toLowerCase()) {
      case 'metal':
        return /*#__PURE__*/_jsx(Wrench, { className: "h-4 w-4" });
      case 'polymer':
        return /*#__PURE__*/_jsx(Box, { className: "h-4 w-4" });
      case 'composite':
        return /*#__PURE__*/_jsx(Layers, { className: "h-4 w-4" });
      default:
        return /*#__PURE__*/_jsx(Package, { className: "h-4 w-4" });
    }
  };

  const isLoading = loadingParts || loadingMaterials || loadingAssemblies || loadingStatistics;

  if (isLoading && !partsData) {
    return (/*#__PURE__*/
      _jsx("div", { className: "flex items-center justify-center h-screen", children: /*#__PURE__*/
        _jsx(Loader2, { className: "h-8 w-8 animate-spin" }) }
      ));

  }

  return (/*#__PURE__*/
    _jsxs("div", { className: "container mx-auto p-6 space-y-6", children: [/*#__PURE__*/

      _jsxs("div", { className: "flex justify-between items-center", children: [/*#__PURE__*/
        _jsxs("div", { children: [/*#__PURE__*/
          _jsx("h1", { className: "text-3xl font-bold", children: "Parts Explorer" }), /*#__PURE__*/
          _jsx("p", { className: "text-muted-foreground", children: "AP242 3D Engineering - Parts, Materials, and CAD Geometry" })] }
        ), /*#__PURE__*/
        _jsxs(Button, { variant: "outline", onClick: () => refetchParts(), disabled: isLoading, children: [
          isLoading ? /*#__PURE__*/_jsx(Loader2, { className: "h-4 w-4 animate-spin mr-2" }) : null, "Refresh"] }

        )] }
      ),


      partsError && /*#__PURE__*/
      _jsxs(Alert, { variant: "destructive", children: [/*#__PURE__*/
        _jsx(AlertCircle, { className: "h-4 w-4" }), /*#__PURE__*/
        _jsxs(AlertDescription, { children: ["Failed to load parts: ",
          partsError instanceof Error ? partsError.message : 'Unknown error'] }
        )] }
      ),



      loadingStatistics ? /*#__PURE__*/
      _jsx("div", { className: "grid grid-cols-1 md:grid-cols-4 gap-4", children:
        [1, 2, 3, 4].map((i) => /*#__PURE__*/
        _jsxs(Card, { children: [/*#__PURE__*/
          _jsx(CardHeader, { className: "pb-2", children: /*#__PURE__*/
            _jsx(Skeleton, { className: "h-4 w-32" }) }
          ), /*#__PURE__*/
          _jsx(CardContent, { children: /*#__PURE__*/
            _jsx(Skeleton, { className: "h-8 w-16" }) }
          )] }, i
        )
        ) }
      ) :
      statistics ? /*#__PURE__*/
      _jsxs("div", { className: "grid grid-cols-1 md:grid-cols-4 gap-4", children: [/*#__PURE__*/
        _jsxs(Card, { children: [/*#__PURE__*/
          _jsxs(CardHeader, { className: "flex flex-row items-center justify-between space-y-0 pb-2", children: [/*#__PURE__*/
            _jsx(CardTitle, { className: "text-sm font-medium", children: "Total Parts" }), /*#__PURE__*/
            _jsx(Package, { className: "h-4 w-4 text-muted-foreground" })] }
          ), /*#__PURE__*/
          _jsx(CardContent, { children: /*#__PURE__*/
            _jsx("div", { className: "text-2xl font-bold", children:
              statistics.Part?.total || 0 }
            ) }
          )] }
        ), /*#__PURE__*/

        _jsxs(Card, { children: [/*#__PURE__*/
          _jsxs(CardHeader, { className: "flex flex-row items-center justify-between space-y-0 pb-2", children: [/*#__PURE__*/
            _jsx(CardTitle, { className: "text-sm font-medium", children: "Materials" }), /*#__PURE__*/
            _jsx(Box, { className: "h-4 w-4 text-blue-500" })] }
          ), /*#__PURE__*/
          _jsx(CardContent, { children: /*#__PURE__*/
            _jsx("div", { className: "text-2xl font-bold", children:
              statistics.Material?.total || 0 }
            ) }
          )] }
        ), /*#__PURE__*/

        _jsxs(Card, { children: [/*#__PURE__*/
          _jsxs(CardHeader, { className: "flex flex-row items-center justify-between space-y-0 pb-2", children: [/*#__PURE__*/
            _jsx(CardTitle, { className: "text-sm font-medium", children: "Assemblies" }), /*#__PURE__*/
            _jsx(Boxes, { className: "h-4 w-4 text-green-500" })] }
          ), /*#__PURE__*/
          _jsx(CardContent, { children: /*#__PURE__*/
            _jsx("div", { className: "text-2xl font-bold", children:
              statistics.Assembly?.total || 0 }
            ) }
          )] }
        ), /*#__PURE__*/

        _jsxs(Card, { children: [/*#__PURE__*/
          _jsxs(CardHeader, { className: "flex flex-row items-center justify-between space-y-0 pb-2", children: [/*#__PURE__*/
            _jsx(CardTitle, { className: "text-sm font-medium", children: "CAD Models" }), /*#__PURE__*/
            _jsx(Layers, { className: "h-4 w-4 text-purple-500" })] }
          ), /*#__PURE__*/
          _jsx(CardContent, { children: /*#__PURE__*/
            _jsx("div", { className: "text-2xl font-bold", children:
              statistics.GeometricModel?.total || 0 }
            ) }
          )] }
        )] }
      ) :
      null, /*#__PURE__*/


      _jsxs(Tabs, { defaultValue: "parts", className: "w-full", children: [/*#__PURE__*/
        _jsxs(TabsList, { children: [/*#__PURE__*/
          _jsx(TabsTrigger, { value: "parts", children: "Parts" }), /*#__PURE__*/
          _jsx(TabsTrigger, { value: "materials", children: "Materials" }), /*#__PURE__*/
          _jsx(TabsTrigger, { value: "assemblies", children: "Assemblies" })] }
        ), /*#__PURE__*/


        _jsx(TabsContent, { value: "parts", children: /*#__PURE__*/
          _jsxs(Card, { children: [/*#__PURE__*/
            _jsxs(CardHeader, { children: [/*#__PURE__*/
              _jsxs("div", { className: "flex items-center justify-between", children: [/*#__PURE__*/
                _jsx(CardTitle, { children: "Parts Catalog" }), /*#__PURE__*/
                _jsx(ExportButton, {
                  entityType: "parts",
                  filters: {
                    status: statusFilter,
                    search: debouncedSearchQuery
                  } }
                )] }
              ), /*#__PURE__*/
              _jsxs("div", { className: "flex gap-4 mt-4", children: [/*#__PURE__*/
                _jsxs("div", { className: "relative flex-1", children: [/*#__PURE__*/
                  _jsx(Search, { className: "absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" }), /*#__PURE__*/
                  _jsx(Input, {
                    placeholder: "Search parts...",
                    value: searchQuery,
                    onChange: (e) => setSearchQuery(e.target.value),
                    className: "pl-8" }
                  )] }
                ), /*#__PURE__*/
                _jsxs(Select, { value: statusFilter, onValueChange: setStatusFilter, children: [/*#__PURE__*/
                  _jsx(SelectTrigger, { className: "w-48", children: /*#__PURE__*/
                    _jsx(SelectValue, { placeholder: "Status" }) }
                  ), /*#__PURE__*/
                  _jsxs(SelectContent, { children: [/*#__PURE__*/
                    _jsx(SelectItem, { value: "all", children: "All Statuses" }), /*#__PURE__*/
                    _jsx(SelectItem, { value: "Released", children: "Released" }), /*#__PURE__*/
                    _jsx(SelectItem, { value: "Development", children: "Development" }), /*#__PURE__*/
                    _jsx(SelectItem, { value: "Obsolete", children: "Obsolete" })] }
                  )] }
                )] }
              )] }
            ), /*#__PURE__*/
            _jsx(CardContent, { children:
              loadingParts ? /*#__PURE__*/
              _jsx("div", { className: "space-y-2", children:
                [1, 2, 3, 4, 5].map((i) => /*#__PURE__*/
                _jsx(Skeleton, { className: "h-12 w-full" }, i)
                ) }
              ) :
              parts.length === 0 ? /*#__PURE__*/
              _jsx("div", { className: "text-center py-8 text-muted-foreground", children: "No parts found. Try adjusting your filters." }

              ) : /*#__PURE__*/

              _jsxs(Table, { children: [/*#__PURE__*/
                _jsx(TableHeader, { children: /*#__PURE__*/
                  _jsxs(TableRow, { children: [/*#__PURE__*/
                    _jsx(TableHead, { children: "Part Number" }), /*#__PURE__*/
                    _jsx(TableHead, { children: "Name" }), /*#__PURE__*/
                    _jsx(TableHead, { children: "Status" }), /*#__PURE__*/
                    _jsx(TableHead, { children: "Materials" }), /*#__PURE__*/
                    _jsx(TableHead, { children: "Requirements" }), /*#__PURE__*/
                    _jsx(TableHead, { children: "Actions" })] }
                  ) }
                ), /*#__PURE__*/
                _jsx(TableBody, { children:
                  parts.map((part) => /*#__PURE__*/
                  _jsxs(TableRow, { children: [/*#__PURE__*/
                    _jsx(TableCell, { className: "font-mono text-sm", children: part.part_number }), /*#__PURE__*/
                    _jsx(TableCell, { className: "font-medium", children: part.name }), /*#__PURE__*/
                    _jsx(TableCell, { children: /*#__PURE__*/
                      _jsx(Badge, { variant: getStatusColor(part.status), children:
                        part.status || 'N/A' }
                      ) }
                    ), /*#__PURE__*/
                    _jsx(TableCell, { children:
                      part.materials && part.materials.length > 0 ? /*#__PURE__*/
                      _jsxs("div", { className: "flex flex-wrap gap-1", children: [
                        part.materials.slice(0, 2).map((mat, idx) => /*#__PURE__*/
                        _jsx(Badge, { variant: "outline", className: "text-xs", children:
                          mat.name }, idx
                        )
                        ),
                        part.materials.length > 2 && /*#__PURE__*/
                        _jsxs(Badge, { variant: "outline", className: "text-xs", children: ["+",
                          part.materials.length - 2] }
                        )] }

                      ) : /*#__PURE__*/

                      _jsx("span", { className: "text-muted-foreground text-sm", children: "None" }) }

                    ), /*#__PURE__*/
                    _jsx(TableCell, { children: /*#__PURE__*/
                      _jsxs(Badge, { variant: "secondary", children: [
                        part.satisfies_requirements?.length || 0, " reqs"] }
                      ) }
                    ), /*#__PURE__*/
                    _jsx(TableCell, { children: /*#__PURE__*/
                      _jsx(Button, {
                        variant: "ghost",
                        size: "sm",
                        onClick: () => fetchPartDetail(part.id), children:
                        "View Details" }

                      ) }
                    )] }, part.id
                  )
                  ) }
                )] }
              ) }

            )] }
          ) }
        ), /*#__PURE__*/


        _jsx(TabsContent, { value: "materials", children: /*#__PURE__*/
          _jsxs(Card, { children: [/*#__PURE__*/
            _jsxs(CardHeader, { children: [/*#__PURE__*/
              _jsx(CardTitle, { children: "Materials Library" }), /*#__PURE__*/
              _jsx("div", { className: "flex gap-4 mt-4", children: /*#__PURE__*/
                _jsxs(Select, { value: materialTypeFilter, onValueChange: setMaterialTypeFilter, children: [/*#__PURE__*/
                  _jsx(SelectTrigger, { className: "w-48", children: /*#__PURE__*/
                    _jsx(SelectValue, { placeholder: "Material Type" }) }
                  ), /*#__PURE__*/
                  _jsxs(SelectContent, { children: [/*#__PURE__*/
                    _jsx(SelectItem, { value: "all", children: "All Types" }), /*#__PURE__*/
                    _jsx(SelectItem, { value: "Metal", children: "Metal" }), /*#__PURE__*/
                    _jsx(SelectItem, { value: "Polymer", children: "Polymer" }), /*#__PURE__*/
                    _jsx(SelectItem, { value: "Composite", children: "Composite" }), /*#__PURE__*/
                    _jsx(SelectItem, { value: "Ceramic", children: "Ceramic" })] }
                  )] }
                ) }
              )] }
            ), /*#__PURE__*/
            _jsx(CardContent, { children:
              loadingMaterials ? /*#__PURE__*/
              _jsx("div", { className: "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4", children:
                [1, 2, 3].map((i) => /*#__PURE__*/
                _jsxs(Card, { children: [/*#__PURE__*/
                  _jsx(CardHeader, { children: /*#__PURE__*/
                    _jsx(Skeleton, { className: "h-6 w-48" }) }
                  ), /*#__PURE__*/
                  _jsx(CardContent, { children: /*#__PURE__*/
                    _jsx(Skeleton, { className: "h-20 w-full" }) }
                  )] }, i
                )
                ) }
              ) :
              materials.length === 0 ? /*#__PURE__*/
              _jsx("div", { className: "text-center py-8 text-muted-foreground", children: "No materials found. Try adjusting your filters." }

              ) : /*#__PURE__*/

              _jsx("div", { className: "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4", children:
                materials.map((material, idx) => /*#__PURE__*/
                _jsxs(Card, { children: [/*#__PURE__*/
                  _jsx(CardHeader, { children: /*#__PURE__*/
                    _jsxs("div", { className: "flex items-start justify-between", children: [/*#__PURE__*/
                      _jsxs("div", { className: "flex items-center gap-2", children: [
                        getMaterialIcon(material.material_type), /*#__PURE__*/
                        _jsx(CardTitle, { className: "text-base", children: material.name })] }
                      ), /*#__PURE__*/
                      _jsx(Badge, { variant: "outline", children: material.material_type })] }
                    ) }
                  ), /*#__PURE__*/
                  _jsxs(CardContent, { className: "space-y-3", children: [
                    material.specification && /*#__PURE__*/
                    _jsxs("div", { children: [/*#__PURE__*/
                      _jsx("p", { className: "text-sm font-medium", children: "Specification" }), /*#__PURE__*/
                      _jsx("p", { className: "text-sm text-muted-foreground", children: material.specification })] }
                    ),


                    material.properties && material.properties.length > 0 && /*#__PURE__*/
                    _jsxs("div", { children: [/*#__PURE__*/
                      _jsx("p", { className: "text-sm font-medium mb-2", children: "Properties" }), /*#__PURE__*/
                      _jsx("div", { className: "space-y-1", children:
                        material.properties.map((prop, propIdx) => /*#__PURE__*/
                        _jsxs("div", { className: "text-xs flex justify-between", children: [/*#__PURE__*/
                          _jsxs("span", { className: "text-muted-foreground", children: [prop.name, ":"] }), /*#__PURE__*/
                          _jsxs("span", { className: "font-mono", children: [
                            prop.value, " ", prop.unit] }
                          )] }, propIdx
                        )
                        ) }
                      )] }
                    ),


                    material.used_in_parts && material.used_in_parts.length > 0 && /*#__PURE__*/
                    _jsxs("div", { children: [/*#__PURE__*/
                      _jsx("p", { className: "text-sm font-medium", children: "Used In" }), /*#__PURE__*/
                      _jsxs(Badge, { variant: "secondary", className: "mt-1", children: [
                        material.used_in_parts.length, " parts"] }
                      )] }
                    ),


                    material.ontology_classes && material.ontology_classes.length > 0 && /*#__PURE__*/
                    _jsxs("div", { children: [/*#__PURE__*/
                      _jsx("p", { className: "text-sm font-medium", children: "Ontology Classification" }), /*#__PURE__*/
                      _jsx("div", { className: "flex flex-wrap gap-1 mt-1", children:
                        material.ontology_classes.map((ont, ontIdx) => /*#__PURE__*/
                        _jsx(Badge, { variant: "outline", className: "text-xs", children:
                          ont }, ontIdx
                        )
                        ) }
                      )] }
                    )] }

                  )] }, idx
                )
                ) }
              ) }

            )] }
          ) }
        ), /*#__PURE__*/


        _jsx(TabsContent, { value: "assemblies", children: /*#__PURE__*/
          _jsxs(Card, { children: [/*#__PURE__*/
            _jsx(CardHeader, { children: /*#__PURE__*/
              _jsx(CardTitle, { children: "Assembly Structures" }) }
            ), /*#__PURE__*/
            _jsx(CardContent, { children:
              loadingAssemblies ? /*#__PURE__*/
              _jsx("div", { className: "space-y-4", children:
                [1, 2, 3].map((i) => /*#__PURE__*/
                _jsxs(Card, { children: [/*#__PURE__*/
                  _jsxs(CardHeader, { children: [/*#__PURE__*/
                    _jsx(Skeleton, { className: "h-6 w-48" }), /*#__PURE__*/
                    _jsx(Skeleton, { className: "h-4 w-32" })] }
                  ), /*#__PURE__*/
                  _jsx(CardContent, { children: /*#__PURE__*/
                    _jsx(Skeleton, { className: "h-12 w-full" }) }
                  )] }, i
                )
                ) }
              ) :
              assemblies.length === 0 ? /*#__PURE__*/
              _jsx("div", { className: "text-center py-8 text-muted-foreground", children: "No assemblies found in the database." }

              ) : /*#__PURE__*/

              _jsx("div", { className: "space-y-4", children:
                assemblies.map((assembly, idx) => /*#__PURE__*/
                _jsxs(Card, { children: [/*#__PURE__*/
                  _jsx(CardHeader, { children: /*#__PURE__*/
                    _jsxs("div", { className: "flex items-center justify-between", children: [/*#__PURE__*/
                      _jsxs("div", { className: "flex items-center gap-3", children: [/*#__PURE__*/
                        _jsx(Boxes, { className: "h-5 w-5 text-muted-foreground" }), /*#__PURE__*/
                        _jsxs("div", { children: [/*#__PURE__*/
                          _jsx(CardTitle, { className: "text-base", children: assembly.name }), /*#__PURE__*/
                          _jsxs("p", { className: "text-sm text-muted-foreground", children: [
                            assembly.component_count || 0, " components"] }
                          )] }
                        )] }
                      ), /*#__PURE__*/
                      _jsx(Badge, { children: assembly.type })] }
                    ) }
                  ), /*#__PURE__*/
                  _jsx(CardContent, { children:
                    assembly.parts && assembly.parts.length > 0 && /*#__PURE__*/
                    _jsx("div", { className: "flex flex-wrap gap-2", children:
                      assembly.parts.map((partName, partIdx) => /*#__PURE__*/
                      _jsx(Badge, { variant: "outline", children:
                        partName }, partIdx
                      )
                      ) }
                    ) }

                  )] }, idx
                )
                ) }
              ) }

            )] }
          ) }
        )] }
      ),


      selectedPart && /*#__PURE__*/
      _jsxs(Card, { className: "fixed right-4 top-20 w-96 max-h-[80vh] overflow-y-auto shadow-lg z-50", children: [/*#__PURE__*/
        _jsx(CardHeader, { children: /*#__PURE__*/
          _jsxs("div", { className: "flex justify-between items-start", children: [/*#__PURE__*/
            _jsxs("div", { children: [/*#__PURE__*/
              _jsx(CardTitle, { children: selectedPart.name }), /*#__PURE__*/
              _jsx("p", { className: "text-sm text-muted-foreground", children: selectedPart.part_number })] }
            ), /*#__PURE__*/
            _jsx(Button, { variant: "ghost", size: "sm", onClick: () => setSelectedPart(null), children: "\u2715" }

            )] }
          ) }
        ), /*#__PURE__*/
        _jsxs(CardContent, { className: "space-y-4", children: [/*#__PURE__*/
          _jsxs("div", { children: [/*#__PURE__*/
            _jsx("h4", { className: "font-semibold mb-2", children: "Description" }), /*#__PURE__*/
            _jsx("p", { className: "text-sm text-muted-foreground", children:
              selectedPart.description || 'No description available' }
            )] }
          ),

          selectedPart.versions && selectedPart.versions.length > 0 && /*#__PURE__*/
          _jsxs("div", { children: [/*#__PURE__*/
            _jsx("h4", { className: "font-semibold mb-2", children: "Versions" }), /*#__PURE__*/
            _jsx("div", { className: "space-y-1", children:
              selectedPart.versions.map((v, idx) => /*#__PURE__*/
              _jsxs(Badge, { variant: "outline", className: "mr-1", children: [
                v.version, " (", v.status, ")"] }, idx
              )
              ) }
            )] }
          ),


          selectedPart.materials && selectedPart.materials.length > 0 && /*#__PURE__*/
          _jsxs("div", { children: [/*#__PURE__*/
            _jsx("h4", { className: "font-semibold mb-2", children: "Materials" }), /*#__PURE__*/
            _jsx("div", { className: "space-y-2", children:
              selectedPart.materials.map((mat, idx) => /*#__PURE__*/
              _jsxs("div", { className: "p-2 bg-muted rounded", children: [/*#__PURE__*/
                _jsx("div", { className: "font-medium text-sm", children: mat.name }), /*#__PURE__*/
                _jsx("div", { className: "text-xs text-muted-foreground", children: mat.specification })] }, idx
              )
              ) }
            )] }
          ),


          bomData && bomData.components.length > 0 && /*#__PURE__*/
          _jsxs("div", { children: [/*#__PURE__*/
            _jsx("h4", { className: "font-semibold mb-2", children: "Bill of Materials" }), /*#__PURE__*/
            _jsx("div", { className: "space-y-1", children:
              bomData.components.map((comp, idx) => /*#__PURE__*/
              _jsxs("div", { className: "text-sm p-2 bg-muted rounded", children: [/*#__PURE__*/
                _jsx("div", { className: "font-medium", children: comp.name }), /*#__PURE__*/
                _jsx("div", { className: "text-xs text-muted-foreground", children: comp.part_number })] }, idx
              )
              ) }
            )] }
          ),


          selectedPart.geometry && selectedPart.geometry.length > 0 && /*#__PURE__*/
          _jsxs("div", { children: [/*#__PURE__*/
            _jsx("h4", { className: "font-semibold mb-2", children: "CAD Geometry" }), /*#__PURE__*/
            _jsx("div", { className: "space-y-1", children:
              selectedPart.geometry.map((geo, idx) => /*#__PURE__*/
              _jsxs("div", { className: "text-sm", children: [/*#__PURE__*/
                _jsx(Badge, { variant: "outline", children: geo.type }), " ", geo.name] }, idx
              )
              ) }
            )] }
          )] }

        )] }
      )] }

    ));

};

export default PartsExplorer;

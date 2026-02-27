import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import {
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  Clock,
  CircleDot,
  FileText,
  Box,
  Cog,
  BarChart3,
  FlaskConical,
  Users,
  ShieldCheck,
  Layers,
} from 'lucide-react';

/** Map evidence codes to icons */
const CATEGORY_ICONS = {
  A1: Box,          // Geometry
  B1: Layers,       // Mesh
  C1: Cog,          // Solver Setup
  D1: BarChart3,    // Run Results
  E1: FlaskConical, // Post-Processing
  F1: ShieldCheck,  // V&V
  G1: Users,        // Peer Review
  H1: CheckCircle2, // Certification
};

/** Default pipeline categories if dossier has none */
const DEFAULT_CATEGORIES = [
  { code: 'A1', name: 'Geometry', status: 'NotStarted', artifacts: [] },
  { code: 'B1', name: 'Mesh', status: 'NotStarted', artifacts: [] },
  { code: 'C1', name: 'Solver Setup', status: 'NotStarted', artifacts: [] },
  { code: 'D1', name: 'Run Results', status: 'NotStarted', artifacts: [] },
  { code: 'E1', name: 'Post-Processing', status: 'NotStarted', artifacts: [] },
  { code: 'F1', name: 'V&V', status: 'NotStarted', artifacts: [] },
  { code: 'G1', name: 'Peer Review', status: 'NotStarted', artifacts: [] },
  { code: 'H1', name: 'Certification', status: 'NotStarted', artifacts: [] },
];

const STATUS_CONFIG = {
  Complete: {
    color: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
    icon: CheckCircle2,
    progressColor: 'bg-green-600',
  },
  InProgress: {
    color: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300',
    icon: CircleDot,
    progressColor: 'bg-blue-600',
  },
  NotStarted: {
    color: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400',
    icon: Clock,
    progressColor: 'bg-gray-400',
  },
};

const EvidencePipeline = ({ categories, onArtifactClick }) => {
  const [expandedCode, setExpandedCode] = useState(null);

  // Normalise: use provided categories or fall back
  const pipeline = (categories && categories.length > 0)
    ? categories.map((cat) => ({
        code: cat.code || cat.label?.charAt(0) + '1',
        name: cat.name || cat.label || cat.code,
        status: cat.status || 'NotStarted',
        artifacts: cat.artifacts || [],
      }))
    : DEFAULT_CATEGORIES;

  // Stats
  const completedCount = pipeline.filter((c) => c.status === 'Complete').length;
  const totalCount = pipeline.length;
  const overallProgress = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;

  return (
    <div className="space-y-4">
      {/* Overall Progress */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Evidence Pipeline Progress</CardTitle>
          <CardDescription>
            {completedCount} of {totalCount} categories complete
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-3">
            <Progress value={overallProgress} className="h-2 flex-1" />
            <span className="text-sm font-medium">{overallProgress}%</span>
          </div>
        </CardContent>
      </Card>

      {/* Pipeline Steps */}
      <div className="space-y-1">
        {pipeline.map((category, idx) => {
          const config = STATUS_CONFIG[category.status] || STATUS_CONFIG.NotStarted;
          const StatusIcon = config.icon;
          const CategoryIcon = CATEGORY_ICONS[category.code] || FileText;
          const isExpanded = expandedCode === category.code;

          return (
            <Card key={category.code} className="overflow-hidden">
              {/* Step header */}
              <button
                className="w-full flex items-center gap-3 p-3 hover:bg-muted/50 transition-colors text-left"
                onClick={() =>
                  setExpandedCode(isExpanded ? null : category.code)
                }
              >
                {/* Step number */}
                <div
                  className={`flex items-center justify-center h-7 w-7 rounded-full text-xs font-bold shrink-0 ${
                    category.status === 'Complete'
                      ? 'bg-green-600 text-white'
                      : category.status === 'InProgress'
                      ? 'bg-blue-600 text-white'
                      : 'bg-muted text-muted-foreground'
                  }`}
                >
                  {idx + 1}
                </div>

                <CategoryIcon className="h-4 w-4 shrink-0 text-muted-foreground" />

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">{category.code}</span>
                    <span className="text-sm text-muted-foreground truncate">
                      {category.name}
                    </span>
                  </div>
                </div>

                <Badge className={config.color}>{category.status}</Badge>

                {category.artifacts.length > 0 && (
                  <span className="text-xs text-muted-foreground">
                    {category.artifacts.length} file(s)
                  </span>
                )}

                {isExpanded ? (
                  <ChevronDown className="h-4 w-4 shrink-0" />
                ) : (
                  <ChevronRight className="h-4 w-4 shrink-0" />
                )}
              </button>

              {/* Expanded artifacts */}
              {isExpanded && (
                <div className="border-t px-3 pb-3 pt-2 bg-muted/20">
                  {category.artifacts.length > 0 ? (
                    <div className="space-y-1">
                      {category.artifacts.map((art) => (
                        <button
                          key={art.id}
                          className="w-full flex items-center gap-2 p-2 rounded hover:bg-muted/50 text-left"
                          onClick={() => onArtifactClick?.(art)}
                        >
                          <FileText className="h-3 w-3 text-muted-foreground" />
                          <span className="text-sm flex-1 truncate">{art.name}</span>
                          <Badge variant="outline" className="text-xs">
                            {art.type}
                          </Badge>
                        </button>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground text-center py-3">
                      No artifacts linked to this category
                    </p>
                  )}
                </div>
              )}
            </Card>
          );
        })}
      </div>

      {/* Connector lines between steps (visual) */}
      <div className="flex items-center gap-2 px-4">
        {pipeline.map((category, idx) => (
          <React.Fragment key={category.code}>
            <div
              className={`h-2 flex-1 rounded-full ${
                category.status === 'Complete'
                  ? 'bg-green-500'
                  : category.status === 'InProgress'
                  ? 'bg-blue-500'
                  : 'bg-gray-200 dark:bg-gray-700'
              }`}
              title={`${category.code}: ${category.name} — ${category.status}`}
            />
          </React.Fragment>
        ))}
      </div>
    </div>
  );
};

export default EvidencePipeline;

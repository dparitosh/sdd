import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Separator } from '@/components/ui/separator';
import {
  ArrowRight,
  Link2,
  Search,
  X,
  ExternalLink,
  Info,
  Layers,
  GitBranch,
} from 'lucide-react';

/** Color map for relation types */
const RELATION_COLORS = {
  SATISFIES: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
  DERIVES_FROM: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300',
  VALIDATES: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300',
  USES: 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900 dark:text-cyan-300',
  CONSTRAINS: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-300',
  PRODUCES: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-300',
  TRACES_TO: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300',
  COMPOSED_OF: 'bg-pink-100 text-pink-800 dark:bg-pink-900 dark:text-pink-300',
};

/** Entity type badge color */
const ENTITY_COLORS = {
  Requirement: 'bg-blue-50 text-blue-700 border-blue-200',
  Part: 'bg-green-50 text-green-700 border-green-200',
  Simulation: 'bg-purple-50 text-purple-700 border-purple-200',
  Material: 'bg-orange-50 text-orange-700 border-orange-200',
  Ontology: 'bg-cyan-50 text-cyan-700 border-cyan-200',
  Constraint: 'bg-red-50 text-red-700 border-red-200',
  Model: 'bg-indigo-50 text-indigo-700 border-indigo-200',
  Result: 'bg-yellow-50 text-yellow-700 border-yellow-200',
  Parameter: 'bg-gray-50 text-gray-700 border-gray-200',
};

const MossecInspector = ({ links = [], open, onClose, onNavigate, embedded = false }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedLink, setSelectedLink] = useState(null);

  // Filter links by search
  const filteredLinks = links.filter((link) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      link.source?.toLowerCase().includes(q) ||
      link.target?.toLowerCase().includes(q) ||
      link.relationType?.toLowerCase().includes(q) ||
      link.semanticDescription?.toLowerCase().includes(q)
    );
  });

  // Group by relation type
  const grouped = filteredLinks.reduce((acc, link) => {
    const rel = link.relationType || 'Unknown';
    if (!acc[rel]) acc[rel] = [];
    acc[rel].push(link);
    return acc;
  }, {});

  // ── Shared content ──────────────────────────────────────────
  const inspectorContent = (
    <>
      {/* Search */}
      <div className="relative">
        <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search links by source, target, or relation…"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-8"
        />
      </div>

      {/* Links list */}
      <div className="flex-1 overflow-y-auto space-y-3 pr-1">
        {Object.entries(grouped).map(([relType, items]) => (
            <div key={relType}>
              <div className="flex items-center gap-2 mb-2">
                <Badge className={RELATION_COLORS[relType] || 'bg-gray-100 text-gray-800'}>
                  {relType}
                </Badge>
                <span className="text-xs text-muted-foreground">
                  {items.length} link(s)
                </span>
              </div>

              <div className="space-y-1">
                {items.map((link) => (
                  <button
                    key={link.id}
                    className={`w-full flex items-center gap-2 p-2 rounded-md border text-left transition-colors hover:bg-muted/50 ${
                      selectedLink?.id === link.id ? 'ring-2 ring-ring' : ''
                    }`}
                    onClick={() =>
                      setSelectedLink(selectedLink?.id === link.id ? null : link)
                    }
                  >
                    {/* Source */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1">
                        {link.sourceType && (
                          <Badge
                            variant="outline"
                            className={`text-[10px] px-1 py-0 ${
                              ENTITY_COLORS[link.sourceType] || ''
                            }`}
                          >
                            {link.sourceType}
                          </Badge>
                        )}
                        <span className="text-sm truncate">{link.source}</span>
                      </div>
                    </div>

                    {/* Arrow */}
                    <ArrowRight className="h-3 w-3 shrink-0 text-muted-foreground" />

                    {/* Target */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1">
                        {link.targetType && (
                          <Badge
                            variant="outline"
                            className={`text-[10px] px-1 py-0 ${
                              ENTITY_COLORS[link.targetType] || ''
                            }`}
                          >
                            {link.targetType}
                          </Badge>
                        )}
                        <span className="text-sm truncate">{link.target}</span>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          ))}

          {filteredLinks.length === 0 && (
            <div className="text-center py-8 text-muted-foreground">
              <Link2 className="h-8 w-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">
                {searchQuery
                  ? 'No links match your search'
                  : 'No MOSSEC links found for this dossier'}
              </p>
            </div>
          )}
        </div>

        {/* Selected Link Detail */}
        {selectedLink && (
          <>
            <Separator />
            <div className="space-y-2 pt-1">
              <p className="text-xs text-muted-foreground font-medium">Link Details</p>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div>
                  <span className="text-xs text-muted-foreground">Source</span>
                  <p className="font-medium">{selectedLink.source}</p>
                </div>
                <div>
                  <span className="text-xs text-muted-foreground">Target</span>
                  <p className="font-medium">{selectedLink.target}</p>
                </div>
                <div>
                  <span className="text-xs text-muted-foreground">Relation</span>
                  <Badge
                    className={
                      RELATION_COLORS[selectedLink.relationType] ||
                      'bg-gray-100 text-gray-800'
                    }
                  >
                    {selectedLink.relationType}
                  </Badge>
                </div>
                <div>
                  <span className="text-xs text-muted-foreground">ID</span>
                  <p className="font-mono text-xs">{selectedLink.id}</p>
                </div>
              </div>
              {selectedLink.semanticDescription && (
                <div className="flex items-start gap-2 p-2 rounded bg-muted/50">
                  <Info className="h-3 w-3 mt-0.5 shrink-0 text-blue-500" />
                  <p className="text-xs">{selectedLink.semanticDescription}</p>
                </div>
              )}
              {onNavigate && (
                <div className="flex gap-2 pt-1">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onNavigate(selectedLink.source)}
                  >
                    <ExternalLink className="h-3 w-3 mr-1" />
                    Go to Source
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onNavigate(selectedLink.target)}
                  >
                    <ExternalLink className="h-3 w-3 mr-1" />
                    Go to Target
                  </Button>
                </div>
              )}
            </div>
          </>
        )}
      </>
    );

    // ── Embedded mode: render as a Card ────────────────────────
    if (embedded) {
      return (
        <Card className="h-full flex flex-col">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm flex items-center gap-2">
                <GitBranch className="h-4 w-4" />
                MOSSEC Inspector
              </CardTitle>
              <Button variant="ghost" size="icon" className="h-6 w-6" onClick={onClose}>
                <X className="h-3 w-3" />
              </Button>
            </div>
            <CardDescription className="text-xs">{links.length} link(s)</CardDescription>
          </CardHeader>
          <CardContent className="flex-1 flex flex-col gap-3 overflow-hidden">
            {inspectorContent}
          </CardContent>
        </Card>
      );
    }

    // ── Dialog mode: original behavior ─────────────────────────
    return (
      <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
        <DialogContent className="sm:max-w-xl max-h-dvh-80 flex flex-col">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <GitBranch className="h-5 w-5" />
              MOSSEC Link Inspector
            </DialogTitle>
            <DialogDescription>
              {links.length} link(s) in this dossier
            </DialogDescription>
          </DialogHeader>
          {inspectorContent}
        </DialogContent>
      </Dialog>
    );
  };

export default MossecInspector;

import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Separator } from '@/components/ui/separator';
import {
  FileText,
  Download,
  Copy,
  CheckCircle2,
  Shield,
  X,
  File,
  Image,
  FileCode,
  FileSpreadsheet,
  Archive,
} from 'lucide-react';

/** Map file extension → icon */
function fileIcon(name) {
  if (!name) return File;
  const ext = name.split('.').pop()?.toLowerCase();
  const mapping = {
    pdf: FileText,
    png: Image,
    jpg: Image,
    jpeg: Image,
    svg: Image,
    json: FileCode,
    xml: FileCode,
    xsd: FileCode,
    xmi: FileCode,
    csv: FileSpreadsheet,
    xlsx: FileSpreadsheet,
    zip: Archive,
    tar: Archive,
    gz: Archive,
  };
  return mapping[ext] || File;
}

const ArtifactPreview = ({ artifact, open, onClose }) => {
  const [copied, setCopied] = useState(false);

  if (!artifact) return null;

  const FileIcon = fileIcon(artifact.name);

  const handleCopyChecksum = async () => {
    if (artifact.checksum) {
      try {
        await navigator.clipboard.writeText(artifact.checksum);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      } catch {
        // Fallback for non-secure contexts
        const ta = document.createElement('textarea');
        ta.value = artifact.checksum;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      }
    }
  };

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileIcon className="h-5 w-5 text-muted-foreground" />
            Artifact Details
          </DialogTitle>
          <DialogDescription>
            {artifact.name}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Basic Info */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <p className="text-xs text-muted-foreground">Name</p>
              <p className="text-sm font-medium truncate">{artifact.name}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Type</p>
              <Badge variant="outline">{artifact.type}</Badge>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Size</p>
              <p className="text-sm">{artifact.size || 'Unknown'}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Status</p>
              <Badge
                className={
                  artifact.status === 'Validated'
                    ? 'bg-green-100 text-green-800'
                    : 'bg-yellow-100 text-yellow-800'
                }
              >
                {artifact.status || 'Pending'}
              </Badge>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Uploaded</p>
              <p className="text-sm">
                {artifact.uploadedAt
                  ? new Date(artifact.uploadedAt).toLocaleString()
                  : 'N/A'}
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">ID</p>
              <p className="text-sm font-mono truncate">{artifact.id}</p>
            </div>
          </div>

          <Separator />

          {/* SHA-256 Checksum */}
          <div>
            <p className="text-xs text-muted-foreground mb-1">SHA-256 Checksum</p>
            <div className="flex items-center gap-2">
              <code className="flex-1 text-xs font-mono bg-muted p-2 rounded-md break-all">
                {artifact.checksum || 'Not available'}
              </code>
              {artifact.checksum && (
                <Button
                  variant="ghost"
                  size="icon"
                  className="shrink-0"
                  onClick={handleCopyChecksum}
                  title="Copy checksum"
                >
                  {copied ? (
                    <CheckCircle2 className="h-4 w-4 text-green-600" />
                  ) : (
                    <Copy className="h-4 w-4" />
                  )}
                </Button>
              )}
            </div>
          </div>

          <Separator />

          {/* Signature Chain */}
          <div>
            <p className="text-xs text-muted-foreground mb-2">Signature Chain</p>
            {artifact.signedBy && artifact.signedBy.length > 0 ? (
              <div className="space-y-1">
                {artifact.signedBy.map((signer, idx) => (
                  <div
                    key={idx}
                    className="flex items-center gap-2 text-sm p-1.5 rounded bg-muted/50"
                  >
                    <Shield className="h-3 w-3 text-blue-500" />
                    <span>{signer}</span>
                    {idx === 0 && (
                      <Badge variant="outline" className="text-xs ml-auto">
                        Primary
                      </Badge>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No signatures recorded</p>
            )}
          </div>

          <Separator />

          {/* Actions */}
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" onClick={onClose}>
              Close
            </Button>
            <Button>
              <Download className="h-4 w-4 mr-2" />
              Download
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default ArtifactPreview;

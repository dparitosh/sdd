import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@ui/card';
import { Button } from '@ui/button';
import { Badge } from '@ui/badge';
import { Input } from '@ui/input';
import { Label } from '@ui/label';
import { ScrollArea } from '@ui/scroll-area';
import { Skeleton } from '@ui/skeleton';
import { Alert, AlertDescription } from '@ui/alert';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@ui/dialog';
import { Separator } from '@ui/separator';
import PageHeader from '@/components/PageHeader';
import { ChevronRight, ChevronDown, Link2, Globe, Plug2 } from 'lucide-react';
import { useOSLC } from '../hooks/useOSLC';

function TreeNode({ node, depth = 0 }) {
  const [expanded, setExpanded] = useState(false);
  const hasChildren = node.children && node.children.length > 0;
  return (
    <li>
      <button
        type="button"
        className="flex items-center gap-1 text-sm py-1 px-1 w-full text-left rounded hover:bg-muted/50"
        onClick={() => hasChildren && setExpanded(!expanded)}
      >
        {hasChildren ? (
          expanded ? <ChevronDown className="h-3.5 w-3.5 shrink-0" /> : <ChevronRight className="h-3.5 w-3.5 shrink-0" />
        ) : (
          <span className="w-3.5" />
        )}
        <Badge variant="outline" className="text-xs mr-1">{node.type ?? 'item'}</Badge>
        <span className="truncate">{node.title ?? node.name ?? node.uri ?? 'Unknown'}</span>
      </button>
      {hasChildren && expanded && (
        <ul className="ml-4 border-l border-muted pl-2">
          {node.children.map((child, i) => (
            <TreeNode key={child.uri ?? i} node={child} depth={depth + 1} />
          ))}
        </ul>
      )}
      {node.dialogs && expanded && (
        <div className="ml-8 mt-1 space-y-1">
          {node.dialogs.map((d, i) => (
            <div key={i} className="flex items-center gap-2 text-xs text-muted-foreground">
              <Link2 className="h-3 w-3" />
              <span>{d.type}: {d.uri ?? d.url ?? '—'}</span>
            </div>
          ))}
        </div>
      )}
    </li>
  );
}

export default function OSLCBrowser() {
  const [connectOpen, setConnectOpen] = useState(false);
  const [rootUrl, setRootUrl] = useState('');
  const [authType, setAuthType] = useState('none');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  const { rootServices, serviceTree, isLoading, error, connect, isConnecting, connectError } = useOSLC();

  const handleConnect = () => {
    connect({ root_url: rootUrl, auth_type: authType, username, password });
    setConnectOpen(false);
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <PageHeader
        title="OSLC Browser"
        description="Browse OSLC Root Services, Catalogs, and Service Providers"
        icon={<Globe className="h-6 w-6 text-primary" />}
      />

      {/* Connect button */}
      <div className="flex items-center gap-3">
        <Dialog open={connectOpen} onOpenChange={setConnectOpen}>
          <DialogTrigger asChild>
            <Button><Plug2 className="h-4 w-4 mr-2" /> Connect OSLC Provider</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Connect to OSLC Provider</DialogTitle>
              <DialogDescription>Enter the root services URL to connect to an OSLC-compliant tool</DialogDescription>
            </DialogHeader>
            <div className="space-y-3 pt-2">
              <div className="space-y-1">
                <Label>Root Services URL</Label>
                <Input placeholder="https://example.com/oslc/rootservices" value={rootUrl} onChange={(e) => setRootUrl(e.target.value)} />
              </div>
              <div className="space-y-1">
                <Label>Auth Type</Label>
                <select className="w-full rounded-md border bg-background px-3 py-2 text-sm" value={authType} onChange={(e) => setAuthType(e.target.value)}>
                  <option value="none">None</option>
                  <option value="basic">Basic</option>
                  <option value="oauth">OAuth</option>
                </select>
              </div>
              {authType === 'basic' && (
                <>
                  <div className="space-y-1">
                    <Label>Username</Label>
                    <Input value={username} onChange={(e) => setUsername(e.target.value)} />
                  </div>
                  <div className="space-y-1">
                    <Label>Password</Label>
                    <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
                  </div>
                </>
              )}
              <Button onClick={handleConnect} disabled={!rootUrl || isConnecting} className="w-full">
                {isConnecting ? 'Connecting…' : 'Connect'}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
        {connectError && <Badge variant="destructive">Connection failed</Badge>}
      </div>

      {error && (
        <Alert variant="destructive"><AlertDescription>{String(error)}</AlertDescription></Alert>
      )}

      {/* Service tree */}
      <Card className="min-h-100">
        <CardHeader>
          <CardTitle className="text-base">Service Tree</CardTitle>
          <CardDescription>Root Services → Catalogs → Service Providers → Services</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-2">{[...Array(5)].map((_, i) => <Skeleton key={i} className="h-5 w-full" />)}</div>
          ) : (serviceTree?.length ?? 0) === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">No OSLC service data available. Connect to a provider or check if rootservices endpoint is running.</p>
          ) : (
            <ScrollArea className="h-100">
              <ul>
                {serviceTree.map((node, i) => (
                  <TreeNode key={node.uri ?? i} node={node} />
                ))}
              </ul>
            </ScrollArea>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

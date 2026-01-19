import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { History, GitBranch, Clock, Play, Copy, ArrowRight, Check } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { cn } from '@/lib/utils';

interface ScenarioVersion {
  id: number;
  name: string;
  version: number;
  description?: string;
  created_at: string;
  tags: string[];
  parent_id?: number;
  latest_simulation?: {
    runway?: { p50: number };
    survival?: { '18m': number };
  };
}

interface ScenarioVersionHistoryProps {
  scenarioId: number;
  versions: ScenarioVersion[];
  isLoading: boolean;
  onSelectVersion: (versionId: number) => void;
  onCreateVersion: (name: string, description: string) => Promise<void>;
  onRunVersion: (versionId: number) => void;
  currentVersionId?: number;
}

export function ScenarioVersionHistory({
  scenarioId,
  versions,
  isLoading,
  onSelectVersion,
  onCreateVersion,
  onRunVersion,
  currentVersionId,
}: ScenarioVersionHistoryProps) {
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [newVersionName, setNewVersionName] = useState('');
  const [newVersionDescription, setNewVersionDescription] = useState('');
  const [isCreating, setIsCreating] = useState(false);

  const handleCreateVersion = async () => {
    if (!newVersionName.trim()) return;
    
    setIsCreating(true);
    try {
      await onCreateVersion(newVersionName, newVersionDescription);
      setCreateDialogOpen(false);
      setNewVersionName('');
      setNewVersionDescription('');
    } finally {
      setIsCreating(false);
    }
  };

  const sortedVersions = [...versions].sort((a, b) => b.version - a.version);

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div className="flex items-center gap-2">
              <History className="h-5 w-5 text-primary" />
              <CardTitle className="text-lg">Version History</CardTitle>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCreateDialogOpen(true)}
              data-testid="button-create-version"
            >
              <GitBranch className="h-4 w-4 mr-1" />
              New Version
            </Button>
          </div>
          <CardDescription>
            Track changes and compare different iterations of your scenario
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              <Skeleton className="h-20 w-full" />
              <Skeleton className="h-20 w-full" />
              <Skeleton className="h-20 w-full" />
            </div>
          ) : versions.length === 0 ? (
            <div className="py-8 text-center">
              <History className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
              <p className="text-muted-foreground">No version history available</p>
              <p className="text-xs text-muted-foreground mt-1">
                Create a new version to start tracking changes
              </p>
            </div>
          ) : (
            <ScrollArea className="h-[400px] pr-4">
              <div className="space-y-3">
                {sortedVersions.map((version, index) => (
                  <div
                    key={version.id}
                    className={cn(
                      'relative p-4 rounded-lg border transition-colors',
                      currentVersionId === version.id
                        ? 'border-primary bg-primary/5'
                        : 'hover:bg-muted/50'
                    )}
                  >
                    {index < sortedVersions.length - 1 && (
                      <div className="absolute left-7 top-[calc(100%+0.25rem)] h-3 w-px bg-border" />
                    )}
                    
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-start gap-3">
                        <div className={cn(
                          'flex items-center justify-center w-8 h-8 rounded-full text-xs font-medium',
                          currentVersionId === version.id
                            ? 'bg-primary text-primary-foreground'
                            : 'bg-muted'
                        )}>
                          v{version.version}
                        </div>
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="font-medium">{version.name}</span>
                            {currentVersionId === version.id && (
                              <Badge variant="secondary" className="text-xs">
                                <Check className="h-3 w-3 mr-1" />
                                Current
                              </Badge>
                            )}
                          </div>
                          {version.description && (
                            <p className="text-sm text-muted-foreground">{version.description}</p>
                          )}
                          <div className="flex items-center gap-3 text-xs text-muted-foreground">
                            <span className="flex items-center gap-1">
                              <Clock className="h-3 w-3" />
                              {formatDistanceToNow(new Date(version.created_at), { addSuffix: true })}
                            </span>
                            {version.latest_simulation && (
                              <>
                                <span>
                                  Runway: {version.latest_simulation.runway?.p50?.toFixed(1) || '?'} mo
                                </span>
                                <span>
                                  Survival: {(version.latest_simulation.survival?.['18m'] || 0).toFixed(0)}%
                                </span>
                              </>
                            )}
                          </div>
                          {version.tags && version.tags.length > 0 && (
                            <div className="flex gap-1 mt-1">
                              {version.tags.map(tag => (
                                <Badge key={tag} variant="outline" className="text-xs">
                                  {tag}
                                </Badge>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => onSelectVersion(version.id)}
                          data-testid={`button-view-version-${version.version}`}
                        >
                          View
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => onRunVersion(version.id)}
                          data-testid={`button-run-version-${version.version}`}
                        >
                          <Play className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </ScrollArea>
          )}
        </CardContent>
      </Card>

      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <GitBranch className="h-5 w-5" />
              Create New Version
            </DialogTitle>
            <DialogDescription>
              Create a new version of this scenario to track changes and compare results.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="version-name">Version Name</Label>
              <Input
                id="version-name"
                placeholder="e.g., Q2 Optimistic Adjustments"
                value={newVersionName}
                onChange={(e) => setNewVersionName(e.target.value)}
                data-testid="input-version-name"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="version-description">Description (optional)</Label>
              <Textarea
                id="version-description"
                placeholder="Describe what changed in this version..."
                value={newVersionDescription}
                onChange={(e) => setNewVersionDescription(e.target.value)}
                rows={3}
                data-testid="input-version-description"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleCreateVersion}
              disabled={!newVersionName.trim() || isCreating}
              data-testid="button-confirm-create-version"
            >
              {isCreating ? 'Creating...' : 'Create Version'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

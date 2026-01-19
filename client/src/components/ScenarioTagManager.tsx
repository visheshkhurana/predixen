import { useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { X, Plus, Tag, Check } from 'lucide-react';
import { cn } from '@/lib/utils';

const PRESET_TAGS = [
  { value: 'baseline', color: 'bg-slate-500' },
  { value: 'growth', color: 'bg-green-500' },
  { value: 'cost-cutting', color: 'bg-amber-500' },
  { value: 'pricing', color: 'bg-blue-500' },
  { value: 'fundraising', color: 'bg-purple-500' },
  { value: 'risk', color: 'bg-red-500' },
  { value: 'optimistic', color: 'bg-emerald-500' },
  { value: 'pessimistic', color: 'bg-orange-500' },
  { value: 'draft', color: 'bg-gray-400' },
  { value: 'reviewed', color: 'bg-teal-500' },
];

interface ScenarioTagManagerProps {
  tags: string[];
  onChange: (tags: string[]) => void;
  compact?: boolean;
}

export function ScenarioTagManager({ tags, onChange, compact = false }: ScenarioTagManagerProps) {
  const [customTag, setCustomTag] = useState('');
  const [isOpen, setIsOpen] = useState(false);

  const addTag = (tag: string) => {
    const normalizedTag = tag.toLowerCase().trim();
    if (normalizedTag && !tags.includes(normalizedTag)) {
      onChange([...tags, normalizedTag]);
    }
    setCustomTag('');
  };

  const removeTag = (tag: string) => {
    onChange(tags.filter(t => t !== tag));
  };

  const toggleTag = (tag: string) => {
    if (tags.includes(tag)) {
      removeTag(tag);
    } else {
      addTag(tag);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && customTag.trim()) {
      e.preventDefault();
      addTag(customTag);
    }
  };

  const getTagColor = (tag: string) => {
    const preset = PRESET_TAGS.find(p => p.value === tag);
    return preset?.color || 'bg-primary';
  };

  if (compact) {
    return (
      <Popover open={isOpen} onOpenChange={setIsOpen}>
        <PopoverTrigger asChild>
          <Button variant="outline" size="sm" className="gap-1" data-testid="button-manage-tags">
            <Tag className="h-3.5 w-3.5" />
            Tags
            {tags.length > 0 && (
              <Badge variant="secondary" className="ml-1 px-1.5">
                {tags.length}
              </Badge>
            )}
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-80" align="start">
          <div className="space-y-3">
            <Label>Manage Tags</Label>
            
            {tags.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {tags.map(tag => (
                  <Badge
                    key={tag}
                    variant="secondary"
                    className="gap-1 pr-1"
                  >
                    <span className={cn('w-2 h-2 rounded-full', getTagColor(tag))} />
                    {tag}
                    <button
                      onClick={() => removeTag(tag)}
                      className="ml-1 hover:bg-muted rounded-full p-0.5"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                ))}
              </div>
            )}

            <div className="flex gap-2">
              <Input
                placeholder="Add custom tag..."
                value={customTag}
                onChange={(e) => setCustomTag(e.target.value)}
                onKeyDown={handleKeyDown}
                className="flex-1"
                data-testid="input-custom-tag"
              />
              <Button
                size="sm"
                onClick={() => addTag(customTag)}
                disabled={!customTag.trim()}
              >
                <Plus className="h-4 w-4" />
              </Button>
            </div>

            <div className="space-y-1">
              <Label className="text-xs text-muted-foreground">Preset Tags</Label>
              <div className="flex flex-wrap gap-1">
                {PRESET_TAGS.map(preset => (
                  <button
                    key={preset.value}
                    onClick={() => toggleTag(preset.value)}
                    className={cn(
                      'flex items-center gap-1 px-2 py-1 rounded-md text-xs transition-colors',
                      tags.includes(preset.value)
                        ? 'bg-primary/10 text-primary border border-primary/30'
                        : 'bg-muted hover:bg-muted/80 border border-transparent'
                    )}
                  >
                    <span className={cn('w-2 h-2 rounded-full', preset.color)} />
                    {preset.value}
                    {tags.includes(preset.value) && <Check className="h-3 w-3" />}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </PopoverContent>
      </Popover>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <Label className="flex items-center gap-2">
          <Tag className="h-4 w-4" />
          Scenario Tags
        </Label>
        {tags.length > 0 && (
          <span className="text-xs text-muted-foreground">{tags.length} tags</span>
        )}
      </div>

      {tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {tags.map(tag => (
            <Badge
              key={tag}
              variant="secondary"
              className="gap-1.5 pr-1.5"
            >
              <span className={cn('w-2 h-2 rounded-full', getTagColor(tag))} />
              {tag}
              <button
                onClick={() => removeTag(tag)}
                className="ml-0.5 hover:bg-muted rounded-full p-0.5"
                data-testid={`button-remove-tag-${tag}`}
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          ))}
        </div>
      )}

      <div className="flex gap-2">
        <Input
          placeholder="Type a custom tag and press Enter..."
          value={customTag}
          onChange={(e) => setCustomTag(e.target.value)}
          onKeyDown={handleKeyDown}
          data-testid="input-custom-tag-full"
        />
        <Button
          variant="outline"
          onClick={() => addTag(customTag)}
          disabled={!customTag.trim()}
        >
          <Plus className="h-4 w-4" />
        </Button>
      </div>

      <div className="space-y-2">
        <Label className="text-xs text-muted-foreground">Quick Add</Label>
        <div className="flex flex-wrap gap-1.5">
          {PRESET_TAGS.filter(p => !tags.includes(p.value)).map(preset => (
            <button
              key={preset.value}
              onClick={() => addTag(preset.value)}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs bg-muted hover:bg-muted/80 transition-colors"
              data-testid={`button-add-preset-${preset.value}`}
            >
              <span className={cn('w-2 h-2 rounded-full', preset.color)} />
              {preset.value}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

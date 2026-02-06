import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Skeleton } from '@/components/ui/skeleton';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter
} from '@/components/ui/dialog';
import { useToast } from '@/hooks/use-toast';
import {
  UsersRound, Plus, Search, Pencil, Github, Linkedin, Calendar, Briefcase, UserX, Users, UserCheck, Clock
} from 'lucide-react';

interface TeamMember {
  id: number;
  name: string;
  email: string;
  role: string;
  type: string;
  department: string;
  status: string;
  start_date: string | null;
  end_date: string | null;
  salary_range: string | null;
  skills: string[];
  github_url: string | null;
  linkedin_url: string | null;
  notes: string | null;
  created_at: string | null;
  updated_at: string | null;
}

const TYPE_STYLES: Record<string, string> = {
  full_time: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  contractor: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  intern: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
};

const TYPE_LABELS: Record<string, string> = {
  full_time: 'Full-Time',
  contractor: 'Contractor',
  intern: 'Intern',
};

const STATUS_STYLES: Record<string, string> = {
  active: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  interviewing: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  offer_sent: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  onboarding: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
  offboarded: 'bg-red-500/10 text-red-400 border-red-500/20',
};

const STATUS_LABELS: Record<string, string> = {
  active: 'Active',
  interviewing: 'Interviewing',
  offer_sent: 'Offer Sent',
  onboarding: 'Onboarding',
  offboarded: 'Offboarded',
};

const DEPARTMENTS = ['Engineering', 'Design', 'QA', 'Product', 'Data', 'DevOps'];

const emptyForm = {
  name: '',
  email: '',
  role: '',
  type: 'full_time',
  department: 'Engineering',
  status: 'active',
  start_date: '',
  end_date: '',
  salary_range: '',
  skills: '',
  github_url: '',
  linkedin_url: '',
  notes: '',
};

async function fetchTeam(params?: Record<string, string>) {
  const url = new URL('/admin/team', window.location.origin);
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v) url.searchParams.set(k, v);
    });
  }
  const token = localStorage.getItem('admin_token') || localStorage.getItem('token');
  const res = await fetch(url.toString(), {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error('Failed to fetch team');
  return res.json();
}

async function saveTeamMember(data: any, id?: number) {
  const token = localStorage.getItem('admin_token') || localStorage.getItem('token');
  const url = id ? `/admin/team/${id}` : '/admin/team';
  const method = id ? 'PUT' : 'POST';
  const res = await fetch(url, {
    method,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Failed to save team member');
  return res.json();
}

async function deleteTeamMember(id: number) {
  const token = localStorage.getItem('admin_token') || localStorage.getItem('token');
  const res = await fetch(`/admin/team/${id}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error('Failed to remove team member');
  return res.json();
}

export default function AdminTeam() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const [deptFilter, setDeptFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingMember, setEditingMember] = useState<TeamMember | null>(null);
  const [form, setForm] = useState(emptyForm);

  const { data: members = [], isLoading } = useQuery<TeamMember[]>({
    queryKey: ['/admin/team'],
    queryFn: () => fetchTeam(),
  });

  const saveMutation = useMutation({
    mutationFn: (data: { form: any; id?: number }) => saveTeamMember(data.form, data.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/admin/team'] });
      toast({ title: editingMember ? 'Team member updated' : 'Team member added' });
      closeDialog();
    },
    onError: (err: any) => {
      toast({ title: 'Error', description: err.message, variant: 'destructive' });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteTeamMember,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/admin/team'] });
      toast({ title: 'Team member offboarded' });
    },
    onError: (err: any) => {
      toast({ title: 'Error', description: err.message, variant: 'destructive' });
    },
  });

  const filtered = useMemo(() => {
    return members.filter((m) => {
      if (search) {
        const q = search.toLowerCase();
        if (!m.name.toLowerCase().includes(q) && !m.role.toLowerCase().includes(q) && !m.email.toLowerCase().includes(q)) return false;
      }
      if (typeFilter !== 'all' && m.type !== typeFilter) return false;
      if (deptFilter !== 'all' && m.department !== deptFilter) return false;
      if (statusFilter !== 'all' && m.status !== statusFilter) return false;
      return true;
    });
  }, [members, search, typeFilter, deptFilter, statusFilter]);

  const stats = useMemo(() => {
    const total = members.length;
    const fullTime = members.filter(m => m.type === 'full_time').length;
    const contractors = members.filter(m => m.type === 'contractor').length;
    const openPositions = members.filter(m => m.status === 'interviewing' || m.status === 'offer_sent').length;
    return { total, fullTime, contractors, openPositions };
  }, [members]);

  function openAdd() {
    setEditingMember(null);
    setForm(emptyForm);
    setDialogOpen(true);
  }

  function openEdit(member: TeamMember) {
    setEditingMember(member);
    setForm({
      name: member.name,
      email: member.email,
      role: member.role,
      type: member.type,
      department: member.department,
      status: member.status,
      start_date: member.start_date || '',
      end_date: member.end_date || '',
      salary_range: member.salary_range || '',
      skills: (member.skills || []).join(', '),
      github_url: member.github_url || '',
      linkedin_url: member.linkedin_url || '',
      notes: member.notes || '',
    });
    setDialogOpen(true);
  }

  function closeDialog() {
    setDialogOpen(false);
    setEditingMember(null);
    setForm(emptyForm);
  }

  function handleSubmit() {
    if (!form.name || !form.email || !form.role) {
      toast({ title: 'Please fill in name, email, and role', variant: 'destructive' });
      return;
    }
    const payload = {
      ...form,
      skills: form.skills ? form.skills.split(',').map(s => s.trim()).filter(Boolean) : [],
      start_date: form.start_date || null,
      end_date: form.end_date || null,
      salary_range: form.salary_range || null,
      github_url: form.github_url || null,
      linkedin_url: form.linkedin_url || null,
      notes: form.notes || null,
    };
    saveMutation.mutate({ form: payload, id: editingMember?.id });
  }

  const statCards = [
    { label: 'Total Members', value: stats.total, icon: Users, color: 'text-primary' },
    { label: 'Full-Time', value: stats.fullTime, icon: UserCheck, color: 'text-emerald-400' },
    { label: 'Contractors', value: stats.contractors, icon: Briefcase, color: 'text-blue-400' },
    { label: 'Open Positions', value: stats.openPositions, icon: Clock, color: 'text-amber-400' },
  ];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-3">
          <UsersRound className="h-8 w-8 text-primary" />
          <div>
            <h1 className="text-2xl font-bold" data-testid="text-page-title">Engineering Team</h1>
            <p className="text-muted-foreground">Build and manage your engineering talent</p>
          </div>
        </div>
        <Button onClick={openAdd} data-testid="button-add-member">
          <Plus className="h-4 w-4 mr-2" />
          Add Team Member
        </Button>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((s) => (
          <Card key={s.label}>
            <CardContent className="p-4">
              <div className="flex items-center gap-2 mb-2">
                <s.icon className={`h-4 w-4 ${s.color}`} />
                <span className="text-xs text-muted-foreground">{s.label}</span>
              </div>
              <p className="text-2xl font-bold" data-testid={`text-stat-${s.label.toLowerCase().replace(/\s/g, '-')}`}>{s.value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search by name, role, or email..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
            data-testid="input-search"
          />
        </div>
        <Select value={typeFilter} onValueChange={setTypeFilter}>
          <SelectTrigger className="w-[140px]" data-testid="select-type-filter">
            <SelectValue placeholder="Type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Types</SelectItem>
            <SelectItem value="full_time">Full-Time</SelectItem>
            <SelectItem value="contractor">Contractor</SelectItem>
            <SelectItem value="intern">Intern</SelectItem>
          </SelectContent>
        </Select>
        <Select value={deptFilter} onValueChange={setDeptFilter}>
          <SelectTrigger className="w-[160px]" data-testid="select-dept-filter">
            <SelectValue placeholder="Department" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Departments</SelectItem>
            {DEPARTMENTS.map(d => (
              <SelectItem key={d} value={d}>{d}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[150px]" data-testid="select-status-filter">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Statuses</SelectItem>
            <SelectItem value="active">Active</SelectItem>
            <SelectItem value="interviewing">Interviewing</SelectItem>
            <SelectItem value="offer_sent">Offer Sent</SelectItem>
            <SelectItem value="onboarding">Onboarding</SelectItem>
            <SelectItem value="offboarded">Offboarded</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {[1, 2, 3].map(i => (
            <Card key={i}>
              <CardContent className="p-5 space-y-3">
                <Skeleton className="h-5 w-40" />
                <Skeleton className="h-4 w-56" />
                <Skeleton className="h-4 w-32" />
                <div className="flex gap-2">
                  <Skeleton className="h-5 w-16" />
                  <Skeleton className="h-5 w-16" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <Card>
          <CardContent className="py-16 text-center">
            <UsersRound className="h-12 w-12 mx-auto mb-4 text-muted-foreground/30" />
            <h3 className="text-lg font-medium mb-1">No team members found</h3>
            <p className="text-sm text-muted-foreground mb-4">
              {members.length === 0
                ? 'Start building your team by adding your first member.'
                : 'Try adjusting your filters or search query.'}
            </p>
            {members.length === 0 && (
              <Button onClick={openAdd} data-testid="button-add-first-member">
                <Plus className="h-4 w-4 mr-2" />
                Add First Member
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filtered.map((member) => (
            <Card key={member.id} data-testid={`card-member-${member.id}`}>
              <CardContent className="p-5">
                <div className="flex items-start justify-between mb-3 gap-2">
                  <div className="min-w-0">
                    <h3 className="font-semibold text-sm truncate" data-testid={`text-member-name-${member.id}`}>{member.name}</h3>
                    <p className="text-sm text-muted-foreground truncate">{member.role}</p>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    {member.github_url && (
                      <Button size="icon" variant="ghost" asChild data-testid={`link-github-${member.id}`}>
                        <a href={member.github_url} target="_blank" rel="noopener noreferrer">
                          <Github className="h-4 w-4" />
                        </a>
                      </Button>
                    )}
                    {member.linkedin_url && (
                      <Button size="icon" variant="ghost" asChild data-testid={`link-linkedin-${member.id}`}>
                        <a href={member.linkedin_url} target="_blank" rel="noopener noreferrer">
                          <Linkedin className="h-4 w-4" />
                        </a>
                      </Button>
                    )}
                    <Button size="icon" variant="ghost" onClick={() => openEdit(member)} data-testid={`button-edit-${member.id}`}>
                      <Pencil className="h-4 w-4" />
                    </Button>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-2 mb-3">
                  <Badge variant="outline" className={`text-xs ${TYPE_STYLES[member.type] || ''}`}>
                    {TYPE_LABELS[member.type] || member.type}
                  </Badge>
                  <Badge variant="outline" className={`text-xs ${STATUS_STYLES[member.status] || ''}`}>
                    {STATUS_LABELS[member.status] || member.status}
                  </Badge>
                  <Badge variant="outline" className="text-xs">{member.department}</Badge>
                </div>

                {member.skills && member.skills.length > 0 && (
                  <div className="flex flex-wrap gap-1 mb-3">
                    {member.skills.slice(0, 5).map((skill) => (
                      <span key={skill} className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground">{skill}</span>
                    ))}
                    {member.skills.length > 5 && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground">+{member.skills.length - 5}</span>
                    )}
                  </div>
                )}

                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  {member.start_date && (
                    <span className="flex items-center gap-1">
                      <Calendar className="h-3 w-3" />
                      {member.start_date}
                    </span>
                  )}
                  <span className="truncate ml-auto">{member.email}</span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingMember ? 'Edit Team Member' : 'Add Team Member'}</DialogTitle>
            <DialogDescription>
              {editingMember ? 'Update team member details.' : 'Add a new member to your engineering team.'}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label htmlFor="name">Name *</Label>
                <Input id="name" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} data-testid="input-form-name" />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="email">Email *</Label>
                <Input id="email" type="email" value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))} data-testid="input-form-email" />
              </div>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="role">Role *</Label>
              <Input id="role" placeholder="e.g. Senior Frontend Engineer" value={form.role} onChange={e => setForm(f => ({ ...f, role: e.target.value }))} data-testid="input-form-role" />
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-1.5">
                <Label>Type</Label>
                <Select value={form.type} onValueChange={v => setForm(f => ({ ...f, type: v }))}>
                  <SelectTrigger data-testid="select-form-type"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="full_time">Full-Time</SelectItem>
                    <SelectItem value="contractor">Contractor</SelectItem>
                    <SelectItem value="intern">Intern</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label>Department</Label>
                <Select value={form.department} onValueChange={v => setForm(f => ({ ...f, department: v }))}>
                  <SelectTrigger data-testid="select-form-dept"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {DEPARTMENTS.map(d => <SelectItem key={d} value={d}>{d}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label>Status</Label>
                <Select value={form.status} onValueChange={v => setForm(f => ({ ...f, status: v }))}>
                  <SelectTrigger data-testid="select-form-status"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="active">Active</SelectItem>
                    <SelectItem value="interviewing">Interviewing</SelectItem>
                    <SelectItem value="offer_sent">Offer Sent</SelectItem>
                    <SelectItem value="onboarding">Onboarding</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label htmlFor="start_date">Start Date</Label>
                <Input id="start_date" type="date" value={form.start_date} onChange={e => setForm(f => ({ ...f, start_date: e.target.value }))} data-testid="input-form-start-date" />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="salary_range">Salary Range</Label>
                <Input id="salary_range" placeholder="e.g. $120k-$150k" value={form.salary_range} onChange={e => setForm(f => ({ ...f, salary_range: e.target.value }))} data-testid="input-form-salary" />
              </div>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="skills">Skills (comma-separated)</Label>
              <Input id="skills" placeholder="e.g. React, TypeScript, Node.js" value={form.skills} onChange={e => setForm(f => ({ ...f, skills: e.target.value }))} data-testid="input-form-skills" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label htmlFor="github_url">GitHub URL</Label>
                <Input id="github_url" placeholder="https://github.com/..." value={form.github_url} onChange={e => setForm(f => ({ ...f, github_url: e.target.value }))} data-testid="input-form-github" />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="linkedin_url">LinkedIn URL</Label>
                <Input id="linkedin_url" placeholder="https://linkedin.com/in/..." value={form.linkedin_url} onChange={e => setForm(f => ({ ...f, linkedin_url: e.target.value }))} data-testid="input-form-linkedin" />
              </div>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="notes">Notes</Label>
              <Textarea id="notes" placeholder="Any additional notes..." value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} className="resize-none" data-testid="input-form-notes" />
            </div>
          </div>
          <DialogFooter className="gap-2">
            {editingMember && (
              <Button
                variant="destructive"
                onClick={() => {
                  deleteMutation.mutate(editingMember.id);
                  closeDialog();
                }}
                data-testid="button-offboard"
              >
                <UserX className="h-4 w-4 mr-2" />
                Offboard
              </Button>
            )}
            <Button variant="outline" onClick={closeDialog} data-testid="button-cancel">Cancel</Button>
            <Button onClick={handleSubmit} disabled={saveMutation.isPending} data-testid="button-save">
              {saveMutation.isPending ? 'Saving...' : editingMember ? 'Update' : 'Add Member'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

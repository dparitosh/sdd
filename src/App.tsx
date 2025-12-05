import { useState } from 'react'
import { Plus, GitBranch, Database, Check, ArrowUpRight } from '@phosphor-icons/react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { toast } from 'sonner'
import { useKV } from '@github/spark/hooks'

type DataSourceType = 'mossecdb' | 'ap244' | 'mbse'

interface Repository {
  id: string
  name: string
  description: string
  dataSource: DataSourceType
  visibility: 'public' | 'private'
  url: string
  createdAt: string
}

const dataSourceOptions = [
  {
    type: 'mossecdb' as DataSourceType,
    title: 'MOSSECDB',
    description: 'Material Open Standards for Engineering Collaboration Database',
    icon: '🗄️'
  },
  {
    type: 'ap244' as DataSourceType,
    title: 'AP244',
    description: 'Product Data Representation and Exchange (STEP AP244)',
    icon: '📐'
  },
  {
    type: 'mbse' as DataSourceType,
    title: 'MBSE',
    description: 'Model-Based Systems Engineering data structures',
    icon: '🔷'
  }
]

function App() {
  const [repositories, setRepositories] = useKV<Repository[]>('neo4j-repositories', [])
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [selectedDataSource, setSelectedDataSource] = useState<DataSourceType | null>(null)
  const [isCreating, setIsCreating] = useState(false)
  
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    visibility: 'public' as 'public' | 'private'
  })

  const handleCreateRepository = async () => {
    if (!formData.name || !selectedDataSource) {
      toast.error('Please fill in all required fields')
      return
    }

    if (!/^[a-zA-Z0-9-_]+$/.test(formData.name)) {
      toast.error('Repository name can only contain letters, numbers, hyphens, and underscores')
      return
    }

    const existingRepo = repositories?.find(r => r.name.toLowerCase() === formData.name.toLowerCase())
    if (existingRepo) {
      toast.error('A repository with this name already exists')
      return
    }

    setIsCreating(true)

    try {
      await new Promise(resolve => setTimeout(resolve, 1500))

      const newRepository: Repository = {
        id: Date.now().toString(),
        name: formData.name,
        description: formData.description,
        dataSource: selectedDataSource,
        visibility: formData.visibility,
        url: `https://github.com/${formData.name}`,
        createdAt: new Date().toISOString()
      }

      setRepositories((current) => [newRepository, ...(current || [])])

      toast.success('Repository created successfully!', {
        description: `${formData.name} is now ready for Neo4j graph development`
      })

      setIsDialogOpen(false)
      setFormData({ name: '', description: '', visibility: 'public' })
      setSelectedDataSource(null)
    } catch (error) {
      toast.error('Failed to create repository', {
        description: 'Please try again or check your connection'
      })
    } finally {
      setIsCreating(false)
    }
  }

  const getDataSourceInfo = (type: DataSourceType) => {
    return dataSourceOptions.find(ds => ds.type === type)
  }

  return (
    <div className="min-h-screen bg-background relative overflow-hidden">
      <div className="absolute inset-0 opacity-20">
        <div className="absolute inset-0" style={{
          backgroundImage: `
            repeating-linear-gradient(0deg, oklch(0.25 0.05 200) 0px, transparent 1px, transparent 40px),
            repeating-linear-gradient(90deg, oklch(0.25 0.05 200) 0px, transparent 1px, transparent 40px)
          `
        }} />
        <div className="absolute top-20 left-20 w-96 h-96 rounded-full bg-accent/10 blur-3xl" />
        <div className="absolute bottom-20 right-20 w-96 h-96 rounded-full bg-primary/20 blur-3xl" />
      </div>

      <div className="relative z-10 max-w-7xl mx-auto p-8">
        <header className="mb-12">
          <div className="flex items-center gap-3 mb-3">
            <Database size={40} weight="duotone" className="text-accent" />
            <h1 className="text-4xl font-bold tracking-tight">Neo4j Graph Repository Creator</h1>
          </div>
          <p className="text-muted-foreground text-lg">
            Create and manage GitHub repositories for Neo4j graph databases specialized in MOSSECDB, AP244, and MBSE data sources
          </p>
        </header>

        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-2xl font-semibold mb-1">Repositories</h2>
            <p className="text-muted-foreground text-sm">
              {repositories?.length || 0} {(repositories?.length || 0) === 1 ? 'repository' : 'repositories'} created
            </p>
          </div>
          
          <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
            <DialogTrigger asChild>
              <Button className="bg-accent text-accent-foreground hover:bg-accent/90 gap-2">
                <Plus size={20} weight="bold" />
                Create Repository
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle className="text-2xl">Create New Repository</DialogTitle>
                <DialogDescription>
                  Set up a new GitHub repository for your Neo4j graph database project
                </DialogDescription>
              </DialogHeader>

              <div className="space-y-6 py-4">
                <div>
                  <Label className="text-base font-medium mb-3 block">Select Data Source Type *</Label>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    {dataSourceOptions.map((source) => (
                      <Card
                        key={source.type}
                        className={`p-4 cursor-pointer transition-all hover:border-accent/50 ${
                          selectedDataSource === source.type
                            ? 'border-accent bg-accent/10'
                            : 'border-border'
                        }`}
                        onClick={() => setSelectedDataSource(source.type)}
                      >
                        <div className="text-3xl mb-2">{source.icon}</div>
                        <h3 className="font-semibold text-base mb-1">{source.title}</h3>
                        <p className="text-xs text-muted-foreground leading-relaxed">
                          {source.description}
                        </p>
                        {selectedDataSource === source.type && (
                          <div className="mt-3 flex items-center gap-1 text-accent text-sm font-medium">
                            <Check size={16} weight="bold" />
                            Selected
                          </div>
                        )}
                      </Card>
                    ))}
                  </div>
                </div>

                <Separator />

                <div className="space-y-4">
                  <div>
                    <Label htmlFor="repo-name" className="text-sm font-medium">
                      Repository Name *
                    </Label>
                    <Input
                      id="repo-name"
                      placeholder="neo4j-mossecdb-graph"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      className="mt-1.5"
                    />
                    <p className="text-xs text-muted-foreground mt-1.5">
                      Only letters, numbers, hyphens, and underscores allowed
                    </p>
                  </div>

                  <div>
                    <Label htmlFor="repo-description" className="text-sm font-medium">
                      Description
                    </Label>
                    <Input
                      id="repo-description"
                      placeholder="Neo4j graph database for..."
                      value={formData.description}
                      onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                      className="mt-1.5"
                    />
                  </div>

                  <div>
                    <Label htmlFor="visibility" className="text-sm font-medium">
                      Visibility
                    </Label>
                    <Select
                      value={formData.visibility}
                      onValueChange={(value: 'public' | 'private') =>
                        setFormData({ ...formData, visibility: value })
                      }
                    >
                      <SelectTrigger id="visibility" className="mt-1.5">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="public">Public</SelectItem>
                        <SelectItem value="private">Private</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                {selectedDataSource && (
                  <>
                    <Separator />
                    <div className="bg-card/50 rounded-lg p-4 border border-border">
                      <h4 className="font-semibold text-sm mb-2 flex items-center gap-2">
                        <Database size={16} className="text-accent" />
                        Template Structure
                      </h4>
                      <div className="font-mono text-xs text-muted-foreground space-y-1">
                        <div>├── README.md</div>
                        <div>├── docker-compose.yml</div>
                        <div>├── cypher/</div>
                        <div>│   ├── schema.cypher</div>
                        <div>│   └── import.cypher</div>
                        <div>├── data/</div>
                        <div>│   └── {selectedDataSource}-sample.csv</div>
                        <div>└── scripts/</div>
                        <div>    └── setup.sh</div>
                      </div>
                    </div>
                  </>
                )}
              </div>

              <DialogFooter>
                <Button
                  variant="outline"
                  onClick={() => setIsDialogOpen(false)}
                  disabled={isCreating}
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleCreateRepository}
                  disabled={!formData.name || !selectedDataSource || isCreating}
                  className="bg-accent text-accent-foreground hover:bg-accent/90"
                >
                  {isCreating ? 'Creating...' : 'Create Repository'}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>

        {!repositories || repositories.length === 0 ? (
          <Card className="p-12 text-center">
            <Database size={64} weight="duotone" className="mx-auto text-muted-foreground mb-4" />
            <h3 className="text-xl font-semibold mb-2">No repositories yet</h3>
            <p className="text-muted-foreground mb-6">
              Create your first Neo4j graph repository to get started
            </p>
            <Button
              onClick={() => setIsDialogOpen(true)}
              className="bg-accent text-accent-foreground hover:bg-accent/90 gap-2"
            >
              <Plus size={20} weight="bold" />
              Create First Repository
            </Button>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {repositories.map((repo) => {
              const sourceInfo = getDataSourceInfo(repo.dataSource)
              return (
                <Card key={repo.id} className="p-6 hover:border-accent/50 transition-all group">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <GitBranch size={20} className="text-accent" />
                      <h3 className="font-semibold text-base font-mono">{repo.name}</h3>
                    </div>
                    <a
                      href={repo.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-muted-foreground hover:text-accent transition-colors"
                    >
                      <ArrowUpRight size={20} />
                    </a>
                  </div>

                  {repo.description && (
                    <p className="text-sm text-muted-foreground mb-4 leading-relaxed">
                      {repo.description}
                    </p>
                  )}

                  <div className="flex items-center gap-2 mb-3">
                    <Badge variant="secondary" className="text-xs">
                      {sourceInfo?.icon} {sourceInfo?.title}
                    </Badge>
                    <Badge variant="outline" className="text-xs">
                      {repo.visibility}
                    </Badge>
                  </div>

                  <div className="text-xs text-muted-foreground">
                    Created {new Date(repo.createdAt).toLocaleDateString()}
                  </div>
                </Card>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

export default App
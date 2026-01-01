import { Badge } from '@ui/badge';
import { Breadcrumb, BreadcrumbList, BreadcrumbItem, BreadcrumbLink, BreadcrumbSeparator, BreadcrumbPage } from '@ui/breadcrumb';
import { Home } from 'lucide-react';
export default function PageHeader({
  title,
  description,
  icon,
  badge,
  badgeVariant = 'secondary',
  actions,
  breadcrumbs
}) {
  return <div className="space-y-4">{breadcrumbs && breadcrumbs.length > 0 && <Breadcrumb><BreadcrumbList><BreadcrumbItem><BreadcrumbLink to="/dashboard"><Home className="h-4 w-4" /></BreadcrumbLink></BreadcrumbItem>{breadcrumbs.map((crumb, idx) => <div className="flex items-center"><BreadcrumbSeparator /><BreadcrumbItem>{crumb.href ? <BreadcrumbLink to={crumb.href}>{crumb.label}</BreadcrumbLink> : <BreadcrumbPage>{crumb.label}</BreadcrumbPage>}</BreadcrumbItem></div>)}</BreadcrumbList></Breadcrumb>}<div className="flex items-start justify-between"><div className="space-y-2"><h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">{icon && <span className="flex-shrink-0">{icon}</span>}{title}{badge && <Badge variant={badgeVariant}>{badge}</Badge>}</h1>{description && <p className="text-base text-muted-foreground max-w-3xl">{description}</p>}</div>{actions && <div className="flex gap-2">{actions}</div>}</div></div>;
}

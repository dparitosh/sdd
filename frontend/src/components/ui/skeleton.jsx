import { cn } from "@/lib/utils";
function Skeleton({
  className,
  ...props
}) {
  return <div className={cn("animate-pulse rounded-md bg-primary/10", className)} role="status" aria-label="Loading..." {...props} />;
}
export function TableSkeleton({
  rows = 5
}) {
  return <div className="space-y-4" role="status" aria-label="Loading table data"><div className="flex gap-4 border-b pb-2">{[1, 2, 3, 4].map(i => <Skeleton className="h-4 flex-1" />)}</div>{Array.from({
      length: rows
    }).map((_, rowIndex) => <div className="flex gap-4">{[1, 2, 3, 4].map(colIndex => <Skeleton className="h-8 flex-1" style={{
        opacity: 1 - rowIndex * 0.1
      }} />)}</div>)}</div>;
}
export function CardSkeleton() {
  return <div className="rounded-lg border p-6 space-y-4" role="status" aria-label="Loading card"><Skeleton className="h-6 w-3/4" /><Skeleton className="h-4 w-full" /><Skeleton className="h-4 w-5/6" /><div className="flex gap-2 pt-2"><Skeleton className="h-8 w-20" /><Skeleton className="h-8 w-20" /></div></div>;
}
export function DashboardSkeleton() {
  return <div className="space-y-6" role="status" aria-label="Loading dashboard"><div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">{[1, 2, 3, 4].map(i => <div className="rounded-lg border p-6 space-y-2"><Skeleton className="h-4 w-24" /><Skeleton className="h-8 w-16" /><Skeleton className="h-3 w-32" /></div>)}</div><div className="rounded-lg border p-6 space-y-4"><Skeleton className="h-6 w-48" /><Skeleton className="h-64 w-full" /></div><div className="rounded-lg border p-6 space-y-4"><Skeleton className="h-6 w-32" /><div className="space-y-3">{[1, 2, 3].map(i => <div className="flex items-center gap-4"><Skeleton className="h-10 w-10 rounded-full" /><div className="flex-1 space-y-2"><Skeleton className="h-4 w-3/4" /><Skeleton className="h-3 w-1/2" /></div></div>)}</div></div></div>;
}
export function ListSkeleton({
  items = 10
}) {
  return <div className="space-y-3" role="status" aria-label="Loading list">{Array.from({
      length: items
    }).map((_, i) => <div className="flex items-center gap-4 p-4 rounded-lg border"><Skeleton className="h-12 w-12 rounded-full" /><div className="flex-1 space-y-2"><Skeleton className="h-4 w-3/4" /><Skeleton className="h-3 w-1/2" /></div><Skeleton className="h-8 w-24" /></div>)}</div>;
}
export function GraphSkeleton() {
  return <div className="space-y-4" role="status" aria-label="Loading graph visualization"><div className="flex items-center justify-between"><Skeleton className="h-8 w-48" /><div className="flex gap-2"><Skeleton className="h-8 w-24" /><Skeleton className="h-8 w-24" /></div></div><div className="rounded-lg border p-6"><Skeleton className="h-[500px] w-full" /></div><div className="flex gap-4"><Skeleton className="h-4 w-32" /><Skeleton className="h-4 w-32" /><Skeleton className="h-4 w-32" /></div></div>;
}
export { Skeleton };

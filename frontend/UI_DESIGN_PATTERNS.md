# UI Design Patterns & Guidelines

## Overview
This document defines the standard UI patterns used across the MBSE Knowledge Graph application to ensure visual consistency and a cohesive user experience.

## Page Structure Pattern

All pages should follow this standard structure:

```tsx
export default function MyPage() {
  // ... state and queries

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Page Title</h1>
          <p className="text-muted-foreground">
            Brief description of page functionality
          </p>
        </div>
        <div className="flex gap-2">
          {/* Action buttons go here */}
          <Button variant="outline" onClick={handleRefresh}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
          <Button onClick={handlePrimaryAction}>
            <Plus className="h-4 w-4 mr-2" />
            Create New
          </Button>
        </div>
      </div>

      {/* Page content */}
      <Card>
        {/* ... */}
      </Card>
    </div>
  );
}
```

## Key Design Principles

### 1. Consistent Spacing
- **Page wrapper**: `<div className="space-y-6">` for all pages
- **Section spacing**: Use `space-y-4` for sections within cards
- **Grid gaps**: Use `gap-4` for grid layouts

### 2. Typography Hierarchy

#### Page Titles
```tsx
<h1 className="text-3xl font-bold tracking-tight">Page Title</h1>
```

#### Section Headings
```tsx
<h2 className="text-xl font-semibold">Section Title</h2>
```

#### Subsection Headings
```tsx
<h3 className="text-lg font-medium">Subsection Title</h3>
```

#### Descriptions
```tsx
<p className="text-muted-foreground">
  Descriptive text using muted color
</p>
```

### 3. Header Layout

All pages use a flex header with title on left, actions on right:

```tsx
<div className="flex items-center justify-between">
  <div>
    <h1 className="text-3xl font-bold tracking-tight">Title</h1>
    <p className="text-muted-foreground">Description</p>
  </div>
  <div className="flex gap-2">
    {/* Buttons */}
  </div>
</div>
```

### 4. Button Patterns

#### Primary Action
```tsx
<Button>
  <Icon className="h-4 w-4 mr-2" />
  Action Label
</Button>
```

#### Secondary Action
```tsx
<Button variant="outline">
  <Icon className="h-4 w-4 mr-2" />
  Action Label
</Button>
```

#### Icon-only Button
```tsx
<Button size="icon" variant="ghost">
  <Icon className="h-4 w-4" />
</Button>
```

### 5. Card Patterns

#### Standard Card
```tsx
<Card>
  <CardHeader>
    <CardTitle>Card Title</CardTitle>
    <CardDescription>Card description</CardDescription>
  </CardHeader>
  <CardContent>
    {/* Content */}
  </CardContent>
</Card>
```

#### Card with Action
```tsx
<Card>
  <CardHeader>
    <div className="flex items-center justify-between">
      <CardTitle>Card Title</CardTitle>
      <Button size="sm" variant="outline">Action</Button>
    </div>
  </CardHeader>
  <CardContent>
    {/* Content */}
  </CardContent>
</Card>
```

### 6. Loading States

```tsx
if (isLoading) {
  return (
    <div className="space-y-6">
      <Skeleton className="h-12 w-64" /> {/* Title */}
      <Skeleton className="h-32 w-full" /> {/* Content */}
    </div>
  );
}
```

### 7. Error States

```tsx
if (error) {
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold tracking-tight">Page Title</h1>
      <Alert variant="destructive">
        <AlertDescription>
          Error message here
        </AlertDescription>
      </Alert>
    </div>
  );
}
```

## Component Examples

### Example 1: Dashboard Page
Reference: `frontend/src/pages/Dashboard.tsx`
- Custom hero header with gradient background
- Periodic table grid layout
- Quick action cards

### Example 2: Requirements Manager
Reference: `frontend/src/pages/RequirementsManager.tsx`
- Standard header with title + actions
- Data table with sorting and filtering
- Create/Edit dialogs

### Example 3: System Monitoring
Reference: `frontend/src/pages/SystemMonitoring.tsx`
- Real-time metrics display
- Status indicators with colors
- Recharts integration

### Example 4: PLM Integration
Reference: `frontend/src/pages/PLMIntegration.tsx`
- Connector cards grid
- Tabbed interface
- Action buttons per connector

## Color & Status Patterns

### Status Colors

#### Success
```tsx
<Badge variant="default" className="bg-green-500">Success</Badge>
<Card className="border-green-500/50 bg-green-500/5">
```

#### Warning
```tsx
<Badge variant="warning" className="bg-yellow-500">Warning</Badge>
<Card className="border-yellow-500/50 bg-yellow-500/5">
```

#### Error
```tsx
<Badge variant="destructive">Error</Badge>
<Card className="border-red-500/50 bg-red-500/5">
```

#### Info
```tsx
<Badge variant="secondary">Info</Badge>
<Card className="border-blue-500/50 bg-blue-500/5">
```

### Health Status Icons

```tsx
// Connected/Healthy
<CheckCircle2 className="h-5 w-5 text-green-500" />

// Warning/Partial
<AlertCircle className="h-5 w-5 text-yellow-500" />

// Error/Failed
<XCircle className="h-5 w-5 text-red-500" />
```

## Navigation Integration

All pages must be registered in:
1. **App Routes**: `frontend/src/App.tsx`
2. **Navigation Menu**: `frontend/src/components/layout/Layout.tsx`

### Adding a New Page

1. Create page file in `frontend/src/pages/NewPage.tsx`
2. Follow the standard page structure pattern
3. Add route in `App.tsx`:
```tsx
<Route path="/new-page" element={<ErrorBoundary><NewPage /></ErrorBoundary>} />
```
4. Add navigation item in `Layout.tsx`:
```tsx
{
  name: 'New Page',
  href: '/new-page',
  icon: IconComponent,
  badge: null,
  description: 'Page description'
}
```

## Accessibility Guidelines

### Keyboard Navigation
- All interactive elements must be keyboard accessible
- Use proper semantic HTML (button, nav, main, etc.)
- Provide aria-labels for icon-only buttons

### Screen Readers
- Use proper heading hierarchy (h1 → h2 → h3)
- Add aria-labels to navigation groups
- Provide alt text for images

### Color Contrast
- Maintain WCAG AA compliance (4.5:1 for normal text)
- Don't rely solely on color to convey information
- Use text labels with color-coded indicators

## Performance Best Practices

### Query Management
- Use TanStack Query for all API calls
- Set appropriate staleTime (5 minutes for stable data)
- Use refetchInterval for real-time data (5-30 seconds)

### Component Optimization
- Wrap expensive components in React.memo
- Use useCallback for event handlers in lists
- Debounce search inputs

### Loading Optimization
- Show skeleton loaders immediately
- Load critical data first
- Lazy load heavy components

## Testing Checklist

When creating or updating pages, verify:

- [ ] Page header follows standard pattern
- [ ] Typography classes are correct (text-3xl, tracking-tight)
- [ ] Spacing is consistent (space-y-6 wrapper)
- [ ] Action buttons are properly aligned
- [ ] Loading states show skeletons
- [ ] Error states show alerts
- [ ] Navigation menu entry added
- [ ] Route registered in App.tsx
- [ ] Mobile responsive (test at 375px, 768px, 1024px)
- [ ] Keyboard navigation works
- [ ] Screen reader friendly

## Common Issues

### ❌ Incorrect Header
```tsx
// Wrong - no flex layout, inconsistent title style
<div>
  <h1 className="text-2xl font-semibold">Title</h1>
</div>
```

### ✅ Correct Header
```tsx
// Right - flex layout, standard title style
<div className="flex items-center justify-between">
  <div>
    <h1 className="text-3xl font-bold tracking-tight">Title</h1>
    <p className="text-muted-foreground">Description</p>
  </div>
</div>
```

### ❌ Incorrect Spacing
```tsx
// Wrong - inconsistent spacing
<div className="space-y-4">
  <div className="mb-8">
    <h1>Title</h1>
  </div>
</div>
```

### ✅ Correct Spacing
```tsx
// Right - consistent space-y-6
<div className="space-y-6">
  <div>
    <h1 className="text-3xl font-bold tracking-tight">Title</h1>
  </div>
</div>
```

## Design System Tools

### ShadCN UI Components
- Button: `<Button>`, `<Button variant="outline">`
- Card: `<Card>`, `<CardHeader>`, `<CardContent>`
- Badge: `<Badge>`, `<Badge variant="destructive">`
- Alert: `<Alert>`, `<AlertDescription>`
- Dialog: `<Dialog>`, `<DialogContent>`
- Table: `<Table>`, `<TableHeader>`, `<TableBody>`
- Select: `<Select>`, `<SelectTrigger>`, `<SelectContent>`
- Input: `<Input>`, `<Textarea>`

### Lucide React Icons
- Common icons: `Database`, `Activity`, `RefreshCw`, `Plus`, `Search`
- Status icons: `CheckCircle2`, `AlertCircle`, `XCircle`
- Navigation icons: `LayoutDashboard`, `FileText`, `Settings`

### Recharts (for graphs)
- Line charts: `<LineChart>`, `<Line>`
- Area charts: `<AreaChart>`, `<Area>`
- Bar charts: `<BarChart>`, `<Bar>`
- Responsive: `<ResponsiveContainer>`

## Conclusion

Following these patterns ensures:
- ✅ Visual consistency across all pages
- ✅ Predictable user experience
- ✅ Maintainable codebase
- ✅ Accessible interface
- ✅ Professional appearance

For questions or suggestions, update this document and notify the team.

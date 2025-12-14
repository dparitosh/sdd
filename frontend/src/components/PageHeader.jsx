
import { Badge } from '@ui/badge';
import {
  Breadcrumb,
  BreadcrumbList,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbSeparator,
  BreadcrumbPage } from
'@ui/breadcrumb';
import { Home } from 'lucide-react';import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
















export default function PageHeader({
  title,
  description,
  icon,
  badge,
  badgeVariant = 'secondary',
  actions,
  breadcrumbs
}) {
  return (/*#__PURE__*/
    _jsxs("div", { className: "space-y-4", children: [

      breadcrumbs && breadcrumbs.length > 0 && /*#__PURE__*/
      _jsx(Breadcrumb, { children: /*#__PURE__*/
        _jsxs(BreadcrumbList, { children: [/*#__PURE__*/
          _jsx(BreadcrumbItem, { children: /*#__PURE__*/
            _jsx(BreadcrumbLink, { to: "/dashboard", children: /*#__PURE__*/
              _jsx(Home, { className: "h-4 w-4" }) }
            ) }
          ),
          breadcrumbs.map((crumb, idx) => /*#__PURE__*/
          _jsxs("div", { className: "flex items-center", children: [/*#__PURE__*/
            _jsx(BreadcrumbSeparator, {}), /*#__PURE__*/
            _jsx(BreadcrumbItem, { children:
              crumb.href ? /*#__PURE__*/
              _jsx(BreadcrumbLink, { to: crumb.href, children: crumb.label }) : /*#__PURE__*/

              _jsx(BreadcrumbPage, { children: crumb.label }) }

            )] }, idx
          )
          )] }
        ) }
      ), /*#__PURE__*/



      _jsxs("div", { className: "flex items-start justify-between", children: [/*#__PURE__*/
        _jsxs("div", { className: "space-y-2", children: [/*#__PURE__*/
          _jsxs("h1", { className: "text-3xl font-bold tracking-tight flex items-center gap-3", children: [
            icon && /*#__PURE__*/_jsx("span", { className: "flex-shrink-0", children: icon }),
            title,
            badge && /*#__PURE__*/_jsx(Badge, { variant: badgeVariant, children: badge })] }
          ),
          description && /*#__PURE__*/
          _jsx("p", { className: "text-base text-muted-foreground max-w-3xl", children:
            description }
          )] }

        ),
        actions && /*#__PURE__*/_jsx("div", { className: "flex gap-2", children: actions })] }
      )] }
    ));

}


import { Link, useLocation } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { Button } from '@ui/button';
import { ScrollArea } from '@ui/scroll-area';
import { Badge } from '@ui/badge';
import { ModeToggle } from '@/components/mode-toggle';
import UserMenu from '@/components/auth/UserMenu';
import {
  LayoutDashboard,
  Search,
  Code,
  Terminal,
  FileText,
  GitBranch,
  Database,
  Activity,
  Zap } from
'lucide-react';import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";





const navigation = [
{ name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard, badge: null },
{ name: 'Advanced Search', href: '/search', icon: Search, badge: null },
{ name: 'REST API', href: '/api-explorer', icon: Code, badge: 'API' },
{ name: 'Query Editor', href: '/query-editor', icon: Terminal, badge: null },
{ name: 'Requirements', href: '/requirements', icon: FileText, badge: null },
{ name: 'Traceability', href: '/traceability', icon: GitBranch, badge: null },
{ name: 'PLM Integration', href: '/plm', icon: Database, badge: 'BETA' },
{ name: 'Monitoring', href: '/monitoring', icon: Activity, badge: null }];


export default function Layout({ children }) {
  const location = useLocation();

  return (/*#__PURE__*/
    _jsxs("div", { className: "flex h-screen bg-gradient-to-br from-background via-background to-muted/20", children: [/*#__PURE__*/

      _jsx("aside", { className: "w-64 border-r bg-card/50 backdrop-blur-xl shadow-lg", children: /*#__PURE__*/
        _jsxs("div", { className: "flex h-full flex-col", children: [/*#__PURE__*/

          _jsx("div", { className: "flex h-16 items-center border-b px-6 bg-gradient-to-r from-primary/10 to-primary/5", children: /*#__PURE__*/
            _jsxs("div", { className: "flex items-center gap-2", children: [/*#__PURE__*/
              _jsx("div", { className: "rounded-lg bg-primary p-1.5", children: /*#__PURE__*/
                _jsx(Database, { className: "h-5 w-5 text-primary-foreground" }) }
              ), /*#__PURE__*/
              _jsxs("div", { children: [/*#__PURE__*/
                _jsx("h1", { className: "text-base font-bold leading-tight", children: "MBSE-Led" }), /*#__PURE__*/
                _jsx("p", { className: "text-xs text-muted-foreground", children: "Simulation Collaboration" })] }
              )] }
            ) }
          ), /*#__PURE__*/


          _jsx(ScrollArea, { className: "flex-1 px-3 py-4", children: /*#__PURE__*/
            _jsx("nav", { className: "space-y-1", children:
              navigation.map((item) => {
                const isActive = location.pathname === item.href;
                return (/*#__PURE__*/
                  _jsx(Link, { to: item.href, children: /*#__PURE__*/
                    _jsxs(Button, {
                      variant: isActive ? 'secondary' : 'ghost',
                      className: cn(
                        'w-full justify-start group transition-all duration-200',
                        isActive && 'bg-primary text-primary-foreground shadow-md',
                        !isActive && 'hover:bg-muted hover:translate-x-1'
                      ), children: [/*#__PURE__*/

                      _jsx(item.icon, { className: cn(
                          "mr-2 h-4 w-4 transition-transform",
                          isActive && "scale-110"
                        ) }), /*#__PURE__*/
                      _jsx("span", { className: "flex-1 text-left", children: item.name }),
                      item.badge && /*#__PURE__*/
                      _jsx(Badge, { variant: "secondary", className: "ml-auto text-xs", children:
                        item.badge }
                      )] }

                    ) }, item.name
                  ));

              }) }
            ) }
          ), /*#__PURE__*/


          _jsx("div", { className: "border-t p-4 bg-muted/30", children: /*#__PURE__*/
            _jsxs("div", { className: "flex items-center justify-between", children: [/*#__PURE__*/
              _jsx("span", { className: "text-xs text-muted-foreground", children: "v2.0.0 \u2022 Phase 2" }), /*#__PURE__*/
              _jsxs("div", { className: "flex items-center gap-1", children: [/*#__PURE__*/
                _jsx("div", { className: "h-2 w-2 rounded-full bg-green-500 animate-pulse" }), /*#__PURE__*/
                _jsx("span", { className: "text-xs text-muted-foreground", children: "Live" })] }
              )] }
            ) }
          )] }
        ) }
      ), /*#__PURE__*/


      _jsxs("main", { className: "flex-1 overflow-y-auto", children: [/*#__PURE__*/

        _jsx("div", { className: "sticky top-0 z-10 border-b bg-background/80 backdrop-blur-md supports-[backdrop-filter]:bg-background/60 shadow-sm", children: /*#__PURE__*/
          _jsxs("div", { className: "container mx-auto flex h-16 items-center justify-between px-6", children: [/*#__PURE__*/
            _jsxs("div", { className: "flex items-center gap-3", children: [/*#__PURE__*/
              _jsx(Zap, { className: "h-5 w-5 text-primary animate-pulse" }), /*#__PURE__*/
              _jsxs("div", { children: [/*#__PURE__*/
                _jsx("div", { className: "text-sm font-medium", children: "MBSE-Led Simulation Engineering Collaboration" }), /*#__PURE__*/
                _jsx("div", { className: "text-xs text-muted-foreground", children: "Distributed Infrastructure \u2022 Multi-Tool Integration" })] }
              )] }
            ), /*#__PURE__*/
            _jsxs("div", { className: "flex items-center gap-4", children: [/*#__PURE__*/
              _jsx(ModeToggle, {}), /*#__PURE__*/
              _jsx(UserMenu, {})] }
            )] }
          ) }
        ), /*#__PURE__*/


        _jsx("div", { className: "container mx-auto p-6", children: /*#__PURE__*/
          _jsx("div", { className: "animate-in fade-in slide-in-from-bottom-4 duration-500", children:
            children }
          ) }
        )] }
      )] }
    ));

}

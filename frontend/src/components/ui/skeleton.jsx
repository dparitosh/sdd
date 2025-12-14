import { cn } from "@/lib/utils";import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";

function Skeleton({
  className,
  ...props
}) {
  return (/*#__PURE__*/
    _jsx("div", {
      className: cn("animate-pulse rounded-md bg-primary/10", className),
      role: "status",
      "aria-label": "Loading...", ...
      props }
    ));

}

export function TableSkeleton({ rows = 5 }) {
  return (/*#__PURE__*/
    _jsxs("div", { className: "space-y-4", role: "status", "aria-label": "Loading table data", children: [/*#__PURE__*/

      _jsx("div", { className: "flex gap-4 border-b pb-2", children:
        [1, 2, 3, 4].map((i) => /*#__PURE__*/
        _jsx(Skeleton, { className: "h-4 flex-1" }, i)
        ) }
      ),


      Array.from({ length: rows }).map((_, rowIndex) => /*#__PURE__*/
      _jsx("div", { className: "flex gap-4", children:
        [1, 2, 3, 4].map((colIndex) => /*#__PURE__*/
        _jsx(Skeleton, {

          className: "h-8 flex-1",
          style: { opacity: 1 - rowIndex * 0.1 } }, colIndex
        )
        ) }, rowIndex
      )
      )] }
    ));

}

export function CardSkeleton() {
  return (/*#__PURE__*/
    _jsxs("div", { className: "rounded-lg border p-6 space-y-4", role: "status", "aria-label": "Loading card", children: [/*#__PURE__*/
      _jsx(Skeleton, { className: "h-6 w-3/4" }), /*#__PURE__*/
      _jsx(Skeleton, { className: "h-4 w-full" }), /*#__PURE__*/
      _jsx(Skeleton, { className: "h-4 w-5/6" }), /*#__PURE__*/
      _jsxs("div", { className: "flex gap-2 pt-2", children: [/*#__PURE__*/
        _jsx(Skeleton, { className: "h-8 w-20" }), /*#__PURE__*/
        _jsx(Skeleton, { className: "h-8 w-20" })] }
      )] }
    ));

}

export function DashboardSkeleton() {
  return (/*#__PURE__*/
    _jsxs("div", { className: "space-y-6", role: "status", "aria-label": "Loading dashboard", children: [/*#__PURE__*/

      _jsx("div", { className: "grid gap-4 md:grid-cols-2 lg:grid-cols-4", children:
        [1, 2, 3, 4].map((i) => /*#__PURE__*/
        _jsxs("div", { className: "rounded-lg border p-6 space-y-2", children: [/*#__PURE__*/
          _jsx(Skeleton, { className: "h-4 w-24" }), /*#__PURE__*/
          _jsx(Skeleton, { className: "h-8 w-16" }), /*#__PURE__*/
          _jsx(Skeleton, { className: "h-3 w-32" })] }, i
        )
        ) }
      ), /*#__PURE__*/


      _jsxs("div", { className: "rounded-lg border p-6 space-y-4", children: [/*#__PURE__*/
        _jsx(Skeleton, { className: "h-6 w-48" }), /*#__PURE__*/
        _jsx(Skeleton, { className: "h-64 w-full" })] }
      ), /*#__PURE__*/


      _jsxs("div", { className: "rounded-lg border p-6 space-y-4", children: [/*#__PURE__*/
        _jsx(Skeleton, { className: "h-6 w-32" }), /*#__PURE__*/
        _jsx("div", { className: "space-y-3", children:
          [1, 2, 3].map((i) => /*#__PURE__*/
          _jsxs("div", { className: "flex items-center gap-4", children: [/*#__PURE__*/
            _jsx(Skeleton, { className: "h-10 w-10 rounded-full" }), /*#__PURE__*/
            _jsxs("div", { className: "flex-1 space-y-2", children: [/*#__PURE__*/
              _jsx(Skeleton, { className: "h-4 w-3/4" }), /*#__PURE__*/
              _jsx(Skeleton, { className: "h-3 w-1/2" })] }
            )] }, i
          )
          ) }
        )] }
      )] }
    ));

}

export function ListSkeleton({ items = 10 }) {
  return (/*#__PURE__*/
    _jsx("div", { className: "space-y-3", role: "status", "aria-label": "Loading list", children:
      Array.from({ length: items }).map((_, i) => /*#__PURE__*/
      _jsxs("div", { className: "flex items-center gap-4 p-4 rounded-lg border", children: [/*#__PURE__*/
        _jsx(Skeleton, { className: "h-12 w-12 rounded-full" }), /*#__PURE__*/
        _jsxs("div", { className: "flex-1 space-y-2", children: [/*#__PURE__*/
          _jsx(Skeleton, { className: "h-4 w-3/4" }), /*#__PURE__*/
          _jsx(Skeleton, { className: "h-3 w-1/2" })] }
        ), /*#__PURE__*/
        _jsx(Skeleton, { className: "h-8 w-24" })] }, i
      )
      ) }
    ));

}

export function GraphSkeleton() {
  return (/*#__PURE__*/
    _jsxs("div", { className: "space-y-4", role: "status", "aria-label": "Loading graph visualization", children: [/*#__PURE__*/
      _jsxs("div", { className: "flex items-center justify-between", children: [/*#__PURE__*/
        _jsx(Skeleton, { className: "h-8 w-48" }), /*#__PURE__*/
        _jsxs("div", { className: "flex gap-2", children: [/*#__PURE__*/
          _jsx(Skeleton, { className: "h-8 w-24" }), /*#__PURE__*/
          _jsx(Skeleton, { className: "h-8 w-24" })] }
        )] }
      ), /*#__PURE__*/
      _jsx("div", { className: "rounded-lg border p-6", children: /*#__PURE__*/
        _jsx(Skeleton, { className: "h-[500px] w-full" }) }
      ), /*#__PURE__*/
      _jsxs("div", { className: "flex gap-4", children: [/*#__PURE__*/
        _jsx(Skeleton, { className: "h-4 w-32" }), /*#__PURE__*/
        _jsx(Skeleton, { className: "h-4 w-32" }), /*#__PURE__*/
        _jsx(Skeleton, { className: "h-4 w-32" })] }
      )] }
    ));

}

export { Skeleton };

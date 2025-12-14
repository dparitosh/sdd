import * as React from 'react';
import * as ScrollAreaPrimitive from '@radix-ui/react-scroll-area';

import { cn } from '@/lib/utils';import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";

const ScrollArea = /*#__PURE__*/React.forwardRef(


  ({ className, children, ...props }, ref) => /*#__PURE__*/
  _jsxs(ScrollAreaPrimitive.Root, {
    ref: ref,
    className: cn('relative overflow-hidden', className), ...
    props, children: [/*#__PURE__*/

    _jsx(ScrollAreaPrimitive.Viewport, { className: "h-full w-full rounded-[inherit]", children:
      children }
    ), /*#__PURE__*/
    _jsx(ScrollBar, {}), /*#__PURE__*/
    _jsx(ScrollAreaPrimitive.Corner, {})] }
  )
);
ScrollArea.displayName = ScrollAreaPrimitive.Root.displayName;

const ScrollBar = /*#__PURE__*/React.forwardRef(


  ({ className, orientation = 'vertical', ...props }, ref) => /*#__PURE__*/
  _jsx(ScrollAreaPrimitive.ScrollAreaScrollbar, {
    ref: ref,
    orientation: orientation,
    className: cn(
      'flex touch-none select-none transition-colors',
      orientation === 'vertical' &&
      'h-full w-2.5 border-l border-l-transparent p-[1px]',
      orientation === 'horizontal' &&
      'h-2.5 flex-col border-t border-t-transparent p-[1px]',
      className
    ), ...
    props, children: /*#__PURE__*/

    _jsx(ScrollAreaPrimitive.ScrollAreaThumb, { className: "relative flex-1 rounded-full bg-border" }) }
  )
);
ScrollBar.displayName = ScrollAreaPrimitive.ScrollAreaScrollbar.displayName;

export { ScrollArea, ScrollBar };

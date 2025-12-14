import * as React from "react";
import * as SelectPrimitive from "@radix-ui/react-select";
import { Check, ChevronDown, ChevronUp } from "lucide-react";

import { cn } from "@/lib/utils";import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";

const Select = SelectPrimitive.Root;

const SelectGroup = SelectPrimitive.Group;

const SelectValue = SelectPrimitive.Value;

const SelectTrigger = /*#__PURE__*/React.forwardRef(


  ({ className, children, ...props }, ref) => /*#__PURE__*/
  _jsxs(SelectPrimitive.Trigger, {
    ref: ref,
    className: cn(
      "flex h-10 w-full items-center justify-between whitespace-nowrap rounded-md border border-input bg-background px-3 py-2 text-sm font-medium shadow-sm ring-offset-background transition-colors hover:bg-accent hover:text-accent-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 [&>span]:line-clamp-1 data-[placeholder]:text-muted-foreground",
      className
    ), ...
    props, children: [

    children, /*#__PURE__*/
    _jsx(SelectPrimitive.Icon, { asChild: true, children: /*#__PURE__*/
      _jsx(ChevronDown, { className: "h-4 w-4 opacity-50 transition-transform duration-200 data-[state=open]:rotate-180" }) }
    )] }
  )
);
SelectTrigger.displayName = SelectPrimitive.Trigger.displayName;

const SelectScrollUpButton = /*#__PURE__*/React.forwardRef(


  ({ className, ...props }, ref) => /*#__PURE__*/
  _jsx(SelectPrimitive.ScrollUpButton, {
    ref: ref,
    className: cn(
      "flex cursor-default items-center justify-center py-1",
      className
    ), ...
    props, children: /*#__PURE__*/

    _jsx(ChevronUp, { className: "h-4 w-4" }) }
  )
);
SelectScrollUpButton.displayName = SelectPrimitive.ScrollUpButton.displayName;

const SelectScrollDownButton = /*#__PURE__*/React.forwardRef(


  ({ className, ...props }, ref) => /*#__PURE__*/
  _jsx(SelectPrimitive.ScrollDownButton, {
    ref: ref,
    className: cn(
      "flex cursor-default items-center justify-center py-1",
      className
    ), ...
    props, children: /*#__PURE__*/

    _jsx(ChevronDown, { className: "h-4 w-4" }) }
  )
);
SelectScrollDownButton.displayName =
SelectPrimitive.ScrollDownButton.displayName;

const SelectContent = /*#__PURE__*/React.forwardRef(


  ({ className, children, position = "popper", ...props }, ref) => /*#__PURE__*/
  _jsx(SelectPrimitive.Portal, { children: /*#__PURE__*/
    _jsxs(SelectPrimitive.Content, {
      ref: ref,
      className: cn(
        "relative z-[100] max-h-96 min-w-[8rem] overflow-hidden rounded-lg border-2 border-border bg-card backdrop-blur-sm text-foreground shadow-corporate-xl data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2 data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2",
        position === "popper" &&
        "data-[side=bottom]:translate-y-1 data-[side=left]:-translate-x-1 data-[side=right]:translate-x-1 data-[side=top]:-translate-y-1",
        className
      ),
      position: position, ...
      props, children: [/*#__PURE__*/

      _jsx(SelectScrollUpButton, {}), /*#__PURE__*/
      _jsx(SelectPrimitive.Viewport, {
        className: cn(
          "p-2 max-h-[var(--radix-select-content-available-height)] bg-card",
          position === "popper" &&
          "h-[var(--radix-select-trigger-height)] w-full min-w-[var(--radix-select-trigger-width)]"
        ), children:

        children }
      ), /*#__PURE__*/
      _jsx(SelectScrollDownButton, {})] }
    ) }
  )
);
SelectContent.displayName = SelectPrimitive.Content.displayName;

const SelectLabel = /*#__PURE__*/React.forwardRef(


  ({ className, ...props }, ref) => /*#__PURE__*/
  _jsx(SelectPrimitive.Label, {
    ref: ref,
    className: cn("px-2 py-1.5 text-sm font-semibold", className), ...
    props }
  )
);
SelectLabel.displayName = SelectPrimitive.Label.displayName;

const SelectItem = /*#__PURE__*/React.forwardRef(


  ({ className, children, ...props }, ref) => /*#__PURE__*/
  _jsxs(SelectPrimitive.Item, {
    ref: ref,
    className: cn(
      "relative flex w-full cursor-pointer select-none items-center rounded-md py-3 pl-4 pr-12 text-sm font-medium outline-none transition-all hover:bg-accent hover:text-accent-foreground focus:bg-accent focus:text-accent-foreground data-[disabled]:pointer-events-none data-[disabled]:opacity-50 data-[state=checked]:bg-primary/15 data-[state=checked]:text-primary data-[state=checked]:font-semibold hover:pl-5 my-0.5",
      className
    ), ...
    props, children: [/*#__PURE__*/

    _jsx("span", { className: "absolute right-4 flex h-5 w-5 items-center justify-center", children: /*#__PURE__*/
      _jsx(SelectPrimitive.ItemIndicator, { children: /*#__PURE__*/
        _jsx(Check, { className: "h-5 w-5 text-primary" }) }
      ) }
    ), /*#__PURE__*/
    _jsx(SelectPrimitive.ItemText, { children: children })] }
  )
);
SelectItem.displayName = SelectPrimitive.Item.displayName;

const SelectSeparator = /*#__PURE__*/React.forwardRef(


  ({ className, ...props }, ref) => /*#__PURE__*/
  _jsx(SelectPrimitive.Separator, {
    ref: ref,
    className: cn("-mx-1 my-1 h-px bg-muted", className), ...
    props }
  )
);
SelectSeparator.displayName = SelectPrimitive.Separator.displayName;

export {
  Select,
  SelectGroup,
  SelectValue,
  SelectTrigger,
  SelectContent,
  SelectLabel,
  SelectItem,
  SelectSeparator,
  SelectScrollUpButton,
  SelectScrollDownButton };

import * as React from "react";

import { Command as CommandPrimitive } from "cmdk";
import { Search } from "lucide-react";

import { cn } from "@/lib/utils";
import { Dialog, DialogContent } from "@ui/dialog";import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";

const Command = /*#__PURE__*/React.forwardRef(


  ({ className, ...props }, ref) => /*#__PURE__*/
  _jsx(CommandPrimitive, {
    ref: ref,
    className: cn(
      "flex h-full w-full flex-col overflow-hidden rounded-md bg-popover text-popover-foreground",
      className
    ), ...
    props }
  )
);
Command.displayName = CommandPrimitive.displayName;



const CommandDialog = ({ children, ...props }) => {
  return (/*#__PURE__*/
    _jsx(Dialog, { ...props, children: /*#__PURE__*/
      _jsx(DialogContent, { className: "overflow-hidden p-0 shadow-lg", children: /*#__PURE__*/
        _jsx(Command, { className: "[&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:text-muted-foreground [&_[cmdk-group]:not([hidden])_~[cmdk-group]]:pt-0 [&_[cmdk-group]]:px-2 [&_[cmdk-input-wrapper]_svg]:h-5 [&_[cmdk-input-wrapper]_svg]:w-5 [&_[cmdk-input]]:h-12 [&_[cmdk-item]]:px-2 [&_[cmdk-item]]:py-3 [&_[cmdk-item]_svg]:h-5 [&_[cmdk-item]_svg]:w-5", children:
          children }
        ) }
      ) }
    ));

};

const CommandInput = /*#__PURE__*/React.forwardRef(


  ({ className, ...props }, ref) => /*#__PURE__*/
  _jsxs("div", { className: "flex items-center border-b px-3", "cmdk-input-wrapper": "", children: [/*#__PURE__*/
    _jsx(Search, { className: "mr-2 h-4 w-4 shrink-0 opacity-50" }), /*#__PURE__*/
    _jsx(CommandPrimitive.Input, {
      ref: ref,
      className: cn(
        "flex h-11 w-full rounded-md bg-transparent py-3 text-sm outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50",
        className
      ), ...
      props }
    )] }
  )
);

CommandInput.displayName = CommandPrimitive.Input.displayName;

const CommandList = /*#__PURE__*/React.forwardRef(


  ({ className, ...props }, ref) => /*#__PURE__*/
  _jsx(CommandPrimitive.List, {
    ref: ref,
    className: cn("max-h-[300px] overflow-y-auto overflow-x-hidden", className), ...
    props }
  )
);

CommandList.displayName = CommandPrimitive.List.displayName;

const CommandEmpty = /*#__PURE__*/React.forwardRef(


  (props, ref) => /*#__PURE__*/
  _jsx(CommandPrimitive.Empty, {
    ref: ref,
    className: "py-6 text-center text-sm", ...
    props }
  )
);

CommandEmpty.displayName = CommandPrimitive.Empty.displayName;

const CommandGroup = /*#__PURE__*/React.forwardRef(


  ({ className, ...props }, ref) => /*#__PURE__*/
  _jsx(CommandPrimitive.Group, {
    ref: ref,
    className: cn(
      "overflow-hidden p-1 text-foreground [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:text-muted-foreground",
      className
    ), ...
    props }
  )
);

CommandGroup.displayName = CommandPrimitive.Group.displayName;

const CommandSeparator = /*#__PURE__*/React.forwardRef(


  ({ className, ...props }, ref) => /*#__PURE__*/
  _jsx(CommandPrimitive.Separator, {
    ref: ref,
    className: cn("-mx-1 h-px bg-border", className), ...
    props }
  )
);
CommandSeparator.displayName = CommandPrimitive.Separator.displayName;

const CommandItem = /*#__PURE__*/React.forwardRef(


  ({ className, ...props }, ref) => /*#__PURE__*/
  _jsx(CommandPrimitive.Item, {
    ref: ref,
    className: cn(
      "relative flex cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none aria-selected:bg-accent aria-selected:text-accent-foreground data-[disabled]:pointer-events-none data-[disabled]:opacity-50",
      className
    ), ...
    props }
  )
);

CommandItem.displayName = CommandPrimitive.Item.displayName;

const CommandShortcut = ({
  className,
  ...props
}) => {
  return (/*#__PURE__*/
    _jsx("span", {
      className: cn(
        "ml-auto text-xs tracking-widest text-muted-foreground",
        className
      ), ...
      props }
    ));

};
CommandShortcut.displayName = "CommandShortcut";

export {
  Command,
  CommandDialog,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandGroup,
  CommandItem,
  CommandSeparator,
  CommandShortcut };

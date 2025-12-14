import * as React from "react";
import * as AvatarPrimitive from "@radix-ui/react-avatar";

import { cn } from "@/lib/utils";import { jsx as _jsx } from "react/jsx-runtime";

const Avatar = /*#__PURE__*/React.forwardRef(


  ({ className, ...props }, ref) => /*#__PURE__*/
  _jsx(AvatarPrimitive.Root, {
    ref: ref,
    className: cn(
      "relative flex h-10 w-10 shrink-0 overflow-hidden rounded-full",
      className
    ), ...
    props }
  )
);
Avatar.displayName = AvatarPrimitive.Root.displayName;

const AvatarImage = /*#__PURE__*/React.forwardRef(


  ({ className, ...props }, ref) => /*#__PURE__*/
  _jsx(AvatarPrimitive.Image, {
    ref: ref,
    className: cn("aspect-square h-full w-full", className), ...
    props }
  )
);
AvatarImage.displayName = AvatarPrimitive.Image.displayName;

const AvatarFallback = /*#__PURE__*/React.forwardRef(


  ({ className, ...props }, ref) => /*#__PURE__*/
  _jsx(AvatarPrimitive.Fallback, {
    ref: ref,
    className: cn(
      "flex h-full w-full items-center justify-center rounded-full bg-muted",
      className
    ), ...
    props }
  )
);
AvatarFallback.displayName = AvatarPrimitive.Fallback.displayName;

export { Avatar, AvatarImage, AvatarFallback };

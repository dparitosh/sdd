import * as React from "react";
import * as LabelPrimitive from "@radix-ui/react-label";
import { cva } from "class-variance-authority";

import { cn } from "@/lib/utils";import { jsx as _jsx } from "react/jsx-runtime";

const labelVariants = cva(
  "text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
);

const Label = /*#__PURE__*/React.forwardRef(



  ({ className, ...props }, ref) => /*#__PURE__*/
  _jsx(LabelPrimitive.Root, {
    ref: ref,
    className: cn(labelVariants(), className), ...
    props }
  )
);
Label.displayName = LabelPrimitive.Root.displayName;

export { Label };

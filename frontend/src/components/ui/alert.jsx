import * as React from "react";
import { cva } from "class-variance-authority";

import { cn } from "@/lib/utils";import { jsx as _jsx } from "react/jsx-runtime";

const alertVariants = cva(
  "relative w-full rounded-lg border px-4 py-3 text-sm [&>svg+div]:translate-y-[-3px] [&>svg]:absolute [&>svg]:left-4 [&>svg]:top-4 [&>svg]:text-foreground [&>svg~*]:pl-7",
  {
    variants: {
      variant: {
        default: "bg-background text-foreground",
        destructive:
        "border-destructive/50 text-destructive dark:border-destructive [&>svg]:text-destructive"
      }
    },
    defaultVariants: {
      variant: "default"
    }
  }
);

const Alert = /*#__PURE__*/React.forwardRef(


  ({ className, variant, ...props }, ref) => /*#__PURE__*/
  _jsx("div", {
    ref: ref,
    role: "alert",
    className: cn(alertVariants({ variant }), className), ...
    props }
  )
);
Alert.displayName = "Alert";

const AlertTitle = /*#__PURE__*/React.forwardRef(


  ({ className, ...props }, ref) => /*#__PURE__*/
  _jsx("h5", {
    ref: ref,
    className: cn("mb-1 font-medium leading-none tracking-tight", className), ...
    props }
  )
);
AlertTitle.displayName = "AlertTitle";

const AlertDescription = /*#__PURE__*/React.forwardRef(


  ({ className, ...props }, ref) => /*#__PURE__*/
  _jsx("div", {
    ref: ref,
    className: cn("text-sm [&_p]:leading-relaxed", className), ...
    props }
  )
);
AlertDescription.displayName = "AlertDescription";

export { Alert, AlertTitle, AlertDescription };

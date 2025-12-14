import * as React from "react";
import { ChevronRight } from "lucide-react";
import { Link } from "react-router-dom";
import { cn } from "@/lib/utils";import { jsx as _jsx } from "react/jsx-runtime";

const Breadcrumb = /*#__PURE__*/React.forwardRef(


  ({ className, ...props }, ref) => /*#__PURE__*/
  _jsx("nav", {
    ref: ref,
    "aria-label": "breadcrumb",
    className: cn("flex items-center space-x-2 text-sm", className), ...
    props }
  )
);
Breadcrumb.displayName = "Breadcrumb";

const BreadcrumbList = /*#__PURE__*/React.forwardRef(


  ({ className, ...props }, ref) => /*#__PURE__*/
  _jsx("ol", {
    ref: ref,
    className: cn("flex items-center space-x-2", className), ...
    props }
  )
);
BreadcrumbList.displayName = "BreadcrumbList";

const BreadcrumbItem = /*#__PURE__*/React.forwardRef(


  ({ className, ...props }, ref) => /*#__PURE__*/
  _jsx("li", {
    ref: ref,
    className: cn("inline-flex items-center", className), ...
    props }
  )
);
BreadcrumbItem.displayName = "BreadcrumbItem";

const BreadcrumbLink = /*#__PURE__*/React.forwardRef(


  ({ className, ...props }, ref) => /*#__PURE__*/
  _jsx(Link, {
    ref: ref,
    className: cn("text-muted-foreground hover:text-foreground transition-colors", className), ...
    props }
  )
);
BreadcrumbLink.displayName = "BreadcrumbLink";

const BreadcrumbPage = /*#__PURE__*/React.forwardRef(


  ({ className, ...props }, ref) => /*#__PURE__*/
  _jsx("span", {
    ref: ref,
    role: "link",
    "aria-disabled": "true",
    "aria-current": "page",
    className: cn("font-medium text-foreground", className), ...
    props }
  )
);
BreadcrumbPage.displayName = "BreadcrumbPage";

const BreadcrumbSeparator = ({
  children,
  className,
  ...props
}) => /*#__PURE__*/
_jsx("li", {
  role: "presentation",
  "aria-hidden": "true",
  className: cn("[&>svg]:size-3.5", className), ...
  props, children:

  children ?? /*#__PURE__*/_jsx(ChevronRight, {}) }
);

BreadcrumbSeparator.displayName = "BreadcrumbSeparator";

export {
  Breadcrumb,
  BreadcrumbList,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbPage,
  BreadcrumbSeparator };

import * as React from "react";
import { ChevronRight } from "lucide-react";
import { Link } from "react-router-dom";
import { cn } from "@/lib/utils";
const Breadcrumb = React.forwardRef(({
  className,
  ...props
}, ref) => <nav ref={ref} aria-label="breadcrumb" className={cn("flex items-center space-x-2 text-sm", className)} {...props} />);
Breadcrumb.displayName = "Breadcrumb";
const BreadcrumbList = React.forwardRef(({
  className,
  ...props
}, ref) => <ol ref={ref} className={cn("flex items-center space-x-2", className)} {...props} />);
BreadcrumbList.displayName = "BreadcrumbList";
const BreadcrumbItem = React.forwardRef(({
  className,
  ...props
}, ref) => <li ref={ref} className={cn("inline-flex items-center", className)} {...props} />);
BreadcrumbItem.displayName = "BreadcrumbItem";
const BreadcrumbLink = React.forwardRef(({
  className,
  ...props
}, ref) => <Link ref={ref} className={cn("text-muted-foreground hover:text-foreground transition-colors", className)} {...props} />);
BreadcrumbLink.displayName = "BreadcrumbLink";
const BreadcrumbPage = React.forwardRef(({
  className,
  ...props
}, ref) => <span ref={ref} role="link" aria-disabled="true" aria-current="page" className={cn("font-medium text-foreground", className)} {...props} />);
BreadcrumbPage.displayName = "BreadcrumbPage";
const BreadcrumbSeparator = ({
  children,
  className,
  ...props
}) => <li role="presentation" aria-hidden="true" className={cn("[&>svg]:size-3.5", className)} {...props}>{children ?? <ChevronRight />}</li>;
BreadcrumbSeparator.displayName = "BreadcrumbSeparator";
export { Breadcrumb, BreadcrumbList, BreadcrumbItem, BreadcrumbLink, BreadcrumbPage, BreadcrumbSeparator };

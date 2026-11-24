/**
 * 组件库统一出口：所有桌面组件在同一处定义（补充单 4-3 组件一致性验收）。
 * 页面一律从这里导入，保证视觉与行为一致。
 */
export { Button, type ButtonProps, type ButtonVariant, type ButtonSize } from "./Button";
export { Card, CardHeader, CardBody, CardFooter, type CardProps } from "./Card";
export { Panel, type PanelProps } from "./Panel";
export { Table, type TableProps, type TableColumn } from "./Table";
export { StatusBadge, statusKindLabel, type StatusBadgeProps, type StatusKind } from "./StatusBadge";
export { Sidebar, type SidebarProps, type SidebarItem } from "./Sidebar";
export { Breadcrumbs, type BreadcrumbsProps, type BreadcrumbItem } from "./Breadcrumbs";
export { Dialog, type DialogProps } from "./Dialog";
export { Drawer, type DrawerProps } from "./Drawer";
export { Tabs, type TabsProps, type TabItem } from "./Tabs";
export { Input, type InputProps } from "./Input";
export { SearchInput, type SearchInputProps } from "./SearchInput";
export { EmptyState, type EmptyStateProps } from "./states/EmptyState";
export { ErrorState, type ErrorStateProps } from "./states/ErrorState";
export { LoadingState, type LoadingStateProps } from "./states/LoadingState";
export { PartialBanner, type PartialBannerProps, type PartialBannerTone } from "./PartialBanner";
export { Timeline, type TimelineProps, type TimelineItem, type TimelineItemStatus } from "./Timeline";
export { SourcePreview, type SourcePreviewProps } from "./SourcePreview";
export { DragDropUploader, type DragDropUploaderProps } from "./DragDropUploader";
export { MetricCard, type MetricCardProps } from "./MetricCard";
export { useDismissable, useFocusTrap, type DismissableOptions } from "./useDismissable";

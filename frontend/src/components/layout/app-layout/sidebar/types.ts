import React from "react";

export type MenuType = "main" | "support" | "others";

export interface SubItem {
  key: string;
  path: string;
  pro?: boolean;
  new?: boolean;
  target?: string;
}

export interface NavItem {
  key: string;
  icon: React.ReactNode;
  path?: string;
  new?: boolean;
  target?: string;
  subItems?: SubItem[];
  /** Hidden for non-admins (the API enforces the same rule). */
  adminOnly?: boolean;
  /** Red count bubble, e.g. account requests waiting for an admin. */
  badgeCount?: number;
}

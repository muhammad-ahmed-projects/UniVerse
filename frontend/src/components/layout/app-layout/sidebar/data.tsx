import {
  BoxIcon,
  CameraIcon,
  GearIcon,
  LayoutGridIcon,
  OctagonAlertIcon,
  UsersIcon,
  VideoIcon,
} from "@/icons";
import type { NavItem } from "./types";

export const navItems: NavItem[] = [
  {
    icon: <LayoutGridIcon className="size-6" />,
    key: "dashboard",
    path: "/",
  },
  {
    icon: <VideoIcon className="size-6" />,
    key: "surveillanceLive",
    path: "/live",
  },
  {
    icon: <CameraIcon className="size-6" />,
    key: "surveillanceCameras",
    path: "/cameras",
  },
  {
    icon: <BoxIcon className="size-6" />,
    key: "surveillanceAlerts",
    path: "/surveillance-alerts",
  },
  {
    icon: <OctagonAlertIcon className="size-6" />,
    key: "surveillanceIncidents",
    path: "/incidents",
  },
  {
    icon: <UsersIcon className="size-6" />,
    key: "surveillancePeople",
    path: "/people",
  },
  {
    icon: <GearIcon className="size-6" />,
    key: "surveillanceSettings",
    path: "/settings",
  },
];

export const othersItems: NavItem[] = [];

export const supportItems: NavItem[] = [];

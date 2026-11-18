import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown";
import { useAuth } from "@/contexts";
import { useTranslations } from "@/i18n";
import {
  ChevronDownIcon,
  LogOutIcon,
  UserCircleIcon,
  UsersIcon,
} from "@/icons";
import { ROLE_LABELS } from "@/services";
import { cn } from "@/utils";
import { useState } from "react";
import { useNavigate } from "react-router";

export default function UserDropdown() {
  const t = useTranslations("userDropdown");
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = useState(false);
  const { user, logout } = useAuth();

  const go = (path: string) => {
    setIsOpen(false);
    void navigate(path);
  };

  const handleSignOut = () => {
    setIsOpen(false);
    logout();
    void navigate("/signin");
  };

  return (
    <DropdownMenu open={isOpen} onOpenChange={setIsOpen}>
      <DropdownMenuTrigger className="dropdown-toggle flex items-center text-gray-700 dark:text-gray-400">
        <span
          aria-hidden="true"
          className="me-3 flex size-11 items-center justify-center rounded-lg bg-brand-50 text-sm font-semibold text-brand-600 uppercase dark:bg-brand-500/15 dark:text-brand-400"
        >
          {user?.username.slice(0, 2) ?? ""}
        </span>

        <span className="me-1 block text-sm font-medium">
          {user?.username ?? "..."}
        </span>

        <ChevronDownIcon
          className={cn(
            "size-5 text-gray-500 duration-200 dark:text-gray-400",
            isOpen ? "rotate-180" : "rotate-0",
          )}
        />
      </DropdownMenuTrigger>

      <DropdownMenuContent align="end" sideOffset={12} className="w-65 p-3">
        <div className="px-3 py-2">
          <span className="block text-sm font-medium text-gray-700 dark:text-gray-400">
            {user?.username}
          </span>
          <span className="mt-0.5 block text-xs text-gray-500 dark:text-gray-400">
            {user ? (user.email ?? ROLE_LABELS[user.role]) : ""}
          </span>
        </div>

        <DropdownMenuSeparator />

        <DropdownMenuItem onClick={() => go("/profile")}>
          <UserCircleIcon className="size-6" />
          {t("profile")}
        </DropdownMenuItem>
        {user?.role === "admin" && (
          <DropdownMenuItem onClick={() => go("/users")}>
            <UsersIcon className="size-6" />
            {t("manageUsers")}
          </DropdownMenuItem>
        )}

        <DropdownMenuSeparator />

        <DropdownMenuItem variant="destructive" onClick={handleSignOut}>
          <LogOutIcon />
          {t("signOut")}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

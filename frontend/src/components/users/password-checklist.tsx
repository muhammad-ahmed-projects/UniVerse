import { CheckIcon, XIcon } from "@/icons";
import { PASSWORD_RULES } from "@/services";
import { cn } from "@/utils";

/** Live list of the strong-password rules, ticked off as the user types. */
export function PasswordChecklist({ password }: { password: string }) {
  return (
    <ul className="grid gap-1 text-xs sm:grid-cols-2" aria-live="polite">
      {PASSWORD_RULES.map((rule) => {
        const ok = rule.test(password);
        return (
          <li
            key={rule.label}
            className={cn(
              "flex items-center gap-1.5",
              ok
                ? "text-green-600 dark:text-green-400"
                : "text-gray-400 dark:text-gray-500",
            )}
          >
            {ok ? (
              <CheckIcon className="size-3.5 shrink-0" />
            ) : (
              <XIcon className="size-3.5 shrink-0" />
            )}
            <span>{rule.label}</span>
            <span className="sr-only">{ok ? "(done)" : "(missing)"}</span>
          </li>
        );
      })}
    </ul>
  );
}

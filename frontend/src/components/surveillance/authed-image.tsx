import { Skeleton } from "@/components/ui/skeleton";
import { useAuthedImage } from "@/hooks/use-authed-image";
import { cn } from "@/utils";

/** <img> for a protected API image path (evidence, face photo). */
export function AuthedImage({
  path,
  alt,
  className,
}: {
  path: string;
  alt: string;
  className?: string;
}) {
  const image = useAuthedImage(path);
  if (image.status === "loading") {
    return <Skeleton className={cn("rounded-lg", className)} />;
  }
  if (image.status === "error") {
    return (
      <div
        className={cn(
          "flex items-center justify-center rounded-lg bg-gray-100 text-xs text-gray-400 dark:bg-white/5",
          className,
        )}
      >
        Unavailable
      </div>
    );
  }
  return <img src={image.src} alt={alt} className={className} />;
}

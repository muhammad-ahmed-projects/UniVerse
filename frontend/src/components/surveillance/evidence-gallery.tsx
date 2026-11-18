import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ChevronLeftIcon, ChevronRightIcon } from "@/icons";
import { type AlertImage, alertImagePath } from "@/services";
import { useState } from "react";
import { AuthedImage } from "./authed-image";

const MAX_THUMBNAILS = 3;

/** Thumbnail strip of an alert's/incident's evidence; click opens a viewer. */
export function EvidenceThumbnails({
  images,
  title,
}: {
  images: AlertImage[];
  title: string;
}) {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  if (images.length === 0) {
    return (
      <span className="text-xs text-gray-400 dark:text-gray-500">
        No images
      </span>
    );
  }

  const extra = images.length - MAX_THUMBNAILS;
  return (
    <>
      <div className="flex items-center gap-1.5">
        {images.slice(0, MAX_THUMBNAILS).map((image, i) => (
          <button
            key={image.id}
            type="button"
            onClick={() => setOpenIndex(i)}
            className="overflow-hidden rounded-md ring-brand-500 outline-none hover:ring-2 focus-visible:ring-2"
            aria-label={`Open evidence image ${i + 1} of ${images.length}`}
          >
            <AuthedImage
              path={alertImagePath(image)}
              alt={`Evidence ${i + 1}`}
              className="h-10 w-14 object-cover"
            />
          </button>
        ))}
        {extra > 0 && (
          <button
            type="button"
            onClick={() => setOpenIndex(MAX_THUMBNAILS)}
            className="text-xs font-medium text-brand-500 hover:underline"
          >
            +{extra}
          </button>
        )}
      </div>
      <EvidenceViewer
        images={images}
        title={title}
        index={openIndex}
        onIndexChange={setOpenIndex}
      />
    </>
  );
}

function EvidenceViewer({
  images,
  title,
  index,
  onIndexChange,
}: {
  images: AlertImage[];
  title: string;
  index: number | null;
  onIndexChange: (index: number | null) => void;
}) {
  const current = index === null ? null : images[index];
  return (
    <Dialog
      open={current != null}
      onOpenChange={(open) => {
        if (!open) onIndexChange(null);
      }}
    >
      <DialogContent className="max-w-[calc(100%-2rem)] sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          {current && index !== null && (
            <DialogDescription>
              Image {index + 1} of {images.length} · captured{" "}
              {new Date(current.captured_at).toLocaleString()}
            </DialogDescription>
          )}
        </DialogHeader>
        {current && index !== null && (
          <div className="space-y-3">
            <AuthedImage
              path={alertImagePath(current)}
              alt={`Evidence ${index + 1} of ${images.length}`}
              className="aspect-video w-full rounded-lg bg-black object-contain"
            />
            {images.length > 1 && (
              <div className="flex items-center justify-between">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={index === 0}
                  onClick={() => onIndexChange(index - 1)}
                >
                  <ChevronLeftIcon />
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={index === images.length - 1}
                  onClick={() => onIndexChange(index + 1)}
                >
                  Next
                  <ChevronRightIcon />
                </Button>
              </div>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

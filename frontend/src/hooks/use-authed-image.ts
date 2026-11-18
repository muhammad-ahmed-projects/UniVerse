import { useEffect, useState } from "react";
import { apiClient } from "@/services";

type AuthedImage =
  | { status: "loading"; src: null }
  | { status: "ready"; src: string }
  | { status: "error"; src: null };

/** Loads a protected image (evidence, face photo) with the bearer token and
 * returns an object URL for an <img>, released on unmount or path change. */
export function useAuthedImage(path: string): AuthedImage {
  const [state, setState] = useState<{ path: string; image: AuthedImage }>({
    path,
    image: { status: "loading", src: null },
  });

  useEffect(() => {
    let url: string | null = null;
    let cancelled = false;
    apiClient
      .getBlob(path)
      .then((blob) => {
        if (cancelled) return;
        url = URL.createObjectURL(blob);
        setState({ path, image: { status: "ready", src: url } });
      })
      .catch(() => {
        if (!cancelled)
          setState({ path, image: { status: "error", src: null } });
      });
    return () => {
      cancelled = true;
      if (url) URL.revokeObjectURL(url);
    };
  }, [path]);

  // A new path shows "loading" right away instead of the previous image.
  return state.path === path ? state.image : { status: "loading", src: null };
}

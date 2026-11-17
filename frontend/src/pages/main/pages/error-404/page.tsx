import { PageMeta } from "@/components/shared/page-meta";
import Error404 from "./index";

export default function Error404Page() {
  return (
    <div>
      <PageMeta
        title="Page Not Found | UniVerse"
        description="The requested page does not exist"
      />
      <Error404 />
    </div>
  );
}

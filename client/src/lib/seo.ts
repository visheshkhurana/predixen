import { useEffect } from "react";

type SEOProps = {
  title: string;
  description?: string;
  jsonLd?: object;
};

export function useSEO({ title, description, jsonLd }: SEOProps) {
  useEffect(() => {
    document.title = title;

    const head = document.querySelector("head");
    if (!head) return;

    let descTag = document.querySelector('meta[name="description"]') as HTMLMetaElement | null;
    if (!descTag) {
      descTag = document.createElement("meta");
      descTag.setAttribute("name", "description");
      head.appendChild(descTag);
    }
    if (description) descTag.setAttribute("content", description);

    let ogTitle = document.querySelector('meta[property="og:title"]') as HTMLMetaElement | null;
    if (!ogTitle) {
      ogTitle = document.createElement("meta");
      ogTitle.setAttribute("property", "og:title");
      head.appendChild(ogTitle);
    }
    ogTitle.setAttribute("content", title);

    if (description) {
      let ogDesc = document.querySelector('meta[property="og:description"]') as HTMLMetaElement | null;
      if (!ogDesc) {
        ogDesc = document.createElement("meta");
        ogDesc.setAttribute("property", "og:description");
        head.appendChild(ogDesc);
      }
      ogDesc.setAttribute("content", description);
    }

    let ldTag = document.querySelector("#seo-jsonld") as HTMLScriptElement | null;
    if (jsonLd) {
      if (!ldTag) {
        ldTag = document.createElement("script");
        ldTag.id = "seo-jsonld";
        ldTag.type = "application/ld+json";
        head.appendChild(ldTag);
      }
      ldTag.text = JSON.stringify(jsonLd);
    } else if (ldTag) {
      head.removeChild(ldTag);
    }

    return () => {};
  }, [title, description, jsonLd]);
}

import { useEffect } from "react";

const SITE_URL = "https://founderconsole.ai";
const TWITTER_HANDLE = "@founderconsole";

type SEOProps = {
  title: string;
  description?: string;
  path?: string;
  ogType?: string;
  robots?: string;
  jsonLd?: object;
  articleMeta?: {
    publishedTime?: string;
    author?: string;
  };
};

function setOrCreateMeta(attr: string, key: string, content: string) {
  let el = document.querySelector(`meta[${attr}="${key}"]`) as HTMLMetaElement | null;
  if (!el) {
    el = document.createElement("meta");
    el.setAttribute(attr, key);
    document.head.appendChild(el);
  }
  el.setAttribute("content", content);
}

function setOrCreateLink(rel: string, href: string) {
  let el = document.querySelector(`link[rel="${rel}"]`) as HTMLLinkElement | null;
  if (!el) {
    el = document.createElement("link");
    el.setAttribute("rel", rel);
    document.head.appendChild(el);
  }
  el.setAttribute("href", href);
}

export function useSEO({ title, description, path, ogType, robots, jsonLd, articleMeta }: SEOProps) {
  useEffect(() => {
    document.title = title;

    if (description) {
      setOrCreateMeta("name", "description", description);
    }

    setOrCreateMeta("property", "og:title", title);
    if (description) {
      setOrCreateMeta("property", "og:description", description);
    }

    const fullUrl = path ? `${SITE_URL}${path}` : SITE_URL;
    setOrCreateLink("canonical", fullUrl);
    setOrCreateMeta("property", "og:url", fullUrl);

    setOrCreateMeta("property", "og:type", ogType || "website");

    setOrCreateMeta("name", "robots", robots || "index, follow");

    setOrCreateMeta("name", "twitter:site", TWITTER_HANDLE);

    if (articleMeta?.publishedTime) {
      setOrCreateMeta("property", "article:published_time", articleMeta.publishedTime);
    }
    if (articleMeta?.author) {
      setOrCreateMeta("property", "article:author", articleMeta.author);
    }

    let ldTag = document.querySelector("#seo-jsonld") as HTMLScriptElement | null;
    if (jsonLd) {
      if (!ldTag) {
        ldTag = document.createElement("script");
        ldTag.id = "seo-jsonld";
        ldTag.type = "application/ld+json";
        document.head.appendChild(ldTag);
      }
      ldTag.text = JSON.stringify(jsonLd);
    } else if (ldTag) {
      document.head.removeChild(ldTag);
    }

    return () => {
      const articleTime = document.querySelector('meta[property="article:published_time"]');
      if (articleTime) articleTime.remove();
      const articleAuthor = document.querySelector('meta[property="article:author"]');
      if (articleAuthor) articleAuthor.remove();
    };
  }, [title, description, path, ogType, robots, jsonLd, articleMeta]);
}

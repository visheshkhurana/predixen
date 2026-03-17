import { Helmet } from "react-helmet-async";

const SITE_URL = "https://founderconsole.ai";
const SITE_NAME = "FounderConsole";
const DEFAULT_OG_IMAGE = `${SITE_URL}/og-image.png`;
const TWITTER_HANDLE = "@founderconsole";

export type SEOHeadProps = {
  title: string;
  description: string;
  path?: string;
  ogType?: string;
  ogImage?: string;
  robots?: string;
  jsonLd?: object | object[];
  articleMeta?: {
    publishedTime?: string;
    author?: string;
  };
  noindex?: boolean;
};

export function SEOHead({
  title,
  description,
  path,
  ogType = "website",
  ogImage = DEFAULT_OG_IMAGE,
  robots,
  jsonLd,
  articleMeta,
  noindex = false,
}: SEOHeadProps) {
  const canonicalUrl = path ? `${SITE_URL}${path}` : SITE_URL;
  const computedRobots = noindex ? "noindex, nofollow" : (robots || "index, follow");

  const jsonLdArray = jsonLd
    ? Array.isArray(jsonLd)
      ? jsonLd
      : [jsonLd]
    : [];

  return (
    <Helmet>
      <title>{title}</title>
      <meta name="description" content={description} />
      <meta name="robots" content={computedRobots} />
      <link rel="canonical" href={canonicalUrl} />

      <meta property="og:title" content={title} />
      <meta property="og:description" content={description} />
      <meta property="og:url" content={canonicalUrl} />
      <meta property="og:type" content={ogType} />
      <meta property="og:image" content={ogImage} />
      <meta property="og:site_name" content={SITE_NAME} />

      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:title" content={title} />
      <meta name="twitter:description" content={description} />
      <meta name="twitter:site" content={TWITTER_HANDLE} />
      <meta name="twitter:image" content={ogImage} />

      {articleMeta?.publishedTime && (
        <meta property="article:published_time" content={articleMeta.publishedTime} />
      )}
      {articleMeta?.author && (
        <meta property="article:author" content={articleMeta.author} />
      )}

      {jsonLdArray.map((ld, i) => (
        <script key={i} type="application/ld+json">
          {JSON.stringify(ld)}
        </script>
      ))}
    </Helmet>
  );
}

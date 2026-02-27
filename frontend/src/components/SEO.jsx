import { Helmet } from 'react-helmet-async';
const defaultProps = {
  title: 'MBSE Knowledge Graph | Model-Based Systems Engineering Platform',
  description: 'Advanced knowledge graph platform for Model-Based Systems Engineering. Manage requirements, parts, traceability, and PLM integration with Neo4j graph database.',
  keywords: 'MBSE, Model-Based Systems Engineering, Knowledge Graph, Neo4j, Requirements Management, PLM Integration',
  canonicalUrl: 'https://mbse-knowledge-graph.com/',
  ogImage: '/og-image.png',
  ogType: 'website'
};
export function SEO({
  title,
  description,
  keywords,
  canonicalUrl,
  ogImage,
  ogType = 'website'
}) {
  const finalTitle = title ? `${title} | MBSE Knowledge Graph` : defaultProps.title;
  const finalDescription = description || defaultProps.description;
  const finalKeywords = keywords || defaultProps.keywords;
  const finalCanonicalUrl = canonicalUrl || defaultProps.canonicalUrl;
  const finalOgImage = ogImage || defaultProps.ogImage;
  return <Helmet><title>{finalTitle}</title><meta name="title" content={finalTitle} /><meta name="description" content={finalDescription} /><meta name="keywords" content={finalKeywords} /><meta property="og:type" content={ogType} /><meta property="og:url" content={finalCanonicalUrl} /><meta property="og:title" content={finalTitle} /><meta property="og:description" content={finalDescription} /><meta property="og:image" content={finalOgImage} /><meta property="twitter:card" content="summary_large_image" /><meta property="twitter:url" content={finalCanonicalUrl} /><meta property="twitter:title" content={finalTitle} /><meta property="twitter:description" content={finalDescription} /><meta property="twitter:image" content={finalOgImage} /><link rel="canonical" href={finalCanonicalUrl} /></Helmet>;
}
export default SEO;

import { Helmet } from 'react-helmet-async';import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";










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

  return (/*#__PURE__*/
    _jsxs(Helmet, { children: [/*#__PURE__*/

      _jsx("title", { children: finalTitle }), /*#__PURE__*/
      _jsx("meta", { name: "title", content: finalTitle }), /*#__PURE__*/
      _jsx("meta", { name: "description", content: finalDescription }), /*#__PURE__*/
      _jsx("meta", { name: "keywords", content: finalKeywords }), /*#__PURE__*/


      _jsx("meta", { property: "og:type", content: ogType }), /*#__PURE__*/
      _jsx("meta", { property: "og:url", content: finalCanonicalUrl }), /*#__PURE__*/
      _jsx("meta", { property: "og:title", content: finalTitle }), /*#__PURE__*/
      _jsx("meta", { property: "og:description", content: finalDescription }), /*#__PURE__*/
      _jsx("meta", { property: "og:image", content: finalOgImage }), /*#__PURE__*/


      _jsx("meta", { property: "twitter:card", content: "summary_large_image" }), /*#__PURE__*/
      _jsx("meta", { property: "twitter:url", content: finalCanonicalUrl }), /*#__PURE__*/
      _jsx("meta", { property: "twitter:title", content: finalTitle }), /*#__PURE__*/
      _jsx("meta", { property: "twitter:description", content: finalDescription }), /*#__PURE__*/
      _jsx("meta", { property: "twitter:image", content: finalOgImage }), /*#__PURE__*/


      _jsx("link", { rel: "canonical", href: finalCanonicalUrl })] }
    ));

}

export default SEO;

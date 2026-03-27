import type { RequestHandler } from '@sveltejs/kit';

export const prerender = true;

const DOMAIN = 'https://les577.fr';

const STATIC_PAGES = [
  { url: '/', priority: '1.0', changefreq: 'daily' },
  { url: '/deputes', priority: '0.9', changefreq: 'weekly' },
  { url: '/votes', priority: '0.9', changefreq: 'daily' },
];

export const GET: RequestHandler = () => {
  const urls = STATIC_PAGES.map(
    (p) => `
  <url>
    <loc>${DOMAIN}${p.url}</loc>
    <changefreq>${p.changefreq}</changefreq>
    <priority>${p.priority}</priority>
  </url>`,
  ).join('');

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">${urls}
</urlset>`;

  return new Response(xml, {
    headers: {
      'Content-Type': 'application/xml',
      'Cache-Control': 'max-age=3600',
    },
  });
};

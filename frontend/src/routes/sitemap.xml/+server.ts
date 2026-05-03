import { PUBLIC_API_BASE_URL } from '$env/static/public';
import type { RequestHandler } from '@sveltejs/kit';

const DOMAIN = 'https://les577.fr';

const STATIC_PAGES = [
  { url: '/', priority: '1.0', changefreq: 'daily' },
  { url: '/deputes', priority: '0.9', changefreq: 'weekly' },
  { url: '/votes', priority: '0.9', changefreq: 'daily' },
];

function urlEntry(loc: string, priority: string, changefreq: string): string {
  return `
  <url>
    <loc>${loc}</loc>
    <changefreq>${changefreq}</changefreq>
    <priority>${priority}</priority>
  </url>`;
}

export const GET: RequestHandler = async () => {
  const entries: string[] = STATIC_PAGES.map((p) =>
    urlEntry(`${DOMAIN}${p.url}`, p.priority, p.changefreq),
  );

  try {
    const [deputesRes, votesRes] = await Promise.all([
      fetch(`${PUBLIC_API_BASE_URL}/deputes?limit=600`),
      fetch(`${PUBLIC_API_BASE_URL}/votes?limit=200`),
    ]);

    if (deputesRes.ok) {
      const { items } = await deputesRes.json();
      for (const d of items ?? []) {
        entries.push(urlEntry(`${DOMAIN}/deputes/${d.id}`, '0.7', 'weekly'));
      }
    }

    if (votesRes.ok) {
      const first = await votesRes.json();
      const allVotes = [...(first.items ?? [])];
      const total: number = first.total ?? 0;
      const limit = 200;
      const pages = Math.ceil(total / limit);
      if (pages > 1) {
        const rest = await Promise.all(
          Array.from({ length: pages - 1 }, (_, i) =>
            fetch(`${PUBLIC_API_BASE_URL}/votes?limit=${limit}&offset=${(i + 1) * limit}`).then(
              (r) => r.json(),
            ),
          ),
        );
        for (const page of rest) allVotes.push(...(page.items ?? []));
      }
      for (const v of allVotes) {
        entries.push(urlEntry(`${DOMAIN}/votes/${v.id}`, '0.6', 'monthly'));
      }
    }
  } catch {
    // Si l'API est indisponible, on retourne le sitemap statique uniquement
  }

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">${entries.join('')}
</urlset>`;

  return new Response(xml, {
    headers: {
      'Content-Type': 'application/xml',
      'Cache-Control': 'public, max-age=3600',
    },
  });
};

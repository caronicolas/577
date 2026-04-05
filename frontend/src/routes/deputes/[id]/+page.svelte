<script lang="ts">
  import { page } from '$app/stores';
  import ActivityCalendar from '$lib/components/ActivityCalendar.svelte';
  import ScoreGauges from '$lib/components/ScoreGauges.svelte';
  import { apiBase } from '$lib/api';

  const id = $derived($page.params.id);

  function texteNum(ref: string | null): string | null {
    if (!ref) return null;
    const m = ref.match(/B(\d+)$/);
    return m ? `n°${parseInt(m[1], 10)}` : null;
  }

  let depute = $state<any>(null);
  let amendements = $state<any[]>([]);
  let votes = $state<any[]>([]);
  let activites = $state<any[]>([]);
  let loading = $state(true);
  let error = $state<string | null>(null);

  const commissions = $derived(
    activites
      .flatMap((a: any) =>
        (a.commissions ?? []).map((c: any) => ({ ...c, date: a.date }))
      )
      .sort((a: any, b: any) => b.date.localeCompare(a.date))
  );

  let expandedCommissions = $state(new Set<string>());

  function toggleCommission(id: string) {
    const next = new Set(expandedCommissions);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    expandedCommissions = next;
  }

  $effect(() => {
    loading = true;
    error = null;
    Promise.all([
      fetch(`${apiBase}/deputes/${id}`).then((r) => r.json()),
      fetch(`${apiBase}/amendements?depute_id=${id}&limit=100`).then((r) => r.json()),
      fetch(`${apiBase}/votes?depute_id=${id}&limit=100`).then((r) => r.json()),
      fetch(`${apiBase}/deputes/${id}/activites`).then((r) => r.json()),
    ])
      .then(([d, a, v, act]) => {
        depute = d;
        amendements = Array.isArray(a) ? a : (a.items ?? []);
        votes = Array.isArray(v) ? v : (v.items ?? []);
        activites = Array.isArray(act) ? act : (act.items ?? []);
        loading = false;
      })
      .catch(() => {
        error = 'Impossible de charger les données.';
        loading = false;
      });
  });
</script>

<svelte:head>
  {#if depute}
    <title>{depute.prenom} {depute.nom_de_famille} — les 577</title>
    <meta name="description" content="{depute.prenom} {depute.nom_de_famille}{depute.groupe ? `, ${depute.groupe.libelle}` : ''}{depute.nom_circonscription ? `, ${depute.nom_circonscription}` : ''}. Votes, amendements et activité à l'Assemblée Nationale." />
    <meta property="og:title" content="{depute.prenom} {depute.nom_de_famille} — les 577" />
    <meta property="og:description" content="{depute.prenom} {depute.nom_de_famille}{depute.groupe ? `, ${depute.groupe.libelle}` : ''}{depute.nom_circonscription ? `, ${depute.nom_circonscription}` : ''}. Votes, amendements et activité à l'Assemblée Nationale." />
    {#if depute.url_photo}
      <meta property="og:image" content={depute.url_photo} />
      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:image" content={depute.url_photo} />
    {/if}
  {:else}
    <title>Député — les 577</title>
  {/if}
</svelte:head>

{#if loading}
  <p class="muted">Chargement…</p>
{:else if error}
  <p class="muted">{error}</p>
{:else if depute}
  <div class="profile">
    {#if depute.url_photo}
      <img
        src={depute.url_photo}
        alt={depute.nom}
        class="photo"
        loading="lazy"
        onerror={(e) => {
          const img = e.currentTarget as HTMLImageElement;
          img.onerror = null;
          img.src = `https://datan.fr/assets/imgs/deputes_original/depute_${depute.id.replace('PA', '')}.png`;
        }}
      />
    {/if}
    <div class="meta">
      <h1>{depute.prenom} {depute.nom_de_famille}</h1>
      {#if depute.actif === false}
        <span class="badge-inactif">Mandat terminé</span>
      {/if}
      {#if depute.groupe}
        <div class="groupe">
          <span
            class="badge"
            style="background: {depute.groupe.couleur ?? 'var(--color-border)'}"
          >{depute.groupe.sigle}</span>
          <span class="groupe-libelle">{depute.groupe.libelle}</span>
        </div>
      {/if}
      <p class="circ">{depute.nom_circonscription ?? ''}{depute.num_departement ? ` (${depute.num_departement})` : ''}</p>
      {#if depute.profession}
        <p class="detail">{depute.profession}</p>
      {/if}
      <div class="socials">
        {#if depute.twitter}
          <a
            href="https://x.com/{depute.twitter}"
            target="_blank"
            rel="noopener noreferrer"
            class="social-link"
            title="X / Twitter"
          >
            <svg viewBox="0 0 24 24" fill="currentColor" class="social-icon" aria-hidden="true">
              <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-4.714-6.231-5.401 6.231H2.746l7.73-8.835L1.254 2.25H8.08l4.253 5.622zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
            </svg>
          </a>
        {/if}
        {#if depute.facebook_url}
          <a
            href={depute.facebook_url}
            target="_blank"
            rel="noopener noreferrer"
            class="social-link"
            title="Facebook"
          >
            <svg viewBox="0 0 24 24" fill="currentColor" class="social-icon" aria-hidden="true">
              <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
            </svg>
          </a>
        {/if}
        {#if depute.instagram_url}
          <a
            href={depute.instagram_url}
            target="_blank"
            rel="noopener noreferrer"
            class="social-link"
            title="Instagram"
          >
            <svg viewBox="0 0 24 24" fill="currentColor" class="social-icon" aria-hidden="true">
              <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98C8.333 23.986 8.741 24 12 24c3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 100 12.324 6.162 6.162 0 000-12.324zM12 16a4 4 0 110-8 4 4 0 010 8zm6.406-11.845a1.44 1.44 0 100 2.881 1.44 1.44 0 000-2.881z"/>
            </svg>
          </a>
        {/if}
        {#if depute.bluesky_url}
          <a
            href={depute.bluesky_url}
            target="_blank"
            rel="noopener noreferrer"
            class="social-link"
            title="Bluesky"
          >
            <svg viewBox="0 0 24 24" fill="currentColor" class="social-icon" aria-hidden="true">
              <path d="M12 10.8c-1.087-2.114-4.046-6.053-6.798-7.995C2.566.944 1.561 1.266.902 1.565.139 1.908 0 3.08 0 3.768c0 .69.378 5.65.624 6.479.815 2.736 3.713 3.66 6.383 3.364.136-.02.275-.039.415-.056-.138.022-.276.04-.415.056-3.912.58-7.387 2.005-2.83 7.078 5.013 5.19 6.87-1.113 7.823-4.308.953 3.195 2.05 9.271 7.733 4.308 4.267-4.308 1.172-6.498-2.74-7.078a8.741 8.741 0 01-.415-.056c.14.017.279.036.415.056 2.67.297 5.568-.628 6.383-3.364.246-.828.624-5.79.624-6.478 0-.69-.139-1.861-.902-2.206-.659-.298-1.664-.62-4.3 1.24C16.046 4.748 13.087 8.687 12 10.8z"/>
            </svg>
          </a>
        {/if}
        {#if depute.url_an}
          <a
            href={depute.url_an}
            target="_blank"
            rel="noopener noreferrer"
            class="social-link social-link--an"
            title="Fiche AN officielle"
          >
            <svg viewBox="0 0 24 24" fill="currentColor" class="social-icon" aria-hidden="true">
              <path d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
            </svg>
          </a>
        {/if}
      </div>
    </div>
  </div>

  <section class="section">
    <h2>Activité — 17<sup>e</sup> législature</h2>
    <ActivityCalendar {activites} dateDebut="2024-06-18" dateFin={new Date().toISOString().slice(0, 10)} />
  </section>

  {#if depute.scores_datan}
    <section class="section">
      <h2>Scores (source Datan)</h2>
      <ScoreGauges scores={depute.scores_datan} groupeLibelle={depute.groupe?.libelle ?? null} />
    </section>
  {/if}

  <div class="columns">
    <section class="col">
      <h2>Commissions ({commissions.length})</h2>
      {#if commissions.length === 0}
        <p class="muted">Aucune commission enregistrée.</p>
      {:else}
        <ul class="list">
          {#each commissions as c (c.reunion_id)}
            {@const open = expandedCommissions.has(c.reunion_id)}
            <li class="commission-item">
              <button class="commission-header" onclick={() => toggleCommission(c.reunion_id)}>
                <svg class="chevron" class:open viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                  <polyline points="9 18 15 12 9 6" />
                </svg>
                <span class="commission-date">{c.date}</span>
                {#if c.heure_debut}
                  <span class="commission-heure">{c.heure_debut}</span>
                {/if}
              </button>
              {#if open}
                <p class="commission-libelle">
                  {#if c.organe_id}
                    <a
                      href="https://www.assemblee-nationale.fr/dyn/17/organes/{c.organe_id}"
                      target="_blank"
                      rel="noopener noreferrer"
                    >{c.organe_libelle ?? c.titre ?? 'Commission'}</a>
                  {:else}
                    {c.organe_libelle ?? c.titre ?? 'Commission'}
                  {/if}
                </p>
              {/if}
            </li>
          {/each}
        </ul>
      {/if}
    </section>

    <section class="col">
      <h2>Votes ({votes.length})</h2>
      {#if votes.length === 0}
        <p class="muted">Aucun vote enregistré.</p>
      {:else}
        <ul class="list">
          {#each votes as v (v.id)}
            <li class="list-item">
              <a href="/votes/{v.scrutin_id ?? v.id}" class="vote-link">
                <span class="vote-titre">{v.titre ?? v.objet ?? 'Scrutin sans titre'}</span>
                {#if v.position}
                  <span class="vote-pos" data-pos={v.position}>{v.position}</span>
                {/if}
              </a>
            </li>
          {/each}
        </ul>
      {/if}
    </section>

    <section class="col">
      <h2>Amendements ({amendements.length})</h2>
      {#if amendements.length === 0}
        <p class="muted">Aucun amendement enregistré.</p>
      {:else}
        <ul class="list">
          {#each amendements as a (a.id)}
            <li class="list-item">
              <a href={a.url_an} target="_blank" rel="noopener noreferrer" class="amend-link">
                <span class="amend-num">N°{a.numero ?? '—'}</span>
                {#if texteNum(a.texte_legislature)}
                  <span class="amend-texte">Texte {texteNum(a.texte_legislature)}</span>
                {/if}
                <span class="amend-titre">{a.titre ?? '—'}</span>
                {#if a.date_depot}
                  <span class="amend-date">{a.date_depot}</span>
                {/if}
                {#if a.sort}
                  <span class="amend-sort" data-sort={a.sort}>{a.sort}</span>
                {/if}
              </a>
            </li>
          {/each}
        </ul>
      {/if}
    </section>
  </div>
{/if}

<style>
  .profile {
    display: flex;
    gap: 1.5rem;
    align-items: flex-start;
    margin-bottom: 2.5rem;
  }

  .photo {
    width: 100px;
    height: 100px;
    border-radius: var(--radius-md);
    object-fit: cover;
    flex-shrink: 0;
  }

  .meta {
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
  }

  h1 { font-size: 1.75rem; font-weight: 700; }

  .badge-inactif {
    display: inline-block;
    font-size: 0.72rem;
    font-weight: 600;
    padding: 0.15rem 0.5rem;
    border-radius: var(--radius-sm);
    background: var(--color-border);
    color: var(--color-text-muted);
    margin-bottom: 0.4rem;
  }

  .badge {
    display: inline-block;
    font-size: 0.75rem;
    font-weight: 700;
    padding: 0.15rem 0.5rem;
    border-radius: var(--radius-sm);
    color: #fff;
    width: fit-content;
  }

  .groupe {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .groupe-libelle {
    font-size: 0.875rem;
    color: var(--color-text-muted);
  }

  .circ { color: var(--color-text-muted); }
  .detail { font-size: 0.875rem; color: var(--color-text-muted); }

  .socials {
    display: flex;
    gap: 0.5rem;
    align-items: center;
    margin-top: 0.25rem;
  }

  .social-link {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    border-radius: var(--radius-sm);
    color: var(--color-text-muted);
    transition: color 0.15s, background 0.15s;
    text-decoration: none;
  }

  .social-link:hover {
    color: var(--color-text);
    background: var(--color-border);
    text-decoration: none;
  }

  .social-icon {
    width: 16px;
    height: 16px;
    flex-shrink: 0;
  }

  .social-link--an .social-icon {
    stroke: currentColor;
    fill: none;
    stroke-width: 2;
    stroke-linecap: round;
    stroke-linejoin: round;
  }

  .section { margin-bottom: 2.5rem; }

  .columns {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 2rem;
    align-items: start;
  }

  @media (max-width: 900px) {
    .columns {
      grid-template-columns: 1fr;
    }
  }

  .col { min-width: 0; }

  h2 {
    font-size: 1.1rem;
    font-weight: 600;
    margin-bottom: 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid var(--color-border);
  }

  .list { list-style: none; }

  .list-item {
    display: flex;
    gap: 1rem;
    align-items: baseline;
    padding: 0.5rem 0;
    border-bottom: 1px solid var(--color-border);
    font-size: 0.875rem;
  }

  .amend-link {
    display: flex;
    gap: 0.75rem;
    align-items: baseline;
    width: 100%;
    color: var(--color-text);
    text-decoration: none;
    font-size: 0.875rem;
    flex-wrap: wrap;
  }

  .amend-link:hover { text-decoration: none; background: var(--color-bg); }

  .amend-num {
    font-family: var(--font-mono);
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--color-text);
    flex-shrink: 0;
  }

  .amend-texte {
    font-size: 0.75rem;
    color: var(--color-text-muted);
    flex-shrink: 0;
    background: var(--color-border);
    padding: 0.05rem 0.35rem;
    border-radius: 3px;
  }

  .amend-titre { flex: 1; color: var(--color-text-muted); }

  .amend-date {
    font-family: var(--font-mono);
    font-size: 0.75rem;
    color: var(--color-text-muted);
    flex-shrink: 0;
  }

  .amend-sort { font-size: 0.75rem; font-weight: 600; flex-shrink: 0; }
  .amend-sort[data-sort="Adopté"] { color: var(--color-vote); }
  .amend-sort[data-sort="Rejeté"] { color: var(--color-absent); }

  .vote-link {
    display: flex;
    gap: 0.5rem;
    align-items: baseline;
    padding: 0.5rem 0;
    border-bottom: 1px solid var(--color-border);
    font-size: 0.875rem;
    color: var(--color-text);
    width: 100%;
  }

  .vote-link:hover { text-decoration: none; background: var(--color-bg); }

  .vote-titre { flex: 1; }

  .vote-pos { flex-shrink: 0; font-size: 0.75rem; font-weight: 600; }
  .vote-pos[data-pos="Pour"] { color: var(--color-vote); }
  .vote-pos[data-pos="Contre"] { color: var(--color-absent); }
  .vote-pos[data-pos="Abstention"] { color: var(--color-text-muted); }

  .muted { color: var(--color-text-muted); }

  .commission-item {
    border-bottom: 1px solid var(--color-border);
    font-size: 0.875rem;
  }

  .commission-header {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    width: 100%;
    background: none;
    border: none;
    padding: 0.4rem 0;
    cursor: pointer;
    color: var(--color-text);
    font-size: 0.875rem;
    text-align: left;
  }

  .commission-header:hover { color: var(--color-text); }

  .chevron {
    width: 14px;
    height: 14px;
    flex-shrink: 0;
    color: var(--color-text-muted);
    transition: transform 0.15s;
  }

  .chevron.open { transform: rotate(90deg); }

  .commission-date {
    font-family: var(--font-mono);
    font-size: 0.75rem;
    color: var(--color-text-muted);
    flex-shrink: 0;
  }

  .commission-heure {
    font-family: var(--font-mono);
    font-size: 0.75rem;
    color: var(--color-commission);
    flex-shrink: 0;
  }

  .commission-libelle {
    color: var(--color-text-muted);
    font-size: 0.875rem;
    padding: 0.25rem 0 0.4rem 1.35rem;
    margin: 0;
  }
</style>

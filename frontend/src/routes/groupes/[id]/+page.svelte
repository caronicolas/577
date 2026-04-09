<script lang="ts">
  import { page } from '$app/stores';
  import { apiBase } from '$lib/api';

  const id = $derived($page.params.id);

  interface DatanGroupe {
    score_cohesion: number | null;
    score_participation: number | null;
    score_majorite: number | null;
    women_pct: number | null;
    age_moyen: number | null;
    score_rose: number | null;
    position_politique: string | null;
  }

  interface DeputeInGroupe {
    id: string;
    prenom: string;
    nom_de_famille: string;
    url_photo: string | null;
    num_departement: string | null;
    nom_circonscription: string | null;
    actif: boolean;
  }

  interface GroupeDetail {
    id: string;
    sigle: string;
    libelle: string;
    couleur: string | null;
    nb_deputes: number;
    nb_deputes_total: number;
    datan: DatanGroupe | null;
    deputes: DeputeInGroupe[];
  }

  let groupe = $state<GroupeDetail | null>(null);
  let loading = $state(true);
  let error = $state<string | null>(null);

  $effect(() => {
    loading = true;
    error = null;
    fetch(`${apiBase}/groupes/${id}`)
      .then((r) => {
        if (!r.ok) throw new Error('Groupe introuvable');
        return r.json();
      })
      .then((data) => {
        groupe = data;
        loading = false;
      })
      .catch((e) => {
        error = e.message;
        loading = false;
      });
  });

  function pct(val: number | null): string {
    if (val == null) return '—';
    return Math.round(val * 100) + ' %';
  }

  function width(val: number | null): number {
    if (val == null) return 0;
    return Math.round(Math.min(Math.max(val, 0), 1) * 100);
  }

  // women_pct est déjà en % (0-100), contrairement aux scores Datan (0-1)
  function pctDirect(val: number | null): string {
    if (val == null) return '—';
    return Math.round(val) + ' %';
  }

  function widthDirect(val: number | null): number {
    if (val == null) return 0;
    return Math.round(Math.min(Math.max(val, 0), 100));
  }

  function age(val: number | null): string {
    if (val == null) return '—';
    return Math.round(val) + ' ans';
  }

  function textColor(hex: string | null): string {
    if (!hex) return '#fff';
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
    return luminance > 0.55 ? '#111' : '#fff';
  }

</script>

<svelte:head>
  {#if groupe}
    <title>{groupe.libelle} ({groupe.sigle}) — les 577</title>
    <meta name="description" content="{groupe.libelle} — {groupe.nb_deputes} député{groupe.nb_deputes > 1 ? 's' : ''} à l'Assemblée Nationale, 17e législature." />
  {:else}
    <title>Groupe parlementaire — les 577</title>
  {/if}
</svelte:head>

<a href="/groupes" class="back">← Groupes</a>

{#if loading}
  <p class="muted">Chargement…</p>
{:else if error}
  <p class="muted">{error}</p>
{:else if groupe}
  <div class="header">
    <div
      class="sigle-badge"
      style="background: {groupe.couleur ?? 'var(--color-border)'}; color: {textColor(groupe.couleur)}"
    >
      {groupe.sigle}
    </div>
    <div>
      <h1>{groupe.libelle}</h1>
      <p class="meta">
        {groupe.nb_deputes} député{groupe.nb_deputes > 1 ? 's' : ''} actif{groupe.nb_deputes > 1 ? 's' : ''}
        {#if groupe.nb_deputes_total > groupe.nb_deputes}
          · {groupe.nb_deputes_total - groupe.nb_deputes} ancien{groupe.nb_deputes_total - groupe.nb_deputes > 1 ? 's' : ''}
        {/if}
        · 17<sup>e</sup> législature
      </p>
      {#if groupe.datan?.position_politique}
        <span class="position-tag">{groupe.datan.position_politique}</span>
      {/if}
    </div>
  </div>

  {#if groupe.datan}
    <section class="section">
      <h2>Statistiques (source Datan)</h2>
      <div class="stats-grid">

        <div class="stat-card">
          <span class="stat-label">Cohésion</span>
          <span class="stat-value">{pct(groupe.datan.score_cohesion)}</span>
          <div class="jauge-track">
            <div class="jauge-bar" style="width: {width(groupe.datan.score_cohesion)}%; background: {groupe.couleur ?? 'var(--color-vote)'}"></div>
          </div>
          <p class="stat-desc">Part des scrutins où le groupe vote dans le même sens</p>
        </div>

        <div class="stat-card">
          <span class="stat-label">Participation</span>
          <span class="stat-value">{pct(groupe.datan.score_participation)}</span>
          <div class="jauge-track">
            <div class="jauge-bar" style="width: {width(groupe.datan.score_participation)}%; background: {groupe.couleur ?? 'var(--color-vote)'}"></div>
          </div>
          <p class="stat-desc">Taux de présence moyen aux scrutins solennels</p>
        </div>

        <div class="stat-card">
          <span class="stat-label">Proximité majorité</span>
          <span class="stat-value">{pct(groupe.datan.score_majorite)}</span>
          <div class="jauge-track">
            <div class="jauge-bar" style="width: {width(groupe.datan.score_majorite)}%; background: {groupe.couleur ?? 'var(--color-vote)'}"></div>
          </div>
          <p class="stat-desc">Alignement avec la majorité présidentielle</p>
        </div>

        <div class="stat-card">
          <span class="stat-label">Parité femmes</span>
          <span class="stat-value">{pctDirect(groupe.datan.women_pct)}</span>
          <div class="jauge-track">
            <div class="jauge-bar" style="width: {widthDirect(groupe.datan.women_pct)}%; background: {groupe.couleur ?? 'var(--color-vote)'}"></div>
          </div>
          <p class="stat-desc">Part des femmes dans le groupe</p>
        </div>

        <div class="stat-card stat-card--inline">
          <span class="stat-label">Âge moyen</span>
          <span class="stat-value">{age(groupe.datan.age_moyen)}</span>
        </div>


      </div>
      <p class="source">
        Source : <a href="https://www.data.gouv.fr/fr/organizations/datan/" target="_blank" rel="noopener noreferrer">Datan</a>
        via data.gouv.fr — Licence Ouverte
      </p>
    </section>
  {/if}

  <section class="section">
    <h2>Députés ({groupe.nb_deputes} actifs)</h2>
    <div class="deputes-grid">
      {#each groupe.deputes as d}
        <a href="/deputes/{d.id}" class="depute-card" class:inactif={!d.actif}>
          {#if d.url_photo}
            <img
              src={d.url_photo}
              alt="{d.prenom} {d.nom_de_famille}"
              class="photo"
              loading="lazy"
              onerror={(e) => {
                const img = e.currentTarget as HTMLImageElement;
                img.onerror = null;
                img.src = `https://datan.fr/assets/imgs/deputes_original/depute_${d.id.replace('PA', '')}.png`;
              }}
            />
          {:else}
            <div class="photo-placeholder"></div>
          {/if}
          <div class="depute-info">
            <span class="depute-nom">{d.prenom} {d.nom_de_famille}</span>
            {#if d.nom_circonscription}
              <span class="depute-circ">{d.nom_circonscription}{d.num_departement ? ` (${d.num_departement})` : ''}</span>
            {/if}
            {#if !d.actif}
              <span class="badge-inactif">Mandat terminé</span>
            {/if}
          </div>
        </a>
      {/each}
    </div>
  </section>
{/if}

<style>
  .back {
    display: inline-block;
    font-size: 0.85rem;
    color: var(--color-text-muted);
    margin-bottom: 1.5rem;
    text-decoration: none;
  }

  .back:hover {
    color: var(--color-text);
    text-decoration: none;
  }

  .header {
    display: flex;
    align-items: center;
    gap: 1.25rem;
    margin-bottom: 2rem;
  }

  .sigle-badge {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 72px;
    height: 72px;
    border-radius: var(--radius-md);
    font-weight: 800;
    font-size: 1rem;
    letter-spacing: 0.03em;
    flex-shrink: 0;
    text-align: center;
    line-height: 1.2;
    padding: 0.25rem;
  }

  h1 {
    font-size: 1.5rem;
    font-weight: 700;
    margin-bottom: 0.25rem;
  }

  .meta {
    font-size: 0.875rem;
    color: var(--color-text-muted);
    margin-bottom: 0.4rem;
  }

  .position-tag {
    display: inline-block;
    font-size: 0.72rem;
    padding: 0.15rem 0.5rem;
    background: var(--color-bg);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    color: var(--color-text-muted);
  }

  .section { margin-bottom: 2.5rem; }

  h2 {
    font-size: 1.1rem;
    font-weight: 600;
    margin-bottom: 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid var(--color-border);
  }

  /* Stats */
  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 1rem;
    margin-bottom: 0.75rem;
  }

  .stat-card {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    padding: 1rem;
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
  }

  .stat-card--inline {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
  }

  .stat-label {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--color-text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .stat-value {
    font-size: 1.5rem;
    font-weight: 700;
    font-family: var(--font-mono);
    color: var(--color-text);
  }

  .stat-card--inline .stat-value {
    font-size: 1.25rem;
  }

  .jauge-track {
    height: 6px;
    background: var(--color-border);
    border-radius: 3px;
    overflow: hidden;
  }

  .jauge-bar {
    height: 100%;
    border-radius: 3px;
    opacity: 0.85;
  }

  .stat-desc {
    font-size: 0.72rem;
    color: var(--color-text-muted);
    margin: 0;
    line-height: 1.4;
  }


  .source {
    font-size: 0.7rem;
    color: var(--color-text-muted);
    margin-top: 0.25rem;
  }

  .source a { color: var(--color-text-muted); }

  /* Deputies grid */
  .deputes-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 0.75rem;
  }

  .depute-card {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.6rem;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    text-decoration: none;
    color: var(--color-text);
    transition: box-shadow 0.12s, border-color 0.12s;
  }

  .depute-card:hover {
    border-color: var(--color-text-muted);
    box-shadow: var(--shadow-md);
    text-decoration: none;
  }

  .depute-card.inactif {
    opacity: 0.55;
  }

  .photo {
    width: 40px;
    height: 40px;
    border-radius: var(--radius-sm);
    object-fit: cover;
    flex-shrink: 0;
  }

  .photo-placeholder {
    width: 40px;
    height: 40px;
    border-radius: var(--radius-sm);
    background: var(--color-border);
    flex-shrink: 0;
  }

  .depute-info {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
    min-width: 0;
  }

  .depute-nom {
    font-size: 0.8rem;
    font-weight: 600;
    line-height: 1.3;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .depute-circ {
    font-size: 0.7rem;
    color: var(--color-text-muted);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .badge-inactif {
    font-size: 0.65rem;
    font-weight: 600;
    padding: 0.1rem 0.35rem;
    border-radius: var(--radius-sm);
    background: var(--color-border);
    color: var(--color-text-muted);
    align-self: flex-start;
  }

  .muted { color: var(--color-text-muted); }
</style>

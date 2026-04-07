<script lang="ts">
  import { apiBase } from '$lib/api';

  interface DatanGroupe {
    score_cohesion: number | null;
    score_participation: number | null;
    score_majorite: number | null;
    women_pct: number | null;
    age_moyen: number | null;
    score_rose: number | null;
    position_politique: string | null;
  }

  interface Groupe {
    id: string;
    sigle: string;
    libelle: string;
    couleur: string | null;
    nb_deputes: number;
    datan: DatanGroupe | null;
  }

  let groupes = $state<Groupe[]>([]);
  let loading = $state(true);
  let error = $state<string | null>(null);

  $effect(() => {
    fetch(`${apiBase}/groupes`)
      .then((r) => r.json())
      .then((data) => {
        groupes = data;
        loading = false;
      })
      .catch(() => {
        error = 'Impossible de charger les groupes.';
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
  <title>Groupes parlementaires — les 577</title>
  <meta name="description" content="Les groupes parlementaires de l'Assemblée Nationale — 17e législature. Composition, scores de cohésion et de participation." />
</svelte:head>

<h1>Groupes parlementaires</h1>
<p class="subtitle">17<sup>e</sup> législature · {groupes.length} groupes</p>

{#if loading}
  <p class="muted">Chargement…</p>
{:else if error}
  <p class="muted error">{error}</p>
{:else}
  <div class="grid">
    {#each groupes as g}
      <a href="/groupes/{g.id}" class="card">
        <div class="card-header">
          <div
            class="sigle-badge"
            style="background: {g.couleur ?? 'var(--color-border)'}; color: {textColor(g.couleur)}"
          >
            {g.sigle}
          </div>
          <div class="card-meta">
            <span class="libelle">{g.libelle}</span>
            <span class="count">{g.nb_deputes} député{g.nb_deputes > 1 ? 's' : ''}</span>
          </div>
        </div>

        {#if g.datan}
          <div class="scores">
            <div class="score-row">
              <span class="score-label">Cohésion</span>
              <div class="score-track">
                <div
                  class="score-bar"
                  style="width: {width(g.datan.score_cohesion)}%; background: {g.couleur ?? 'var(--color-vote)'}"
                ></div>
              </div>
              <span class="score-val">{pct(g.datan.score_cohesion)}</span>
            </div>
            <div class="score-row">
              <span class="score-label">Participation</span>
              <div class="score-track">
                <div
                  class="score-bar"
                  style="width: {width(g.datan.score_participation)}%; background: {g.couleur ?? 'var(--color-vote)'}"
                ></div>
              </div>
              <span class="score-val">{pct(g.datan.score_participation)}</span>
            </div>
            {#if g.datan.position_politique}
              <span class="position-tag">{g.datan.position_politique}</span>
            {/if}
          </div>
        {/if}
      </a>
    {/each}
  </div>
{/if}

<style>
  h1 {
    font-size: 1.75rem;
    font-weight: 700;
    margin-bottom: 0.25rem;
  }

  .subtitle {
    color: var(--color-text-muted);
    margin-bottom: 2rem;
    font-size: 0.9rem;
  }

  .muted { color: var(--color-text-muted); }
  .error { color: var(--color-absent); }

  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 1rem;
  }

  .card {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    padding: 1.25rem;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    text-decoration: none;
    color: var(--color-text);
    transition: box-shadow 0.15s, border-color 0.15s;
  }

  .card:hover {
    border-color: var(--color-text-muted);
    box-shadow: var(--shadow-md);
    text-decoration: none;
  }

  .card-header {
    display: flex;
    align-items: center;
    gap: 1rem;
  }

  .sigle-badge {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 56px;
    height: 56px;
    border-radius: var(--radius-md);
    font-weight: 800;
    font-size: 0.85rem;
    letter-spacing: 0.03em;
    flex-shrink: 0;
    text-align: center;
    line-height: 1.2;
    padding: 0.25rem;
  }

  .card-meta {
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
    min-width: 0;
  }

  .libelle {
    font-size: 0.9rem;
    font-weight: 600;
    line-height: 1.3;
  }

  .count {
    font-size: 0.8rem;
    color: var(--color-text-muted);
  }

  .scores {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .score-row {
    display: grid;
    grid-template-columns: 80px 1fr 40px;
    align-items: center;
    gap: 0.5rem;
  }

  .score-label {
    font-size: 0.72rem;
    color: var(--color-text-muted);
    text-align: right;
  }

  .score-track {
    height: 5px;
    background: var(--color-border);
    border-radius: 3px;
    overflow: hidden;
  }

  .score-bar {
    height: 100%;
    border-radius: 3px;
    opacity: 0.8;
  }

  .score-val {
    font-size: 0.72rem;
    font-family: var(--font-mono);
    color: var(--color-text-muted);
    text-align: right;
  }

  .position-tag {
    font-size: 0.7rem;
    color: var(--color-text-muted);
    padding: 0.1rem 0.4rem;
    background: var(--color-bg);
    border-radius: var(--radius-sm);
    align-self: flex-start;
  }
</style>

<script lang="ts">
  import { page } from '$app/stores';
  import { apiBase } from '$lib/api';
  const PAGE_SIZE = 50;

  let search = $state('');
  // Initialiser depuis l'URL si dossier_ref est présent (ex: lien depuis /votes/:id)
  let selectedDossier = $state<{ ref: string; libelle: string } | null>(null);

  // Résoudre le libellé si on arrive avec ?dossier_ref= dans l'URL
  $effect(() => {
    const urlRef = $page.url.searchParams.get('dossier_ref');
    if (urlRef && !selectedDossier) {
      // On attend les données pour avoir le libellé — on set la ref provisoirement
      selectedDossier = { ref: urlRef, libelle: urlRef };
      // Puis on résout le libellé depuis l'API
      fetch(`${apiBase}/votes/dossiers`)
        .then((r) => r.json())
        .then((dossiers: { dossier_ref: string; dossier_libelle: string }[]) => {
          const found = dossiers.find((d) => d.dossier_ref === urlRef);
          if (found) selectedDossier = { ref: urlRef, libelle: found.dossier_libelle };
        });
    }
  });
  let scrutins = $state<any[]>([]);
  let total = $state(0);
  let loading = $state(true);
  let loadingMore = $state(false);

  $effect(() => {
    const q = search;
    const d = selectedDossier;
    loading = true;
    scrutins = [];
    const params = new URLSearchParams({ limit: String(PAGE_SIZE) });
    if (q) params.set('q', q);
    if (d) params.set('dossier_ref', d.ref);
    fetch(`${apiBase}/votes?${params}`)
      .then((r) => r.json())
      .then((data) => {
        scrutins = data.items ?? [];
        total = data.total ?? 0;
        loading = false;
      });
  });

  function loadMore() {
    loadingMore = true;
    const params = new URLSearchParams({
      limit: String(PAGE_SIZE),
      offset: String(scrutins.length),
    });
    if (search) params.set('q', search);
    if (selectedDossier) params.set('dossier_ref', selectedDossier.ref);
    fetch(`${apiBase}/votes?${params}`)
      .then((r) => r.json())
      .then((data) => {
        scrutins = [...scrutins, ...(data.items ?? [])];
        loadingMore = false;
      });
  }

  function filterByDossier(ref: string, libelle: string) {
    selectedDossier = { ref, libelle };
    search = '';
  }

  function clearDossier() {
    selectedDossier = null;
  }
</script>

<svelte:head>
  <title>Scrutins et votes — les 577</title>
  <meta name="description" content="Tous les scrutins publics de l'Assemblée Nationale, 17e législature. Résultats par groupe parlementaire, hémicycle interactif pour chaque vote." />
  <meta property="og:title" content="Scrutins et votes — les 577" />
  <meta property="og:description" content="Tous les scrutins publics de l'Assemblée Nationale, 17e législature. Résultats par groupe parlementaire, hémicycle interactif pour chaque vote." />
</svelte:head>

<div class="header">
  <h1>Scrutins</h1>
  <input
    type="search"
    placeholder="Rechercher un scrutin…"
    bind:value={search}
    class="input"
  />
</div>

{#if selectedDossier}
  <div class="dossier-banner">
    <span class="dossier-label">Texte filtré :</span>
    <span class="dossier-titre">{selectedDossier.libelle}</span>
    <button class="dossier-clear" onclick={clearDossier} aria-label="Effacer le filtre">✕</button>
  </div>
{/if}

{#if loading}
  <p class="muted">Chargement…</p>
{:else}
  <p class="count">{scrutins.length} / {total} scrutin{total > 1 ? 's' : ''}</p>
  <ul class="list">
    {#each scrutins as s (s.id)}
      <li>
        <a href="/votes/{s.id}" class="row">
          <span class="date">{s.date_seance}</span>
          <div class="titre-wrap">
            <span class="titre">{s.titre}</span>
            {#if s.dossier_ref && s.dossier_libelle}
              <button
                class="dossier-tag"
                onclick={(e) => { e.preventDefault(); filterByDossier(s.dossier_ref, s.dossier_libelle); }}
                title="Filtrer par ce texte"
              >{s.dossier_libelle}</button>
            {/if}
          </div>
          <span class="sort" class:adopte={s.sort === 'adopté'} class:rejete={s.sort === 'rejeté'}>
            {s.sort ?? '—'}
          </span>
          <span class="stats">
            {#if s.nombre_pours != null}
              <span class="pour">{s.nombre_pours} pour</span> ·
              <span class="contre">{s.nombre_contres} contre</span>
            {/if}
          </span>
        </a>
      </li>
    {/each}
  </ul>
  {#if scrutins.length < total}
    <div class="load-more">
      <button onclick={loadMore} disabled={loadingMore} class="btn-more">
        {loadingMore ? 'Chargement…' : `Charger plus (${total - scrutins.length} restants)`}
      </button>
    </div>
  {/if}
{/if}

<style>
  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
    flex-wrap: wrap;
    margin-bottom: 1.5rem;
  }

  h1 { font-size: 1.75rem; font-weight: 700; }

  .input {
    padding: 0.4rem 0.75rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    font-size: 0.9rem;
    background: var(--color-surface);
    color: var(--color-text);
    min-width: 280px;
  }

  .dossier-banner {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    padding: 0.4rem 0.75rem;
    margin-bottom: 1rem;
    font-size: 0.85rem;
  }

  .dossier-label { color: var(--color-text-muted); flex-shrink: 0; }
  .dossier-titre { color: var(--color-text); font-weight: 500; flex: 1; }
  .dossier-clear {
    background: none;
    border: none;
    color: var(--color-text-muted);
    cursor: pointer;
    font-size: 0.8rem;
    padding: 0 0.2rem;
    flex-shrink: 0;
  }
  .dossier-clear:hover { color: var(--color-text); }

  .count {
    font-size: 0.85rem;
    color: var(--color-text-muted);
    margin-bottom: 0.75rem;
  }

  .list { list-style: none; }

  .row {
    display: grid;
    grid-template-columns: 110px 1fr 80px 160px;
    gap: 1rem;
    align-items: start;
    padding: 0.75rem 1rem;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    margin-bottom: 0.5rem;
    color: var(--color-text);
    transition: box-shadow 0.15s;
    font-size: 0.875rem;
  }

  .row:hover {
    box-shadow: var(--shadow-sm);
    text-decoration: none;
  }

  .date {
    font-family: var(--font-mono);
    font-size: 0.8rem;
    color: var(--color-text-muted);
    padding-top: 0.1rem;
  }

  .titre-wrap {
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
    min-width: 0;
  }

  .titre { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

  .dossier-tag {
    display: inline-block;
    align-self: flex-start;
    background: var(--color-border, #e2e8f0);
    color: var(--color-text-muted);
    border: none;
    border-radius: 3px;
    padding: 0.1rem 0.4rem;
    font-size: 0.72rem;
    cursor: pointer;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 100%;
    transition: background 0.15s, color 0.15s;
    text-align: left;
  }

  .dossier-tag:hover {
    background: var(--color-text-muted);
    color: var(--color-surface);
  }

  .sort { font-size: 0.8rem; font-weight: 600; padding-top: 0.1rem; }
  .sort.adopte { color: var(--color-vote); }
  .sort.rejete { color: var(--color-absent); }

  .stats { font-size: 0.78rem; color: var(--color-text-muted); padding-top: 0.1rem; }
  .pour { color: var(--color-vote); }
  .contre { color: var(--color-absent); }

  .load-more {
    display: flex;
    justify-content: center;
    padding: 1.5rem 0;
  }

  .btn-more {
    padding: 0.6rem 1.5rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-surface);
    color: var(--color-text);
    font-size: 0.875rem;
    cursor: pointer;
    transition: box-shadow 0.15s;
  }

  .btn-more:hover:not(:disabled) { box-shadow: var(--shadow-sm); }
  .btn-more:disabled { opacity: 0.6; cursor: default; }

  .muted { color: var(--color-text-muted); }
</style>

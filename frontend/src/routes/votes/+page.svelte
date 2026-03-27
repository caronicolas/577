<script lang="ts">
  import { apiBase } from '$lib/api';
  const PAGE_SIZE = 50;

  let search = $state('');
  let scrutins = $state<any[]>([]);
  let total = $state(0);
  let loading = $state(true);
  let loadingMore = $state(false);

  $effect(() => {
    const q = search;
    loading = true;
    scrutins = [];
    const params = new URLSearchParams({ limit: String(PAGE_SIZE) });
    if (q) params.set('q', q);
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
    fetch(`${apiBase}/votes?${params}`)
      .then((r) => r.json())
      .then((data) => {
        scrutins = [...scrutins, ...(data.items ?? [])];
        loadingMore = false;
      });
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

{#if loading}
  <p class="muted">Chargement…</p>
{:else}
  <p class="count">{scrutins.length} / {total} scrutin{total > 1 ? 's' : ''}</p>
  <ul class="list">
    {#each scrutins as s (s.id)}
      <li>
        <a href="/votes/{s.id}" class="row">
          <span class="date">{s.date_seance}</span>
          <span class="titre">{s.titre}</span>
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
    align-items: baseline;
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
  }

  .titre { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

  .sort { font-size: 0.8rem; font-weight: 600; }
  .sort.adopte { color: var(--color-vote); }
  .sort.rejete { color: var(--color-absent); }

  .stats { font-size: 0.78rem; color: var(--color-text-muted); }
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

  .btn-more:hover:not(:disabled) {
    box-shadow: var(--shadow-sm);
  }

  .btn-more:disabled {
    opacity: 0.6;
    cursor: default;
  }

  .muted { color: var(--color-text-muted); }
</style>

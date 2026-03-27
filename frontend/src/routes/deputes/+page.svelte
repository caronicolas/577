<script lang="ts">
  import { apiBase } from '$lib/api';
  let search = $state('');
  let groupe = $state('');
  let departement = $state('');
  let deputes = $state<any[]>([]);
  let total = $state(0);
  let loading = $state(true);

  $effect(() => {
    const params = new URLSearchParams();
    if (search) params.set('q', search);
    if (groupe) params.set('groupe', groupe);
    if (departement) params.set('departement', departement);
    params.set('limit', '600');

    loading = true;
    fetch(`${apiBase}/deputes?${params}`)
      .then((r) => r.json())
      .then((data) => {
        deputes = data.items ?? [];
        total = data.total ?? 0;
        loading = false;
      });
  });
</script>

<svelte:head>
  <title>Députés — Assemblée Nationale</title>
</svelte:head>

<div class="header">
  <h1>Députés</h1>
  <div class="filters">
    <input
      type="search"
      placeholder="Rechercher par nom…"
      bind:value={search}
      class="input"
    />
    <input
      type="text"
      placeholder="Groupe (ex: RN)"
      bind:value={groupe}
      class="input input--sm"
    />
    <input
      type="text"
      placeholder="Dpt (ex: 75)"
      bind:value={departement}
      class="input input--sm"
    />
  </div>
</div>

{#if loading}
  <p class="muted">Chargement…</p>
{:else}
  <p class="count">{total} député{total > 1 ? 's' : ''}</p>
  <ul class="grid">
    {#each deputes as d (d.id)}
      <li>
        <a href="/deputes/{d.id}" class="card">
          {#if d.url_photo}
            <img src={d.url_photo} alt={d.nom} class="photo" loading="lazy" />
          {:else}
            <div class="photo placeholder"></div>
          {/if}
          <div class="info">
            <strong>{d.nom}</strong>
            {#if d.groupe?.sigle}
              <span
                class="badge"
                style="background: {d.groupe.couleur ?? 'var(--color-border)'}"
              >{d.groupe.sigle}</span>
            {/if}
            <span class="circ">{d.nom_circonscription ?? ''}</span>
          </div>
        </a>
      </li>
    {/each}
  </ul>
{/if}

<style>
  .header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 1rem;
    margin-bottom: 1.5rem;
  }

  h1 { font-size: 1.75rem; font-weight: 700; }

  .filters {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
  }

  .input {
    padding: 0.4rem 0.75rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    font-size: 0.9rem;
    background: var(--color-surface);
    color: var(--color-text);
    min-width: 200px;
  }

  .input--sm { min-width: 120px; }

  .count {
    font-size: 0.85rem;
    color: var(--color-text-muted);
    margin-bottom: 1rem;
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 1rem;
    list-style: none;
  }

  .card {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    color: var(--color-text);
    transition: box-shadow 0.15s;
  }

  .card:hover {
    box-shadow: var(--shadow-md);
    text-decoration: none;
  }

  .photo {
    width: 44px;
    height: 44px;
    border-radius: 50%;
    object-fit: cover;
    flex-shrink: 0;
  }

  .placeholder {
    background: var(--color-border);
  }

  .info {
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
    overflow: hidden;
  }

  .info strong {
    font-size: 0.875rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .badge {
    display: inline-block;
    font-size: 0.7rem;
    font-weight: 700;
    padding: 0.1rem 0.4rem;
    border-radius: var(--radius-sm);
    color: #fff;
    width: fit-content;
  }

  .circ {
    font-size: 0.75rem;
    color: var(--color-text-muted);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .muted { color: var(--color-text-muted); }
</style>

<script lang="ts">
  import { apiBase } from '$lib/api';

  interface Groupe {
    id: string;
    sigle: string;
    libelle: string;
    couleur: string | null;
    nb_deputes: number;
  }

  interface Depute {
    id: string;
    nom: string;
    num_departement: string | null;
    nom_circonscription: string | null;
    place_hemicycle: number | null;
    url_photo: string | null;
    groupe: Groupe | null;
  }

  interface Dept {
    code: string;
    nom: string;
  }

  let search = $state('');
  let selectedGroupe = $state('');
  let selectedDept = $state('');
  let deputes = $state<Depute[]>([]);
  let total = $state(0);
  let loading = $state(true);

  let groupes = $state<Groupe[]>([]);
  let departements = $state<Dept[]>([]);

  // Fetch groups once
  fetch(`${apiBase}/groupes`)
    .then((r) => r.json())
    .then((data: Groupe[]) => {
      groupes = data.sort((a, b) => b.nb_deputes - a.nb_deputes);
    });

  const hors_hemicycle = $derived(
    deputes.filter((d) => d.place_hemicycle != null && d.place_hemicycle > 577).length
  );

  const hasFilters = $derived(!!search || !!selectedGroupe || !!selectedDept);

  $effect(() => {
    const params = new URLSearchParams();
    if (search) params.set('q', search);
    if (selectedGroupe) params.set('groupe', selectedGroupe);
    if (selectedDept) params.set('departement', selectedDept);
    params.set('limit', '600');

    loading = true;
    fetch(`${apiBase}/deputes?${params}`)
      .then((r) => r.json())
      .then((data: { items: Depute[]; total: number }) => {
        deputes = data.items ?? [];
        total = data.total ?? 0;
        loading = false;

        // Build dept list from initial unfiltered load
        if (!selectedGroupe && !selectedDept && !search && departements.length === 0) {
          const seen = new Map<string, string>();
          for (const d of deputes) {
            if (d.num_departement && d.nom_circonscription && !seen.has(d.num_departement)) {
              seen.set(d.num_departement, d.nom_circonscription);
            }
          }
          departements = [...seen.entries()]
            .map(([code, nom]) => ({ code, nom }))
            .sort((a, b) => a.code.localeCompare(b.code, undefined, { numeric: true }));
        }
      });
  });

  function resetFilters() {
    search = '';
    selectedGroupe = '';
    selectedDept = '';
  }
</script>

<svelte:head>
  <title>Les 577 députés — les 577</title>
  <meta name="description" content="Liste des 577 députés de l'Assemblée Nationale, 17e législature. Filtrez par groupe parlementaire, département ou recherchez par nom." />
  <meta property="og:title" content="Les 577 députés — les 577" />
  <meta property="og:description" content="Liste des 577 députés de l'Assemblée Nationale, 17e législature. Filtrez par groupe parlementaire, département ou recherchez par nom." />
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
    <select bind:value={selectedGroupe} class="select">
      <option value="">Tous les groupes</option>
      {#each groupes as g (g.id)}
        <option value={g.sigle}>{g.sigle} — {g.libelle}</option>
      {/each}
    </select>
    <select bind:value={selectedDept} class="select select--sm">
      <option value="">Tous les dpts</option>
      {#each departements as d (d.code)}
        <option value={d.code}>{d.code} — {d.nom}</option>
      {/each}
    </select>
    {#if hasFilters}
      <button class="reset-btn" onclick={resetFilters}>✕ Réinitialiser</button>
    {/if}
  </div>
</div>

{#if loading}
  <p class="muted">Chargement…</p>
{:else}
  <p class="count">
    {total} député{total > 1 ? 's' : ''}
    <span class="info-wrap" aria-describedby="info-tooltip">
      <span class="info-icon" aria-label="Information sur le nombre de députés">ⓘ</span>
      <span class="info-tooltip" id="info-tooltip" role="tooltip">
        L'Assemblée compte 577 sièges.
        {#if hors_hemicycle > 0}
          {hors_hemicycle} suppléant{hors_hemicycle > 1 ? 's' : ''} récemment entré{hors_hemicycle > 1 ? 's' : ''} en fonction
          n'apparaissent pas dans l'hémicycle : l'AN leur attribue un numéro de siège provisoire
          (> 577) en attendant une réaffectation officielle. Ils figurent bien dans cette liste
          et leurs fiches sont accessibles.
        {:else}
          Tous les députés actifs ont un siège attribué dans l'hémicycle.
        {/if}
      </span>
    </span>
  </p>
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
    align-items: center;
  }

  .input,
  .select {
    padding: 0.4rem 0.75rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    font-size: 0.9rem;
    background: var(--color-surface);
    color: var(--color-text);
    height: 2.1rem;
  }

  .input { min-width: 200px; }

  .select {
    min-width: 180px;
    cursor: pointer;
    appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%236b6b66' d='M6 8L1 3h10z'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 0.6rem center;
    padding-right: 2rem;
  }

  .select--sm { min-width: 140px; }

  .reset-btn {
    padding: 0.4rem 0.75rem;
    font-size: 0.8rem;
    background: none;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    color: var(--color-text-muted);
    cursor: pointer;
    height: 2.1rem;
    white-space: nowrap;
  }

  .reset-btn:hover {
    background: var(--color-border);
    color: var(--color-text);
  }

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

  .info-wrap {
    position: relative;
    display: inline-block;
    vertical-align: middle;
  }

  .info-icon {
    cursor: default;
    color: var(--color-text-muted);
    font-size: 0.85rem;
    user-select: none;
  }

  .info-tooltip {
    display: none;
    position: absolute;
    top: 0;
    left: calc(100% + 8px);
    width: 280px;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-md);
    padding: 0.6rem 0.75rem;
    font-size: 0.78rem;
    line-height: 1.5;
    color: var(--color-text);
    white-space: normal;
    z-index: 100;
    pointer-events: none;
  }

  .info-wrap:hover .info-tooltip,
  .info-wrap:focus-within .info-tooltip {
    display: block;
  }
</style>

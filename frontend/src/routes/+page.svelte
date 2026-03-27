<script lang="ts">
  import Hemicycle from '$lib/components/Hemicycle.svelte';
  import { apiBase } from '$lib/api';

  let deputes = $state<any[]>([]);
  let loading = $state(true);
  let error = $state<string | null>(null);

  $effect(() => {
    fetch(`${apiBase}/api/deputes?limit=577`)
      .then((r) => { if (!r.ok) throw new Error(String(r.status)); return r.json(); })
      .then((data) => {
        deputes = data.items ?? [];
        loading = false;
      })
      .catch(() => {
        error = 'Impossible de charger les données.';
        loading = false;
      });
  });

  const groupes = $derived.by(() => {
    const seen = new Map<string, { sigle: string; libelle: string; couleur: string; count: number }>();
    for (const d of deputes) {
      if (!d.groupe) continue;
      const g = d.groupe;
      if (seen.has(g.id)) {
        seen.get(g.id)!.count++;
      } else {
        seen.set(g.id, { sigle: g.sigle, libelle: g.libelle, couleur: g.couleur ?? '#cbcbcb', count: 1 });
      }
    }
    return [...seen.values()].sort((a, b) => b.count - a.count);
  });

  let selectedGroupe = $state<string | null>(null);

  function toggleGroupe(sigle: string) {
    selectedGroupe = selectedGroupe === sigle ? null : sigle;
  }
</script>

<svelte:head>
  <title>Hémicycle — Assemblée Nationale</title>
</svelte:head>

<section class="hero">
  <h1>Hémicycle interactif</h1>
  <p>577 sièges · 17<sup>e</sup> législature · Survolez un siège pour en savoir plus</p>
</section>

{#if loading}
  <div class="loading">Chargement…</div>
{:else if error}
  <div class="error">{error}</div>
{:else}
  <div class="legend">
    {#each groupes as g}
      <button
        class="legend-item"
        class:active={selectedGroupe === g.sigle}
        class:dimmed={selectedGroupe !== null && selectedGroupe !== g.sigle}
        onclick={() => toggleGroupe(g.sigle)}
        title={selectedGroupe === g.sigle ? 'Réinitialiser le filtre' : `Filtrer : ${g.libelle}`}
      >
        <span class="swatch" style="background: {g.couleur}"></span>
        <span class="sigle">{g.sigle}</span>
        <span class="libelle">{g.libelle}</span>
        <span class="count">({g.count})</span>
      </button>
    {/each}
  </div>
  <Hemicycle mode="groupe" data={deputes} {selectedGroupe} />
{/if}

<style>
  .hero {
    margin-bottom: 2rem;
  }

  h1 {
    font-size: 1.75rem;
    font-weight: 700;
    margin-bottom: 0.5rem;
  }

  p {
    color: var(--color-text-muted);
  }

  .loading,
  .error {
    padding: 2rem;
    text-align: center;
    color: var(--color-text-muted);
  }

  .legend {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem 0.75rem;
    margin-bottom: 1rem;
    max-width: 900px;
    margin-inline: auto;
  }

  .legend-item {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.8rem;
    padding: 0.25rem 0.5rem;
    border-radius: var(--radius-sm);
    border: 1px solid transparent;
    background: none;
    cursor: pointer;
    color: inherit;
    transition: background 0.12s, opacity 0.12s, border-color 0.12s;
  }

  .legend-item:hover {
    background: var(--color-border);
  }

  .legend-item.active {
    border-color: var(--color-border);
    background: var(--color-surface);
  }

  .legend-item.dimmed {
    opacity: 0.35;
  }

  .swatch {
    width: 10px;
    height: 10px;
    border-radius: 2px;
    flex-shrink: 0;
  }

  .sigle {
    font-weight: 700;
    color: var(--color-text);
  }

  .libelle {
    color: var(--color-text-muted);
  }

  .count {
    color: var(--color-text-muted);
    font-size: 0.72rem;
  }
</style>

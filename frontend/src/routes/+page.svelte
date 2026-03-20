<script lang="ts">
  import Hemicycle from '$lib/components/Hemicycle.svelte';

  let deputes = $state<any[]>([]);
  let loading = $state(true);
  let error = $state<string | null>(null);

  $effect(() => {
    fetch('/api/deputes')
      .then((r) => r.json())
      .then((data) => {
        deputes = data;
        loading = false;
      })
      .catch(() => {
        error = 'Impossible de charger les données.';
        loading = false;
      });
  });
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
  <Hemicycle mode="groupe" data={deputes} />
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
</style>

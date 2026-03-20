<script lang="ts">
  import { page } from '$app/stores';
  import Hemicycle from '$lib/components/Hemicycle.svelte';

  const id = $derived($page.params.id);

  let scrutin = $state<any>(null);
  let loading = $state(true);
  let error = $state<string | null>(null);

  $effect(() => {
    loading = true;
    fetch(`/api/votes/${id}`)
      .then((r) => {
        if (!r.ok) throw new Error('Scrutin introuvable');
        return r.json();
      })
      .then((data) => {
        scrutin = data;
        loading = false;
      })
      .catch((e) => {
        error = e.message;
        loading = false;
      });
  });
</script>

<svelte:head>
  <title>{scrutin?.titre ?? 'Scrutin'} — AN</title>
</svelte:head>

{#if loading}
  <p class="muted">Chargement…</p>
{:else if error}
  <p class="error">{error}</p>
{:else if scrutin}
  <div class="header">
    <p class="meta">
      Scrutin n°{scrutin.numero} · {scrutin.date_seance}
      {#if scrutin.sort}
        · <strong class="sort" class:adopte={scrutin.sort === 'adopté'} class:rejete={scrutin.sort === 'rejeté'}>
          {scrutin.sort}
        </strong>
      {/if}
    </p>
    <h1>{scrutin.titre}</h1>
    {#if scrutin.url_an}
      <a href={scrutin.url_an} target="_blank" rel="noopener noreferrer">
        Document source officiel →
      </a>
    {/if}
  </div>

  <div class="stats">
    {#if scrutin.nombre_votants != null}
      <div class="stat"><span class="val">{scrutin.nombre_votants}</span><span class="lbl">votants</span></div>
    {/if}
    {#if scrutin.nombre_pours != null}
      <div class="stat pour"><span class="val">{scrutin.nombre_pours}</span><span class="lbl">pour</span></div>
    {/if}
    {#if scrutin.nombre_contres != null}
      <div class="stat contre"><span class="val">{scrutin.nombre_contres}</span><span class="lbl">contre</span></div>
    {/if}
    {#if scrutin.nombre_abstentions != null}
      <div class="stat"><span class="val">{scrutin.nombre_abstentions}</span><span class="lbl">abstentions</span></div>
    {/if}
  </div>

  <Hemicycle mode="vote" data={scrutin.votes} />
{/if}

<style>
  .header { margin-bottom: 1.5rem; }

  .meta {
    font-size: 0.85rem;
    color: var(--color-text-muted);
    margin-bottom: 0.5rem;
  }

  h1 { font-size: 1.5rem; font-weight: 700; margin-bottom: 0.75rem; }

  .sort.adopte { color: var(--color-vote); }
  .sort.rejete { color: var(--color-absent); }

  .stats {
    display: flex;
    gap: 1.5rem;
    margin-bottom: 2rem;
  }

  .stat {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.2rem;
  }

  .val { font-size: 1.5rem; font-weight: 700; }
  .lbl { font-size: 0.75rem; color: var(--color-text-muted); text-transform: uppercase; }

  .pour .val { color: var(--color-vote); }
  .contre .val { color: var(--color-absent); }

  .muted, .error { color: var(--color-text-muted); }
  .error { color: var(--color-absent); }
</style>

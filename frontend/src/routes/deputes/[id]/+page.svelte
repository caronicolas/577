<script lang="ts">
  import { page } from '$app/stores';
  import ActivityCalendar from '$lib/components/ActivityCalendar.svelte';

  const id = $derived($page.params.id);

  let depute = $state<any>(null);
  let amendements = $state<any[]>([]);
  let votes = $state<any[]>([]);
  let loading = $state(true);

  $effect(() => {
    loading = true;
    Promise.all([
      fetch(`/api/deputes/${id}`).then((r) => r.json()),
      fetch(`/api/amendements?depute_id=${id}&limit=100`).then((r) => r.json()),
    ]).then(([d, a]) => {
      depute = d;
      amendements = a;
      loading = false;
    });
  });
</script>

<svelte:head>
  <title>{depute ? `${depute.prenom} ${depute.nom_de_famille}` : 'Député'} — AN</title>
</svelte:head>

{#if loading}
  <p class="muted">Chargement…</p>
{:else if depute}
  <div class="profile">
    {#if depute.url_photo}
      <img src={depute.url_photo} alt={depute.nom} class="photo" />
    {/if}
    <div class="meta">
      <h1>{depute.prenom} {depute.nom_de_famille}</h1>
      {#if depute.groupe_sigle}
        <span
          class="badge"
          style="background: {depute.groupe_couleur ?? 'var(--color-border)'}"
        >{depute.groupe_sigle}</span>
      {/if}
      <p class="circ">{depute.nom_circonscription ?? ''}{depute.num_departement ? ` (${depute.num_departement})` : ''}</p>
      {#if depute.profession}
        <p class="detail">{depute.profession}</p>
      {/if}
      {#if depute.twitter}
        <a
          href="https://twitter.com/{depute.twitter}"
          target="_blank"
          rel="noopener noreferrer"
          class="twitter"
        >@{depute.twitter}</a>
      {/if}
      {#if depute.url_an}
        <a href={depute.url_an} target="_blank" rel="noopener noreferrer">
          Fiche AN officielle
        </a>
      {/if}
    </div>
  </div>

  <section class="section">
    <h2>Activité — 17<sup>e</sup> législature</h2>
    <ActivityCalendar activites={[]} dateDebut="2024-06-18" dateFin={new Date().toISOString().slice(0, 10)} />
  </section>

  <section class="section">
    <h2>Amendements ({amendements.length})</h2>
    {#if amendements.length === 0}
      <p class="muted">Aucun amendement enregistré.</p>
    {:else}
      <ul class="list">
        {#each amendements as a (a.id)}
          <li class="list-item">
            <span class="amend-num">{a.numero ?? '—'}</span>
            <span class="amend-titre">{a.titre ?? 'Sans titre'}</span>
            <span class="amend-sort" data-sort={a.sort}>{a.sort ?? ''}</span>
          </li>
        {/each}
      </ul>
    {/if}
  </section>
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

  .badge {
    display: inline-block;
    font-size: 0.75rem;
    font-weight: 700;
    padding: 0.15rem 0.5rem;
    border-radius: var(--radius-sm);
    color: #fff;
    width: fit-content;
  }

  .circ { color: var(--color-text-muted); }
  .detail { font-size: 0.875rem; color: var(--color-text-muted); }
  .twitter { font-size: 0.875rem; }

  .section { margin-bottom: 2.5rem; }

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

  .amend-num {
    font-family: var(--font-mono);
    font-size: 0.75rem;
    color: var(--color-text-muted);
    flex-shrink: 0;
    width: 60px;
  }

  .amend-titre { flex: 1; }

  .amend-sort[data-sort="Adopté"] { color: var(--color-vote); }
  .amend-sort[data-sort="Rejeté"] { color: var(--color-absent); }

  .muted { color: var(--color-text-muted); }
</style>

<script lang="ts">
  import { page } from '$app/stores';
  import Hemicycle from '$lib/components/Hemicycle.svelte';
  import { apiBase } from '$lib/api';

  const id = $derived($page.params.id);

  let scrutin = $state<any>(null);
  let loading = $state(true);
  let error = $state<string | null>(null);
  let selectedGroupe = $state<string | null>(null);

  $effect(() => {
    loading = true;
    selectedGroupe = null;
    fetch(`${apiBase}/votes/${id}`)
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

  function toggleGroupe(sigle: string) {
    selectedGroupe = selectedGroupe === sigle ? null : sigle;
  }

  interface GroupeStats {
    sigle: string;
    couleur: string;
    pour: number;
    contre: number;
    abstention: number;
    nonVotant: number;
    total: number;
  }

  const groupeStats = $derived.by((): GroupeStats[] => {
    if (!scrutin?.votes) return [];
    const map = new Map<string, GroupeStats>();
    for (const v of scrutin.votes) {
      const sigle = v.groupe_sigle ?? '?';
      const couleur = v.groupe_couleur ?? '#cbcbcb';
      if (!map.has(sigle)) {
        map.set(sigle, { sigle, couleur, pour: 0, contre: 0, abstention: 0, nonVotant: 0, total: 0 });
      }
      const g = map.get(sigle)!;
      g.total++;
      if (v.position === 'pour') g.pour++;
      else if (v.position === 'contre') g.contre++;
      else if (v.position === 'abstention') g.abstention++;
      else g.nonVotant++;
    }
    return [...map.values()].sort((a, b) => b.total - a.total);
  });

  const totalPour = $derived(groupeStats.reduce((s, g) => s + g.pour, 0));
  const totalContre = $derived(groupeStats.reduce((s, g) => s + g.contre, 0));
  const totalAbstention = $derived(groupeStats.reduce((s, g) => s + g.abstention, 0));
  const maxVotes = $derived(Math.max(totalPour, totalContre, totalAbstention, 1));

  let barTooltip = $state<{ libelle: string; count: number; label: string; x: number; y: number } | null>(null);

  function showBarTooltip(e: MouseEvent, g: GroupeStats, label: string, count: number) {
    barTooltip = { libelle: g.sigle, count, label, x: e.clientX, y: e.clientY };
  }

  function moveBarTooltip(e: MouseEvent) {
    if (barTooltip) { barTooltip = { ...barTooltip, x: e.clientX, y: e.clientY }; }
  }

  function hideBarTooltip() { barTooltip = null; }
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

  <div class="legend">
    {#each groupeStats as g}
      <button
        class="legend-item"
        class:active={selectedGroupe === g.sigle}
        class:dimmed={selectedGroupe !== null && selectedGroupe !== g.sigle}
        onclick={() => toggleGroupe(g.sigle)}
        title={selectedGroupe === g.sigle ? 'Réinitialiser' : g.sigle}
      >
        <span class="swatch" style="background: {g.couleur}"></span>
        <span class="sigle">{g.sigle}</span>
        <span class="count">({g.total})</span>
      </button>
    {/each}
  </div>

  <Hemicycle mode="vote" data={scrutin.votes} {selectedGroupe} />

  <div class="chart">
    {#each [
      { label: 'Pour', total: totalPour, position: 'pour' as const, cls: 'pour' },
      { label: 'Contre', total: totalContre, position: 'contre' as const, cls: 'contre' },
      { label: 'Abstention', total: totalAbstention, position: 'abstention' as const, cls: 'abst' },
    ] as row}
      {#if row.total > 0}
        <div class="chart-row">
          <span class="chart-label {row.cls}">{row.label}</span>
          <div class="bar-track" style="width: {(row.total / maxVotes) * 100}%">
            {#each groupeStats.filter(g => g[row.position] > 0) as g}
              {@const pct = (g[row.position] / row.total) * 100}
              <div
                class="bar-seg"
                class:dimmed={selectedGroupe !== null && selectedGroupe !== g.sigle}
                style="width: {pct}%; background: {g.couleur}"
                onmouseenter={(e) => showBarTooltip(e, g, row.label, g[row.position])}
                onmousemove={moveBarTooltip}
                onmouseleave={hideBarTooltip}
                role="img"
                aria-label="{g.sigle} : {g[row.position]} {row.label.toLowerCase()}"
              ></div>
            {/each}
          </div>
          <span class="chart-count">{row.total}</span>
        </div>
      {/if}
    {/each}
  </div>
{/if}

{#if barTooltip}
  <div
    class="bar-tooltip"
    style="left: {barTooltip.x + 12}px; top: {barTooltip.y - 8}px"
    role="tooltip"
  >
    <strong>{barTooltip.libelle}</strong>
    <span>{barTooltip.count} {barTooltip.label.toLowerCase()}</span>
  </div>
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

  .bar-tooltip {
    position: fixed;
    z-index: 300;
    pointer-events: none;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    padding: 0.4rem 0.65rem;
    box-shadow: var(--shadow-md);
    font-size: 0.8rem;
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
    white-space: nowrap;
  }

  /* Légende groupes */
  .legend {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem 0.75rem;
    margin-top: 1.5rem;
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

  .legend-item:hover { background: var(--color-border); }
  .legend-item.active { border-color: var(--color-border); background: var(--color-surface); }
  .legend-item.dimmed { opacity: 0.35; }

  .swatch {
    width: 10px;
    height: 10px;
    border-radius: 2px;
    flex-shrink: 0;
  }

  .sigle { font-weight: 700; }
  .count { color: var(--color-text-muted); font-size: 0.72rem; }

  /* Graphique barres */
  .chart {
    max-width: 900px;
    margin: 1.5rem auto 0;
    display: flex;
    flex-direction: column;
    gap: 0.6rem;
  }

  .chart-row {
    display: grid;
    grid-template-columns: 80px 1fr 40px;
    align-items: center;
    gap: 0.75rem;
  }

  .chart-label {
    font-size: 0.8rem;
    font-weight: 600;
    text-align: right;
  }

  .chart-label.pour { color: var(--color-vote); }
  .chart-label.contre { color: var(--color-absent); }
  .chart-label.abst { color: var(--color-text-muted); }

  .bar-track {
    display: flex;
    height: 20px;
    border-radius: var(--radius-sm);
    overflow: hidden;
    min-width: 2px;
  }

  .bar-seg {
    height: 100%;
    transition: opacity 0.15s;
    flex-shrink: 0;
  }

  .bar-seg.dimmed { opacity: 0.2; }

  .chart-count {
    font-size: 0.8rem;
    font-weight: 600;
    color: var(--color-text-muted);
  }
</style>

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
      if (v.position === 'absent') continue; // absents exclus des stats groupe
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
  const totalAbsents = $derived(scrutin?.votes?.filter((v: any) => v.position === 'absent').length ?? 0);

  const TYPE_VOTE_INFO: Record<string, string> = {
    'scrutin public solennel': 'Scrutin solennel — vote public et nominatif sur les textes les plus importants (budget, loi de finances, motion de confiance…). Chaque député·e vote individuellement et son vote est publié.',
    'scrutin public ordinaire': 'Scrutin ordinaire — vote public nominatif en séance plénière sur des textes courants. Moins médiatisé que le solennel, mais le vote de chaque député·e est également enregistré.',
    'motion de censure': "Motion de censure — vote visant à renverser le gouvernement. Adoptée si la majorité absolue des membres de l'Assemblée vote pour.",
  };

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
  {#if scrutin}
    <title>{scrutin.titre} — les 577</title>
    <meta name="description" content="Scrutin n°{scrutin.numero} du {scrutin.date_seance} — {scrutin.titre}. Résultats détaillés et hémicycle interactif." />
    <meta property="og:title" content="{scrutin.titre} — les 577" />
    <meta property="og:description" content="Scrutin n°{scrutin.numero} du {scrutin.date_seance} — {scrutin.titre}. Résultats détaillés et hémicycle interactif." />
  {:else}
    <title>Scrutin — les 577</title>
  {/if}
</svelte:head>

{#if loading}
  <p class="muted">Chargement…</p>
{:else if error}
  <p class="error">{error}</p>
{:else if scrutin}
  <div class="header">
    <h1>{scrutin.titre}</h1>
    <p class="meta">
      Scrutin n°{scrutin.numero} · {scrutin.date_seance}
      {#if scrutin.sort}
        · <strong class="sort" class:adopte={scrutin.sort === 'adopté'} class:rejete={scrutin.sort === 'rejeté'}>
          {scrutin.sort}
        </strong>
      {/if}
      {#if scrutin.type_vote}
        · <span
            class="type-vote-badge"
            data-tooltip={TYPE_VOTE_INFO[scrutin.type_vote] ?? scrutin.type_vote}
          >{scrutin.type_vote}</span>
      {/if}
    </p>
    {#if scrutin.dossier_libelle}
      <a class="dossier-tag" href="/votes?dossier_ref={scrutin.dossier_ref}">
        {scrutin.dossier_libelle}
      </a>
    {/if}
    {#if scrutin.url_an}
      <a href={scrutin.url_an} target="_blank" rel="noopener noreferrer">
        Document source officiel →
      </a>
    {/if}
    {#if scrutin.expose_sommaire}
      <div class="expose">
        <p class="expose-label">Exposé sommaire</p>
        <p class="expose-text">{scrutin.expose_sommaire}</p>
      </div>
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
    {#if totalAbsents > 0}
      <div class="stat absent"><span class="val">{totalAbsents}</span><span class="lbl">absents</span></div>
    {/if}
  </div>

  <div class="color-legend">
    <span class="cl-item"><span class="cl-swatch" style="background:#38a169"></span>Pour</span>
    <span class="cl-item"><span class="cl-swatch" style="background:#e53e3e"></span>Contre</span>
    <span class="cl-item"><span class="cl-swatch" style="background:#a0aec0"></span>Abstention</span>
    <span class="cl-item"><span class="cl-swatch" style="background:#718096"></span>Non-votant</span>
    <span class="cl-item"><span class="cl-swatch" style="background:#1a202c"></span>Absent</span>
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

  .dossier-tag {
    display: inline-block;
    background: var(--color-border, #e2e8f0);
    color: var(--color-text-muted);
    border-radius: 3px;
    padding: 0.2rem 0.6rem;
    font-size: 0.78rem;
    margin-top: 0.4rem;
    margin-bottom: 0.5rem;
    text-decoration: none;
    transition: background 0.15s, color 0.15s;
  }

  .dossier-tag:hover {
    background: var(--color-text-muted);
    color: var(--color-surface);
    text-decoration: none;
  }

  .expose {
    margin-top: 1rem;
    padding: 0.75rem 1rem;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    max-width: 720px;
  }

  .expose-label {
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--color-text-muted);
    margin-bottom: 0.4rem;
  }

  .expose-text {
    font-size: 0.875rem;
    line-height: 1.6;
    color: var(--color-text);
  }

  h1 { font-size: 1.5rem; font-weight: 700; margin-bottom: 0.5rem; }

  .meta {
    font-size: 0.95rem;
    color: var(--color-text-muted);
    margin-bottom: 0.75rem;
  }

  .sort { font-weight: 600; }
  .sort.adopte { color: var(--color-vote); }
  .sort.rejete { color: var(--color-absent); }

  .type-vote-badge {
    position: relative;
    display: inline-block;
    font-size: 0.75rem;
    padding: 0.15rem 0.5rem;
    border-radius: var(--radius-sm);
    background: var(--color-bg);
    border: 1px solid var(--color-border);
    color: var(--color-text-muted);
    cursor: help;
    text-transform: capitalize;
    vertical-align: middle;
  }

  .type-vote-badge[data-tooltip]::after {
    content: attr(data-tooltip);
    position: absolute;
    bottom: calc(100% + 6px);
    left: 50%;
    transform: translateX(-50%);
    background: var(--color-text);
    color: var(--color-surface);
    font-size: 0.75rem;
    line-height: 1.45;
    padding: 0.5rem 0.75rem;
    border-radius: var(--radius-sm);
    width: 280px;
    white-space: normal;
    pointer-events: none;
    opacity: 0;
    transition: opacity 0.15s;
    z-index: 10;
    text-transform: none;
    font-weight: 400;
  }

  .type-vote-badge[data-tooltip]:hover::after {
    opacity: 1;
  }

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
  .absent .val { color: #1a202c; }

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

  /* Légende couleurs vote */
  .color-legend {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem 1rem;
    font-size: 0.78rem;
    color: var(--color-text-muted);
    margin-bottom: 1rem;
  }

  .cl-item {
    display: flex;
    align-items: center;
    gap: 0.35rem;
  }

  .cl-swatch {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 2px;
    flex-shrink: 0;
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

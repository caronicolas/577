<script lang="ts">
  interface VoteJour {
    scrutin_id: string;
    titre: string;
    position: string; // pour / contre / abstention / nonVotant
  }

  interface AmendementJour {
    id: string;
    numero: string | null;
    titre: string | null;
    url_an: string | null;
  }

  interface CommissionJour {
    reunion_id: string;
    titre: string | null;
    heure_debut: string | null;
    organe_libelle: string | null;
  }

  interface Activite {
    date: string; // YYYY-MM-DD
    present: boolean;
    a_vote: boolean;
    a_pris_parole: boolean;
    a_depose_amendement: boolean;
    a_commission: boolean;
    votes: VoteJour[];
    amendements: AmendementJour[];
    commissions: CommissionJour[];
    nb_scrutins_seance: number | null;
  }

  interface Props {
    activites: Activite[];
    dateDebut: string;
    dateFin: string;
  }

  const { activites, dateDebut, dateFin }: Props = $props();

  const CELL = 12;
  const GAP = 2;
  const STEP = CELL + GAP;
  const WEEKS_LABEL_W = 24;
  const MONTH_LABEL_H = 14;

  /** Construit un map date ISO → activité */
  const activiteByDate = $derived(
    new Map(activites.map((a) => [a.date, a]))
  );

  /** Génère toutes les dates entre dateDebut et dateFin, alignées sur semaine ISO (lundi) */
  const weeks = $derived.by(() => {
    const start = new Date(dateDebut);
    const end = new Date(dateFin);

    // Reculer au lundi précédent
    const monday = new Date(start);
    monday.setDate(monday.getDate() - ((monday.getDay() + 6) % 7));

    const allWeeks: string[][] = [];
    let current = new Date(monday);

    while (current <= end) {
      const week: string[] = [];
      for (let d = 0; d < 7; d++) {
        week.push(current.toISOString().slice(0, 10));
        current.setDate(current.getDate() + 1);
      }
      allWeeks.push(week);
    }
    return allWeeks;
  });

  function cellColor(date: string): string {
    const a = activiteByDate.get(date);
    if (!a) return '#edf2f7'; // hors période ou pas de données
    if (!a.present) return 'var(--color-absent)';
    if (a.a_vote && (a.a_pris_parole || a.a_depose_amendement)) return 'var(--color-vote-actif)';
    if (a.a_vote) return 'var(--color-vote)';
    if (a.a_commission) return 'var(--color-commission)';
    return 'var(--color-present)';
  }

  function cellLabel(date: string): string {
    const a = activiteByDate.get(date);
    if (!a) return date;
    const parts: string[] = [date];
    if (!a.present) parts.push('Absent');
    else {
      parts.push('Présent');
      if (a.a_vote) parts.push('· a voté');
      if (a.a_pris_parole) parts.push('· prise de parole');
      if (a.a_depose_amendement) parts.push('· amendement');
    }
    return parts.join(' ');
  }

  const monthLabels = $derived.by(() => {
    const labels: { wi: number; label: string }[] = [];
    let lastMonth = -1;
    for (let wi = 0; wi < weeks.length; wi++) {
      const d = new Date(weeks[wi][0] + 'T12:00:00');
      const m = d.getMonth();
      if (m !== lastMonth) {
        labels.push({ wi, label: d.toLocaleString('fr-FR', { month: 'short' }) });
        lastMonth = m;
      }
    }
    return labels;
  });

  const svgWidth = $derived(WEEKS_LABEL_W + weeks.length * STEP);
  const svgHeight = $derived(MONTH_LABEL_H + 7 * STEP);

  const DAY_LABELS = ['L', 'M', 'M', 'J', 'V', 'S', 'D'];

  const dateFormatter = new Intl.DateTimeFormat('fr-FR', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });

  interface TooltipState {
    date: string;
    activite: Activite | null;
    x: number;
    y: number;
    anchorY: number; // centre vertical de la cellule survolée
  }

  let tooltip = $state<TooltipState | null>(null);
  let tooltipEl = $state<HTMLElement | null>(null);
  let calendarEl = $state<HTMLElement | null>(null);
  let hideTimer: ReturnType<typeof setTimeout> | null = null;

  $effect(() => {
    if (calendarEl && weeks.length > 0) {
      calendarEl.scrollLeft = calendarEl.scrollWidth;
    }
  });

  // Après chaque rendu du tooltip, on ajuste y en fonction de la vraie hauteur
  $effect(() => {
    if (!tooltipEl || !tooltip) return;
    const h = tooltipEl.offsetHeight;
    const MARGIN = 8;
    const ideal = tooltip.anchorY - h / 2;
    const clamped = Math.max(MARGIN, Math.min(ideal, window.innerHeight - h - MARGIN));
    if (clamped !== tooltip.y) {
      tooltip = { ...tooltip, y: clamped };
    }
  });

  function tooltipX(cell: DOMRect): number {
    const TOOLTIP_W = 340;
    const MARGIN = 8;
    const right = cell.right + MARGIN;
    return right + TOOLTIP_W > window.innerWidth ? cell.left - TOOLTIP_W - MARGIN : right;
  }

  function handleMouseEnter(e: MouseEvent, date: string) {
    if (hideTimer) { clearTimeout(hideTimer); hideTimer = null; }
    const cell = (e.currentTarget as SVGRectElement).getBoundingClientRect();
    const anchorY = cell.top + cell.height / 2;
    tooltip = {
      date,
      activite: activiteByDate.get(date) ?? null,
      x: tooltipX(cell),
      y: anchorY, // position initiale — sera corrigée par $effect
      anchorY,
    };
  }

  function handleCellLeave() {
    hideTimer = setTimeout(() => { tooltip = null; hideTimer = null; }, 120);
  }

  function handleTooltipEnter() {
    if (hideTimer) { clearTimeout(hideTimer); hideTimer = null; }
  }

  function handleTooltipLeave() {
    tooltip = null;
  }

  function formatDate(iso: string): string {
    const d = new Date(iso + 'T12:00:00');
    const s = dateFormatter.format(d);
    return s.charAt(0).toUpperCase() + s.slice(1);
  }

  const POSITION_LABEL: Record<string, string> = {
    pour: 'Pour',
    contre: 'Contre',
    abstention: 'Abstention',
    nonVotant: 'Non votant',
  };
</script>

<div class="calendar" bind:this={calendarEl}>
  <svg
    width={svgWidth}
    height={svgHeight}
    role="img"
    aria-label="Calendrier d'activité"
  >
    <!-- Labels mois -->
    {#each monthLabels as { wi, label }}
      <text
        x={WEEKS_LABEL_W + wi * STEP}
        y={MONTH_LABEL_H - 3}
        font-size="8"
        fill="var(--color-text-muted)"
      >{label}</text>
    {/each}

    <!-- Labels jours -->
    {#each DAY_LABELS as label, i}
      <text
        x={WEEKS_LABEL_W - 4}
        y={MONTH_LABEL_H + i * STEP + CELL * 0.85}
        text-anchor="end"
        font-size="8"
        fill="var(--color-text-muted)"
      >{label}</text>
    {/each}

    <!-- Cellules -->
    {#each weeks as week, wi}
      {#each week as date, di}
        <rect
          x={WEEKS_LABEL_W + wi * STEP}
          y={MONTH_LABEL_H + di * STEP}
          width={CELL}
          height={CELL}
          rx="2"
          fill={cellColor(date)}
          role="img"
          aria-label={cellLabel(date)}
          tabindex="-1"
          onmouseenter={(e) => handleMouseEnter(e, date)}
          onmouseleave={handleCellLeave}
        />
      {/each}
    {/each}
  </svg>

  <!-- Légende -->
</div>

{#if tooltip}
  {@const a = tooltip.activite}
  <div
    class="tooltip"
    style="left: {tooltip.x}px; top: {tooltip.y}px"
    bind:this={tooltipEl}
    onmouseenter={handleTooltipEnter}
    onmouseleave={handleTooltipLeave}
    role="tooltip"
  >
    <div class="tooltip-date">{formatDate(tooltip.date)}</div>
    {#if !a}
      <div class="tooltip-line">Aucune donnée</div>
    {:else if !a.present}
      <div class="tooltip-line tooltip-absent">Absent</div>
      {#if a.nb_scrutins_seance}
        <div class="tooltip-note">
          {a.nb_scrutins_seance} scrutin{a.nb_scrutins_seance > 1 ? 's' : ''} ont eu lieu ce jour
          sans qu'il·elle n'y ait participé (ni pour, ni contre, ni abstention, ni non-votant).
        </div>
      {/if}
    {:else}
      <div class="tooltip-line">Présent en séance</div>
      {#if a.votes.length > 0}
        <div class="tooltip-section">Votes</div>
        {#each a.votes as v}
          <a class="tooltip-line tooltip-link" href="/votes/{v.scrutin_id}">
            <span class="position position--{v.position.toLowerCase()}">{POSITION_LABEL[v.position] ?? v.position}</span>
            <span>{v.titre}</span>
          </a>
        {/each}
      {/if}
      {#if a.amendements.length > 0}
        <div class="tooltip-section">Amendements déposés</div>
        {#each a.amendements as am}
          {#if am.url_an}
            <a class="tooltip-line tooltip-link" href={am.url_an} target="_blank" rel="noopener noreferrer">
              {am.numero ? `${am.numero} — ` : ''}{am.titre ?? 'Sans titre'}
            </a>
          {:else}
            <div class="tooltip-line">{am.numero ? `${am.numero} — ` : ''}{am.titre ?? 'Sans titre'}</div>
          {/if}
        {/each}
      {/if}
      {#if a.commissions.length > 0}
        <div class="tooltip-section">Commissions</div>
        {#each a.commissions as c}
          <div class="tooltip-line">
            {#if c.heure_debut}<span class="commission-heure">{c.heure_debut}</span>{/if}
            {c.organe_libelle ?? c.titre ?? 'Commission'}
          </div>
        {/each}
      {/if}
    {/if}
  </div>
{/if}

<div class="legend">
  <span class="swatch" style="background: var(--color-absent)"></span> Absent
  <span class="swatch" style="background: var(--color-present)"></span> Présent
  <span class="swatch" style="background: var(--color-vote)"></span> A voté
  <span class="swatch" style="background: var(--color-vote-actif)"></span> A voté + intervention
  <span class="swatch" style="background: var(--color-commission)"></span> Commission
</div>

<style>
  .calendar {
    overflow-x: auto;
    padding-bottom: 0.5rem;
  }

  svg {
    display: block;
    overflow: visible;
  }

  .legend {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    font-size: 0.75rem;
    color: var(--color-text-muted);
    margin-top: 0.5rem;
    flex-wrap: wrap;
  }

  .swatch {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 2px;
  }

  .tooltip {
    position: fixed;
    background: var(--color-surface, #fff);
    border: 1px solid var(--color-border, #e2e8f0);
    border-radius: 6px;
    padding: 0.5rem 0.75rem;
    font-size: 0.8rem;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
    max-width: 340px;
    max-height: calc(100vh - 16px);
    overflow-y: auto;
    z-index: 1000;
  }

  .tooltip-link {
    display: flex;
    gap: 0.4rem;
    align-items: baseline;
    color: inherit;
    text-decoration: none;
    border-radius: 3px;
    padding: 0.1rem 0.2rem;
    margin: 0 -0.2rem;
    cursor: pointer;
  }

  .tooltip-link:hover {
    background: var(--color-border, #e2e8f0);
    text-decoration: none;
  }

  .tooltip-date {
    font-weight: 600;
    margin-bottom: 0.25rem;
    color: var(--color-text, #1a202c);
    white-space: nowrap;
  }

  .tooltip-section {
    font-weight: 600;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--color-text-muted, #718096);
    margin-top: 0.4rem;
    margin-bottom: 0.15rem;
  }

  .tooltip-line {
    color: var(--color-text-muted, #718096);
    display: flex;
    gap: 0.4rem;
    align-items: baseline;
    white-space: normal;
    line-height: 1.4;
    padding: 0.1rem 0;
  }

  .tooltip-line:not(.tooltip-link)::before {
    content: '· ';
    flex-shrink: 0;
  }

  .position {
    font-weight: 700;
    font-size: 0.7rem;
    padding: 0.05rem 0.3rem;
    border-radius: 3px;
    flex-shrink: 0;
  }

  .position--pour       { background: #c6f6d5; color: #276749; }
  .position--contre     { background: #fed7d7; color: #9b2c2c; }
  .position--abstention { background: #e2e8f0; color: #4a5568; }
  .position--nonvotant  { background: #e2e8f0; color: #718096; }

  .commission-heure {
    font-size: 0.7rem;
    font-family: var(--font-mono);
    color: var(--color-commission);
    flex-shrink: 0;
  }

  .tooltip-absent {
    color: var(--color-absent);
    font-weight: 600;
  }

  .tooltip-note {
    margin-top: 0.3rem;
    font-size: 0.75rem;
    color: var(--color-text-muted, #718096);
    line-height: 1.4;
    font-style: italic;
  }
</style>

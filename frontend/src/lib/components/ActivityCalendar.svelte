<script lang="ts">
  interface Activite {
    date: string; // YYYY-MM-DD
    present: boolean;
    a_vote: boolean;
    a_pris_parole: boolean;
    a_depose_amendement: boolean;
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

  const svgWidth = $derived(WEEKS_LABEL_W + weeks.length * STEP);
  const svgHeight = $derived(7 * STEP);

  const DAY_LABELS = ['L', 'M', 'M', 'J', 'V', 'S', 'D'];
</script>

<div class="calendar">
  <svg width={svgWidth} height={svgHeight + STEP} role="img" aria-label="Calendrier d'activité">
    <!-- Labels jours -->
    {#each DAY_LABELS as label, i}
      <text
        x={WEEKS_LABEL_W - 4}
        y={i * STEP + CELL * 0.85}
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
          y={di * STEP}
          width={CELL}
          height={CELL}
          rx="2"
          fill={cellColor(date)}
          role="cell"
          aria-label={cellLabel(date)}
        >
          <title>{cellLabel(date)}</title>
        </rect>
      {/each}
    {/each}
  </svg>

  <!-- Légende -->
  <div class="legend">
    <span class="swatch" style="background: var(--color-absent)"></span> Absent
    <span class="swatch" style="background: var(--color-present)"></span> Présent
    <span class="swatch" style="background: var(--color-vote)"></span> A voté
    <span class="swatch" style="background: var(--color-vote-actif)"></span> A voté + intervention
  </div>
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
</style>

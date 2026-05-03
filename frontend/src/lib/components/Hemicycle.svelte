<script lang="ts">
  import { goto } from '$app/navigation';
  import seatsData from '$lib/data/hemicycle-seats.json';
  import HemicycleTooltip from './HemicycleTooltip.svelte';

  type Mode = 'groupe' | 'vote';

  interface Props {
    mode: Mode;
    /** mode=groupe : tableau de DeputeListItem  |  mode=vote : tableau de VoteDeputeItem */
    data: any[];
    selectedGroupe?: string | null;
  }

  const { mode, data, selectedGroupe = null }: Props = $props();

  const SVG_W = seatsData.svg_width;
  const SVG_H = seatsData.svg_height;
  const SEAT_SIZE = 7;

  const VOTE_COLORS: Record<string, string> = {
    pour: '#38a169',
    contre: '#e53e3e',
    abstention: '#a0aec0',
    nonVotant: '#2d3748',
    absent: '#1a202c',
  };

  const DIMMED_COLOR = '#e2e8f0';

  /** Construit un map place → couleur selon le mode. */
  const colorByPlace = $derived.by(() => {
    const map = new Map<number, string>();
    if (mode === 'groupe') {
      for (const d of data) {
        if (d.place_hemicycle != null) {
          const isFiltered = selectedGroupe !== null && d.groupe?.sigle !== selectedGroupe;
          map.set(d.place_hemicycle, isFiltered ? DIMMED_COLOR : (d.groupe?.couleur ?? '#cbcbcb'));
        }
      }
    } else {
      for (const v of data) {
        if (v.place_hemicycle != null) {
          const isFiltered = selectedGroupe !== null && v.groupe_sigle !== selectedGroupe;
          map.set(v.place_hemicycle, isFiltered ? DIMMED_COLOR : (VOTE_COLORS[v.position] ?? '#cbcbcb'));
        }
      }
    }
    return map;
  });

  /** Construit un map place → donnée pour le tooltip. */
  const dataByPlace = $derived.by(() => {
    const map = new Map<number, any>();
    for (const d of data) {
      if (d.place_hemicycle != null) map.set(d.place_hemicycle, d);
    }
    return map;
  });

  let tooltip = $state<{ depute: any; x: number; y: number } | null>(null);
  const TOOLTIP_ID = 'hemicycle-tooltip';

  function showTooltip(depute: any, x: number, y: number) {
    tooltip = { depute, x, y };
  }

  function handleMouseEnter(e: MouseEvent, seat: (typeof seatsData.seats)[0]) {
    const d = dataByPlace.get(seat.place);
    if (!d) return;
    const rect = (e.currentTarget as SVGElement).closest('svg')!.getBoundingClientRect();
    showTooltip(d, e.clientX - rect.left, e.clientY - rect.top);
  }

  function handleFocus(e: FocusEvent, seat: (typeof seatsData.seats)[0]) {
    const d = dataByPlace.get(seat.place);
    if (!d) return;
    const el = e.currentTarget as SVGElement;
    const rect = el.closest('svg')!.getBoundingClientRect();
    const elRect = el.getBoundingClientRect();
    showTooltip(d, elRect.left - rect.left + SEAT_SIZE, elRect.top - rect.top);
  }

  function handleMouseLeave() {
    tooltip = null;
  }

  function handleBlur() {
    tooltip = null;
  }

  function handleClick(seat: (typeof seatsData.seats)[0]) {
    const d = dataByPlace.get(seat.place);
    if (!d) return;
    const id = d.depute_id ?? d.id;
    if (id) goto(`/deputes/${id}`);
  }

  function seatAriaLabel(seat: (typeof seatsData.seats)[0]): string {
    const d = dataByPlace.get(seat.place);
    if (!d) return `Siège vide ${seat.place}`;
    const nom = d.nom ?? d.depute_id ?? '';
    if (mode === 'groupe') {
      const groupe = d.groupe?.sigle ?? '';
      return groupe ? `${nom}, ${groupe}, siège ${seat.place}` : `${nom}, siège ${seat.place}`;
    }
    const pos = d.position ? `, ${d.position}` : '';
    return `${nom}${pos}, siège ${seat.place}`;
  }
</script>

<div class="hemicycle-wrapper">
  <svg
    viewBox="0 0 {SVG_W} {SVG_H}"
    xmlns="http://www.w3.org/2000/svg"
    aria-label="Hémicycle de l'Assemblée Nationale — {data.length} députés"
    role="img"
  >
    {#each seatsData.seats as seat (seat.place)}
      {@const color = colorByPlace.get(seat.place) ?? '#e2e8f0'}
      {@const interactive = dataByPlace.has(seat.place)}
      <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
      <rect
        x={seat.x - SEAT_SIZE / 2}
        y={seat.y - SEAT_SIZE / 2}
        width={SEAT_SIZE}
        height={SEAT_SIZE}
        fill={color}
        stroke="#fff"
        stroke-width="0.5"
        rx="1"
        class="seat"
        class:interactive
        onmouseenter={(e) => handleMouseEnter(e, seat)}
        onmouseleave={handleMouseLeave}
        onfocus={(e) => handleFocus(e, seat)}
        onblur={handleBlur}
        onclick={() => handleClick(seat)}
        onkeydown={(e) => (e.key === 'Enter' || e.key === ' ') && handleClick(seat)}
        role={interactive ? 'button' : 'presentation'}
        tabindex={interactive ? 0 : undefined}
        aria-label={interactive ? seatAriaLabel(seat) : undefined}
        aria-describedby={interactive && tooltip?.depute === dataByPlace.get(seat.place) ? TOOLTIP_ID : undefined}
      />
    {/each}
  </svg>

  {#if tooltip}
    <HemicycleTooltip id={TOOLTIP_ID} depute={tooltip.depute} x={tooltip.x} y={tooltip.y} {mode} />
  {/if}
</div>

<style>
  .hemicycle-wrapper {
    position: relative;
    width: 100%;
    max-width: 900px;
    margin: 0 auto;
  }

  svg {
    width: 100%;
    height: auto;
    display: block;
  }

  .seat {
    transition: opacity 0.1s;
  }

  .seat.interactive {
    cursor: pointer;
  }

  .seat.interactive:hover {
    opacity: 0.75;
    stroke: #000;
    stroke-width: 1;
  }

  .seat.interactive:focus {
    outline: none;
    stroke: #1a56db;
    stroke-width: 1.5;
    opacity: 0.9;
  }
</style>

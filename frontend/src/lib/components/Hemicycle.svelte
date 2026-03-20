<script lang="ts">
  import { goto } from '$app/navigation';
  import seatsData from '$lib/data/hemicycle-seats.json';
  import HemicycleTooltip from './HemicycleTooltip.svelte';

  type Mode = 'groupe' | 'vote';

  interface Props {
    mode: Mode;
    /** mode=groupe : tableau de DeputeListItem  |  mode=vote : tableau de VoteDeputeItem */
    data: any[];
  }

  const { mode, data }: Props = $props();

  const SVG_W = seatsData.svg_width;
  const SVG_H = seatsData.svg_height;
  const SEAT_SIZE = 7;

  const VOTE_COLORS: Record<string, string> = {
    pour: '#38a169',
    contre: '#e53e3e',
    abstention: '#a0aec0',
    nonVotant: '#2d3748',
  };

  /** Construit un map place → couleur selon le mode. */
  const colorByPlace = $derived.by(() => {
    const map = new Map<number, string>();
    if (mode === 'groupe') {
      for (const d of data) {
        if (d.place_hemicycle != null) {
          map.set(d.place_hemicycle, d.groupe_couleur ?? '#cbcbcb');
        }
      }
    } else {
      for (const v of data) {
        if (v.place_hemicycle != null) {
          map.set(v.place_hemicycle, VOTE_COLORS[v.position] ?? '#cbcbcb');
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

  function handleMouseEnter(e: MouseEvent, seat: (typeof seatsData.seats)[0]) {
    const d = dataByPlace.get(seat.place);
    if (!d) return;
    const rect = (e.currentTarget as SVGElement).closest('svg')!.getBoundingClientRect();
    tooltip = {
      depute: d,
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    };
  }

  function handleMouseLeave() {
    tooltip = null;
  }

  function handleClick(seat: (typeof seatsData.seats)[0]) {
    const d = dataByPlace.get(seat.place);
    if (!d) return;
    const id = d.depute_id ?? d.id;
    if (id) goto(`/deputes/${id}`);
  }
</script>

<div class="hemicycle-wrapper">
  <svg
    viewBox="0 0 {SVG_W} {SVG_H}"
    xmlns="http://www.w3.org/2000/svg"
    aria-label="Hémicycle de l'Assemblée Nationale"
    role="img"
  >
    {#each seatsData.seats as seat (seat.place)}
      {@const color = colorByPlace.get(seat.place) ?? '#e2e8f0'}
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
        class:interactive={dataByPlace.has(seat.place)}
        onmouseenter={(e) => handleMouseEnter(e, seat)}
        onmouseleave={handleMouseLeave}
        onclick={() => handleClick(seat)}
        role="button"
        tabindex="-1"
        aria-label="Siège {seat.place}"
      />
    {/each}
  </svg>

  {#if tooltip}
    <HemicycleTooltip depute={tooltip.depute} x={tooltip.x} y={tooltip.y} {mode} />
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
</style>

<script lang="ts">
  interface ScoresDatan {
    score_participation: number | null;
    score_participation_specialite: number | null;
    score_loyaute: number | null;
    score_majorite: number | null;
  }

  interface Props {
    scores: ScoresDatan | null;
    groupeLibelle?: string | null;
  }

  const { scores, groupeLibelle = null }: Props = $props();

  function pct(val: number | null): string {
    if (val == null) return '—';
    return Math.round(val * 100) + ' %';
  }

  function width(val: number | null): number {
    if (val == null) return 0;
    return Math.round(Math.min(Math.max(val, 0), 1) * 100);
  }

  const jauges = $derived([
    {
      label: 'Participation',
      description: 'Part des scrutins solennels auxquels il·elle a participé',
      value: scores?.score_participation ?? null,
      color: 'var(--color-vote)',
    },
    {
      label: 'Loyauté au groupe',
      description: groupeLibelle
        ? `Vote avec ${groupeLibelle} sur les scrutins solennels`
        : 'Vote dans le même sens que son groupe',
      value: scores?.score_loyaute ?? null,
      color: 'var(--color-commission)',
    },
    {
      label: 'Proximité majorité',
      description: 'Vote dans le même sens que la majorité présidentielle',
      value: scores?.score_majorite ?? null,
      color: 'var(--color-vote-actif)',
    },
  ]);
</script>

<div class="gauges">
  {#each jauges as j}
    <div class="jauge">
      <div class="jauge-header">
        <span class="jauge-label">{j.label}</span>
        <span class="jauge-value" class:empty={j.value == null}>{pct(j.value)}</span>
      </div>
      <div class="jauge-track">
        <div
          class="jauge-bar"
          style="width: {width(j.value)}%; background: {j.color}"
        ></div>
      </div>
      <p class="jauge-desc">{j.description}</p>
    </div>
  {/each}
</div>

<p class="source">
  Source : <a href="https://www.data.gouv.fr/fr/organizations/datan/" target="_blank" rel="noopener noreferrer">Datan</a>
  via data.gouv.fr — Licence Ouverte
</p>

<style>
  .gauges {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .jauge {
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
  }

  .jauge-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 0.5rem;
  }

  .jauge-label {
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--color-text);
  }

  .jauge-value {
    font-size: 0.85rem;
    font-weight: 700;
    font-family: var(--font-mono);
    color: var(--color-text);
    flex-shrink: 0;
  }

  .jauge-value.empty {
    color: var(--color-text-muted);
    font-weight: 400;
  }

  .jauge-track {
    height: 8px;
    background: var(--color-border);
    border-radius: 4px;
    overflow: hidden;
  }

  .jauge-bar {
    height: 100%;
    border-radius: 4px;
    transition: width 0.4s ease;
  }

  .jauge-desc {
    font-size: 0.75rem;
    color: var(--color-text-muted);
    margin: 0;
  }

  .source {
    font-size: 0.7rem;
    color: var(--color-text-muted);
    margin-top: 0.75rem;
    margin-bottom: 0;
  }

  .source a {
    color: var(--color-text-muted);
  }
</style>

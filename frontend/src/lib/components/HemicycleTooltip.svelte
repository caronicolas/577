<script lang="ts">
  interface Props {
    id: string;
    depute: any;
    x: number;
    y: number;
    mode: 'groupe' | 'vote';
  }

  const { id, depute, x, y, mode }: Props = $props();

  const POSITION_LABEL: Record<string, string> = {
    pour: 'Pour',
    contre: 'Contre',
    abstention: 'Abstention',
    nonVotant: 'Non-votant',
  };
</script>

<div
  {id}
  class="tooltip"
  style="left: {x + 12}px; top: {y - 8}px"
  role="tooltip"
  aria-live="polite"
>
  <div class="tooltip-inner">
    {#if depute.url_photo}
      <img src={depute.url_photo} alt={depute.nom ?? depute.depute_id} class="photo" />
    {/if}
    <div class="content">
      <strong class="nom">{depute.nom ?? depute.depute_id}</strong>
      {#if mode === 'groupe' && depute.groupe}
        <span
          class="badge"
          style="background: {depute.groupe.couleur ?? 'var(--color-border)'}"
        >{depute.groupe.sigle}</span>
        <span class="groupe-libelle">{depute.groupe.libelle}</span>
      {/if}
      {#if mode === 'vote' && depute.position}
        <span class="position" data-pos={depute.position}>
          {POSITION_LABEL[depute.position] ?? depute.position}
        </span>
      {/if}
      {#if depute.nom_circonscription}
        <span class="circ">{depute.nom_circonscription}</span>
      {/if}
    </div>
  </div>
</div>

<style>
  .tooltip {
    position: absolute;
    z-index: 200;
    pointer-events: none;
  }

  .tooltip-inner {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    padding: 0.5rem 0.75rem;
    box-shadow: var(--shadow-md);
    white-space: nowrap;
    font-size: 0.8rem;
  }

  .photo {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    object-fit: cover;
    flex-shrink: 0;
  }

  .content {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
  }

  .nom { font-weight: 600; }

  .badge {
    display: inline-block;
    font-size: 0.68rem;
    font-weight: 700;
    padding: 0.1rem 0.35rem;
    border-radius: var(--radius-sm);
    color: #fff;
    width: fit-content;
  }

  .position {
    font-size: 0.75rem;
    font-weight: 600;
  }

  .position[data-pos="pour"] { color: #38a169; }
  .position[data-pos="contre"] { color: #e53e3e; }
  .position[data-pos="abstention"] { color: #718096; }
  .position[data-pos="nonVotant"] { color: #2d3748; }

  .groupe-libelle {
    font-size: 0.72rem;
    color: var(--color-text-muted);
  }

  .circ {
    font-size: 0.72rem;
    color: var(--color-text-muted);
  }
</style>

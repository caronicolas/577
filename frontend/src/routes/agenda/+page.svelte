<script lang="ts">
  import { apiBase } from '$lib/api';

  interface PointODJ {
    ordre: number | null;
    titre: string | null;
  }

  interface Seance {
    id: string;
    date: string;
    titre: string | null;
    type_seance: string | null;
    is_senat: boolean;
    points_odj: PointODJ[];
  }

  interface Reunion {
    id: string;
    date: string;
    heure_debut: string | null;
    heure_fin: string | null;
    titre: string | null;
    organe_id: string | null;
    organe_libelle: string | null;
    is_senat: boolean;
  }

  interface JourAgenda {
    date: string;
    seances: Seance[];
    reunions: Reunion[];
  }

  let jours = $state<JourAgenda[]>([]);
  let loading = $state(true);
  const dateFormatter = new Intl.DateTimeFormat('fr-FR', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });

  function formatDate(iso: string): string {
    const d = new Date(iso + 'T12:00:00');
    const s = dateFormatter.format(d);
    return s.charAt(0).toUpperCase() + s.slice(1);
  }

  function formatHeure(h: string | null): string {
    if (!h) return '';
    return h.replace(':', 'h');
  }

  $effect(() => {
    fetch(`${apiBase}/agenda?jours=60`)
      .then((r) => r.json())
      .then((data: JourAgenda[]) => {
        jours = data;
        loading = false;
      })
      .catch(() => {
        loading = false;
      });
  });
</script>

<svelte:head>
  <title>Agenda — les 577</title>
  <meta name="description" content="Agenda des travaux de l'Assemblée Nationale : séances publiques, réunions de commissions, 17e législature." />
  <meta property="og:title" content="Agenda — les 577" />
  <meta property="og:description" content="Agenda des travaux de l'Assemblée Nationale : séances publiques, réunions de commissions, 17e législature." />
</svelte:head>

<div class="header">
  <h1>Agenda</h1>
  <p class="subtitle">Séances et commissions · 17<sup>e</sup> législature</p>
</div>

{#if loading}
  <p class="muted">Chargement…</p>
{:else if jours.length === 0}
  <p class="muted">Aucun événement trouvé sur cette période.</p>
{:else}
  {#each jours as jour (jour.date)}
    <div class="jour">
      <h2 class="jour-date">{formatDate(jour.date)}</h2>

      {#each jour.seances as s (s.id)}
        <div class="seance-section" class:seance-section--senat={s.is_senat}>
          <div class="seance-header">
            <span class="seance-badge" class:seance-badge--senat={s.is_senat}>
              {s.is_senat ? 'Sénat' : 'Séance AN'}
            </span>
            {#if s.titre}
              <span class="seance-titre">{s.titre}</span>
            {/if}
          </div>

          {#if s.points_odj.length > 0}
            <div class="section-block">
              <div class="section-label">Ordre du jour</div>
              <ul class="odj">
                {#each s.points_odj as p}
                  {#if p.titre}
                    <li class="odj-item">
                      {#if p.ordre != null}<span class="odj-num">{p.ordre}.</span>{/if}
                      <span>{p.titre}</span>
                    </li>
                  {/if}
                {/each}
              </ul>
            </div>
          {/if}

        </div>
      {/each}

      {#if jour.reunions.length > 0}
        <div class="commissions-groupe">
          <div class="commissions-titre">Commissions</div>
          {#each jour.reunions as r (r.id)}
            <div class="event event--commission" class:event--senat={r.is_senat}>
              <div class="event-header">
                {#if r.heure_debut || r.heure_fin}
                  <span class="event-heure">
                    {formatHeure(r.heure_debut)}{r.heure_fin ? `–${formatHeure(r.heure_fin)}` : ''}
                  </span>
                {/if}
                {#if r.is_senat}
                  <span class="event-type event-type--senat">Sénat</span>
                {/if}
                <span class="event-organe">{r.organe_libelle ?? r.titre ?? 'Commission'}</span>
                {#if r.titre && r.organe_libelle && r.titre !== r.organe_libelle}
                  <span class="event-titre-commission">{r.titre}</span>
                {/if}
              </div>
            </div>
          {/each}
        </div>
      {/if}
    </div>
  {/each}
{/if}

<style>
  .header {
    margin-bottom: 2rem;
  }

  h1 {
    font-size: 1.75rem;
    font-weight: 700;
  }

  .subtitle {
    color: var(--color-text-muted);
    font-size: 0.9rem;
    margin-top: 0.25rem;
  }

  .jour {
    margin-bottom: 2.5rem;
  }

  .jour-date {
    font-size: 1rem;
    font-weight: 700;
    color: var(--color-text);
    border-bottom: 2px solid var(--color-border);
    padding-bottom: 0.4rem;
    margin-bottom: 0.75rem;
  }

  /* Séance */
  .seance-section {
    border-left: 3px solid var(--color-vote);
    padding: 0.6rem 0.75rem;
    border-radius: var(--radius-md);
    border: 1px solid var(--color-border);
    border-left-width: 3px;
    background: var(--color-surface);
    margin-bottom: 0.75rem;
    font-size: 0.875rem;
  }

  .seance-section--senat {
    border-left-color: #a0aec0;
    opacity: 0.85;
  }

  .seance-header {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 0.5rem;
    margin-bottom: 0.75rem;
  }

  .seance-badge {
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    background: var(--color-vote);
    color: #fff;
    padding: 0.1rem 0.4rem;
    border-radius: 3px;
    flex-shrink: 0;
  }

  .seance-badge--senat {
    background: #a0aec0;
  }

  .seance-titre {
    color: var(--color-text-muted);
    font-size: 0.8rem;
  }

  /* Blocs ODJ / scrutins */
  .section-block {
    margin-bottom: 0.75rem;
  }

  .section-block + .section-block {
    padding-top: 0.6rem;
    border-top: 1px solid var(--color-border);
  }

  .section-label {
    font-size: 0.68rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--color-text-muted);
    margin-bottom: 0.35rem;
  }

  /* ODJ */
  .odj {
    list-style: none;
    margin: 0;
    padding: 0;
  }

  .odj-item {
    display: flex;
    gap: 0.4rem;
    align-items: baseline;
    color: var(--color-text-muted);
    font-size: 0.8rem;
    padding: 0.2rem 0;
    border-top: 1px solid var(--color-border);
  }

  .odj-num {
    font-family: var(--font-mono);
    font-size: 0.72rem;
    color: var(--color-vote);
    flex-shrink: 0;
    min-width: 18px;
  }

  /* Scrutins */
  .scrutins {
    list-style: none;
    margin: 0;
    padding: 0;
  }

  .scrutin-item {
    border-top: 1px solid var(--color-border);
  }

  .scrutin-header {
    display: flex;
    align-items: baseline;
    gap: 0.4rem;
    width: 100%;
    padding: 0.3rem 0;
    background: none;
    border: none;
    text-align: left;
    color: inherit;
    font: inherit;
    cursor: default;
    flex-wrap: wrap;
  }

  .scrutin-header--clickable {
    cursor: pointer;
  }

  .scrutin-header--clickable:hover .scrutin-titre {
    text-decoration: underline;
  }

  .scrutin-num {
    font-family: var(--font-mono);
    font-size: 0.7rem;
    color: var(--color-vote);
    flex-shrink: 0;
  }

  .scrutin-titre {
    font-size: 0.8rem;
    color: var(--color-text);
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .scrutin-sort {
    font-size: 0.68rem;
    font-weight: 700;
    padding: 0.1rem 0.35rem;
    border-radius: 3px;
    flex-shrink: 0;
    background: var(--color-border);
    color: var(--color-text-muted);
  }

  .scrutin-sort--adopte {
    background: #c6f6d5;
    color: #276749;
  }

  .scrutin-sort--rejete {
    background: #fed7d7;
    color: #9b2c2c;
  }

  .chevron {
    font-size: 0.72rem;
    color: var(--color-text-muted);
    transition: transform 0.15s;
    flex-shrink: 0;
    margin-left: auto;
  }

  .chevron--open {
    transform: rotate(90deg);
  }

  .scrutin-details {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 0.3rem 0 0.4rem 0;
    font-size: 0.8rem;
  }

  .decompte {
    font-family: var(--font-mono);
    font-size: 0.75rem;
    display: flex;
    gap: 0.5rem;
  }

  .pour { color: #38a169; }
  .contre { color: #e53e3e; }
  .abst { color: var(--color-text-muted); }

  .scrutin-link {
    font-size: 0.78rem;
    color: var(--color-vote);
    text-decoration: none;
  }

  .scrutin-link:hover {
    text-decoration: underline;
  }

  /* Commissions */
  .event {
    padding: 0.4rem 0.75rem;
    border-radius: var(--radius-md);
    border: 1px solid var(--color-border);
    background: var(--color-surface);
    margin-bottom: 0.35rem;
    font-size: 0.875rem;
  }

  .event--commission {
    border-left: 3px solid var(--color-commission);
  }

  .event--senat {
    border-left-color: #a0aec0;
    opacity: 0.85;
  }

  .event-header {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 0.5rem;
  }

  .event-type {
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    background: var(--color-vote);
    color: #fff;
    padding: 0.1rem 0.4rem;
    border-radius: 3px;
    flex-shrink: 0;
  }

  .event-type--senat {
    background: #a0aec0;
  }

  .event-heure {
    font-family: var(--font-mono);
    font-size: 0.75rem;
    color: var(--color-commission);
    flex-shrink: 0;
    min-width: 80px;
  }

  .event-organe {
    font-weight: 600;
    color: var(--color-text);
  }

  .event-titre-commission {
    color: var(--color-text-muted);
    font-size: 0.8rem;
    font-style: italic;
  }

  .commissions-groupe {
    margin-top: 0.25rem;
  }

  .commissions-titre {
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--color-text-muted);
    margin-bottom: 0.35rem;
    margin-top: 0.75rem;
  }

  .muted {
    color: var(--color-text-muted);
  }
</style>

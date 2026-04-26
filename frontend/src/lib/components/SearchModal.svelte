<script lang="ts">
  import { goto } from '$app/navigation';
  import { apiBase } from '$lib/api';

  interface Props {
    open: boolean;
    onclose: () => void;
  }

  const { open, onclose }: Props = $props();

  interface DeputeResult {
    type: 'depute';
    id: string;
    nom: string;
    prenom: string;
    groupe_sigle: string | null;
    groupe_couleur: string | null;
    url_photo: string | null;
  }

  interface ScrutinResult {
    type: 'scrutin';
    id: string;
    titre: string;
    date_seance: string;
    sort: string | null;
  }

  let query = $state('');
  let deputes = $state<DeputeResult[]>([]);
  let scrutins = $state<ScrutinResult[]>([]);
  let loading = $state(false);
  let debounceTimer: ReturnType<typeof setTimeout>;

  $effect(() => {
    if (!open) {
      query = '';
      deputes = [];
      scrutins = [];
      loading = false;
    }
  });

  $effect(() => {
    const q = query.trim();
    clearTimeout(debounceTimer);
    if (q.length < 2) {
      deputes = [];
      scrutins = [];
      loading = false;
      return;
    }
    loading = true;
    debounceTimer = setTimeout(() => {
      fetch(`${apiBase}/search?q=${encodeURIComponent(q)}`)
        .then((r) => r.json())
        .then((data) => {
          deputes = data.deputes ?? [];
          scrutins = data.scrutins ?? [];
          loading = false;
        })
        .catch(() => {
          loading = false;
        });
    }, 300);
  });

  function navigate(href: string) {
    onclose();
    goto(href);
  }

  function handleBackdropClick(e: MouseEvent) {
    if (e.target === e.currentTarget) onclose();
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') onclose();
  }

  const hasResults = $derived(deputes.length > 0 || scrutins.length > 0);
  const showEmpty = $derived(query.trim().length >= 2 && !loading && !hasResults);
</script>

{#if open}
  <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
  <div class="backdrop" onclick={handleBackdropClick}>
    <div class="modal" role="dialog" aria-modal="true" aria-label="Recherche">
      <div class="search-bar">
        <svg class="icon-search" viewBox="0 0 20 20" fill="none" aria-hidden="true">
          <circle cx="8.5" cy="8.5" r="5.5" stroke="currentColor" stroke-width="1.5"/>
          <path d="M13 13l3.5 3.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
        <!-- svelte-ignore a11y_autofocus -->
        <input
          autofocus
          type="search"
          placeholder="Rechercher un député, un scrutin…"
          bind:value={query}
          onkeydown={handleKeydown}
          class="input"
          aria-label="Recherche globale"
        />
        {#if loading}
          <span class="spinner" aria-hidden="true"></span>
        {/if}
        <button class="close-btn" onclick={onclose} aria-label="Fermer">
          <kbd>Esc</kbd>
        </button>
      </div>

      {#if hasResults}
        <div class="results">
          {#if deputes.length > 0}
            <div class="section">
              <p class="section-label">Députés</p>
              <ul>
                {#each deputes as d (d.id)}
                  <li>
                    <button class="result-item" onclick={() => navigate(`/deputes/${d.id}`)}>
                      <span class="avatar">
                        {#if d.url_photo}
                          <img src={d.url_photo} alt="" />
                        {:else}
                          <span class="avatar-fallback">{d.prenom[0]}{d.nom[0]}</span>
                        {/if}
                      </span>
                      <span class="result-main">
                        <span class="result-name">{d.prenom} {d.nom}</span>
                        {#if d.groupe_sigle}
                          <span
                            class="result-badge"
                            style="background: {d.groupe_couleur ?? '#ccc'}22; color: {d.groupe_couleur ?? '#888'}"
                          >{d.groupe_sigle}</span>
                        {/if}
                      </span>
                    </button>
                  </li>
                {/each}
              </ul>
            </div>
          {/if}

          {#if scrutins.length > 0}
            <div class="section">
              <p class="section-label">Scrutins</p>
              <ul>
                {#each scrutins as s (s.id)}
                  <li>
                    <button class="result-item" onclick={() => navigate(`/votes/${s.id}`)}>
                      <span class="result-main">
                        <span class="result-name result-titre">{s.titre}</span>
                        <span class="result-meta">
                          {s.date_seance}
                          {#if s.sort}
                            · <span class:adopte={s.sort === 'adopté'} class:rejete={s.sort === 'rejeté'}>{s.sort}</span>
                          {/if}
                        </span>
                      </span>
                    </button>
                  </li>
                {/each}
              </ul>
            </div>
          {/if}
        </div>
      {:else if showEmpty}
        <p class="empty">Aucun résultat pour « {query.trim()} »</p>
      {/if}
    </div>
  </div>
{/if}

<style>
  .backdrop {
    position: fixed;
    inset: 0;
    z-index: 500;
    background: rgba(0, 0, 0, 0.45);
    display: flex;
    align-items: flex-start;
    justify-content: center;
    padding-top: 10vh;
  }

  .modal {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-md);
    width: 100%;
    max-width: 580px;
    margin: 0 1rem;
    overflow: hidden;
  }

  .search-bar {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.75rem 1rem;
    border-bottom: 1px solid var(--color-border);
  }

  .icon-search {
    width: 18px;
    height: 18px;
    color: var(--color-text-muted);
    flex-shrink: 0;
  }

  .input {
    flex: 1;
    border: none;
    background: none;
    font-size: 0.95rem;
    color: var(--color-text);
    outline: none;
  }

  .input::placeholder {
    color: var(--color-text-muted);
  }

  .spinner {
    width: 16px;
    height: 16px;
    border: 2px solid var(--color-border);
    border-top-color: var(--color-text-muted);
    border-radius: 50%;
    animation: spin 0.6s linear infinite;
    flex-shrink: 0;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .close-btn {
    background: none;
    border: none;
    cursor: pointer;
    padding: 0;
    flex-shrink: 0;
  }

  kbd {
    font-size: 0.7rem;
    font-family: var(--font-mono);
    color: var(--color-text-muted);
    border: 1px solid var(--color-border);
    border-radius: 3px;
    padding: 0.1rem 0.35rem;
  }

  .results {
    max-height: 420px;
    overflow-y: auto;
  }

  .section {
    padding: 0.5rem 0;
  }

  .section + .section {
    border-top: 1px solid var(--color-border);
  }

  .section-label {
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--color-text-muted);
    padding: 0.25rem 1rem 0.35rem;
    margin: 0;
  }

  ul {
    list-style: none;
    margin: 0;
    padding: 0;
  }

  .result-item {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    width: 100%;
    text-align: left;
    padding: 0.55rem 1rem;
    background: none;
    border: none;
    cursor: pointer;
    color: var(--color-text);
    transition: background 0.1s;
  }

  .result-item:hover {
    background: var(--color-bg);
  }

  .avatar {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    overflow: hidden;
    flex-shrink: 0;
    background: var(--color-border);
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .avatar img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .avatar-fallback {
    font-size: 0.65rem;
    font-weight: 700;
    color: var(--color-text-muted);
    text-transform: uppercase;
  }

  .result-main {
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
    min-width: 0;
    flex: 1;
  }

  .result-name {
    font-size: 0.875rem;
    font-weight: 500;
  }

  .result-titre {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .result-badge {
    display: inline-block;
    font-size: 0.7rem;
    font-weight: 700;
    padding: 0.05rem 0.35rem;
    border-radius: 3px;
    align-self: flex-start;
  }

  .result-meta {
    font-size: 0.75rem;
    color: var(--color-text-muted);
  }

  .adopte { color: var(--color-vote); font-weight: 600; }
  .rejete { color: var(--color-absent); font-weight: 600; }

  .empty {
    padding: 1.5rem 1rem;
    font-size: 0.875rem;
    color: var(--color-text-muted);
    text-align: center;
    margin: 0;
  }
</style>

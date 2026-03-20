<script lang="ts">
  import '../app.css';
  import { page } from '$app/stores';

  const navLinks = [
    { href: '/', label: 'Hémicycle' },
    { href: '/deputes', label: 'Députés' },
    { href: '/votes', label: 'Votes' },
  ];
</script>

<header>
  <nav class="container">
    <a href="/" class="brand">🏛️ Assemblée Nationale</a>
    <ul>
      {#each navLinks as link}
        <li>
          <a href={link.href} class:active={$page.url.pathname === link.href}>
            {link.label}
          </a>
        </li>
      {/each}
    </ul>
  </nav>
</header>

<main class="container">
  <slot />
</main>

<footer class="container">
  <p>
    Données open data
    <a href="https://data.assemblee-nationale.fr" rel="noopener noreferrer" target="_blank">
      Assemblée Nationale
    </a>
    ·
    <a href="https://www.data.gouv.fr/organizations/assemblee-nationale/" rel="noopener noreferrer" target="_blank">
      data.gouv.fr
    </a>
  </p>
  <p>
    <a href="https://www.nosdeputes.fr" rel="noopener noreferrer" target="_blank">
      NosDéputés.fr par Regards Citoyens à partir de l'Assemblée nationale
    </a>
    — Licence ODbL
  </p>
</footer>

<style>
  header {
    background: var(--color-surface);
    border-bottom: 1px solid var(--color-border);
    position: sticky;
    top: 0;
    z-index: 100;
  }

  nav {
    display: flex;
    align-items: center;
    gap: 2rem;
    height: 56px;
  }

  .brand {
    font-weight: 700;
    font-size: 1rem;
    color: var(--color-text);
    white-space: nowrap;
  }

  ul {
    display: flex;
    gap: 0.25rem;
    list-style: none;
  }

  ul a {
    display: block;
    padding: 0.375rem 0.75rem;
    border-radius: var(--radius-sm);
    color: var(--color-text-muted);
    font-size: 0.9rem;
    transition: background 0.15s, color 0.15s;
  }

  ul a:hover,
  ul a.active {
    background: var(--color-bg);
    color: var(--color-text);
    text-decoration: none;
  }

  main {
    padding-top: 2rem;
    padding-bottom: 4rem;
    min-height: calc(100vh - 56px - 80px);
  }

  footer {
    border-top: 1px solid var(--color-border);
    padding: 1.5rem 0;
    font-size: 0.8rem;
    color: var(--color-text-muted);
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }
</style>

<script lang="ts">
  import '../app.css';
  import { page } from '$app/stores';
  import { dev } from '$app/environment';

  const navLinks = [
    { href: '/', label: 'Hémicycle' },
    { href: '/deputes', label: 'Députés' },
    { href: '/votes', label: 'Votes' },
    { href: '/agenda', label: 'Agenda' },
  ];

  let menuOpen = $state(false);

  function closeMenu() {
    menuOpen = false;
  }

  $effect(() => {
    // Ferme le menu à chaque changement de page
    $page.url.pathname;
    menuOpen = false;
  });
</script>

<svelte:head>
  <link rel="canonical" href="https://les577.fr{$page.url.pathname}" />
  <meta property="og:url" content="https://les577.fr{$page.url.pathname}" />
  {#if !dev}
    <!-- Wysistat analytics -->
    <script>
      var _wsq = _wsq || [];
      _wsq.push(['_setNom', 'les577']);
      _wsq.push(['_wysistat']);
      (function(){
        var ws = document.createElement('script');
        ws.type = 'text/javascript';
        ws.async = true;
        ws.src = ('https:' == document.location.protocol ? 'https://www' : 'http://www') + '.wysistat.com/ws.jsa';
        var s = document.getElementsByTagName('script')[0]||document.getElementsByTagName('body')[0];
        s.parentNode.insertBefore(ws, s);
      })();
    </script>
  {/if}
</svelte:head>

<header>
  <nav class="container">
    <a href="/" class="brand">
      <svg viewBox="0 0 32 32" class="brand-icon" aria-hidden="true" xmlns="http://www.w3.org/2000/svg">
        <g fill="currentColor">
          <circle cx="10.02" cy="27.48" r="1.2"/><circle cx="10.99" cy="24.7" r="1.2"/><circle cx="13.15" cy="22.72" r="1.2"/><circle cx="16.0" cy="22.0" r="1.2"/><circle cx="18.85" cy="22.72" r="1.2"/><circle cx="21.01" cy="24.7" r="1.2"/><circle cx="21.98" cy="27.48" r="1.2"/>
          <circle cx="6.04" cy="27.13" r="1.2"/><circle cx="6.73" cy="24.25" r="1.2"/><circle cx="8.23" cy="21.71" r="1.2"/><circle cx="10.41" cy="19.71" r="1.2"/><circle cx="13.08" cy="18.44" r="1.2"/><circle cx="16.0" cy="18.0" r="1.2"/><circle cx="18.92" cy="18.44" r="1.2"/><circle cx="21.59" cy="19.71" r="1.2"/><circle cx="23.77" cy="21.71" r="1.2"/><circle cx="25.27" cy="24.25" r="1.2"/><circle cx="25.96" cy="27.13" r="1.2"/>
          <circle cx="2.05" cy="26.78" r="1.2"/><circle cx="2.62" cy="23.87" r="1.2"/><circle cx="3.79" cy="21.15" r="1.2"/><circle cx="5.5" cy="18.74" r="1.2"/><circle cx="7.69" cy="16.74" r="1.2"/><circle cx="10.24" cy="15.24" r="1.2"/><circle cx="13.06" cy="14.31" r="1.2"/><circle cx="16.0" cy="14.0" r="1.2"/><circle cx="18.94" cy="14.31" r="1.2"/><circle cx="21.76" cy="15.24" r="1.2"/><circle cx="24.31" cy="16.74" r="1.2"/><circle cx="26.5" cy="18.74" r="1.2"/><circle cx="28.21" cy="21.15" r="1.2"/><circle cx="29.38" cy="23.87" r="1.2"/><circle cx="29.95" cy="26.78" r="1.2"/>
        </g>
      </svg>
      les 577
    </a>

    <!-- Navigation desktop -->
    <ul class="nav-desktop">
      {#each navLinks as link}
        <li>
          <a href={link.href} class:active={$page.url.pathname === link.href}>
            {link.label}
          </a>
        </li>
      {/each}
    </ul>

    <!-- Burger mobile -->
    <button
      class="burger"
      aria-label={menuOpen ? 'Fermer le menu' : 'Ouvrir le menu'}
      aria-expanded={menuOpen}
      onclick={() => (menuOpen = !menuOpen)}
    >
      <span class="bar"></span>
      <span class="bar"></span>
      <span class="bar"></span>
    </button>
  </nav>

  <!-- Menu mobile -->
  {#if menuOpen}
    <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
    <div class="overlay" onclick={closeMenu}></div>
    <ul class="nav-mobile">
      {#each navLinks as link}
        <li>
          <a href={link.href} class:active={$page.url.pathname === link.href} onclick={closeMenu}>
            {link.label}
          </a>
        </li>
      {/each}
    </ul>
  {/if}
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
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-weight: 700;
    font-size: 1rem;
    color: var(--color-text);
    white-space: nowrap;
  }

  .brand-icon {
    width: 24px;
    height: 24px;
    flex-shrink: 0;
  }

  /* Desktop nav */
  .nav-desktop {
    display: flex;
    gap: 0.25rem;
    list-style: none;
  }

  .nav-desktop a {
    display: block;
    padding: 0.375rem 0.75rem;
    border-radius: var(--radius-sm);
    color: var(--color-text-muted);
    font-size: 0.9rem;
    transition: background 0.15s, color 0.15s;
  }

  .nav-desktop a:hover,
  .nav-desktop a.active {
    background: var(--color-bg);
    color: var(--color-text);
    text-decoration: none;
  }

  /* Burger button */
  .burger {
    display: none;
    flex-direction: column;
    justify-content: center;
    gap: 5px;
    width: 36px;
    height: 36px;
    padding: 6px;
    background: none;
    border: none;
    cursor: pointer;
    margin-left: auto;
    border-radius: var(--radius-sm);
  }

  .burger:hover {
    background: var(--color-border);
  }

  .bar {
    display: block;
    width: 100%;
    height: 2px;
    background: var(--color-text);
    border-radius: 2px;
    transition: opacity 0.15s;
  }

  /* Mobile dropdown */
  .overlay {
    position: fixed;
    inset: 56px 0 0 0;
    z-index: 99;
  }

  .nav-mobile {
    position: absolute;
    top: 56px;
    right: 1rem;
    z-index: 200;
    list-style: none;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-md);
    padding: 0.5rem;
    min-width: 160px;
  }

  .nav-mobile a {
    display: block;
    padding: 0.6rem 0.75rem;
    border-radius: var(--radius-sm);
    color: var(--color-text-muted);
    font-size: 0.9rem;
    transition: background 0.15s, color 0.15s;
  }

  .nav-mobile a:hover,
  .nav-mobile a.active {
    background: var(--color-bg);
    color: var(--color-text);
    text-decoration: none;
  }

  @media (max-width: 600px) {
    .nav-desktop { display: none; }
    .burger { display: flex; }
  }

  main {
    padding-top: 2rem;
    padding-bottom: 4rem;
    min-height: calc(100vh - 56px - 80px);
  }

  footer {
    border-top: 1px solid var(--color-border);
    padding: 1.5rem 0 1.5rem 15px;
    font-size: 0.8rem;
    color: var(--color-text-muted);
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }
</style>

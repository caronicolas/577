<svelte:head>
  <title>À propos — les 577</title>
  <meta name="description" content="Les 577 est un site citoyen d'information sur l'Assemblée Nationale française. Sources de données, méthodologie et attribution." />
  <meta property="og:title" content="À propos — les 577" />
  <meta property="og:description" content="Les 577 est un site citoyen d'information sur l'Assemblée Nationale française. Sources de données, méthodologie et attribution." />
</svelte:head>

<div class="page">
  <h1>À propos</h1>

  <section>
    <p class="intro">
      <strong>les 577</strong> est un site citoyen qui rend plus accessibles les données publiques
      de l'Assemblée Nationale française. Toutes les données affichées proviennent de sources
      officielles en open data.
    </p>
  </section>

  <section>
    <h2>Sources de données</h2>

    <div class="source-list">
      <div class="source">
        <div class="source-header">
          <span class="source-name">Assemblée Nationale — open data</span>
          <a href="https://data.assemblee-nationale.fr" target="_blank" rel="noopener noreferrer" class="source-link">data.assemblee-nationale.fr →</a>
        </div>
        <p>Scrutins, votes, amendements, dossiers législatifs, données des députés et des groupes parlementaires. Données de la 17e législature (depuis juin 2024). Mises à jour quotidiennes ou hebdomadaires selon le type.</p>
      </div>

      <div class="source">
        <div class="source-header">
          <span class="source-name">NosDéputés.fr — Regards Citoyens</span>
          <a href="https://www.nosdeputes.fr" target="_blank" rel="noopener noreferrer" class="source-link">nosdeputes.fr →</a>
        </div>
        <p>
          Coordonnées des 577 sièges de l'hémicycle utilisées pour la visualisation.
          Données sous <strong>Licence ODbL</strong> — attribution obligatoire :
          <em>"NosDéputés.fr par Regards Citoyens à partir de l'Assemblée nationale"</em>.
        </p>
      </div>

      <div class="source">
        <div class="source-header">
          <span class="source-name">Datan — data.gouv.fr</span>
          <a href="https://www.data.gouv.fr/fr/organizations/datan/" target="_blank" rel="noopener noreferrer" class="source-link">data.gouv.fr →</a>
        </div>
        <p>Scores de participation aux scrutins solennels et de cohésion avec le groupe parlementaire, affichés sur chaque fiche député. Données sous Licence Ouverte.</p>
      </div>
    </div>
  </section>

  <section>
    <h2>Méthodologie</h2>

    <div class="method-list">
      <div class="method">
        <h3>Hémicycle</h3>
        <p>Chaque siège est positionné selon les coordonnées réelles extraites du SVG open data de Regards Citoyens. Les couleurs représentent le groupe parlementaire auquel appartient le député à la date de consultation, ou son vote lors d'un scrutin.</p>
      </div>

      <div class="method">
        <h3>Calendrier d'activité</h3>
        <p>Le calendrier de style "contributions GitHub" couvre la 17e législature depuis juin 2024. L'intensité de couleur reflète le niveau d'activité : absent (rouge), présent sans vote (vert clair), a voté (vert), a voté et pris la parole ou déposé un amendement (vert foncé).</p>
      </div>

      <div class="method">
        <h3>Scores Datan</h3>
        <p>Le score de participation mesure la part des scrutins solennels auxquels le député a participé. Le score de loyauté mesure la proportion de votes dans le même sens que la majorité de son groupe. Ces scores sont calculés par Datan et non par ce site.</p>
      </div>

      <div class="method">
        <h3>Fréquence de mise à jour</h3>
        <ul>
          <li>Scrutins et votes : quotidien</li>
          <li>Amendements : quotidien</li>
          <li>Agenda et commissions : quotidien</li>
          <li>Groupes parlementaires : quotidien</li>
          <li>Données des députés : hebdomadaire (lundi)</li>
          <li>Scores Datan : hebdomadaire (mardi)</li>
        </ul>
      </div>
    </div>
  </section>

  <section>
    <h2>Ce site</h2>
    <p>
      Ce site est développé de manière indépendante, sans lien avec l'Assemblée Nationale ni aucun parti politique.
      Il ne collecte pas de données personnelles et n'utilise pas de cookies publicitaires.
      Le code source est disponible sur
      <a href="https://github.com/caronicolas/577" target="_blank" rel="noopener noreferrer">GitHub</a>.
    </p>
  </section>
</div>

<style>

  h1 {
    font-size: 1.75rem;
    font-weight: 700;
    margin-bottom: 2rem;
  }

  section {
    margin-bottom: 2.5rem;
  }

  .intro {
    font-size: 1rem;
    line-height: 1.7;
    color: var(--color-text);
  }

  h2 {
    font-size: 1.1rem;
    font-weight: 700;
    margin-bottom: 1.25rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid var(--color-border);
  }

  h3 {
    font-size: 0.9rem;
    font-weight: 700;
    margin-bottom: 0.4rem;
    color: var(--color-text);
  }

  p {
    font-size: 0.875rem;
    line-height: 1.65;
    color: var(--color-text);
    margin: 0;
  }

  .source-list {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 1rem;
  }

  .source {
    padding: 1rem 1.25rem;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .source-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 1rem;
    flex-wrap: wrap;
  }

  .source-name {
    font-weight: 700;
    font-size: 0.9rem;
  }

  .source-link {
    font-size: 0.78rem;
    color: var(--color-text-muted);
    white-space: nowrap;
  }

  .method-list {
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
  }

  .method {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
  }

  ul {
    margin: 0.4rem 0 0 1.25rem;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
  }

  li {
    font-size: 0.875rem;
    line-height: 1.5;
    color: var(--color-text);
  }
</style>

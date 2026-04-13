import type { TranslationSchema } from './de';

export const fr: TranslationSchema = {
  meta: {
    title: 'Bünzli — Votre assistant IA zurichois',
    description:
      "Un assistant IA local, privé et souverain pour Zurich. Données réelles de la ville, chiffrement de bout en bout, et une compréhension profonde de la ville.",
  },

  nav: {
    skip: 'Aller au contenu',
  },

  hero: {
    eyebrow: 'Gratuit. Privé. De Zurich.',
    headline: 'Zurich se connaît mieux que quiconque.',
    subline:
      'Bünzli est votre assistant IA local — avec de vraies données zurichoises, une vraie confidentialité, et zéro blabla.',
    ctaBeta: 'Tester la bêta',
    ctaCollaborate: 'Collaborer',
    ctaBetaNote: 'Gratuit. Sans carte de crédit.',
    ctaCollabNote: 'Dev, design, communauté — tous bienvenus.',
  },

  why: {
    heading: 'Pourquoi Bünzli?',
    problemHeading: "Le problème : l'IA générique ne comprend pas Zurich.",
    problemText:
      "ChatGPT ne sait pas quand arrive le tram 13. Il ne connaît pas les Badis du lac, les quartiers tranquilles, les règles de recyclage ni les votations locales. Il invente des restaurants, hallucine des horaires et vous donne des réponses pour une autre ville. C'est gentil — mais pas ce dont vous avez besoin quand vous vivez ici.",
    solutionHeading: 'La solution : une IA vraiment chez elle ici.',
    solutionText:
      'Bünzli est construit sur de vraies données zurichoises et des connexions en direct. Liens en temps réel avec ZVV, météo, températures des Badis, votations, restaurants et plus encore. Une archive de connaissances issues des sites officiels de la ville, de blogs culinaires et de textes juridiques locaux. Privé, local, souverain — fait pour la ville où vous vivez.',
  },

  different: {
    heading: 'Ce qui nous distingue',
    subline: 'Quatre choses qui différencient Bünzli des assistants IA génériques.',
    cards: [
      {
        icon: '🔒',
        title: "La confidentialité n'est pas une fonctionnalité",
        desc: "Vos conversations sont anonymisées, chiffrées de bout en bout et stockées uniquement localement dans votre navigateur. Nous ne voyons pas ce que vous demandez. Ce n'est pas une promesse — c'est une architecture.",
      },
      {
        icon: '📍',
        title: 'Vraies données zurichoises',
        desc: 'Pas de connaissances générales mondiales. Bünzli connaît les sites de la ville, les pages cantonales, les blogs culinaires et les lois locales — et se met à jour régulièrement.',
      },
      {
        icon: '⚡',
        title: 'Connexions en direct',
        desc: '12 connecteurs en temps réel donnent à Bünzli accès à la ville telle qu\'elle est maintenant — pas telle qu\'elle était l\'année dernière.',
      },
      {
        icon: '🇨🇭',
        title: 'Souveraineté suisse',
        desc: "Infomaniak héberge tout sur des serveurs suisses. Le droit suisse s'applique. Vos données ne quittent pas la Suisse.",
      },
    ],
  },

  howItWorks: {
    heading: 'Comment ça fonctionne — expliqué simplement',
    subline:
      "Vous n'avez pas besoin de comprendre cela pour utiliser Bünzli. Mais nous l'expliquons quand même — honnêtement, sans jargon.",
    items: [
      {
        icon: '🧠',
        title: "Qu'est-ce que l'IA?",
        text: "Un modèle de langage prédit quel mot est le plus susceptible de venir ensuite — basé sur d'immenses quantités de texte. Il ne « pense » pas — il reconnaît des motifs. Imaginez une autocomplétion très avancée qui fait vraiment sens.",
      },
      {
        icon: '📚',
        title: "Qu'est-ce que le RAG?",
        text: "Le RAG (Retrieval-Augmented Generation) signifie : l'IA ne devine pas simplement — elle consulte d'abord de vraies informations zurichoises. Comme donner une carte de bibliothèque plutôt que de laisser quelqu'un inventer. Nous l'alimentons avec des pages officielles de la ville, des blogs culinaires, des textes juridiques et des connaissances locales.",
      },
      {
        icon: '🔌',
        title: "Que sont les connecteurs MCP?",
        text: "Pensez-y comme les mains de l'IA. Sans eux, elle ne peut que parler. Avec eux, elle peut vérifier le prochain tram, voir s'il pleut, trouver un restaurant ou vous dire à quelle température est le lac. Des données en direct — pas des suppositions.",
      },
      {
        icon: '🛡️',
        title: 'En quoi notre confidentialité est-elle différente?',
        text: "La plupart des services IA stockent tout ce que vous dites — pour toujours — pour entraîner de futurs modèles. Nous non. Vos conversations vivent uniquement sur votre appareil, chiffrées. Nous ne pouvons littéralement pas les lire.",
      },
      {
        icon: '🏔️',
        title: 'Que signifie « souverain »?',
        text: "Vos données restent en Suisse. L'IA tourne sur des serveurs suisses. Nous respectons le droit suisse. Aucune entreprise étrangère ne décide de ce qui arrive à vos conversations.",
      },
    ],
  },

  connectors: {
    heading: 'Connexions en direct avec la ville',
    subline:
      '12 connecteurs en temps réel relient Bünzli au Zurich que vous connaissez. Demandez le prochain tram, la température de la Badi ou où manger ce soir.',
    items: [
      { icon: '🚋', name: 'ZVV Transit',         desc: 'Départs, correspondances et perturbations en temps réel.' },
      { icon: '🌤️', name: 'Météo',               desc: 'Prévisions locales et conditions actuelles pour Zurich.' },
      { icon: '🎭', name: 'Lieux',               desc: 'Bars, clubs, maisons culturelles et salles de concert.' },
      { icon: '🎉', name: 'Événements',           desc: "Ce qui se passe aujourd'hui, ce week-end et cette semaine à Zurich." },
      { icon: '🍽️', name: 'Restaurants',          desc: 'Recommandations locales, horaires et cuisines.' },
      { icon: '🗳️', name: 'Votations',            desc: 'Votations suisses et zurichoises en cours et à venir.' },
      { icon: '🏊', name: 'Températures Badi',    desc: "À quelle température est le lac en ce moment? Indice de baignade pour tous les Badis de Zurich." },
      { icon: '🅿️', name: 'Parkings',             desc: 'Places de parc libres dans le centre-ville.' },
      { icon: '💨', name: 'Qualité de l\'air',    desc: "Valeurs actuelles de particules fines et indice de qualité de l'air pour Zurich." },
      { icon: '♻️', name: 'Recyclage',             desc: 'Où recycler quoi — Kehrichtsack, verre, PET, textiles.' },
      { icon: '📍', name: "Points d'intérêt",     desc: 'Commerces, sites touristiques et conseils locaux près de chez vous.' },
      { icon: '📚', name: 'Base de connaissances', desc: 'Connaissances officielles de la ville et du canton, directement accessibles.' },
    ],
  },

  privacy: {
    heading: 'La confidentialité d\'abord',
    subline:
      "Pas comme promesse marketing. Comme réalité technique. Voici exactement comment ça fonctionne.",
    pillars: [
      {
        icon: '🔐',
        title: 'Chiffrement de bout en bout',
        desc: "Vos conversations sont chiffrées avant de quitter votre appareil. Seul vous détenez la clé — pas nous, pas Infomaniak.",
      },
      {
        icon: '💾',
        title: 'Stockage local uniquement',
        desc: "Votre historique de chat vit exclusivement dans votre navigateur — jamais sur nos serveurs. Videz le cache et il disparaît. C'est voulu.",
      },
      {
        icon: '👤',
        title: 'Requêtes anonymisées',
        desc: "Les requêtes à l'IA sont transmises de manière anonyme. Nous ne pouvons pas relier qui a demandé quoi. C'est techniquement impossible par conception.",
      },
      {
        icon: '📊',
        title: 'Analytique minimale',
        desc: "Nous utilisons uniquement les statistiques de base d'Infomaniak. Pas de traceurs tiers, pas de cookies, pas de Google Analytics. Nous savons combien de visiteurs nous avons. C'est tout.",
      },
    ],
  },

  tech: {
    heading: 'Notre stack technique — expliqué honnêtement',
    subline:
      'La transparence est une valeur fondamentale. Voici avec quoi nous travaillons — et pourquoi.',
    items: [
      {
        name: 'Apertus 70B',
        role: 'Le cerveau',
        desc: "Le grand modèle de langage qui propulse Bünzli. Tourne entièrement sur l'infrastructure suisse d'Infomaniak — aucune donnée ne part aux États-Unis ou en UE.",
      },
      {
        name: 'FastAPI',
        role: 'L\'épine dorsale',
        desc: 'Un framework web Python moderne qui connecte toutes les parties. Rapide, ouvert, bien documenté.',
      },
      {
        name: 'ChromaDB',
        role: 'La mémoire',
        desc: "Une base de données vectorielle qui stocke nos connaissances zurichoises dans un format permettant à l'IA de les rechercher à la vitesse de l'éclair.",
      },
      {
        name: 'ZITADEL',
        role: 'Le videur',
        desc: "Gestion d'identité sécurisée pour la connexion et le contrôle d'accès. Projet open-source suisse — pas Auth0, pas Okta.",
      },
      {
        name: 'Infomaniak',
        role: 'Le foyer',
        desc: 'Hébergeur suisse avec des centres de données à Genève et Winterthour. Les données restent en Suisse. Point.',
      },
      {
        name: 'Open WebUI',
        role: 'Le visage',
        desc: "L'interface de chat que vous voyez et utilisez. Open-source, entièrement personnalisable — sans dépendance aux produits UI commerciaux.",
      },
    ],
  },

  community: {
    heading: 'Ce qui vient ensuite',
    subline:
      "Ce n'est que le début. Bünzli appartient à Zurich — et nous le construisons ensemble.",
    items: [
      {
        icon: '🗣️',
        title: 'Züridütsch',
        desc: 'Une version complète en dialecte zurichois est en cours. Parce que certaines choses sonnent mieux en dialecte.',
      },
      {
        icon: '👧',
        title: 'Mode enfant',
        desc: 'Une version sûre et adaptée à l\'âge pour les écoles et les familles. Zurich expliqué pour la prochaine génération.',
      },
      {
        icon: '🔓',
        title: 'Open source',
        desc: "Nous prévoyons d'ouvrir entièrement le code. L'IA de Zurich devrait appartenir à Zurich.",
      },
      {
        icon: '🤝',
        title: 'Piloté par la communauté',
        desc: 'Demandes de fonctionnalités, connaissances locales, corrections — par la communauté, pour la communauté.',
      },
    ],
  },

  languages: {
    heading: 'Bünzli parle votre langue',
    subline:
      'Parce que Zurich est multilingue — et notre IA devrait l\'être aussi.',
    items: [
      { code: 'de', name: 'Deutsch',    note: 'La version officielle.' },
      { code: 'en', name: 'English',    note: 'For internationals calling Zürich home.' },
      { code: 'fr', name: 'Français',   note: 'Pour la Suisse romande et les francophones.' },
      { code: 'it', name: 'Italiano',   note: 'Per chi parla italiano a Zurigo.' },
      { code: 'zh', name: 'Züridütsch', note: 'La version qui se sent comme chez soi.' },
    ],
  },

  cta: {
    heading: 'Rejoignez Bünzli',
    subline:
      "Nous sommes encore en développement — mais nous cherchons des personnes qui veulent contribuer à le façonner.",
    betaLabel:   'Tester la bêta',
    betaSubject: 'Beta Test Request — buenzli.space',
    betaBody:    'Bonjour,\n\nJe souhaite tester Bünzli en bêta.\n\nMon profil LinkedIn: \nPourquoi je veux tester: \nComment j\'utiliserais Bünzli: ',
    collabLabel:   'Collaborer',
    collabSubject: 'Collaboration Inquiry — buenzli.space',
    collabBody:    'Bonjour,\n\nJe souhaite collaborer sur Bünzli.\n\nMon profil LinkedIn: \nPourquoi je veux collaborer: \nCe que j\'apporte (développement, design, connaissance locale, communauté, etc.): ',
  },

  footer: {
    tagline: 'IA de Zurich, pour Zurich.',
    privacy: 'Confidentialité',
    legal: 'Mentions légales',
    madeIn: 'Construit à Zurich 🇨🇭',
  },
};

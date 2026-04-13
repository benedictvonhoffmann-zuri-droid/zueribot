import type { TranslationSchema } from './de';

export const it: TranslationSchema = {
  meta: {
    title: 'Bünzli — Il tuo assistente IA di Zurigo',
    description:
      "Un assistente IA locale, privato e sovrano per Zurigo. Dati reali della città, crittografia end-to-end e una profonda comprensione della città.",
  },

  nav: {
    skip: 'Vai al contenuto',
  },

  hero: {
    eyebrow: 'Gratuito. Privato. Da Zurigo.',
    headline: 'Zurigo si conosce meglio di chiunque altro.',
    subline:
      'Bünzli è il tuo assistente IA locale — con veri dati di Zurigo, vera privacy, e zero fronzoli.',
    ctaBeta: 'Testa la beta',
    ctaCollaborate: 'Collabora',
    ctaBetaNote: 'Gratuito. Nessuna carta di credito.',
    ctaCollabNote: 'Dev, design, comunità — tutti benvenuti.',
  },

  why: {
    heading: 'Perché Bünzli?',
    problemHeading: "Il problema: l'IA generica non capisce Zurigo.",
    problemText:
      "ChatGPT non sa quando arriva il tram 13. Non conosce le Badi del lago, i quartieri tranquilli, le regole del riciclaggio o le votazioni locali. Inventa ristoranti, allucinica orari e ti dà risposte per un'altra città. Va bene — ma non è quello di cui hai bisogno quando vivi qui.",
    solutionHeading: 'La soluzione: IA che vive davvero qui.',
    solutionText:
      'Bünzli è costruito su dati reali di Zurigo e connessioni live. Link in tempo reale a ZVV, meteo, temperature delle Badi, votazioni, ristoranti e altro ancora. Un archivio di conoscenze dai siti ufficiali della città, blog gastronomici e testi legali locali. Privato, locale, sovrano — fatto per la città in cui vivi.',
  },

  different: {
    heading: 'Cosa ci distingue',
    subline: 'Quattro cose che distinguono Bünzli dagli assistenti IA generici.',
    cards: [
      {
        icon: '🔒',
        title: 'La privacy non è una funzionalità',
        desc: "Le tue conversazioni sono anonimizzate, crittografate end-to-end e archiviate solo localmente nel tuo browser. Non vediamo cosa chiedi. Non è una promessa — è architettura.",
      },
      {
        icon: '📍',
        title: 'Veri dati di Zurigo',
        desc: 'Nessuna conoscenza generica mondiale. Bünzli conosce i siti della città, le pagine cantonali, i blog gastronomici e le leggi locali — e si aggiorna regolarmente.',
      },
      {
        icon: '⚡',
        title: 'Connessioni live',
        desc: '12 connettori in tempo reale danno a Bünzli accesso alla città com\'è adesso — non com\'era l\'anno scorso.',
      },
      {
        icon: '🇨🇭',
        title: 'Sovranità svizzera',
        desc: "Infomaniak ospita tutto su server svizzeri. Si applica la legge svizzera. I tuoi dati non lasciano la Svizzera.",
      },
    ],
  },

  howItWorks: {
    heading: 'Come funziona — spiegato semplicemente',
    subline:
      "Non hai bisogno di capirlo per usare Bünzli. Ma lo spieghiamo comunque — onestamente, senza gergo.",
    items: [
      {
        icon: '🧠',
        title: "Cos'è l'IA?",
        text: "Un modello linguistico prevede quale parola verrà più probabilmente dopo — basandosi su enormi quantità di testo. Non \"pensa\" — riconosce schemi. Pensa a un autocompletamento molto avanzato che ha davvero senso.",
      },
      {
        icon: '📚',
        title: "Cos'è il RAG?",
        text: "Il RAG (Retrieval-Augmented Generation) significa: l'IA non indovina semplicemente — controlla prima le informazioni reali di Zurigo. Come dare a qualcuno una tessera della biblioteca invece di lasciarlo inventare. Lo alimentiamo con pagine ufficiali della città, blog gastronomici, testi legali e conoscenze locali.",
      },
      {
        icon: '🔌',
        title: "Cosa sono i connettori MCP?",
        text: "Pensali come le mani dell'IA. Senza di essi, può solo parlare. Con essi, può controllare il prossimo tram, vedere se piove, trovare un ristorante o dirti quanto è caldo il lago. Dati live — non supposizioni.",
      },
      {
        icon: '🛡️',
        title: 'Cosa rende diversa la nostra privacy?',
        text: "La maggior parte dei servizi IA memorizza tutto ciò che dici — per sempre — per addestrare modelli futuri. Noi no. Le tue conversazioni vivono solo sul tuo dispositivo, crittografate. Non possiamo letteralmente leggerle.",
      },
      {
        icon: '🏔️',
        title: 'Cosa significa "sovrano"?',
        text: "I tuoi dati rimangono in Svizzera. L'IA gira su server svizzeri. Seguiamo la legge svizzera. Nessuna azienda straniera decide cosa succede alle tue conversazioni.",
      },
    ],
  },

  connectors: {
    heading: 'Connessioni live con la città',
    subline:
      '12 connettori in tempo reale collegano Bünzli alla Zurigo che conosci. Chiedi del prossimo tram, della temperatura della Badi o dove mangiare stasera.',
    items: [
      { icon: '🚋', name: 'ZVV Transit',         desc: 'Partenze, coincidenze e interruzioni in tempo reale.' },
      { icon: '🌤️', name: 'Meteo',               desc: 'Previsioni locali e condizioni attuali per Zurigo.' },
      { icon: '🎭', name: 'Luoghi',              desc: 'Bar, club, case culturali e sale da concerto.' },
      { icon: '🎉', name: 'Eventi',              desc: "Cosa c'è oggi, questo fine settimana e questa settimana a Zurigo." },
      { icon: '🍽️', name: 'Ristoranti',          desc: 'Raccomandazioni locali, orari e cucine.' },
      { icon: '🗳️', name: 'Votazioni',           desc: 'Votazioni svizzere e zurighesi attuali e imminenti.' },
      { icon: '🏊', name: 'Temperature Badi',    desc: 'Quanto è caldo il lago adesso? Indice di balneazione per tutte le Badi di Zurigo.' },
      { icon: '🅿️', name: 'Parcheggi',           desc: 'Posti auto liberi in centro città.' },
      { icon: '💨', name: 'Qualità dell\'aria',  desc: "Valori attuali di particolato e indice di qualità dell'aria per Zurigo." },
      { icon: '♻️', name: 'Riciclaggio',          desc: 'Dove riciclare cosa — Kehrichtsack, vetro, PET, tessili.' },
      { icon: '📍', name: 'Punti di interesse',  desc: 'Negozi, attrazioni e consigli locali vicino a te.' },
      { icon: '📚', name: 'Base di conoscenze',  desc: 'Conoscenze ufficiali della città e del cantone, direttamente accessibili.' },
    ],
  },

  privacy: {
    heading: 'Privacy prima di tutto',
    subline:
      "Non come promessa di marketing. Come realtà tecnica. Ecco esattamente come funziona.",
    pillars: [
      {
        icon: '🔐',
        title: 'Crittografia end-to-end',
        desc: "Le tue conversazioni vengono crittografate prima di lasciare il tuo dispositivo. Solo tu hai la chiave — non noi, non Infomaniak.",
      },
      {
        icon: '💾',
        title: 'Solo archiviazione locale',
        desc: "La cronologia delle chat vive esclusivamente nel tuo browser — mai sui nostri server. Svuota la cache e sparisce. È intenzionale.",
      },
      {
        icon: '👤',
        title: 'Richieste anonimizzate',
        desc: "Le richieste all'IA vengono inoltrate in modo anonimo. Non possiamo collegare chi ha chiesto cosa. È tecnicamente impossibile per design.",
      },
      {
        icon: '📊',
        title: 'Analisi minimale',
        desc: "Utilizziamo solo le statistiche di base di Infomaniak. Nessun tracker di terze parti, nessun cookie, nessun Google Analytics. Sappiamo quanti visitatori abbiamo. Tutto qui.",
      },
    ],
  },

  tech: {
    heading: 'Il nostro stack tecnologico — spiegato onestamente',
    subline:
      'La trasparenza è un valore fondamentale. Ecco con cosa lavoriamo — e perché.',
    items: [
      {
        name: 'Apertus 70B',
        role: 'Il cervello',
        desc: "Il grande modello linguistico che alimenta Bünzli. Gira interamente sull'infrastruttura svizzera di Infomaniak — nessun dato che va negli USA o nell'UE.",
      },
      {
        name: 'FastAPI',
        role: 'La spina dorsale',
        desc: 'Un moderno framework web Python che collega tutte le parti. Veloce, aperto, ben documentato.',
      },
      {
        name: 'ChromaDB',
        role: 'La memoria',
        desc: "Un database vettoriale che archivia la nostra conoscenza di Zurigo in un formato che l'IA può cercare alla velocità della luce.",
      },
      {
        name: 'ZITADEL',
        role: 'Il buttafuori',
        desc: "Gestione sicura dell'identità per login e controllo degli accessi. Progetto open-source svizzero — no Auth0, no Okta.",
      },
      {
        name: 'Infomaniak',
        role: 'La casa',
        desc: 'Provider di hosting svizzero con data center a Ginevra e Winterthur. I dati rimangono in Svizzera. Punto.',
      },
      {
        name: 'Open WebUI',
        role: 'Il volto',
        desc: "L'interfaccia di chat che vedi e usi. Open-source, completamente personalizzabile — senza dipendenza da prodotti UI commerciali.",
      },
    ],
  },

  community: {
    heading: 'Cosa viene dopo',
    subline:
      "Questo è solo l'inizio. Bünzli appartiene a Zurigo — e lo costruiamo insieme.",
    items: [
      {
        icon: '🗣️',
        title: 'Züridütsch',
        desc: 'Una versione completa in dialetto zurighese è in lavorazione. Perché alcune cose suonano meglio in dialetto.',
      },
      {
        icon: '👧',
        title: 'Modalità bambini',
        desc: 'Una versione sicura e adatta all\'età per scuole e famiglie. Zurigo spiegata per la prossima generazione.',
      },
      {
        icon: '🔓',
        title: 'Open source',
        desc: "Prevediamo di aprire completamente il codice. L'IA di Zurigo dovrebbe appartenere a Zurigo.",
      },
      {
        icon: '🤝',
        title: 'Guidato dalla comunità',
        desc: 'Richieste di funzionalità, conoscenze locali, correzioni — dalla comunità, per la comunità.',
      },
    ],
  },

  languages: {
    heading: 'Bünzli parla la tua lingua',
    subline:
      'Perché Zurigo è multilingue — e la nostra IA dovrebbe esserlo anche lei.',
    items: [
      { code: 'de', name: 'Deutsch',    note: 'La versione ufficiale.' },
      { code: 'en', name: 'English',    note: 'For internationals calling Zürich home.' },
      { code: 'fr', name: 'Français',   note: 'Pour la Suisse romande et les francophones.' },
      { code: 'it', name: 'Italiano',   note: 'Per chi parla italiano a Zurigo.' },
      { code: 'zh', name: 'Züridütsch', note: 'La versione che si sente come a casa.' },
    ],
  },

  cta: {
    heading: 'Unisciti a Bünzli',
    subline:
      "Siamo ancora in sviluppo — ma cerchiamo persone che vogliano contribuire a plasmarlo.",
    betaLabel:   'Testa la beta',
    betaSubject: 'Beta Test Request — buenzli.space',
    betaBody:    'Ciao,\n\nVorrei testare Bünzli in beta.\n\nIl mio profilo LinkedIn: \nPerché voglio testare: \nCome userei Bünzli: ',
    collabLabel:   'Collabora',
    collabSubject: 'Collaboration Inquiry — buenzli.space',
    collabBody:    'Ciao,\n\nVorrei collaborare a Bünzli.\n\nIl mio profilo LinkedIn: \nPerché voglio collaborare: \nCosa porto (sviluppo, design, conoscenza locale, comunità, ecc.): ',
  },

  footer: {
    tagline: 'IA da Zurigo, per Zurigo.',
    privacy: 'Privacy',
    legal: 'Note legali',
    madeIn: 'Costruito a Zurigo 🇨🇭',
  },
};

// TODO: native speaker review — AI-generated Züridütsch draft
// Züri Dütsch has no standardised orthography. This draft aims for Zürich city dialect.
// Key conventions used: isch=ist, ned=nicht, chend=kennt, mer=wir/man, kes=kein,
// sälber=selbst, chli=klein/etwas, händ=haben, gönd=gehen, lueg=schau, gäll=gell

import type { TranslationSchema } from './de';

export const zh: TranslationSchema = {
  meta: {
    title: 'Bünzli — Dini Züri-KI',
    description:
      'En lokale, private, souveräni KI für Züri. Echti Stadtdate, End-to-End-Verschlüsselig, und es tiäfs Verstande vo dr Stadt — uf Züridütsch, wenn nötig.',
  },

  nav: {
    skip: 'Zum Inhalt',
  },

  hero: {
    eyebrow: 'Gratis. Privat. Vo Züri.',
    headline: 'Züri chent sich sälber am beschte.',
    subline:
      'Bünzli isch dini lokali KI — mit echte Züri-Date, echter Privatsphäre, und kes Gschnurr.',
    ctaBeta: 'Beta teste',
    ctaCollaborate: 'Mitmache',
    ctaBetaNote: 'Gratis. Kei Kreditkarte.',
    ctaCollabNote: 'Dev, Design, Community — alli sind willkomme.',
  },

  why: {
    heading: 'Warum Bünzli?',
    problemHeading: 'S Problem: Generischi KI versteit Züri ned.',
    problemText:
      'ChatGPT wäiss ned, wänn d 13er-Tram chunnt. Es chent d Badis am See ned, d stille Quartier, d Recyclingregele oder d lokale Abstimmige ned. Es erfindet Restaurants, halluziniert Ufzyte und git dir Antwörte für en anderi Stadt. Isch nett — aber ned das, was mer brucht, wenn mer hie läbt.',
    solutionHeading: 'D Lösig: En KI, wo wirklich dehei isch.',
    solutionText:
      'Bünzli isch mit echte Züri-Date und Live-Verbindig ufbaut. Echtziit-Links zu ZVV, Wätter, Baditemperatüre, Abstimmige, Restaurants und meh. Es Wissensarchiv us offizielle Stadtsyte, Foodblogs und lokale Quälle. Privat, lokal, souverän — gmacht für d Stadt, woni läbsch.',
  },

  different: {
    heading: 'Was üs unterscheidet',
    subline: 'Vieri Sache, wo Bünzli vo generische KI-Assistente abhebt.',
    cards: [
      {
        icon: '🔒',
        title: 'Privatsphäre isch kes Feature',
        desc: 'Dini Chats wärde anonymisiert, End-to-End verschlüsslet und nur lokal in dim Browser gspeichert. Mer gseht ned, was du fragsch. Das isch kes Verspreche — das isch Architektur.',
      },
      {
        icon: '📍',
        title: 'Echti Züri-Date',
        desc: 'Kes allgemäini Wältwisse. Bünzli chent d Stadtsyte, d Kantonssite, d Foodblogs und d lokale Gsetz — und aktualisiert sich regelmässig.',
      },
      {
        icon: '⚡',
        title: 'Live-Verbindig',
        desc: '12 Echtziit-Konnektore gänd Bünzli Zugiff uf d Stadt, wie si grad isch — ned wie si vor eme Jahr gsi isch.',
      },
      {
        icon: '🇨🇭',
        title: 'Schwizer Souveränität',
        desc: 'Infomaniak hostet alles uf Schwizer Server. Schwizer Rächt gilt. Dini Date verlönd d Schwiz ned.',
      },
    ],
  },

  howItWorks: {
    heading: 'Wie das funktioniert — eifach erklärt',
    subline:
      'Du muesch das ned verstah, zum Bünzli z nutze. Aber mer erklärts trotzdem — ehrlich, ohni Fachjargon.',
    items: [
      {
        icon: '🧠',
        title: 'Was isch KI?',
        text: 'Es Spraachmodell sait vorüs, weles Wort als nächsts wahrschynlich chunnt — basierend uf riesige Mänge Text. Es "dänkt" ned — es erchent Muster. Stell dir en sehr fortgschritteni Autovervollständigung vor, wo tatsächlich Sinn macht.',
      },
      {
        icon: '📚',
        title: 'Was isch RAG?',
        text: 'RAG (Retrieval-Augmented Generation) bedeutet: D KI ratet ned eifach — si luegt zerscht in echte Züri-Informatione nach. Wie en Bibliothekuswiis statt Erfinde. Mer fütterets mit offizielle Stadtsyte, Foodblogs, Gsetzestexte und lokalem Wisse.',
      },
      {
        icon: '🔌',
        title: 'Was sind MCP-Konnektore?',
        text: "Dänk a si als d Händ vo dr KI. Ohni si chann si nur rede. Mit ene chann si d nächscht Tram checke, luege ob s rägnet, es Restaurant finde oder dir säge, wie warm dr See isch. Live-Date — kei Raterei.",
      },
      {
        icon: '🛡️',
        title: 'Was macht üsi Privatsphäre anders?',
        text: 'D meischte KI-Dienscht speichernd alles, was du sagsch — für immer — zum künftigi Modell z trainiere. Mir ned. Dini Chats läbend nur uf dim Grät, verschlüsslet. Mir chönnd si buchstäblich ned läse.',
      },
      {
        icon: '🏔️',
        title: 'Was bedeutet "souverän"?',
        text: 'Dini Date blibend in dr Schwiz. D KI lauft uf Schwizer Server. Mir folgend Schwizer Rächt. Kei uslendischs Unternehme entscheided, was mit dinere Gspröch passiert.',
      },
    ],
  },

  connectors: {
    heading: 'Live-Verbindig zur Stadt',
    subline:
      '12 Echtziit-Konnektore verbindend Bünzli mit em Züri, wo du chentsch. Frag nach em nächschte Zug, dr Badi-Temperatur oder wo du hüt z Nacht isch.',
    items: [
      { icon: '🚋', name: 'ZVV Transit',        desc: 'Abfahrte, Verbindig und Störige in Echtziit.' },
      { icon: '🌤️', name: 'Wätter',             desc: 'Lokali Wettervorhersag und aktuelli Bedingige für Züri.' },
      { icon: '🎭', name: 'Veraastaltigsort',   desc: 'Bars, Clubs, Kulturhüser und Konzertlokal in dr Stadt.' },
      { icon: '🎉', name: 'Events',             desc: 'Was hüt, dis Wuchenend und die Wuche in Züri lauft.' },
      { icon: '🍽️', name: 'Restaurants',        desc: 'Lokali Empfehlige, Ufzyte und Küche.' },
      { icon: '🗳️', name: 'Abstimmige',         desc: 'Aktuelli und komendi Schwizer und Züri Abstimmige.' },
      { icon: '🏊', name: 'Badi-Temperature',   desc: 'Wie warm isch dr See grad? Badeindex für alli Züri-Badis.' },
      { icon: '🅿️', name: 'Parkplatz',          desc: 'Freii Parkhüser und Parkplatz in dr Innestatt.' },
      { icon: '💨', name: 'Luftqualität',        desc: 'Aktuelli Feinstaubwert und Luftqualitätsindex für Züri.' },
      { icon: '♻️', name: 'Recycling',           desc: 'Wo was recycled wird — Kehrichtsack, Glas, PET, Textilie.' },
      { icon: '📍', name: 'Points of Interest',  desc: 'Gschäft, Sehenswertigkeite und lokali Tipps in dinere Nächi.' },
      { icon: '📚', name: 'Wissensbase',         desc: 'Offizielle Stadt- und Kantonswisse, direkt abrüefbar.' },
    ],
  },

  privacy: {
    heading: 'Privatsphäre zerscht',
    subline:
      'Ned als Marketingverspreche. Als technischi Realität. Da isch gnau, wie s funktioniert.',
    pillars: [
      {
        icon: '🔐',
        title: 'End-to-End-Verschlüsselig',
        desc: "Dini Gspröch wärde verschlüsslet, bevor si dis Grät verlönd. Nur du häsch dr Schlüssel — ned mir, ned Infomaniak.",
      },
      {
        icon: '💾',
        title: 'Nur lokali Speicherig',
        desc: "Dini Chatverlauf läbt nur in dim Browser — nie uf üsere Server. Wenn du dr Browser-Cache läärsch, isch er wäg. Das isch Absicht.",
      },
      {
        icon: '👤',
        title: 'Anonymisierti Afrage',
        desc: "Afrage an d KI wärde anonymisiert wiitergläitet. Mir chönd ned verbinde, wer was gfragt het. Das gaht technisch gar ned.",
      },
      {
        icon: '📊',
        title: 'Minimali Analytik',
        desc: "Mir nutze nur d Basis-Sytestatistike vo Infomaniak. Kei Drittanbieter-Tracker, kei Cookies, kein Google Analytics. Mir wäissed, wie vill Besucher mir händ. Das wars.",
      },
    ],
  },

  tech: {
    heading: 'Üser Tech-Stack — ehrlich erklärt',
    subline:
      'Transparenz isch en Kernwert. Da isch, womit mir arbeite — und warum.',
    items: [
      {
        name: 'Apertus 70B',
        role: 'S Gehirn',
        desc: "S grossi Spraachmodell, wo Bünzli antribt. Lauft komplett uf Infomaniaks Schwizer Infrastruktur — kei Dateabfluss id USA oder EU.",
      },
      {
        name: 'FastAPI',
        role: 'S Ruckgrat',
        desc: 'En modernes Python-Webframework, wo alli Täil verbindet. Schnell, offe, guet dokumentiert.',
      },
      {
        name: 'ChromaDB',
        role: 'S Gedächtnis',
        desc: "En Vektordatenbank, wo üses Züri-Wisse so speichert, dass d KI blizschnell drin suche chann. Lokal, privat, kein Cloud-Zwang.",
      },
      {
        name: 'ZITADEL',
        role: 'Dr Türsteher',
        desc: "Sicheres Identity-Management für Login und Zuegangskontrolle. Schwizer Open-Source-Projekt — kein Auth0, kein Okta.",
      },
      {
        name: 'Infomaniak',
        role: 'S Zuhause',
        desc: 'Schwizer Hosting-Anbitter mit Rechezentrum in Genf und Winterthur. Date blibend in dr Schwiz. Punkt.',
      },
      {
        name: 'Open WebUI',
        role: 'S Gsicht',
        desc: "D Chat-Oberflächi, wo du gsiisch und bruuchsch. Open-Source, vollständig aapassbar — kein Abhängigkeit vo kommerzielle UI-Produkt.",
      },
    ],
  },

  community: {
    heading: 'Was als Nächsts chunnt',
    subline:
      "Das isch erst dr Afang. Bünzli ghört Züri — und mir bäuet s zäme wiiter.",
    items: [
      {
        icon: '🗣️',
        title: 'Züridütsch',
        desc: "En vollständigi Züridütsch-Version isch in Arbeit. Wil mängi Sache eifach besser uf Mundart klingend. Gäll?",
      },
      {
        icon: '👧',
        title: 'Chindsmodus',
        desc: 'En sichere, altersgerechti Version für Schulen und Familien. Züri erklärt, für d nächschti Generation.',
      },
      {
        icon: '🔓',
        title: 'Open Source',
        desc: "Mir planed, dr Code vollständig z öffne. Züris KI sott Züri ghöre — und vo Züri wiiterentwicklet wärde.",
      },
      {
        icon: '🤝',
        title: 'Community-gestüüret',
        desc: "Feature-Requests, lokals Wisse, Verbässerigsvörschläg — vo dr Community, für d Community. Du wäisst am beschte, was Züri bruucht.",
      },
    ],
  },

  languages: {
    heading: 'Bünzli redet dini Spraach',
    subline:
      "Wil Züri mehrsproochig isch — und üsi KI das au sii sott.",
    items: [
      { code: 'de', name: 'Deutsch',    note: 'D offizielli Version.' },
      { code: 'en', name: 'English',    note: 'For internationals calling Zürich home.' },
      { code: 'fr', name: 'Français',   note: 'Pour la Suisse romande et les francophones.' },
      { code: 'it', name: 'Italiano',   note: 'Per chi parla italiano a Zurigo.' },
      { code: 'zh', name: 'Züridütsch', note: 'D Version, wo sich wie Zuhause afühlt.' },
    ],
  },

  cta: {
    heading: 'Wärde Teil vo Bünzli',
    subline:
      "Mir sind noch in dr Entwicklig — aber mir sueched Mönsche, wo mitwirke wänd.",
    betaLabel:   'Beta teste',
    betaSubject: 'Beta Test Request — buenzli.space',
    betaBody:    'Sali,\n\nIch möcht Bünzli beta teste.\n\nMin LinkedIn-Profil: \nWarum ich beta teste möcht: \nWofür ich Bünzli nutze würd: ',
    collabLabel:   'Mitmache',
    collabSubject: 'Collaboration Inquiry — buenzli.space',
    collabBody:    'Sali,\n\nIch möcht bi Bünzli mitmache.\n\nMin LinkedIn-Profil: \nWarum ich mitmache möcht: \nWas ich ibring (Entwicklig, Design, lokals Wisse, Community, uws.): ',
  },

  footer: {
    tagline: 'KI vo Züri, für Züri.',
    privacy: 'Dateschutz',
    legal: 'Impressum',
    madeIn: 'Baut in Züri 🇨🇭',
  },
};

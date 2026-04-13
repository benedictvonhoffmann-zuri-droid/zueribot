import type { TranslationSchema } from './de';

export const en: TranslationSchema = {
  meta: {
    title: 'Bünzli — Your Zürich AI Assistant',
    description:
      'A local, private, sovereign AI assistant for Zürich. Real city data, end-to-end encryption, and a deep understanding of the city — in Züri Dütsch if needed.',
  },

  nav: {
    skip: 'Skip to content',
  },

  hero: {
    eyebrow: 'Free. Private. From Zürich.',
    headline: 'Zürich knows itself best.',
    subline:
      'Bünzli is your local AI assistant — real Zürich data, real privacy, zero fluff.',
    ctaBeta: 'Beta test',
    ctaCollaborate: 'Collaborate',
    ctaBetaNote: 'Free. No credit card.',
    ctaCollabNote: 'Dev, design, community — all welcome.',
  },

  why: {
    heading: 'Why Bünzli?',
    problemHeading: "The problem: generic AI doesn't understand Zürich.",
    problemText:
      "ChatGPT doesn't know when the 13 tram is coming. It doesn't know the lake Badis, the quiet neighbourhoods, the recycling rules or local votes. It invents restaurants, hallucinates opening hours, and gives you answers for a different city. That's fine — but not what you need when you actually live here.",
    solutionHeading: 'The solution: AI that actually lives here.',
    solutionText:
      'Bünzli is built on real Zürich data and live connections. Real-time links to ZVV, weather, lake temperatures, votes, restaurants and more. A knowledge archive from official city pages, food blogs and local legal texts. Private, local, sovereign — built for the city you call home.',
  },

  different: {
    heading: 'What makes us different',
    subline: 'Four things that set Bünzli apart from generic AI assistants.',
    cards: [
      {
        icon: '🔒',
        title: 'Privacy is not a feature',
        desc: "Your chats are anonymised, end-to-end encrypted, and stored only locally in your browser. We can't see what you ask. That's not a promise — it's architecture.",
      },
      {
        icon: '📍',
        title: 'Real Zürich data',
        desc: 'No generic world knowledge. Bünzli knows city websites, cantonal pages, food blogs and local laws — and updates regularly.',
      },
      {
        icon: '⚡',
        title: 'Live connections',
        desc: '12 real-time connectors give Bünzli access to the city as it is right now — not as it was last year.',
      },
      {
        icon: '🇨🇭',
        title: 'Swiss sovereignty',
        desc: 'Infomaniak hosts everything on Swiss servers. Swiss law applies. Your data does not leave Switzerland.',
      },
    ],
  },

  howItWorks: {
    heading: 'How it works — explained simply',
    subline:
      "You don't need to understand this to use Bünzli. But we explain it anyway — honestly, without jargon.",
    items: [
      {
        icon: '🧠',
        title: 'What is AI?',
        text: 'A language model predicts which word is most likely to come next — based on vast amounts of text. It doesn\'t "think" — it recognises patterns. Think of it as a very advanced autocomplete that actually makes sense.',
      },
      {
        icon: '📚',
        title: 'What is RAG?',
        text: "RAG (Retrieval-Augmented Generation) means: the AI doesn't just guess — it first checks real Zürich information. Like giving someone a library card instead of letting them make things up. We feed it official city pages, food blogs, legal texts and local knowledge — so its answers about Zürich are actually about your Zürich.",
      },
      {
        icon: '🔌',
        title: 'What are MCP connectors?',
        text: "Think of them as the AI's hands. Without them, it can only talk. With them, it can check the next tram, see if it's raining, find you a restaurant, or tell you how warm the lake is. Live data — not guesses.",
      },
      {
        icon: '🛡️',
        title: 'What makes our privacy different?',
        text: "Most AI services store everything you say — forever — to train future models. We don't. Your chats live only on your device, encrypted. We literally cannot read them. That's not marketing — that's how the system is built.",
      },
      {
        icon: '🏔️',
        title: 'What does "sovereign" mean?',
        text: "Your data stays in Switzerland. The AI runs on Swiss servers. We follow Swiss law. No foreign company decides what happens with your conversations.",
      },
    ],
  },

  connectors: {
    heading: 'Live connections to the city',
    subline:
      '12 real-time connectors link Bünzli to the Zürich you know. Ask about the next tram, the Badi temperature, or where to eat tonight.',
    items: [
      { icon: '🚋', name: 'ZVV Transit',        desc: 'Departures, connections and disruptions in real time.' },
      { icon: '🌤️', name: 'Weather',             desc: 'Local forecast and current conditions for Zürich.' },
      { icon: '🎭', name: 'Venues',              desc: 'Bars, clubs, cultural centres and concert venues.' },
      { icon: '🎉', name: 'Events',              desc: "What's on today, this weekend and this week in Zürich." },
      { icon: '🍽️', name: 'Restaurants',         desc: 'Local recommendations, opening hours and cuisines.' },
      { icon: '🗳️', name: 'Votes',               desc: 'Current and upcoming Swiss and Zürich ballots.' },
      { icon: '🏊', name: 'Badi temperatures',   desc: 'How warm is the lake right now? Swimming index for all Zürich Badis.' },
      { icon: '🅿️', name: 'Parking',             desc: 'Free car parks and parking spaces in the city centre.' },
      { icon: '💨', name: 'Air quality',          desc: 'Current particulate matter values and air quality index for Zürich.' },
      { icon: '♻️', name: 'Recycling',            desc: "Where to recycle what — Kehrichtsack, glass, PET, textiles." },
      { icon: '📍', name: 'Points of interest',  desc: 'Shops, sights and local tips near you.' },
      { icon: '📚', name: 'Knowledge base',       desc: 'Official city and cantonal knowledge, directly accessible.' },
    ],
  },

  privacy: {
    heading: 'Privacy first',
    subline:
      "Not as a marketing promise. As a technical reality. Here's exactly how it works.",
    pillars: [
      {
        icon: '🔐',
        title: 'End-to-end encryption',
        desc: "Your conversations are encrypted before they leave your device. Only you hold the key — not us, not Infomaniak.",
      },
      {
        icon: '💾',
        title: 'Local storage only',
        desc: 'Your chat history lives exclusively in your browser — never on our servers. Clear your browser cache and it\'s gone. That\'s intentional.',
      },
      {
        icon: '👤',
        title: 'Anonymised requests',
        desc: "Requests to the AI are forwarded anonymously. We cannot connect who asked what. That's technically impossible by design.",
      },
      {
        icon: '📊',
        title: 'Minimal analytics',
        desc: "We use only Infomaniak's basic page statistics. No third-party trackers, no cookies, no Google Analytics. We know how many visitors we have. That's it. That's all we want to know.",
      },
    ],
  },

  tech: {
    heading: 'Our tech stack — explained honestly',
    subline:
      'Transparency is a core value. Here is what we work with — and why.',
    items: [
      {
        name: 'Apertus 70B',
        role: 'The brain',
        desc: "The large language model powering Bünzli. Runs entirely on Infomaniak's Swiss infrastructure — no data leaving for the US or EU.",
      },
      {
        name: 'FastAPI',
        role: 'The backbone',
        desc: 'A modern Python web framework connecting all the parts. Fast, open, well-documented.',
      },
      {
        name: 'ChromaDB',
        role: 'The memory',
        desc: 'A vector database that stores our Zürich knowledge in a format the AI can search at lightning speed. Local, private, no cloud dependency.',
      },
      {
        name: 'ZITADEL',
        role: 'The bouncer',
        desc: "Secure identity management for login and access control. Swiss open-source project — no Auth0, no Okta.",
      },
      {
        name: 'Infomaniak',
        role: 'The home',
        desc: 'Swiss hosting provider with data centres in Geneva and Winterthur. Data stays in Switzerland. Full stop.',
      },
      {
        name: 'Open WebUI',
        role: 'The face',
        desc: 'The chat interface you see and use. Open-source, fully customisable — no dependency on commercial UI products.',
      },
    ],
  },

  community: {
    heading: "What's coming next",
    subline:
      "This is just the beginning. Bünzli belongs to Zürich — and we're building it together.",
    items: [
      {
        icon: '🗣️',
        title: 'Züri Dütsch',
        desc: 'A full Zürich dialect version is in the works. Because some things just sound better in dialect. Right?',
      },
      {
        icon: '👧',
        title: 'Child mode',
        desc: 'A safe, age-appropriate version for schools and families. Zürich explained for the next generation.',
      },
      {
        icon: '🔓',
        title: 'Open source',
        desc: "We plan to open the code fully. Zürich's AI should belong to Zürich — and be developed by Zürich.",
      },
      {
        icon: '🤝',
        title: 'Community-driven',
        desc: 'Feature requests, local knowledge, corrections — from the community, for the community. You know best what Zürich needs.',
      },
    ],
  },

  languages: {
    heading: 'Bünzli speaks your language',
    subline:
      "Because Zürich is multilingual — and our AI should be too.",
    items: [
      { code: 'de', name: 'Deutsch',    note: 'The official version.' },
      { code: 'en', name: 'English',    note: 'For internationals calling Zürich home.' },
      { code: 'fr', name: 'Français',   note: 'For Swiss Romandy and all Francophones.' },
      { code: 'it', name: 'Italiano',   note: 'For Italian speakers in Zürich.' },
      { code: 'zh', name: 'Züridütsch', note: 'The version that feels like home.' },
    ],
  },

  cta: {
    heading: 'Join Bünzli',
    subline:
      "We're still in development — but we're looking for people who want to help shape it. Beta testers and collaborators.",
    betaLabel:   'Beta test',
    betaSubject: 'Beta Test Request — buenzli.space',
    betaBody:    'Hello,\n\nI would like to beta test Bünzli.\n\nMy LinkedIn profile: \nWhy I want to beta test: \nWhat I would use Bünzli for: ',
    collabLabel:   'Collaborate',
    collabSubject: 'Collaboration Inquiry — buenzli.space',
    collabBody:    'Hello,\n\nI would like to collaborate on Bünzli.\n\nMy LinkedIn profile: \nWhy I want to collaborate: \nWhat I bring (development, design, local knowledge, community, etc.): ',
  },

  footer: {
    tagline: 'AI from Zürich, for Zürich.',
    privacy: 'Privacy',
    legal: 'Legal notice',
    madeIn: 'Built in Zürich 🇨🇭',
  },
};

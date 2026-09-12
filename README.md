# watchlist-utils

###### This repository contains a few python files to read S&P500, NASDAQ, and DOW components from Wikipedia and save them as JSON files.
###### It also populates a JSON file of companies market cap. This is information is downloaded and saved as csv manually.

## Firebase Hosting

This is a static site. There is no frontend build step; Firebase serves the `public/` directory directly.

Install and authenticate the Firebase CLI once:

```bash
npm install -g firebase-tools
firebase login
firebase use watchlist-static-files
```

Test locally with the hosting emulator:

```bash
firebase emulators:start --only hosting
```

Deploy from the repository root:

```bash
firebase deploy --only hosting
```

The default URL is `https://watchlist-static-files.web.app`. The deployment contains only static files under `public/`; local `config.json` is ignored and must never be deployed because it contains the CoinMarketCap API key.
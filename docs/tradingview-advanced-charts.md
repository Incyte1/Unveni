# TradingView Advanced Charts integration

This project follows the official TradingView Advanced Charts installation pattern, adapted to the Vite app in `apps/web`.

## Required asset layout

After TradingView grants access to the private repository, copy these folders into the web app's public assets:

- `charting_library/` -> `apps/web/public/charting_library/`
- `datafeeds/` -> `apps/web/public/datafeeds/`
- create `apps/web/.env.local` with `VITE_ENABLE_TRADINGVIEW=true`

The app expects these files to resolve at runtime:

- `/charting_library/charting_library.standalone.js`
- `/datafeeds/udf/dist/bundle.js`

## Runtime behavior

`apps/web/src/components/chart/ChartContainer.tsx` loads the TradingView scripts dynamically and initializes:

```ts
new TradingView.widget({
  container: "...",
  locale: "en",
  library_path: "/charting_library/",
  datafeed: new Datafeeds.UDFCompatibleDatafeed("https://demo-feed-data.tradingview.com"),
  symbol,
  interval: "1D",
  fullscreen: false,
  autosize: true,
  debug: true
});
```

The chart mounts inside the selected trade drawer, so switching ranked opportunities updates the underlying symbol shown in the TradingView widget.

## Local run

From the repo root:

```bash
npm install
npm run dev:web
```

Open `http://localhost:5173`.

## License boundary

TradingView's Advanced Charts library is proprietary and non-redistributable. This repository therefore includes only:

- the integration code
- placeholder directories
- setup documentation

The actual TradingView library files must be obtained from TradingView and kept out of public git history.

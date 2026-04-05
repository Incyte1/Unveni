export {};

declare global {
  interface Window {
    Datafeeds?: {
      UDFCompatibleDatafeed: new (url: string) => unknown;
    };
    TradingView?: {
      version?: () => string;
      widget: new (options: TradingViewWidgetOptions) => TradingViewWidgetInstance;
    };
  }
}

interface TradingViewWidgetOptions {
  allow_symbol_change?: boolean;
  autosize?: boolean;
  container: string;
  datafeed: unknown;
  debug?: boolean;
  fullscreen?: boolean;
  interval: string;
  library_path: string;
  locale: string;
  symbol: string;
  theme?: "light" | "dark";
}

interface TradingViewWidgetInstance {
  remove?: () => void;
}

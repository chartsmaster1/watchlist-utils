"""Ticker normalization shared by index preparers."""


ALIASES = {
    'BRK-B': 'BRK.B',
    'BF-A': 'BF.B',
    'BF-B': 'BF.B',
    'GOOGL': 'GOOG',
}


def normalize_tickers(values):
    return values.fillna('').astype(str).str.strip().replace(ALIASES)


def report_missing_market_caps(dataframe):
    missing = sorted(dataframe.loc[dataframe['MarketCap'].isna(), 'Ticker'].unique())
    if missing:
        print(f'Warning: {len(missing)} tickers have no market cap: {missing}')
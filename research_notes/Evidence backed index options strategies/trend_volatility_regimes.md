# Trend-following, volatility-targeting and regime filters for SPY/QQQ/IWM, and options adaptation

Evidence tags: [PR]=peer-reviewed, [WP]=working paper, [IDX]=index-provider/press on index, [PRAC]=practitioner/aggregator. Limit: ~15 tool calls; many numbers come from search snippets or aggregator summaries and are flagged.

## 1. Time-series momentum / century-of-trend / managed-futures track records

### Takeaway
Diversified futures trend-following has strong long-sample evidence (AQR hypothetical net Sharpe 0.77 over 1880-2013) but the sample is weaker after 2000 (0.62 for 2000-2013) and the 2009-2019 decade was poor in real-money index data, followed by a record 2022. Equity-index-only trend is a much weaker, noisier subset of this evidence.

### Cited Findings
- Moskowitz-Ooi-Pedersen, JFE May 2012 [PR]: significant TSMOM in 58 liquid futures (equity index, currency, commodity, bond); persistence 1-12 months, partial reversal at longer horizons; diversified TSMOM Sharpe above 1.20 gross (abstract summary) — [secondary summary via search](https://quantpedia.com/strategies/time-series-momentum-effect/)
- Hurst-Ooi-Pedersen "A Century of Evidence on Trend-Following Investing" (AQR; JPM Fall 2014, updated 2017) [PR/practitioner-white-paper]: 1880-2013 hypothetical TSMOM gross 14.9%, net of 2/20 fees and simulated transaction costs 11.2% annualized, vol 9.7%, net Sharpe 0.77, correlation to S&P 500 0.00 — [AQR paper PDF](https://oxfordstrat.com/coasdfASD32/uploads/2016/03/A-Century-of-Evidence-on-Trend-Following-Investing.pdf)
- Same paper decade net Sharpe: 1970s 1.70, 1950s 1.45, 1920s 1.09, 1980s 0.96, 1990s 0.98, 2000-2013 0.62; weakest 1910s 0.13, 1880s 0.27 — [AQR paper PDF](https://oxfordstrat.com/coasdfASD32/uploads/2016/03/A-Century-of-Evidence-on-Trend-Following-Investing.pdf)
- Same paper: first 10 decades described as out-of-sample vs. earlier studies; 80% 60/40 + 20% TSMOM: net Sharpe 0.54 vs 0.38, max drawdown -50.2% vs -62.3%; authors argue even Sharpe 0.4 trend still helps; they cite rising cross-asset correlation, AUM growth ($22bn 1999 to >$280bn 2014) as reasons for lower future Sharpe — [AQR paper PDF](https://oxfordstrat.com/coasdfASD32/uploads/2016/03/A-Century-of-Evidence-on-Trend-Following-Investing.pdf)
- Same paper: most 60/40 bear markets unfolded gradually (avg peak-to-trough length of 10 largest drawdowns ~15 months), which is why trend works in them — [AQR paper PDF](https://oxfordstrat.com/coasdfASD32/uploads/2016/03/A-Century-of-Evidence-on-Trend-Following-Investing.pdf)
- SG Trend Index 2022: +27.3%, record; SG CTA Index +20.1%, best since 2000 inception; prior double-digit year was 2014 (+19.7%); 2022 was only third time SG index >20% — [TheFullFX/press on SG indices](https://thefullfx.com/year-end-drop-fails-to-dampen-stellar-2022-for-trend-followers/) [IDX]; [Hedgeweek](https://www.hedgeweek.com/trend-followers-turn-leaders-ctas-deliver-record-returns-2022/)
- SG Trend 2020: +6.28% (per search summary) — [SG/press](https://content.sgmarkets.com/CTA_UPDATE_KEEPING_UP_WITH_THE_TRENDFOLLOWERS_2025) [IDX]
- Press/practitioner characterization: classical liquid-market trend "struggled over most of the 10 years since the GFC", shown by SG Trend and Barclay CTA indices; SG Trend +36% first three quarters 2022 — [CME Group education](https://cmegroup.com/education/articles-and-reports/the-market-environment-for-trend-following.html) [PRAC]; CME paper "Trends not dead" (Babbedge/Kerson 2019) exists but fetch timed out, content not read — [CME PDF](https://www.cmegroup.com/education/files/trends-not-dead-babbedge-kerson-2019.pdf)

### Inferences
- Hypothetical AQR figures use simulated costs and 10% vol target; real index returns include actual fees and are lower. Treat 0.4-0.6 as a realistic forward Sharpe, in line with authors' own conservative case.
- Evidence is for diversified multi-asset futures, with short sides. Long-only SPY/QQQ/IWM timing captures only the equity-bear-avoidance part; no direct inheritance of Sharpe 0.77.
- 2022 payoff came mainly from bonds/rates/commodities, not equity (inference, not verified here); a US-equity-only trend filter would not have replicated it.

### Gaps
- Full SG Trend / SG CTA / Barclay BTOP50 annual return table 2010-2025 not found; only 2014, 2020, 2022 verified. 2011-2019 annualized figure unverified. 2023-2025 not found. Need SG Prime Services data or BarclayHedge.
- MOP 2012 paper itself not read; Sharpe figure from secondary source.
- Equity-index-only TSMOM Sharpe from MOP/AQR not extracted.

## 2. Moving-average timing on equity indices (Faber)

### Takeaway
Faber's 10-month SMA rule cuts drawdown a lot and Sharpe modestly; independent long-sample, net-of-cost tests (Zakamulin) find only marginal Sharpe gains (7-12%), no statistically significant outperformance post-1932, and possibly fatter left tails. Benefit is concentrated in a few crises (2008, 1929-32).

### Cited Findings
- Faber 2007 SSRN paper (most-downloaded SSRN paper, >200k downloads); 10-month SMA on 5 asset classes, monthly, in cash when below — [ETF.com/Swedroe summary](https://www.etf.com/sections/index-investor-corner/swedroe-why-financial-trends-persist) [PRAC]
- Faber 2013 update, 5-asset 1973-2012: Sharpe 0.73 vs 0.44 buy-and-hold, max DD -9.5% vs -46.0%, return 10.5% vs 9.9%; S&P 500 alone 1901-2012: Sharpe 0.55 vs 0.32, max DD -50.3% vs -83.5%; invested ~70% of time, 3-4 trades/year; flagged as dependent on extreme episodes such as 2008 (gross) — [CXO Advisory summary](https://www.cxoadvisory.com/technical-trading/long-term-outperformance-from-trends-defined-by-moving-averages) [PRAC]
- Faber "Revisited 10 Years Later," JPM 2018: out-of-sample Sharpe reported 0.80 vs earlier 0.45 (summary wording ambiguous; likely rule vs buy-and-hold comparison) — [ETF.com/Swedroe](https://www.etf.com/sections/index-investor-corner/swedroe-why-financial-trends-persist) [PRAC; treat with caution]
- Zakamulin, "Real-Life Performance of Market Timing with Moving Average and TSMOM Rules" (2013): with 0.5% equity / 0.1% bond one-way costs, 1930-2012 out-of-sample net Sharpe gain vs S&P buy-and-hold only 7-12% (SMA +10%, intrinsic momentum +12%; bootstrap 7%); timing may "elevate rather than suppress downside risk", fatter left tail; rules underperform B&H in ~80% of the intervals between exit and re-entry; ignores taxes — [CXO summary](https://www.cxoadvisory.com/technical-trading/net-performance-of-sma-and-intrinsic-momentum-timing-strategies) [WP/PR-summary via PRAC]
- Zakamulin "Comprehensive Look at Empirical Performance of MA Trading Strategies" (SSRN 2677212): 155 years of S&P Composite; MA rules outperform in bear states, generate many false signals in both states; outperformance over 1870-2014 but no statistically significant outperformance post-1932 per search summary — [SSRN](https://papers.ssrn.com/abstract=2677212) [WP]
- Zakamulin 2018 showed extraordinary reported MA performance in another study was due to look-ahead bias — [CXO summary link via search](https://www.cxoadvisory.com/?p=23058) [PRAC; exact target study not identified]

### Inferences
- Realistic expectation for 200-day/10-month filter on SPY: DD reduction substantial, return roughly equal or lower, Sharpe gain small once costs counted. In ETFs today 0.5% one-way cost is too high; costs are ~1-3 bp for SPY, so Zakamulin's net haircut overstates modern cost, but the bear-state-only benefit still holds.
- Daily 200-day SMA has more whipsaws than the monthly rule; no source found quantifying daily whipsaw count for SPY/QQQ/IWM.

### Gaps
- No independent replication specifically on QQQ and IWM found. No post-2018 (2020 crash V-shape, 2022, 2025) evaluation found. Faber's own post-publication Sharpe claim not verified from primary text.

## 3. Volatility-managed portfolios

### Takeaway
Moreira-Muir's in-sample alphas largely fail out-of-sample for most factors (Cederburg et al.), and transaction costs wipe out most non-market factor gains, but the volatility-managed market portfolio is the strongest survivor, with some evidence it stays profitable after costs. Barroso-Santa-Clara is solid for momentum factor, not directly for index timing.

### Cited Findings
- Moreira-Muir, "Volatility-Managed Portfolios," JF 72(4) 2017 [PR]: scaling inversely to prior realized variance yields large alphas and higher Sharpe for market, value, momentum, profitability, ROE, investment factors and FX carry; mechanism: volatility changes not offset by proportional expected-return changes — [NBER 22208](https://www.nber.org/papers/22208)
- Cederburg-O'Doherty-Wang-Yan, JFE 138 (2020) 95-117 [PR]: across 103 equity strategies, vol-managed portfolios do not systematically beat unmanaged; spanning alphas not implementable in real time; real-time versions generally have lower Sharpe and CER; cause is structural instability of spanning regressions; in 72 of 103 strategies adding vol-managed option lowers gross Sharpe/CER — [JFE PDF](https://www.lehigh.edu/~xuy219/research/COWY.pdf), [Alpha Architect summary](https://alphaarchitect.com/does-portfolio-timing-based-on-volatility-signals-outperform-buy-and-hold/)
- Same paper cites market vol-managed combination Sharpe 0.53 vs 0.42 for unmanaged market in one real-time design (snippet line, context not fully read) — [JFE PDF](https://www.lehigh.edu/~xuy219/research/COWY.pdf)
- Barroso-Santa-Clara, "Momentum Has Its Moments," JFE April 2015 [PR]: momentum risk predictable from own realized variance; 12% constant-vol targeting nearly doubles Sharpe and removes crashes, sample 1927-2011 — [CFA Institute blog](https://blogs.cfainstitute.org/blog/2018/01/17/timing-the-market-momentum-and-beyond) [PRAC summary]
- Barroso-Detzel (2021): after transaction costs, vol-management of non-market factors generally yields zero abnormal returns and lower Sharpe; vol-managed market portfolio alphas are profitable after costs but concentrated in easily arbitraged stocks (summary from search; authors/venue as reported by search tool, not verified) — [search summary, Barroso/Detzel](https://ciencia.ucp.pt/en/publications/do-limits-to-arbitrage-explain-the-benefits-of-volatility-managed-2/) [PR, secondary]
- Harvey et al. "The Impact of Volatility Targeting": higher Sharpe from vol targeting holds for risk assets (equity, credit), linked to leverage effect — [via search summary](https://macrosynergy.com/?p=4016) [PRAC]
- Guasoni-Mayerhofer "Limits of Leverage": rising rebalance costs lower Sharpe as leverage rises — [arXiv 1506.02802](https://arxiv.org/pdf/1506.02802) [WP]

### Inferences
- For a long-only options bot, vol-scaling means de-risking when realized vol is high (reducing option contract count or notional). That is the part with best support (equity risk assets, de-leveraging only needs no leverage). Levering up in calm periods is where Cederburg critique and cost drag bite; avoid.
- Vol-targeting has lower drawdown rather than clearly higher Sharpe on out-of-sample evidence.

### Gaps
- No VIX-threshold regime filter paper (e.g., fixed VIX>X cutoffs) with net-of-cost out-of-sample results found. QQQ/IWM-specific vol-managed results not found. Turnover numbers not extracted.

## 4. Regime filters for intraday strategies

### Takeaway
One peer-reviewed study shows intraday momentum on SPY is stronger on high-vol, high-volume and recession days. Direct tests of higher-timeframe trend filters on intraday strategies found nothing credible in this pass.

### Cited Findings
- Gao-Han-Li-Zhou, "Market Intraday Momentum," JFE 2018 (SSRN 2552752 June 2015) [PR]: SPY 1993-2013, first half-hour return predicts last half-hour return; stronger on more volatile days, higher volume days, recession days, some macro-release days; ~6.02% per year utility gain for mean-variance investor; also holds for ten other liquid ETFs — [WUSTL profile/search summary](https://profiles.wustl.edu/en/publications/market-intraday-momentum/) (paper index: SSRN 2552752)
- A VIX<20 disable filter applied in a replication/blog implementation, reflecting vol dependence — [QuantConnect research](https://www.quantconnect.com/research/15348/intraday-etf-momentum/) [blog/practitioner; not independently validated]

### Inferences
- Volatility regime is the supported conditioning variable for intraday momentum; daily trend-regime gating of intraday signals is untested here.
- Sample ends 2013; decay after publication (2014+) not verified.

### Gaps
- No published post-2013 out-of-sample test of intraday momentum on SPY/QQQ/IWM found. No published test of daily-trend filter improving intraday reversion/momentum found.

## 5. Options adaptation (LEAPS, call spreads, cash-secured)

### Takeaway
No peer-reviewed study found that tests trend-timed long-dated calls versus shares. Related academic option-overlay work (Israelov-Nielsen) shows option structures can add hidden exposures and costs; protective-put evidence says de-risking by divesting beats buying puts for the same return.

### Cited Findings
- Israelov-Nielsen, "Covered Calls Uncovered," FAJ 2015 [PR]: covered call = long equity + short volatility (Sharpe near 1.0, ~10% of risk) + uncompensated equity-reversal exposure (~25% of risk, little return) — [CXO summary](https://www.cxoadvisory.com/equity-options/enhancement-of-index-covered-calls-via-hedging), [AQR FAJ PDF](https://www.aqr.com/-/media/AQR/Documents/Insights/Journal-Article/FAJ-Covered-Call-Strategies-One-Fact-and-Eight-Myths.pdf)
- Israelov "Pathetic Protection" [WP/PR]: sized to equal average return, divesting equity (reducing exposure) has lower drawdown, vol, beta and higher Sharpe than buying puts, except when a large crash occurs before option expiry — [Advisor Perspectives](https://www.advisorperspectives.com/articles/2019/08/22/are-puts-efficient-at-protecting-downside-risk) [PRAC summary]
- Practitioner claim: LEAPS (1-3 yr) match trend holding horizons better than short-dated options — [TurtleTrader](https://www.turtletrader.com/leaps/) [PRAC/commercial, no data]
- Practitioner backtest: trend-filtered credit spreads (short put spreads above 200-day MA, short call spreads below) on SPY/GLD/TLT — [Option Alpha podcast](https://optionalpha.com/podcast/trend-trading) [PRAC; results not extracted]
- Stock-replacement via deep ITM calls: capital efficiency, max loss = premium — [SentimenTrader](https://sentimentrader.com/blog/options-101-understanding-the-stock-replacement-strategy) [PRAC; no performance data]

### Inferences
- A long ITM LEAPS call during an uptrend is long equity plus long volatility minus financing/time premium; carries implied-vol and time-decay costs vs shares. Net cost vs shares is roughly financing implied by the call-pricing minus dividends, plus bid-ask. Not quantified from a source.
- Consistent with Israelov: scale option exposure down on regime-off rather than hold long puts as insurance.

### Gaps
- No source with numerical cost/performance of LEAPS or call-spread trend-timing vs shares. No academic test of call spreads as trend instruments. Bid-ask spread data for SPY/QQQ/IWM LEAPS not found. Needs own backtest on historical chain data.

## 6. Summary scorecard (net Sharpe, drawdown, turnover, decay, sample dependence)

### Takeaway
Best-supported: multi-asset futures trend (long sample, pre-2000 strong). Equity-index MA timing: DD benefit robust, Sharpe benefit marginal after costs. Vol-managed market: best survivor among vol timing, others fail out-of-sample. Intraday regime and options trend: thin evidence.

### Cited Findings
- AQR TSMOM: net Sharpe 0.77 (1880-2013), 0.62 (2000-2013), cost basis simulated — [AQR](https://oxfordstrat.com/coasdfASD32/uploads/2016/03/A-Century-of-Evidence-on-Trend-Following-Investing.pdf)
- Faber S&P 500 SMA: Sharpe 0.55 vs 0.32, DD -50.3% vs -83.5%, 3-4 trades/yr (gross) — [CXO](https://www.cxoadvisory.com/technical-trading/long-term-outperformance-from-trends-defined-by-moving-averages)
- Zakamulin net: Sharpe gain 7-12%, may fatten left tail; no significant outperformance post-1932 — [CXO](https://www.cxoadvisory.com/technical-trading/net-performance-of-sma-and-intrinsic-momentum-timing-strategies), [SSRN](https://papers.ssrn.com/abstract=2677212)
- Vol-managed: out-of-sample fails for most of 103 strategies — [JFE](https://www.lehigh.edu/~xuy219/research/COWY.pdf)

### Inferences
- Decay since publication: AQR documents decade fade and index data show 2010s drought; Faber 10y revisit reportedly positive but dominated by 2008-type events and unverified. Treat all as sample dependent on 2008 and 2022.
- Practical bot design implied by evidence: monthly/slow trend gate with low turnover, de-risk (not lever) on high realized vol, measure options cost explicitly against shares.

### Gaps
- Turnover figures only for Faber (3-4 trades/yr). No decay-since-publication quantification for Faber rule or Moreira-Muir on 2014-2025 data.

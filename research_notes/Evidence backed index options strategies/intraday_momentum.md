# Intraday momentum and time-of-day effects on US index ETFs/futures (SPY, QQQ, IWM, ES/NQ/RTY)

Evidence tags: [PR] peer-reviewed, [WP] working paper, [PRAC] practitioner, [BLOG] blog, [ANEC] anecdotal. Research date 2026-10-08. Ranking (best to weakest evidence): (1) Baltussen et al JFE 2021; (2) Gao et al JFE 2018; (3) Lou-Polk-Skouras JFE 2019 / Cliff-Cooper-Gulen overnight drift; (4) Zarattini-Barbon-Aziz SFI 24-97; (5) opening-range breakout (Zarattini-Aziz); (6) Heston-Korajczyk-Sadka / Bogousslavsky (mechanism, not index-ETF tradable). No paper found tests any of these with options; all are shares/ETF/futures.

## 1. Gao, Han, Li, Zhou (JFE 2018): first half-hour predicts last half-hour

### Takeaway
Seminal, peer-reviewed, real in-sample and OOS predictability on SPY 1993-2013 (R2 ~1.6%, timing Sharpe ~1.08 gross), survives ~1.2bp-spread costs in-sample, but the economic edge is small per trade, was never tested post-2013 by the authors, and later work (Baltussen 2021 says last-30-min signal is better with "rest of day" return; Rosa 2022 says the overnight-return variant fails OOS) shows the exact first-half-hour signal is fragile.

### Cited Findings
- Sample: 1 Feb 1993 - 31 Dec 2013, S&P 500 ETF (SPY) high-frequency data [PR; working-paper draft Dec 2015 used for numbers, JFE figures may differ slightly] — [Gao et al. draft](https://c.mql5.com/forextsd/forum/173/intraday_momentum_-_the_first_half-hour_return_predicts_the_last_half-hour_return.pdf) (text read locally via PDF; mirror host is a third-party forum; same paper abstract at [WashU profile](https://profiles.wustl.edu/en/publications/market-intraday-momentum/))
- In-sample predictive R2 of last half-hour on first half-hour return = 1.6%; adding the twelfth half-hour (the half-hour before the last) = 2.6%; high first-half-hour volatility raises combined R2 to 3.3%. Stronger on recession days, high volume days, and some macro-news days; stronger when first half-hour return is positive — same source.
- OOS R2 = 1.2% (first half-hour alone), 1.8% (with 12th half-hour) — same source.
- Market timing (long last half-hour if first half-hour return >0, short otherwise): 6.67%/yr, std 6.19%, Sharpe 1.08, vs buy-and-hold 6.04%/yr, std 20.57%, Sharpe 0.29 — same source.
- Costs (TAQ bid/ask at 3:30pm, post-decimalization from Jul 2001): return falls from ~6.9% to 4.46%/yr (-2.47pp), std unchanged 6.10%. From 2005 onward: 6.52% after costs vs 7.96% before (proportional spread ~1.2bp after 2005). Both-signal version: 4.74% after vs 5.50% before — same source. (Cost model assumes entry at 3:30 quote and exit at 4pm closing auction; no commissions/impact beyond spread.)
- Breadth: also significant for ten other actively traded ETFs (Dow, Nasdaq, Russell 2000 exposures among them, plus financials, real estate, bonds, international) and for FTSE 100 and EuroStoxx 50 futures; OOS predictability and CE gains on lower-liquidity ETFs "often greater" than SPY; NOT in currency or commodity futures — same source. (Exact per-ETF tickers/stats for QQQ/IWM not extracted; check the paper's Table before relying on them.)
- Mechanism proposed by authors: informed traders/daytraders timing trades for U-shaped volume (first/last half-hour) — same source. Baltussen et al. later argue gamma hedging is a better explanation.
- Secondary summary of the SPY study: 1999-2012 SPY R2 ~0.02; OOS up to 0.018; gross 6.3%/yr vs -0.5% for always-long last half hour; a short confirmation window Aug 2012-May 2014 gave correlation 0.12, R2 0.014; summary warns frictions "would materially affect exploitability" — [CXO Advisory, practitioner summary](https://www.cxoadvisory.com/?p=25481) [PRAC]
- Post-publication/decay: a search snippet attributed to a 2023 master's thesis (2007-2018 data) says patterns weaken over time; I could not trace it to a fetched page, so treat as unverified [ANEC].
- Rosa, "Understanding intraday momentum strategies", J. Futures Markets 2022 [PR]: for the version where the overnight return predicts last half-hour, predictability disappears out-of-sample; Markov-switching finds two regimes, signal strength matters, threshold filters beat always-trading — [IDEAS/RePEc](https://ideas.repec.org/a/wly/jfutmk/v42y2022i12p2218-2234.html) (abstract only; sample dates not extracted)

### Inferences
- Edge per trade is a couple of bp of SPY at best; 1-3bp equity spread already eats ~25-35% of gross in Gao's own numbers, so any option premium spread (many times wider in % of underlying) would likely erase it.
- Signal is a ~30-minute holding-period bet; to use it with a 1DTE option you would hold an option for 30 min to capture a ~few-bp expected move versus a spread of several bp: likely negative expectancy.
- Post-2013 persistence is unverified by anything I fetched; assume decay until tested on own data.

### Gaps
- No fetched post-2018 independent replication of the exact first-half-hour SPY signal with stats. The Baltussen sample (to May 2020) is the latest peer-reviewed extension.
- Per-ETF (QQQ, IWM) coefficients not extracted.
- JFE-published numbers vs 2015 draft not reconciled.

## 2. Baltussen, Da, Lammers, Martens (JFE 2021): hedging demand and intraday momentum

### Takeaway
Best-evidenced paper: 60+ futures, Dec 1974 - May 2020, predictor is the return from prior close to 30 minutes before close (r_ROD), which beats the first-half-hour return; OOS R2 is positive and strongest for equity index futures; mechanism = negative-gamma hedgers (option market makers, leveraged ETFs) trading with the move into the close. Positive net Sharpe for S&P futures at a one-tick cost per the authors, but not shown after full realistic costs; no post-May-2020 or 0DTE-era test in the paper.

### Cited Findings
- Abstract: 60+ futures (equities, bonds, commodities, currencies), 1974-2020, last-30-min return positively predicted by rest-of-day return; effect reverts over following days; linked to gamma hedging of option market makers and leveraged ETFs — [JFE 142 (2021) 377-403, full text read locally](https://academicweb.nd.edu/~zda/intramom.pdf) [PR]; also [Erasmus repository](https://pure.eur.nl/en/publications/hedging-demand-and-market-intraday-momentum/)
- Equity futures pooled: beta on first half-hour 4.86 (t 6.52), adj R2 1.49%, OOS R2 -1.71% for first-half-hour alone; beta on r_ROD 4.18 (t 7.29), R2 2.45%, OOS R2 2.88%. Combined first-half-hour + r_ROD OOS R2 negative for first-half-hour alone — i.e., the Gao signal alone fails OOS in this larger futures sample, r_ROD does not — same paper (Table 2, coefficients and R2 multiplied by 100 as in paper).
- Same sign vs opposite sign: when r_ROD and first-half-hour return disagree, r_ROD is the better predictor — same paper (Table 3).
- Subsamples 1974-1999 and 2000-2020: results similar in both; equity coefficient on r_ROD 3.98 (t 6.65) in 2000-2020, R2 ~2.3% — same paper (Table 5).
- Timing strategy Sharpe (equity index futures portfolio, no costs): first-half-hour rule SR 1.07 (4.21%/yr, vol 3.95%); both-signals rule SR 1.60; r_ROD rule SR 1.73 (6.86%/yr, vol 3.96%); buy-and-hold SR 0.51; Always-long-last-half-hour SR 0.11 — same paper (Table 6). 1/N portfolio across equity futures, so single-contract Sharpe will be lower.
- Costs: authors do not model costs; state S&P 500 futures yield a positive net Sharpe if cost = one tick, and that frequent trading may make it unexploitable for many investors — same paper, Section 3.5.
- Strong in last four months of sample (Feb-May 2020 COVID) — same paper.
- Mechanism evidence: stronger predictive coefficient when dealers' net gamma exposure (NGE, SqueezeMetrics, 1996-May 2020) is more negative and when leveraged-ETF share of the market is higher: IndexingLETF x r_ROD interaction coefficient 1.79 (t 2.20) in equity futures 2006-2020 — same paper. Cheng-Madhavan (2010) estimate LETF rebalancing = 16.8% of MOC volume on a 1% move day and 50.2% on a 5% day — cited within same paper.
- 0DTE era (post-paper, independent evidence): Adams et al. find S&P 500 volatility lower by ~60 annualized bp on 0DTE days; market-maker net gamma predicts order-flow reversal and negative high-frequency momentum within ~10 minutes, fading after ~1 hour; pre-positioned longer-dated option gamma matters more than intraday 0DTE trading — [Quantpedia summary of SSRN 5641974](https://quantpedia.com/do-sp500-0dtes-options-increase-market-volatility/?a=6080) [WP via practitioner summary]
- Dim, Eraker, Vilkov (2024) "0DTEs: Trading, Gamma Risk and Volatility Propagation": no evidence 0DTE open-interest gamma amplifies index volatility or that intraday 0DTE volume shocks amplify past returns — [Harbourfront Quant summary](https://harbourfrontquant.substack.com/p/impact-of-zero-dte-options-on-the) [BLOG summary of WP; original not fetched]
- 0DTE share of SPX options volume ~59% in 2025, ~63% Feb 2026 — [SpotGamma](https://spotgamma.com/0dte-options-explained/) [PRAC, vendor]

### Inferences
- If 0DTE dealer positioning is net long gamma (stabilizing) on average, the negative-gamma momentum channel could be weaker on average days and concentrated in negative-gamma/high-vol days; consistent with high-vol-day dependence in Gao and Zarattini. This is inference, not tested by any paper I found.
- The signal's best implementable form is r_ROD at ~15:30 ET with a ~30-minute hold; ES/NQ/RTY futures at a one-tick cost is the cleanest vehicle.

### Gaps
- No paper found testing the Baltussen predictor on June 2020 - 2026 (including 2022, 2024-25) or post-May-2022 daily 0DTE SPX. Treat post-2020 persistence as unknown.
- Net-of-cost Sharpe for a single ES contract not reported.
- Original Dim-Eraker-Vilkov text not fetched.

## 3. Zarattini, Barbon, Aziz, SFI WP 24-97: "Beat the Market" SPY noise-area strategy

### Takeaway
Working-paper, long (2007-Mar 2024) intraday-only SPY trend strategy with costs of $0.0035/share + $0.001 slippage; headline 19.6%/yr, Sharpe 1.33, MDD 25% requires volatility-targeted leverage up to 4x; the unlevered base version had Sharpe 0.61 and the refined unlevered version roughly doubled it. Independent replications I found are anecdotal/low-quality and report weaker results; no peer review.

### Cited Findings
- Rules: Noise Area = band around the day's open (and prior close) using the average absolute move from open to HH:MM over prior 14 days (vol multiplier 1), time-varying through the day. Trade only at HH:00/HH:30; long above the upper boundary, short below; exit at close or on reversal; stops refined with VWAP (and later dynamic stop at the band/VWAP); all positions closed at 16:00 (no overnight). Exposure 100% of equity at day start, later scaled by daily volatility, leverage cap 4x — [SFI WP 24-97 full text](https://alexandria.unisg.ch/server/api/core/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/content) [WP]; [SFI page](https://www.sfi.ch/de/publications/n-24-97-beat-the-market-an-effective-intraday-momentum-strategy-for-s-p500-etf-spy)
- Costs: $0.0035/share commission (IBKR entry level) + $0.001/share slippage, justified by authors' own real-money tests (mean ~$0.001, median lower) — same paper.
- Version progression (2007-2024, all net of those costs): base (opposite-band stop) 6.2%/yr, vol 10.9%, Sharpe 0.61, 178% total, worst day -10.33%, negative skew, 5,494 trades, hit 53% on trades; with VWAP stop 9.7%/yr, vol 7.7%, Sharpe roughly double; volatility-scaled with 4x leverage cap: 19.6%/yr, vol 14.3%, Sharpe 1.33, 1,985% total, max drawdown 25%, daily hit ratio ~43%, best/worst trade +9.1%/-2.9%; beta slightly below zero — same paper (Tables 1-4).
- Regime: Sharpe rises with opening VIX (~1.50 when VIX>6 i.e. all days; ~3.5 when VIX>40; falls beyond that on few observations). Worse on low-vol days. Also tested vs dealer gamma proxy (RSI-based) — same paper.
- Robustness: optimal lookback 90 days gives Sharpe 1.50 vs 1.35 at 14 days; vol multiplier 1.5 gives 1.55 — authors argue base params are not overfit — same paper (FAQ/Q14). FAQ also claims same rules on 33 futures markets 2007-2024 gave average Sharpe 0.60, portfolio 1.65, and other ETFs/stocks 2018-2024 with diversified Sharpe >2 (authors' own claims, not independently verified).
- Independent replication: TradingView/forum re-implementations report smaller returns and very low Sharpe, margin calls with margin checks on — [Quantified Strategies write-up and TradingView scripts, via search snippet] [BLOG/ANEC, not verified; no specific numbers retrieved]. No peer-reviewed or serious independent replication found.
- Related: Quantpedia Awards 2025, 4th place (not evidence of validity) — [FSI news](https://fsi.unisg.ch/de/newsdetail/news/quantpedia-awards-2025-fsis-barbon-and-team-secure-4th-place-with-intraday-momentum-strategy/)

### Inferences
- Headline Sharpe 1.33 depends on leverage/vol-scaling choices tuned after seeing the base-version results (VWAP stop and vol scaling added in the paper). That is design-in-sample iteration even if parameters look robust. 2007-2024 includes high-vol years (2008, 2020, 2022) where the strategy does best; the 2012-2017 low-vol stretch is likely weaker.
- Trades ~1.8x/day on ~100% (up to 4x) of equity: with SPY options as the vehicle, cost per round trip (several bp of SPY spread-equivalent plus theta) is a large multiple of $0.0045/share (~0.1bp-ish of a $500 SPY).

### Gaps
- Year-by-year returns (esp. 2023-2025) not extracted.
- No credible independent replication with numbers.

## 4. Other credible intraday work

### Takeaway
Intraday periodicity (Heston-Korajczyk-Sadka), infrequent rebalancing (Bogousslavsky) and overnight/intraday decomposition (Cliff-Cooper-Gulen, Lou-Polk-Skouras) are well-published but are mostly cross-sectional or about holding periods, not about tradable intraday index signals with option structures. Opening-range-breakout (ORB) evidence on index ETFs is thin: QQQ ORB paper is a working paper with idealized (no-spread) assumptions; one blog replication finds gross edge ~ equals costs.

### Cited Findings
- Heston, Korajczyk, Sadka (J. Finance 2010) [PR]: stock returns in a half-hour interval positively predict returns in the same interval on subsequent days (exact multiples of 24h), lasting up to ~40 trading days; stronger in first and last half-hour; not explained by volume/spreads/volatility — [Kellogg summary](https://www.kellogg.northwestern.edu/academics-research/research/detail/2010/intraday-patterns-in-the-cross-section-of-stock-returns/?p=1); [arXiv version](https://ar5iv.arxiv.org/html/1005.3535). Cross-section of stocks, not an index-timing rule; Baltussen finds no comparable time-series effect at the index level (coefficient on yesterday's last half-hour is negative and significant in equity futures) — [Baltussen et al.](https://academicweb.nd.edu/~zda/intramom.pdf)
- Bogousslavsky (J. Finance 2016) [PR]: infrequent rebalancing model producing autocorrelation that switches sign at the rebalancing horizon, consistent with intraday return seasonality — [Bogousslavsky paper](https://memento.epfl.ch/public/upload/files/Paper_Bogousslavsky.pdf). Theory; no index-ETF trading rule or costs.
- Lou, Polk, Skouras (JFE 2019) [PR]: stock-level momentum profits accrue overnight, while reversal-type and other strategy profits accrue intraday, with opposite signs across periods; stronger for large caps and high-price stocks; institutions trade against momentum intraday — [LSE Research Online](https://researchonline.lse.ac.uk/id/eprint/119010); [Alpha Architect summary](https://alphaarchitect.com/2015/02/overnight-momentum-vs-intraday-momentum/) [PRAC]. Cross-sectional; not an index-ETF timing signal.
- Cliff, Cooper, Gulen (2007/2008) [WP, widely cited]: 1993-2006 average overnight stock returns +0.028% to +0.048%, daytime -0.028% to +0.002% for S&P 500 stocks; index/ETFs show the same pattern ("Like Night and Day") — via [Alpha Architect/CXO secondary summaries], e.g. [CXO overnight page](https://www.cxoadvisory.com/calendar-effects/buy-at-the-close-and-sell-at-the-open) [PRAC]. Implication: most index drift is overnight, which bears directly on 1DTE options (held across close) vs intraday-only strategies. Post-2020 persistence not verified here.
- ORB on QQQ (Zarattini & Aziz, SSRN 4416622 [WP]): 5-minute opening range, enter at start of second candle in direction of the first, stop at opposite extreme, profit target 10R else exit at close; QQQ 2016-Feb/2023, $25k start, max 4x leverage, commission $0.0005/share, 1% risk per trade; authors report 33% annualized alpha unlevered and 1,484% on TQQQ vs 169% QQQ buy-and-hold; backtest assumes no spread/slippage — [SSRN abstract](https://papers.ssrn.com/abstract=4416622); [CXO Advisory description of assumptions](https://www.cxoadvisory.com/technical-trading/day-trading-with-an-opening-range-breakout-strategy) [PRAC]. (Return numbers via search snippet of SSRN/secondary sources; I did not read the paper.)
- Independent ORB replication [BLOG, treat with caution, post dated through Jun 2026 and unreviewed]: same 5-min ORB on NQ, SPX, Dow, DAX, FTSE as CFDs, Jan 2015-Jun 2026 (~2,900 sessions): gross +0.131R (NQ), +0.119R (SPX), +0.116R (DAX) with 20-23% hit rate reproduces original; net of spread/slippage NQ +0.002R, SPX -0.081R, Dow -0.081R, DAX -0.038R, FTSE -0.079R; conclusion: gross edge ~ cost — [MQL5 blog](https://www.mql5.com/en/blogs/post/776235). CFD costs are higher than ES/SPY, so this overstates cost for a futures trader.
- Crabel (1990, "Day Trading with Short Term Price Patterns and Opening Range Breakout") [PRAC book]: no statistics retrieved; no peer-reviewed or reproducible stats located for Crabel's rules on index ETFs. Zarattini-Barbon-Aziz explicitly cite Crabel/Kaufman volatility-breakout systems as precursors — [SFI WP 24-97](https://alexandria.unisg.ch/server/api/core/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/content)

### Inferences
- ORB's headline numbers are driven by a 20% hit rate / fat right tail (10R target), and TQQQ leverage; with realistic costs it is marginal per the one blog replication.
- Overnight drift is the more robust documented time-of-day effect for index ETFs, but it needs overnight holding (compatible with 1DTE-held-overnight structures, not intraday-only) and its post-2020 durability is unverified.

### Gaps
- No Crabel statistics found; no peer-reviewed ORB test on SPY/QQQ/IWM.
- No fetched replication of Lou-Polk-Skouras on index ETFs or for 2020-2026.
- Heston et al. and Bogousslavsky not tested for index options by anyone found.

## 5. Net-of-cost, in/out-of-sample, decay, regime dependence, capacity (cross-paper table in prose)

### Takeaway
Pattern across all sources: predictability is statistically real in-sample on SPY/ES, OOS-confirmed in Gao (to 2013) and Baltussen (to May 2020, r_ROD only), strongest in high-vol/recession/news regimes, and net-of-cost profitability exists only with very cheap execution (shares/futures at <=1 tick). Capacity is large for ES/SPY at the close but the edge per trade is small. No source tests options.

### Cited Findings
- Gao: gross Sharpe 1.08, post-cost return 4.5-6.5%/yr on ~6% vol (2001/2005-2013) — [Gao et al.](https://c.mql5.com/forextsd/forum/173/intraday_momentum_-_the_first_half-hour_return_predicts_the_last_half-hour_return.pdf)
- Baltussen: equity-futures portfolio gross Sharpe 1.07-1.73 depending on signal; positive after one-tick cost for S&P futures — [Baltussen et al.](https://academicweb.nd.edu/~zda/intramom.pdf)
- Zarattini-Barbon-Aziz: net Sharpe 0.61 -> 1.33 across versions; MDD 25% (levered version) — [SFI WP 24-97](https://alexandria.unisg.ch/server/api/core/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/content)
- Regime: Gao stronger recession/high vol/high volume/news days; Baltussen strong in Feb-May 2020; Zarattini Sharpe increases with VIX up to ~40; Rosa finds signal-strength regimes and OOS failure for the overnight-return version — sources above.
- Decay: Rosa 2022 OOS failure of overnight-return variant; Baltussen OOS failure of first-half-hour-alone in equity futures (-1.71%) while r_ROD holds; no direct 2021-2026 stats found.
- Year-specific (2020, 2022, 2024-25) breakdowns: only 2020 (Feb-May) from Baltussen. 2022 and 2024-25 not available from sources fetched.

### Inferences
- Because intraday-index edges concentrate in high-VIX days and last-30-min moves, the 2022 bear market and Apr 2025 volatility would be expected to favour the strategies, while 2017/2021/2024 low-vol grinding would not — unverified by any source fetched.

### Gaps
- Capacity numbers not found in any paper; SPY/ES close liquidity is enormous so capacity is not binding for retail size (inference).
- No year-by-year table obtained for 2022 or 2024-25.

## 6. Which could be implemented with long ATM 1DTE options or defined-risk spreads, and what option costs do

### Takeaway
None has been tested with options. By inference, Baltussen/Gao last-30-minute signals are poorly suited to options (tiny expected move, short holding period, spread >> edge); Zarattini noise-area and ORB involve larger directional moves held for hours and are the better fits to a long-option expression, but each paper's edge is on the same order as the underlying's cost and no option-based test exists. Treat all option conclusions below as inference unless cited.

### Cited Findings
- SPX 0DTE ATM round-trip spread ~1-3bp of underlying (vs 3-8bp for weeklies) per vendor-type article; dated and not rigorous — [Lambda Fin comparison, via search snippet] [PRAC/BLOG]. SPY/index option spread in % of premium not obtained from a rigorous source.
- NDX 0DTE ATM mid-to-bid spread study exists (Volos) but figures not retrieved — [Volos Software](https://volossoftware.com/insights/improving-0dte-trading-returns) [PRAC]
- Gao: shares spread costs ~1.2bp of price round trip entry-at-3:30 reduce return by ~1.4pp (2005+) / ~2.5pp (2001+) of ~7% gross — [Gao et al.](https://c.mql5.com/forextsd/forum/173/intraday_momentum_-_the_first_half-hour_return_predicts_the_last_half-hour_return.pdf)
- 0DTE hedging flows are not found to amplify volatility (Dim-Eraker-Vilkov, Adams et al.) — sources in Section 2.

### Inferences
- Last-30-min strategies (Gao, Baltussen): expected last-half-hour move on a signal day is a few bp to ~10bp; one ATM option's bid-ask round trip is typically on the order of 1-3bp of underlying per the above, plus delta/gamma/theta noise and, for 1DTE, overnight vega/gap risk if held. Edge/cost ratio near or below 1: likely negative. Verdict: do not implement with options; use ES/MES or SPY shares if at all.
- Noise-area (Zarattini): holding from ~10:30 to close on breakout days, average winner/loser sizes up to several tenths of a percent of SPY, long 1DTE ATM call/put aligned with the breakout could capture the convex part (higher hit on big trend days), and the strategy's Sharpe rises with VIX. But IV also rises on those days (you pay up for options), theta and spread cost apply on ~1.8 trades/day, and the paper's own tail-ratio (hit ratio 37-43%) means a long-premium expression pays theta on the ~60% losing days. A defined-risk debit vertical reduces spread and vega at the cost of capped upside. Plausible but untested; require own backtest with real chains.
- ORB: low hit rate (20%) and 10R target is structurally similar to long-option convexity, but the blog replication suggests the underlying edge nets to ~zero even in CFDs; options costs would be larger.
- Overnight drift (Cliff-Cooper-Gulen): fits a 1DTE long-call held overnight conceptually, but index drift (~0.03-0.05%/night in 1993-2006) is smaller than ATM spread plus theta, so it is not option-implementable.
- Practical recommendation ranking for options-capable accounts (inference): (a) conditional use: Zarattini-style trend-day filter (strong breakout beyond noise band, high VIX) with debit spreads; (b) not recommended: any last-30-min signal; (c) not recommended: bare ORB.

### Gaps
- No rigorous measurement of SPY/QQQ/IWM 1DTE ATM spread as % of premium obtained.
- No academic or practitioner study with options P&L for any of these signals.
- IWM and RTY/QQQ/NQ specific intraday-momentum stats: only Gao's statement that Russell 2000 and Nasdaq ETFs show momentum (often stronger OOS) and Zarattini's FAQ claims on futures; no extracted tables.

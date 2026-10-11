# Short-horizon mean reversion and calendar/event effects on SPY/QQQ/IWM

Coverage note: ~16 searches/fetches. Evidence is thin for IWM/QQQ specifically (almost all sources are SPY/S&P 500). No source found reports net-of-cost Sharpe for most items; gaps flagged. Tags: [PR]=peer-reviewed, [WP]=working paper, [PRAC]=practitioner, [BLOG]=blog, [AGG]=aggregator summary.

## 1. Short-term mean reversion in index ETFs (Connors RSI(2), IBS, N-day lows, gap-fill)

### Takeaway
Originator evidence (Connors 1995-2007) has no data-snooping control, drawdown, subperiod or friction analysis. The one independent post-2016 test found shows RSI(2) on the S&P 500 positive but far below buy-and-hold. Gap-fill statistics are practitioner-grade and depend heavily on gap size. No peer-reviewed independent test of RSI(2)/IBS on SPY/QQQ/IWM was found.

### Cited Findings
- CXO Advisory's review of Connors' 2008 book: tests covered 1995-2007 daily data (2-period RSI, pullback buying, VIX-based indicators); reviewer flags no data-snooping correction, no drawdown analysis, no subperiod verification, overlapping "8 million trades" a trader could not take, no trading frictions. [PRAC/AGG] — [CXO Advisory](https://www.cxoadvisory.com/technical-trading/a-few-notes-on-short-term-trading-strategies-that-work/)
- Backtrex RSI(2) on S&P 500 (SPX500 CFD proxy), Oct 2016-Oct 2026, daily: long RSI(2)<5 above 200d SMA, short RSI(2)>95 below it, exit on 5d SMA/200d SMA cross, 100% equity, 0.02%/side commission. 73 trades in 10 years, win rate 71.2%, avg win 1.22%, avg loss 2.10%, total +18.1% vs buy-hold +255.4%, CAGR 1.7% vs 13.5%, max DD -21.5% vs -35%. Yearly: 2018 -9.8%, 2019 -3.0%, 2020 -1.3%, 2023 -1.1%, positives 2017/2021/2024-2026. Sharpe not reported. Includes short leg, which likely drags; long-only split not given. [BLOG/PRAC; single site, methodology partly opaque] — [Backtrex](https://backtrex.com/en/backtests/connors-rsi-2-sp-500)
- Quantified Strategies IBS = (Close-Low)/(High-Low); basic rule buy IBS<0.2, sell >0.8; claims "worked remarkably well for over two decades" on SPY since 1993; variants combine IBS<0.25 with RSI(21)<45 or 3-day RSI. Exact stats/cost assumptions not retrieved (fetch 404). [BLOG; vendor with commercial interest] — [Quantified Strategies](https://quantifiedstrategies.substack.com/p/the-classical-mean-reversion-strategy), [IBS post](https://quantifiedstrategies.substack.com/p/ibs-internal-bar-strength-trading)
- Gap-fill stats (SPY): small down-gaps (0-0.19%) fill 92%, 0.2-0.39% fill 69%, >0.4% under 50%; wednesday down-gaps 80% vs friday 20%; overall gaps unfilled intraday 82% of time per one source; gap-down >=1% averages +0.09% open-to-close, 51.4% positive. Small-gap fill is mechanically trivial (gap is tiny vs normal range). Sources conflict on same-day fill rate (60% vs "not filled within a day 82%"). [BLOG/PRAC, no cost/period rigor] — [TradeThatSwing](https://tradethatswing.com/sp-500-spy-es-gap-fill-strategy-and-statistics/), [Market Chameleon](https://marketchameleon.com/Overview/IVV/Stock-Price-Action/Historical-Gap-Down-Moves)
- SPY multi-horizon mean reversion: two-day return variance 8.1% below random walk, weekly 16.3%, quarterly 34%. Same paper finds lag-1 autocorrelation driven by magnitude not sign (bid-ask bounce/staleness fingerprint, not directional reversal). arXiv ID 2606.* postdates my training; unverified preprint. [WP] — [arXiv 2606.29591](https://arxiv.org/abs/2606.29591)

### Inferences
- Pattern across sources: high win rate, small avg win, larger avg loss (RSI(2): 1.22% vs 2.10%); low exposure and low CAGR vs buy-hold. Tail risk is the cost of the high hit rate.
- Post-2015/2020: only evidence is a 2016-2026 blog backtest showing weak/choppy results incl. negative 2018-2020, consistent with decay or regime dependence (trend years). Cannot separate from the short leg.
- Options fit: signals are low frequency (~7/yr RSI(2)), multi-day hold; defined-risk put credit spreads or short-dated call debit spreads possible, but win-small/lose-big payoff gets worse with spreads capping gains; long premium suffers theta/IV (signals fire when IV is high, i.e. expensive premium). No test of options implementation found.

### Gaps
- No peer-reviewed independent test of RSI(2)/IBS/N-day-low on SPY/QQQ/IWM; no QQQ/IWM-specific stats found; no net-of-cost Sharpe for IBS; no academic source on gap fill; no options-implemented backtest.

## 2. Overnight vs intraday, turn-of-month, pre-FOMC, Monday/Turnaround Tuesday

### Takeaway
Overnight/intraday split is real in-sample and academically published, but net-of-cost tradability is disputed. Pre-FOMC drift has essentially vanished after 2015 (peer-reviewed). Turn-of-month is the best-supported calendar effect historically but with conflicting out-of-sample evidence. Day-of-week effects are weak/unstable.

### Cited Findings
- Lou, Polk, Skouras (JFE 2019): momentum profits accrue overnight, other anomalies' profits intraday, with offsetting cross-period reversal lasting years; stronger for large-cap/high-price stocks. Firm-level cross-section, not an index-ETF timing rule. [PR] — [LSE repository](https://researchonline.lse.ac.uk/id/eprint/119010)
- Knuteson: SPY open-to-close $1 over ~30 years grew to $1.20 (below T-bills) vs $17.27 overnight; he attributes pattern to large quant firms' trading. Speculative explanation, self-published/arXiv. [WP/BLOG-reported] — [Advisor Perspectives](https://www.advisorperspectives.com/articles/2022/06/24/night-moves-is-the-overnight-drift-the-grandmother-of-all-market-anomalies), [arXiv listing](https://ideas.repec.org/p/arx/papers/2201.00223.html)
- Alpha Architect/other summary: >88% of SPY's total return is overnight; transaction costs and market impact erase most or all expected gain of an overnight-only strategy; at $3/trade a toy system loses money. Associated with Hendershott et al. (2020) work. Full text of Alpha Architect post not retrieved (403); figures via search snippet. [PRAC/AGG] — [Alpha Architect](https://alphaarchitect.com/trading-costs-wipe-out-the-overnight-return-anomaly/)
- Pre-FOMC: Lucca-Moench documented drift 1994-2011. Kurov, Wolfe, Gilbert (Finance Research Letters 2021, sample to Dec 2019): drift "essentially disappeared after 2015", with or without press conferences; linked to reduced uncertainty. [PR] — [IDEAS/RePEc](https://ideas.repec.org/a/eee/finlet/v40y2021ics1544612320315956.html)
- Pre-FOMC drift magnitude conditional on implied vol: ~109bp when VIX-type implied vol above prior median vs 9.7bp below (Quantpedia summary of a study; underlying paper not named in snippet). [AGG] — [Quantpedia](https://quantpedia.com/fomc-equity-drift-occurs-in-periods-of-high-uncertainty/)
- Turn-of-month (Xu & McConnell; Quantpedia backtest 1926-2005): last day of month to day 3: 7.2% annualized, 6.9% vol, Sharpe 1.04, max DD -20.79%; 0.15%/day on turn days vs 0.01% other days; hold ~4 days/month. Quantpedia caveat: calendar effects vanish/rotate. Gross, pre-2005 sample. [AGG of PR] — [Quantpedia](https://quantpedia.com/strategies/turn-of-the-month-in-equity-indexes)
- Atlanta Fed working paper (Maberly & Waggoner, 2000): TOTM effect in S&P 500 futures disappears after 1990. Contrary: Carcano & Tornero say TOTM in S&P futures is the only calendar effect significant and persistent. Both via search snippets. [WP; conflicting] — [Atlanta Fed](https://www.atlantafed.org/research/publications/wp/2000/11.aspx), [Quantpedia screener](https://quantpedia.com/screener/Details/41)
- Day-of-week: study of S&P 500 2013-2023 found no day-of-week effect; inconsistent results across consecutive 5-year subperiods (via search summary). Sproule & Gosselin (2023) question calendar-anomaly research agenda. [WP/PR, snippet-level] — [MPRA 117001](https://mpra.ub.uni-muenchen.de/117001), [CXO](https://cxoadvisory.com/calendar-effects/any-recent-day-of-the-week-anomalies)
- Turnaround Tuesday: Quantified Strategies and S2N Navigator claim persistent profitability; no rigorous cost/significance control seen. [BLOG] — [QS](https://quantifiedstrategies.substack.com/p/turnaround-tuesday-strategy-backtest)

### Inferences
- Pre-FOMC: drop (not persist) out-of-sample; at most a high-vol-regime effect, ~8 events/yr.
- Overnight: trading it needs daily round-trips (~250/yr) -> cost-heavy; options version (hold calls overnight) pays theta+spread on every overnight, and overnight IV is partly priced. Untested in sources found.
- TOTM: low turnover (12 entries/yr) so best fit for options (monthly call debit spread around month-end); tested net-of-cost evidence post-2005 absent.

### Gaps
- Post-2015/2020 net-of-cost TOTM and overnight performance on SPY/QQQ/IWM not found from primary sources; Hendershott et al. paper not read directly; Monday/Tuesday: no peer-reviewed post-2015 SPY test read in full.

## 3. VIX mean reversion / spikes as long-entry signals

### Takeaway
Descriptive forward-return stats support buying elevated VIX over 12 months, but sources are aggregators/blogs with look-ahead and clustering issues. No rigorous short-horizon, cost-aware test found.

### Cited Findings
- Aggregator dataset article: S&P 500 median 12-month forward return +22.4% when VIX>30 since 1990 vs +11.3% when VIX<15; VIX>45: +30.6% median, 96.4% hit rate, 4 of 112 observations negative. Observations are daily and heavily overlapping/clustered (2008, 2020), so effective sample is a handful of episodes. [BLOG/AGG] — [eco3min](https://eco3min.fr/en/vix-contrarian-almanac-dataset/)
- Connors VIX-based indicators were part of the 1995-2007 originator tests, same caveats as section 1. [PRAC] — [CXO](https://www.cxoadvisory.com/technical-trading/a-few-notes-on-short-term-trading-strategies-that-work/)
- Practitioner note: VIX predicts volatility but not overall losses; realized returns during volatile periods had slightly more upside than downside. [PRAC] — [Advisor Perspectives](https://www.advisorperspectives.com/commentaries/2024/08/13/leaving-volatile-markets-can-result-missed-upside)

### Inferences
- Rare signal (VIX>45 in a few episodes), so trade frequency near zero; max drawdown from catching knives (2008, 2020 early) not reported in sources.
- Options: high VIX makes long premium expensive; defined-risk bull put spreads or call spreads (selling rich IV) fit better. Not backtested in sources found.

### Gaps
- No peer-reviewed VIX-spike timing study, no drawdown or 1-20 day horizon stats, no QQQ/IWM, no options-implemented results.

## 4. High-frequency (1-5 min) mean reversion vs momentum, and 0DTE effects

### Takeaway
Intraday: momentum at the half-hour scale (first half-hour predicts last), reversal at ~10-15 minute scale, with 0DTE market-maker gamma strengthening short-horizon reversals. Whether 0DTE destabilizes is disputed but both major papers find damping, not amplification.

### Cited Findings
- Gao, Han, Li, Zhou (JFE 2018): SPY 1993-2013, first half-hour return predicts last half-hour return, R-sq ~2%; stronger on high-vol, high-volume, recession and some news days; out-of-sample R-sq 1.8% (6.3% vs -0.5% gross annual return, 1999-2012). Gross, ETF-only, pre-2013. [PR via CXO/Alpha Architect summaries] — [Alpha Architect](https://alphaarchitect.com/2014/08/attention-prop-traders-the-first-half-hour-of-trading-predicts-the-last-half-hour/), [CXO](https://cxoadvisory.com/calendar-effects/first-and-last-half-hours-of-trading-linked)
- Adams et al. (0DTE): S&P 500 volatility lower by 60 annualized bp on days with 0DTE trading; higher market-maker net gamma predicts stronger order-flow reversals within 10 minutes, negative momentum in high-frequency returns, lower volatility, all dissipating within an hour; effect from longer-dated options rolling into 0DTE (24bp) rather than intraday 0DTE accumulation (3bp). [WP] — [Quantpedia summary](https://quantpedia.com/do-sp500-0dtes-options-increase-market-volatility/?a=6080)
- Dim, Eraker, Vilkov (2024, "0DTEs: Trading, Gamma Risk and Volatility Propagation"): no evidence higher 0DTE gamma raises index volatility; linked to lower intraday vol; 0DTE volume shocks don't amplify past returns; 0DTE volatility risk premium high. [WP] — [summary at Harbourfront Quant](https://harbourfrontquant.substack.com/p/the-rise-of-0dte-options-cause-for)
- Cboe: over 95% of 0DTE trades are limited-risk; ~4% naked short options. [PRAC, exchange with commercial interest] — [Cboe](https://www.cboe.com/insights/posts/0-dt-es-decoded-positioning-trends-and-market-impact/)
- Microstructure: return reversals most pronounced at 15-minute horizons; sub-minute continuation in large stocks, stress periods and first half-hour; bid-ask bounce/inventory effects cause short-horizon negative autocorrelation. [WP] — [arXiv 2511.06177](https://arxiv.org/pdf/2511.06177), [arXiv 2606.29591](https://arxiv.org/abs/2606.29591)

### Inferences
- 1-5 min reversals are small relative to spread+commission for SPY options (wide relative bid-ask on 0DTE, theta); the documented reversal is a market-maker flow effect, possibly capturable only with underlying/futures, not long premium.
- Intraday momentum (GHLZ) signal requires one trade/day; options version (end-of-day 0DTE directional spread) untested in sources.

### Gaps
- Adams et al. author list/paper not read directly; no cost-net Sharpe for any intraday rule; no QQQ/IWM; no independent post-2020 replication of GHLZ found; Dim-Eraker-Vilkov and Adams summaries are second-hand.

## Overall ranking by evidence quality (for these questions)
1. Lou-Polk-Skouras, Gao-Han-Li-Zhou, Kurov et al. (peer-reviewed; but cross-sectional or gross, and pre-FOMC refuted post-2015)
2. 0DTE working papers (Adams et al., Dim-Eraker-Vilkov) - mechanism evidence, no tradable P&L
3. Turn-of-month (long history; conflicting out-of-sample)
4. Practitioner/blog backtests: RSI(2), IBS, gap-fill, Turnaround Tuesday, VIX spikes (no rigorous cost, snooping or subperiod control; RSI(2) post-2016 weak)

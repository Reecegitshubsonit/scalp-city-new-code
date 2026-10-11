# Index option strategies: documented performance (premium selling vs buying, 0DTE/1DTE)

Tags: [index-provider] [peer-reviewed] [working paper] [practitioner] [vendor] [anecdotal]. Research depth limited (~17 tool calls); several primary PDFs not machine-readable; gaps listed per section.

## 1. Benchmark index track records (BXM, BXMD, PUT, WPUT, CLL, PPUT)

### Takeaway
Cboe option-writing indices (BXM/PUT/WPUT) show roughly equity-like long-run returns with ~65% of S&P vol and smaller max drawdowns, but they are gross of costs, have beta 0.56-0.82, strongly negative skew, and lag the S&P in strong bull years (2023-2024). No 0DTE/1DTE Cboe benchmark index was found in this research.

### Cited Findings
- [index-provider] PUT index, since mid-1986: 10.13% annual compound vs 9.85% S&P 500; std dev 10.16% vs 15.26% — [Hedgeweek summary of Cboe/Bondarenko study](https://www.hedgeweek.com/options-indices-offered-noteworthy-returns-over-30-years-says-study/)
- [index-provider] Another Cboe-cited window (June 1986 - Dec 2017): PUT 10.1% vs S&P 10.3% with about 66% of the risk — search-result summary, [Cboe benchmark article](https://www.cboe.com/insights/posts/benchmark-indices-series-income-generation-and-smoother-returns-with-cboes-bxm-bxmd-put-and-cmbo-indices) (the exact figure was not in the fetched text; treat as secondary)
- [index-provider] 2006-2015 worst drawdowns: WPUT -24.2%, PUT -32.7%, S&P 500 -50.9%. Average annual gross premium collected 2006-2015: PUT 24.1%, WPUT 39.3% (weekly puts collect premium 52x/yr) — [Hedgeweek/Cboe study of weekly vs monthly putwrite](https://www.hedgeweek.com/new-cboe-study-examines-weekly-and-monthly-sp-500-putwrite-indexes/); [Cboe release](https://ir.cboe.com/news/news-details/2016/New-Study-On-Weekly-Monthly-SP-500-PutWrite-Indexes-Released-01-27-2016/default.aspx)
- [index-provider] PUT 1986-2018: total return 1835% (PPUT 708%); annualized vol 9.95% vs S&P 14.93%; beta 0.56; monthly alpha 0.2%; skewness -2.09; strategy = monthly cash-secured ATM put sale with T-bills. PUT beat S&P, R2000, MSCI World, 30y Treasuries and PPUT on Sharpe, Sortino, Stutzer — [Cboe white paper summary](https://www.cboe.com/insights/posts/white-paper-shows-volatility-risk-premium-facilitated-higher-risk-adjusted-returns-for-put-index/). The page does not discuss transaction costs or max drawdown.
- [index-provider] Cboe: BXM, BXMD, PUT, CMBO (35+ yrs to July 2021) had lower std dev and smaller max drawdowns than S&P 500/MSCI EAFE/bonds/commodities; returned less than S&P; betas 0.57-0.82. BXM (ATM) gross premium averaged 1.7%/month since May 2006; BXY-type OTM 0.9%/month — [Cboe benchmark series](https://www.cboe.com/insights/posts/benchmark-indices-series-income-generation-and-smoother-returns-with-cboes-bxm-bxmd-put-and-cmbo-indices). Specific Sharpe/MDD values and 2008/2018/2020/2022 year numbers not in fetched text.
- [index-provider] PUT calendar returns: 2022 -7.7%, 2023 +14.3%, 2024 +17.8% vs S&P 500 TR -18.1%, +26.3%, +25.0% — search-result snippet citing [S&P DJI research PDF](https://www.spglobal.com/spdji/tc/documents/research/research-defining-paths-with-options-based-index-strategies-tc.pdf) (not verified against the PDF; verify before use).
- [index-provider] Protective put (PPUT) and collar (CLL) 1986-2021: betas < 0.75; PPUT had 18 monthly declines >=6% vs 35 for S&P; in 2008 and 2020 PPUT beat other stock/commodity indices by >10 points; but fewer monthly gains >4% — cost of put buying. Collars sacrifice upside — [Cboe PPUT/CLL/CLLZ](https://www.cboe.com/insights/posts/benchmark-indices-series-hedging-downside-exposure-with-pput-cll-and-cllz-indices)
- [index-provider] Caveat from Cboe/Bondarenko work: results are gross, not net; option turnover far above buy-and-hold — [Cboe white paper page](https://www.cboe.com/insights/posts/new-research-shows-options-based-strategies-can-generate-higher-gross-premiums-with-less-volatility-over-traditional-asset-classes)
- [peer-reviewed/practitioner] Israelov & Nielsen (FAJ 2014): covered call = short volatility plus reduced equity beta; "downside protection" is cheaper by simply cutting equity exposure; good when implied vol is high vs expectations — [CFA/FAJ abstract via search](https://rpc.cfainstitute.org/en/research/financial-analysts-journal/2014/covered-call-strategies-one-fact-and-eight-myths); full PDF at [AQR](https://www.aqr.com/-/media/AQR/Documents/Insights/Journal-Article/FAJ-Covered-Call-Strategies-One-Fact-and-Eight-Myths.pdf) (PDF text not extractable here; eight myths not enumerated)

### Inferences
- PUT/WPUT drawdown (-24% to -33% in 2008) shows even "diversified" index put-writing takes large drawdowns; WPUT's smaller drawdown comes from rolling weekly (faster re-strike), not lower risk.
- Gross-of-cost indices overstate retail-implementable results, especially weekly/daily versions.
- Index-level evidence concerns monthly/weekly ATM exposure with full cash collateral, not 0DTE or defined-risk spreads.

### Gaps
- Table of Sharpe, MDD and 2008/2018/2020/2022 yearly returns for BXM, BXMD, PUT, WPUT, CLL: not obtained (Cboe data PDFs/factsheets not fetched). Cboe factsheet candidate: https://cdn.cboe.com/resources/indices/factsheet/CboeGlobalIndices_PUT-Index.pdf
- Bondarenko's paper itself (SSRN) not read; only Cboe summaries. Ilmanen and AQR option-VRP chapters not retrieved.
- Cboe 0DTE/short-dated benchmark index existence: not found; 2018 (Volmageddon) behavior of PUT/BXM not found.

## 2. Variance risk premium (VRP) evidence and retail harvestability

### Takeaway
Implied vol exceeds realized on average (VIX ~19.3 vs realized ~15.1, 1990-2018), and the VRP predicts returns, so premium is real; whether retail nets it in short-dated ETF options after spreads is not established, and 0DTE evidence below says spreads eat most or all.

### Cited Findings
- [index-provider] VIX avg 19.3% vs S&P realized 15.1% 1990-2018, a 4.2-point gap — [Cboe white paper summary](https://www.cboe.com/insights/posts/white-paper-shows-volatility-risk-premium-facilitated-higher-risk-adjusted-returns-for-put-index/)
- [peer-reviewed] Bollerslev, Tauchen, Zhou (RFS 2009): VRP (model-free implied minus high-frequency realized variance) explains a nontrivial share of post-1990 aggregate return variation, strongest at quarterly horizon — [SSRN abstract](https://papers.ssrn.com/abstract=948309)
- [working paper] Dim, Eraker, Vilkov ("0DTEs: Trading, Gamma Risk and Volatility Propagation", 2024): 0DTE options carry the largest VRP; no evidence that 0DTE gamma raises index vol — secondary via [Harbourfront summary](https://harbourfrontquant.substack.com/p/impact-of-zero-dte-options-on-the) and [ResearchGate listing](https://www.researchgate.net/publication/377984312_0DTEs_Trading_Gamma_Risk_and_Volatility_Propagation) (not fetched directly)
- [working paper] Bandi, Fusari, Reno: 0DTE pricing model with time-varying skew/kurtosis; "suggestive" results on 0DTE-based return/variance risk premium predictability — [JHU Carey summary via search](https://carey.jhu.edu/news/risk-reward-insights-0dte-option-trading) (page itself returned 403; snippet only)

### Inferences
- VRP is on the order of a few vol points on average; in a 0DTE context the realized premium per trade is tiny relative to half-spread (see sect. 3).

### Gaps
- Carr & Wu (2009) and Bakshi-Kapadia (2003) not retrieved. Net-of-cost VRP harvest studies for SPY/QQQ/IWM weekly options: not found.

## 3. 0DTE / 1DTE research

### Takeaway
Retail 0DTE traders lose on net, mainly buying; unconditional 0DTE structures are roughly zero or negative net of execution costs, with conditional/timed variants only thinly positive. Defined-risk iron condors had negative net Sharpe in the Vilkov et al out-of-sample test.

### Cited Findings
- [working paper] Beckmeyer, Branger, Gayda (March 2023, SSRN 4404704): retail SPX 0DTE traders lost >$70M over a ~2-yr sample (Jan 2021-Feb 2023 Cboe data); average losses $184k/day full sample, $358k/day after daily expirations began May 2022; retail bought more than sold, leaving market makers net short; spreads widen near expiry yet retail traded in the last hour — [Bloomberg/BNN](https://www.bnnbloomberg.ca/day-traders-lose-358-000-per-day-gambling-on-zero-day-options-1.1910634); [CXO Advisory (data scope)](https://cxoadvisory.com/individual-investing/retail-0dte-option-trader-performance); [WealthManagement](https://www.wealthmanagement.com/equities/retail-investors-are-love-same-day-options). Decomposition of loss into spread cost vs directional loss: not obtained (paywall).
- [index-provider] Cboe: 0DTE ~2M contracts/day; retail 50-60% of SPX 0DTE volume (dipped to 47%); 95%+ of trades defined-risk (long options or short spreads), ~4% naked shorts; market-maker net gamma hedging ~0.2% of SPX liquidity — [Cboe "0DTEs Decoded"](https://www.cboe.com/insights/posts/0-dt-es-decoded-positioning-trends-and-market-impact)
- [working paper] Vilkov et al. 0DTE strategies repo/paper (Sept 2016-Jan 2026; daily expiries from April 2022): entry 10:00 ET held to close; unconditional strategies near zero, net Sharpe typically negative/near zero after half-spread + 0.5bp fees; conditional OOS (2019-2026) gross/net Sharpe: put ratio spreads 1.18/0.93, strangles 0.56/0.39, iron fly/condor 0.77/-0.20, top-3 basket 1.12/0.82; authors: unconditional 0DTE "difficult to justify as a standing allocation"; suggests tactical sleeve sized on tail risk — [paper-annotated.md](https://github.com/vilkovgr/0dte-strategies/blob/main/docs/paper/paper-annotated.md) (fetched via summarizer; verify numbers against paper; conditional results depend on signal selection, risk of overfit)
- [practitioner/working paper] Volos (2025): time-of-day transaction-cost structure; worst in final minutes before expiry. Average spreads up to ~9% for ultra-short-term options vs ~2% for 21-48 DTE — search snippet from [ResearchGate: Profitability of selected 0DTE strategies](https://www.researchgate.net/publication/388321185_Profitability_of_selected_0DTE_index_options_strategies); another snippet in the same search claims SPX 0DTE median ATM spread 0.20 index pts ($20/contract), OTM 0.05-0.10 pts, via [Concretum](https://concretumgroup.substack.com/p/spx-0dte-options) (practitioner, unverified). The two spread claims use different bases (relative vs absolute).
- [working paper] Adams, Dim, Eraker, Fontaine, Ornthanalai, Vilkov: "Do S&P500 Options Increase Market Volatility? Evidence from 0DTEs" — [SSRN 5641974](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5641974) (listed only, not read).

### Inferences
- Selling 0DTE spreads is roughly the other side of retail's losing buys, but half-spread plus fees consumes most of the gross edge; SPX vs SPY/QQQ/IWM spread differences matter and SPY 0DTE evidence is thin.
- Cboe retail share data implies sellers of defined-risk structures are not rare; no edge claim follows.

### Gaps
- Direct comparison of 0DTE selling vs buying on SPY/QQQ/IWM with real quotes: not found. 1DTE-specific studies: not found. Effective (vs quoted) spread measurement for retail fills: not found. Hedge fund / dealer-side 0DTE P&L: not found.

## 4. Defined-risk structures: backtests with real quotes

### Takeaway
Best-documented retail-accessible backtests are Spintwig's (methodology-rich) and vendor win-rate stats; vendor win rates of 63-75% say nothing about expectancy. Only the Vilkov et al paper gives net-of-cost academic evidence (iron condor net Sharpe -0.20).

### Cited Findings
- [practitioner] Spintwig short-put SPY backtest (Early Retirement Now guest series part 5): 2018-02-21 to 2020-06-05, entries Mon/Wed/Fri 3:46pm ET, ~5-delta strike, exit at 50% max profit or expiry; "significantly more volatility and even some losses" vs a smooth fixed-income-style income target — [ERN part 5](https://earlyretirementnow.com/2020/06/17/passive-income-through-option-writing-part-5). Extended to SPX 2016-09-01 to 2021-10-29 (2-3 DTE entries, 5 and 10 delta) — [ERN part 9](https://earlyretirementnow.com/2021/11/10/passive-income-through-option-writing-part-9-2016-2021-backtest-guest-post-by-spintwig) (only search snippets; page fetch 404; CAGR/MDD/commission assumptions not retrieved).
- [vendor] Option Alpha platform stats: 3,170 iron condors at 63% win rate, 4,959 iron butterflies at 72%; 0DTE iron fly/condor win rates 66.8%/70.2%; generic claim of 30-45 DTE condors 10-18% annualized, 65-75% win, MDD -25% to -40% (unsourced aggregator figure) — [Option Alpha](https://optionalpha.com/blog/0dte-options-strategy-performance), [Option Alpha podcast](https://optionalpha.com/podcast/win-rates-when-selling-options). Vendor; no per-trade cost audit.
- [vendor] Backtest platform claims (e.g., 78.9% win/2.32 Sharpe May 2022-Aug 2026; 68% win/1.72 Sharpe/-9.4% MDD) are signal-optimized marketing — search-result snippets only (e.g., [Option Omega via OptionsTradingIQ](https://optionstradingiq.com/option-omega/)); do not rely.
- [vendor] Tastylive SPY backtests March 2023 - Feb 2024 on short 0DTE (one-year sample, bull market) — referenced in search; contents not retrieved.
- [vendor] Option Alpha: entry time 10:30am vs 2:30pm 0DTE SPX iron condor differed ~$15k P/L — [Option Alpha](https://optionalpha.com/videos/morning-vs-afternoon-0dte-backtested-options-strategies) (illustrates parameter sensitivity).

### Inferences
- Win rates 65-75% with defined risk mean average loser > average winner; need profit factor, which vendors rarely publish.
- Backtest windows after April 2022 contain no 2008/2020-type tail.

### Gaps
- Profit factor, drawdown and cost assumptions for Spintwig, tastylive, Option Alpha: not obtained. Option Samurai: not researched. Credit vs debit spread academic comparisons: not found.

## 5. Risk of ruin, negative skew, capital needs for a limited paper bot

### Takeaway
Put-writing has skew -2.09 (monthly PUT) and index drawdowns -24% to -33%; short-dated sellers face gap/tail events and vol-spike losses. A paper bot should model costs and tail days explicitly and cap per-trade max loss.

### Cited Findings
- [index-provider] PUT skewness -2.09 — [Cboe](https://www.cboe.com/insights/posts/white-paper-shows-volatility-risk-premium-facilitated-higher-risk-adjusted-returns-for-put-index/)
- [working paper] Vilkov et al.: size positions on tail-risk measures not mean P&L; short-vol structures did better in high-VIX regimes; OTM sold options profitable in up to ~75% of observations — [paper-annotated.md](https://github.com/vilkovgr/0dte-strategies/blob/main/docs/paper/paper-annotated.md)
- [index-provider] Cboe: 95%+ of SPX 0DTE flow is defined-risk — [Cboe](https://www.cboe.com/insights/posts/0-dt-es-decoded-positioning-trends-and-market-impact)

### Inferences
- Defined-risk spreads cap per-trade loss at width minus credit, margin = max loss; for a small account that sets the contract count (e.g., $5-wide SPY spread ~ $500 max loss/contract). This is arithmetic, not sourced.
- Assume entry at bid/ask or worse and test with worst-case slippage; prefer conditional rules only with out-of-sample validation.

### Gaps
- Published risk-of-ruin calculations for index spread strategies: not found. Specific tail events (Feb 2018 Volmageddon, Mar 2020, Aug 2024 vol spike) lacking sourced P&L for short-dated sellers.

## 6. Buying side: long calls/puts, crash protection

### Takeaway
Evidence found: protective puts reduce tail months but cost premium; retail 0DTE buyers lose on net. No credible long-run track record found for systematic long-option buying as a return source.

### Cited Findings
- [index-provider] PPUT: fewer big down months (18 vs 35) and >10pt better in 2008 and 2020, but fewer big up months and a premium cost — [Cboe](https://www.cboe.com/insights/posts/benchmark-indices-series-hedging-downside-exposure-with-pput-cll-and-cllz-indices); PPUT total return 708% vs PUT 1835% 1986-2018 — [Cboe](https://www.cboe.com/insights/posts/white-paper-shows-volatility-risk-premium-facilitated-higher-risk-adjusted-returns-for-put-index/)
- [working paper] Retail buyers dominate 0DTE and lose in aggregate — [Beckmeyer et al via BNN](https://www.bnnbloomberg.ca/day-traders-lose-358-000-per-day-gambling-on-zero-day-options-1.1910634)
- [working paper] Risk reversal showed small positive mean P&L (~0.01% of spot) in Vilkov et al unconditional test; marginal — [paper-annotated.md](https://github.com/vilkovgr/0dte-strategies/blob/main/docs/paper/paper-annotated.md)

### Inferences
- Because the VRP is positive on average, systematic long options carry negative expected return before timing signals; momentum-with-limited-risk claims need own validation.

### Gaps
- Academic evidence on long call/straddle returns on index options (e.g., Coval-Shumway): not retrieved. Debit-spread backtests with real quotes: not found.

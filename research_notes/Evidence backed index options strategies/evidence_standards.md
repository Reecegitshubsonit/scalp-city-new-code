# Evidence standards for ranking candidate strategies (base rates, statistics, verification, costs)

Evidence tags: [PR]=peer-reviewed, [WP]=working paper, [REG]=regulator/legal-practice summary, [PRAC]=practitioner/aggregator, [BLOG]=blog/forum, [ANEC]=anecdotal/industry-reported.
Note: several figures below came via search-result summaries, not full-paper reads; flagged where so. Formulas for MinTRL/PSR/DSR are from secondary sources that reproduce the papers.

## 1. Replication and decay of published anomalies

### Takeaway
Published equity anomalies lose roughly a quarter of return out-of-sample (data-mining part) and over half post-publication; whether "most anomalies are false" depends on method (65-82% fail under Hou-Xue-Zhang strict screens vs ~82% replicate under Jensen-Kelly-Pedersen Bayesian approach). Survivors are the large, liquid, economically-motivated ones (value, momentum, investment, profitability). For a single liquid index instrument, expect the effective haircut to be heavy; assume published Sharpe x ~0.4-0.5 as a planning prior.

### Cited Findings
- McLean-Pontiff: 97 return predictors; portfolio returns 26% lower out-of-sample, 58% lower post-publication; implied ~32% (58-26) decline due to publication-informed trading; larger declines for higher in-sample returns; effects stronger in high idiosyncratic-risk, low-liquidity stocks. [PR, J. Finance 2016] — [summary](https://academicnewsletter.sufe.edu.cn/info/359722); paper copy [Ivey PDF](https://ivey.uwo.ca/media/3775549/pontiff.pdf)
- Hou-Xue-Zhang "Replicating Anomalies" (RFS 2020): 452 anomalies, microcaps mitigated (NYSE breakpoints, value-weighted); 65% fail |t|>=1.96; 82% fail multiple-test hurdle |t|>=2.78; replicating well: value, momentum, investment, profitability. [PR] — [Systematically Biased summary](https://systematicallybiased.substack.com/p/pockets-of-replicability-post5), [Alpha Architect](https://alphaarchitect.com/replicating-anomalies/) [PRAC/BLOG summaries; paper at [IDEAS](https://ideas.repec.org/a/oup/rfinst/v33y2020i5p2019-2133..html)]
- Harvey-Liu-Zhu (RFS 2016): 313 published + 63 near-published papers, 316 factors; new factors should clear t>3.0 (p<0.0027). [PR] — [NBER w20592](https://nber.org/papers/w20592), [SSRN](https://papers.ssrn.com/abstract=2513152)
- Harvey-Liu "Backtesting" (JPM 2015): multiple-testing Sharpe haircut is nonlinear; the common 50% haircut is only a rule of thumb; highest Sharpes moderately penalized, marginal ones heavily. [PR] — [Duke PDF](https://people.duke.edu/~charvey/Research/Published_Papers/P120_Backtesting.PDF), [Man Institute](https://www.man.com/insights/backtesting)
- Linnainmaa-Roberts (RFS 2018): 36 accounting-based anomalies; majority likely data-snooping artifacts; out-of-sample (pre-/post-sample) average returns and Sharpe ratios fall, volatilities and cross-anomaly correlations rise. [PR] — [Wharton PDF](https://jacobslevycenter.wharton.upenn.edu/wp-content/uploads/2017/08/The-History-of-the-Cross-Section-of-Stock-Returns.pdf), [NBER w22894](https://nber.org/papers/w22894)
- Jensen-Kelly-Pedersen (J. Finance 2023): 153 factors, 93 countries, Bayesian; ~82% replicable; evidence strengthened by the large number of factors; contrasts with ~35% replication reported elsewhere. [PR/WP] — [NBER w28432](https://www.nber.org/papers/w28432), [Alpha Architect](https://alphaarchitect.com/is-there-a-replication-crisis-in-finance/)
- Chen: "Most claimed statistical findings in cross-sectional return predictability are likely true" (counterpoint to HLZ). [WP] — [arXiv 2206.15365](https://arxiv.org/pdf/2206.15365)

### Inferences
- Base-rate range for "claim holds up net of multiple-testing and costs" is wide: ~18-35% (HXZ/strict) to ~80% (JKP, factor-level, long-short, global). Conflict is about method/population, not data.
- All of this is cross-sectional equity factor evidence. NONE of it directly validates index-options strategies (single instrument, few independent bets, short history). Index/option-strategy claims should be treated as lower-evidence than diversified factors: small effective N of independent observations, high autocorrelation, and heavy tails.
- Planning prior (my judgement, not a published number): apply McLean-Pontiff 58% post-publication haircut to published-strategy return; for an unpublished/self-discovered backtest, additionally apply a multiple-testing haircut (section 2). Strategies that are widely published, cheap to trade, and in a single liquid market (e.g. index-option premium selling, 0DTE) are the most exposed to crowding decay.
- Rule: factors with a risk-premium or structural (insurance/hedging-demand, forced-flow) explanation survive better than pure pattern findings.

### Gaps
- No full-text read of the papers; numbers come from abstracts/secondary summaries. No source found giving an anomaly-survival rate specifically for index-option or intraday strategies.
- Linnainmaa-Roberts exact quantitative survival fraction not retrieved.

## 2. Statistical standards (Sharpe inference, DSR, MinBTL, MinTRL)

### Takeaway
Sharpe ratios from short samples are very noisy; ~1 year of data cannot distinguish SR 1 from 0. After N tried variants, the best in-sample Sharpe is expected to be large by chance (about 1.2 SR-sd for N=5, 2.5 for N=100). Require a deflated Sharpe that accounts for the number of trials, plus a live/out-of-sample period of years, not months.

### Cited Findings
- Deflated Sharpe Ratio (Bailey & Lopez de Prado) corrects for selection bias under multiple testing, backtest overfitting, sample length and non-normality; raises the PSR threshold according to the number of independent trials. [PR, J. Portfolio Mgmt 2014] — [SSRN 2460551](https://papers.ssrn.com/abstract=2460551), [tradingstrategy.ai glossary](https://tradingstrategy.ai/glossary/probabilistic-sharpe-ratio)
- Expected max Sharpe across N independent trials (null): SR* = sqrt(V) * [ (1-g)*Phi^-1(1-1/N) + g*Phi^-1(1-1/(N*e)) ], g=0.5772 (Euler-Mascheroni), V=variance of Sharpe estimates across trials. DSR = PSR evaluated with benchmark SR*. [PRAC reproduction of PR paper] — [Wikipedia DSR](https://en.wikipedia.org/wiki/Deflated_Sharpe_ratio), [LuxAlgo](https://www.luxalgo.com/library/concept/deflated-sharpe-ratio/)
- PSR(c) = Phi( (SR_hat - c) / sqrt( (1 - skew*SR_hat + (kurt-1)/4 * SR_hat^2) / T ) ), skew/kurt = sample skewness/raw kurtosis, T=number of return observations, SR in same frequency as T. [PRAC reproduction] — [Portfolio Optimizer](https://portfoliooptimizer.io/blog/the-probabilistic-sharpe-ratio-bias-adjustment-confidence-intervals-hypothesis-testing-and-minimum-track-record-length/)
- MinTRL(c) = [1 - skew*SR_hat + (kurt-1)/4 * SR_hat^2] * [ z_(1-alpha) / (SR_hat - c) ]^2 (in observations). Worked example from source: annualized SR ~1.0, 136 monthly points, benchmark 0.75 annualized -> MinTRL ~184 months at 95%. [PRAC reproduction] — same Portfolio Optimizer link
- Bailey-Borwein-Lopez de Prado-Zhu: after only 7 configurations, a researcher is expected to find at least one 2-year backtest with annualized SR>1 when true SR=0; authors define Minimum Backtest Length (MinBTL); most papers do not report trials count. [PR, Notices AMS 2014] — [WMU scholarworks](https://scholarworks.wmich.edu/math_pubs/40/)
- Harvey-Liu-Zhu t>3 hurdle and Harvey-Liu nonlinear Sharpe haircut (section 1).

### Inferences (my computations; normal returns, skew=0, kurt=3, so variance factor = 1 + SR^2/2 per year-unit)
Years needed for SR_hat to exceed 0 at one-sided confidence: T_years = (1+SR^2/2)*(z/SR)^2

| True/observed annual SR | 95% (z=1.645) | 99% (z=2.326) | ~trading days at 95% |
|---|---|---|---|
| 0.5 | 12.2 y | 24.4 y | - |
| 1.0 | 4.1 y | 8.1 y | ~1,020 |
| 1.5 | 2.6 y | 5.1 y | ~640 |
| 2.0 | 2.0 y | 4.1 y | - |

- Against a non-zero hurdle (c=0.5): SR 1.0 -> 16.2 y; SR 1.5 -> 5.8 y; SR 2.0 -> 3.6 y (95%).
- Negative skew / fat tails (typical of short-premium option strategies: skew<0, kurt>>3) INCREASE the multiplier [1 - skew*SR + (kurt-1)/4*SR^2], so required length is longer than the table. Example: SR=1.5 daily-annualized, skew=-2, kurt=10 -> factor = 1+3+5.06 = 9.1 vs 2.1 (normal) -> ~4.3x longer (~11 y at 95%). Option sellers should use the non-normal formula with measured skew/kurt, and note a short sample may not contain the tail event at all.
- Expected-max-Sharpe (in units of SR-estimate sd): N=5 -> 1.19; 10 -> 1.57; 50 -> 2.28; 100 -> 2.53; 1000 -> 3.26. For 1 year of data the SR-estimate sd is ~1, so trying 100 variants and picking the best yields an expected "annual SR 2.5" from pure noise.
- Trade-count view: Sharpe per trade ~ mean/sd of trade P&L; t-stat of mean trade = SR_trade*sqrt(n). To clear t>3 need n >= (3/SR_trade)^2; e.g. mean/sd of 0.2 per trade -> 225 independent trades; 0.1 -> 900. Overlapping/correlated trades (same-day, same regime) do not count as independent.
- Count trials honestly: every parameter value, filter, instrument, DTE, strike delta, time-of-day tried counts toward N.

### Gaps
- Did not retrieve the exact MinBTL equation (approx. MinBTL ~ 2*ln(N)/E[max SR]^2 years in the paper per my recollection - UNVERIFIED; the PDF fetch failed). Treat as unverified.
- Effective-N for correlated trials (DSR requires clustering/independent-trial estimate) not sourced.

## 3. What counts as a verified track record

### Takeaway
Only third-party-custodied, time-stamped, real-capital records (brokerage/administrator statements, audited fund financials, GIPS-style verification) count as strong. Platform "verified" badges, demos, hypothetical/backtested results and social-media P&L are weak or non-evidence; regulators treat hypothetical/backtested performance as requiring special safeguards.

### Cited Findings
- SEC Marketing Rule (Rule 206(4)-1, compliance date Nov 4, 2022): hypothetical performance includes model, backtested and targeted/projected returns; allowed only with policies to ensure relevance to audience's financial situation/objectives and disclosure of risks and limitations. SEC sweep charged nine advisers for hypothetical-performance violations. [REG/legal summaries] — [Troutman](https://www.troutman.com/insights/the-secs-new-marketing-rule-practically-speaking-hypothetical-performance/), [SEC order IA-6803](https://www.sec.gov/files/litigation/admin/2024/ia-6803.pdf), [Seward & Kissel](https://www.sewkis.com/publications/sec-sweep-into-marketing-rule-violations-results-in-charges-against-nine-investment-advisers/)
- FINRA Rule 2210 currently generally prohibits predictions/projections in public communications; a 2026 proposal would permit conditional projected/targeted returns to align with the SEC rule; social media subject to same accuracy/balance standards; testimonials must not mislead. [REG] — [Sidley](https://www.sidley.com/en/insights/newsupdates/2026/02/finra-proposes-to-permit-projected-performance-and-targeted-returns-in-member-communications), [Mayer Brown](https://www.mayerbrown.com/-/media/files/perspectives-events/publications/2026/03/finra-proposes-amendments-to-communications-rule-to-permit-use-of-projections.pdf%3Frev=-1)
- Myfxbook: "verified" means trades/deposits match the broker feed; known weaknesses are demo accounts displaying as real, choosable start dates (cherry-picking), and deposit/withdrawal manipulation of the equity curve; 2-3 years of age is harder to fake. [BLOG/forum] — [BabyPips guide](https://forums.babypips.com/t/a-guide-to-using-and-recognising-myfxbook-accounts/52656), [BabyPips fake vs real](https://forums.babypips.com/t/ways-to-recognize-fake-and-real-accounts-on-myfxbook/194062)
- Collective2: results labeled hypothetical per the platform; backtest upload not allowed (record starts on first day on platform); marketplace/tracker, not a certifier; system code can change at any time. [BLOG/forum] — [EliteTrader thread](https://elitetrader.com/et/threads/how-does-collective2-work.229089/)
- Darwinex: trades via Darwinex account contribute to a verified auditable record; Darwinex Zero uses synthetic funds (paper-style, so not real-capital evidence). [PRAC/company] — [Darwinex](https://www.darwinex.com/about), [fintech.global](https://fintech.global/2026/07/17/darwinex-launches-native-tradingview-integration/)

### Inferences
- Evidence hierarchy (my ranking): (1) audited fund / index provider with published methodology and live post-launch history; (2) custodian/broker statements covering all accounts, with deposits/withdrawals; (3) platform-verified live real-money with long history and no start-date selection; (4) platform-verified demo / synthetic; (5) backtest with disclosed trial count; (6) screenshots, social-media P&L, unverified claims.
- Social-media P&L is non-evidence: selection (survivors post), no full-account view, no deposit/withdrawal data, no trial count, editable, and incentives (follows, course/signal sales). Regulators' restrictions on hypothetical/projected performance in advertising reflect the same concern.
- Index-provider histories (e.g. Cboe strategy benchmark indexes) are mostly backtests before launch date; only the post-launch segment is live. Split pre/post inception when judging.

### Gaps
- No primary SEC/FINRA text read directly; legal-firm summaries used. No source retrieved on GIPS verification or on Collective2 audit specifics beyond forum posts (low quality).
- No authoritative published rate of fabricated/misleading platform track records.

## 4. Retail algorithmic and day-trading outcomes

### Takeaway
Every large dataset shows retail day trading and short-dated options trading is a net loser; costs are the primary driver. Prop-firm data show low pass and payout rates. Good-faith published success rates specifically for retail *algorithmic* strategies were not found.

### Cited Findings
- Chague-De-Losso-Giovannetti (Brazil mini-Ibovespa futures, 19,646 new day traders 2013-2015; those persisting 300+ days): 97% lost money; only 0.4% earned more than a bank-teller wage (~US$54/day); no evidence of learning. [WP/published] — [FGV repository](https://repositorio.fgv.br/items/e87d04fc-4b4c-4a56-ab5a-1c84c1afde1b/full), [CXO summary](https://www.cxoadvisory.com/investing-expertise/day-trading-a-bust/)
- Barber-Lee-Liu-Odean (Taiwan 1995-99): <1% of day traders predictably earn positive abnormal returns net of fees; >80% lose; aggregate losses >2% of GDP. [PR/WP] — [Berkeley PDF](https://faculty.haas.berkeley.edu/odean/papers/day%20traders/Day%20Trading%20Skill%20110523.pdf), [CXO](https://www.cxoadvisory.com/individual-investing/do-day-traders-make-money/)
- Beckmeyer-Branger-Gayda, "Retail Traders Love 0DTE Options... But Should They?" (SSRN 4404704, 2023): retail lost >$70M over ~2 years in SPX 0DTE, avg $184k/day, $358k/day after daily expirations began; >$50M of losses from transaction costs; retail net buyers (market makers net short). [WP] — [SSRN](https://ssrn.com/abstract=4404704), [Bloomberg](https://www.bloomberg.com/news/articles/2023-04-21/day-traders-lose-358-000-per-day-gambling-on-zero-day-options), [paper summary](https://medium.com/@y125789/retail-traders-love-0dte-options-paper-summary-6da4a7ff7d72) [BLOG for the last]
- Prop firms: FPFX Tech dataset (>100,000 traders, 10 firms): 14% passed challenge, ~7% ever reached payout, average payouts ~4% of funded account; other trackers: 5-14% of challenges end funded, ~12.3% in Track360 sample. [ANEC/industry-reported; vendor and aggregator data, firms have incentives] — [Track360](https://track360.io/blog/prop-trading-industry-statistics-2026), [Finance Magnates](https://www.financemagnates.com/forex/only-1-in-20-traders-pass-prop-firm-challenges-reports-the-funded-trader/)

### Inferences
- Reasons most retail algos fail (synthesis from above plus section 2): trading costs vs small gross edge; overfitting (unreported trial counts); regime change / crowding decay (McLean-Pontiff); short samples (MinTRL); tail blow-ups in short-premium strategies; execution gap between backtest mid-price fills and live fills.
- Prop-firm pass rates are not evidence of strategy quality: payoff structures sell rule-bound options on variance; survivors reflect selection from large sign-up pools. Treat as a retail base-rate signal only.
- Caveat on direction: the day-trader studies mostly measure discretionary, high-turnover retail flow, not systematic low-turnover strategies; they set a cost/behavior base rate, not a ceiling for systematic strategies.

### Gaps
- No peer-reviewed success rate specific to retail algorithmic bots found. Prop-firm figures are industry-reported, not audited.
- CXO page for Beckmeyer paywalled; exact 0DTE spread/return-per-trade numbers not retrieved.

## 5. Cost realism for options

### Takeaway
Quoted spreads are the wrong cost for a non-timed retail order: untimed traders pay roughly the conventional effective spread, and only latency-advantaged traders pay a fraction of it. Model fills conservatively at or beyond mid-to-natural, include fees, and require gross edge to exceed a multiple of round-trip cost.

### Cited Findings
- Muravyev-Pearson, "Options Trading Costs Are Lower than You Think" (RFS 2020): for average trade, timing-adjusted effective spread is one-third smaller than conventionally measured; for trades exploiting quote-change predictability, adjusted effective spread ~1.3 cents/unit vs 8.1 cents average bid-ask spread and 6.2 cents conventional effective spread; investors who cannot time trades bear on average the conventionally measured effective spreads. [PR] — [CXO summary](https://www.cxoadvisory.com/equity-options/timing-option-trades-to-suppress-trading-frictions/), [Illinois](https://experts.illinois.edu/en/publications/options-trading-costs-are-lower-than-you-think/fingerprints/)
- Beckmeyer et al.: >$50M of $70M+ retail 0DTE SPX losses attributable to transaction costs (section 4). [WP]

### Inferences (rules of thumb - my judgement, no direct source)
- Implied conventional effective spread ~6.2/8.1 = ~77% of quoted spread in that sample, i.e. a market-order-like fill pays ~3/4 of the quoted spread round-trip-half each way; limit-at-mid fills are uncertain and adverse-selected (you fill when price moves against you).
- Conservative backtest cost model: entry and exit each at mid -/+ 50-75% of half-spread... simpler: charge 50-100% of the quoted full spread per round trip for liquid index options (use 100% for thin strikes, wide spreads, fast markets, open/close, or multi-leg: charge per leg), plus commissions/exchange/regulatory fees per contract, plus slippage on stop/exit (stops fill through quote). Use time-stamped historical NBBO, not end-of-day mid; reject strategies whose quote data are daily closes.
- Required edge: gross expected P&L per trade >= ~3x modeled round-trip cost to survive (cost misestimation of 2x still leaves positive edge); at 1x cost the strategy is a coin flip once decay (section 1) is applied. Sensitivity test: strategy must stay profitable (Sharpe >0.5, positive mean) at 2x modeled costs.
- Edge survival: with 58% post-publication decay and cost drag, a published gross edge of e.g. 30 bp/trade retains ~12.6 bp before costs; if round-trip cost is 10 bp, net ~2.6 bp. High-turnover, short-dated strategies are therefore the most fragile.
- Multi-leg structures multiply spread costs by leg count; credit spreads at 0-3 DTE pay spread on a small premium, so cost/premium ratio is large. Compute cost as % of premium collected and % of max risk.
- Latency: retail API latency (hundreds of ms) forfeits the timing advantage in Muravyev-Pearson; assume no latency edge. Add 1-5s delay to all signals in backtest and check sensitivity.

### Gaps
- No source found for percent-of-spread fill assumptions on SPX/SPY options for retail limit orders, nor current (2026) fee schedules. Rules above are unverified heuristics.

## 6. Checklist and scoring rubric

### Takeaway
Score each candidate 0-2 on eight criteria (0-16 total). Gate criteria force exclusion regardless of total. Thresholds derive from sections 1-5; weights and cutoffs are judgement calls, not published standards.

### Cited Findings
- Component thresholds anchor to: t>3 (HLZ), t>=2.78 multiple-test (HXZ), 58% post-publication decay (McLean-Pontiff), MinTRL formula (Bailey-LdP), spread findings (Muravyev-Pearson). Sources in sections 1-5.

### Inferences (proposed rubric)

Hard gates (fail any -> do not implement as bot; at most "watchlist"):
- G1: no trial/parameter count disclosed AND no ability to reproduce -> exclude.
- G2: net-of-cost P&L not shown, or only mid-price fills -> exclude until re-run with cost model.
- G3: evidence solely social-media/screenshot/hypothetical marketed performance -> exclude.
- G4: strategy has unbounded/undefined loss with no modeled tail (naked short premium) and sample has no stressed period (e.g. Feb 2018, Mar 2020, Aug 2024) -> exclude or require defined-risk form.

Score 0/1/2:

| # | Criterion | 0 | 1 | 2 |
|---|---|---|---|---|
| 1 | Source quality | blog/social/anecdote | working paper, practitioner with methodology | peer-reviewed or audited/regulated live record with method disclosed |
| 2 | Sample length / independent observations | <2 y or <100 independent trades | 2-5 y or 100-300 trades | >5 y covering >=2 vol regimes incl. a stress event, >300 independent trades; meets MinTRL(c=0) at 95% using measured skew/kurt |
| 3 | Out-of-sample | none | pseudo-OOS (holdout, walk-forward) by same author | true post-publication/live OOS or independent replication, different market/period |
| 4 | Multiple-testing control | trials unknown | trials counted, simple haircut | DSR>0.95 or t>3 after correcting for N; stated trial count |
| 5 | Decay evidence | decayed >50% post-publication or in recent years | decay 20-50% / unknown but plausible crowding | stable or <20% decline in recent 3 y out-of-sample; structural premium rationale |
| 6 | Cost robustness | gross only or breaks at 1x costs | positive at 1x, breaks at 2x | positive at 2x modeled costs; gross edge >=3x round-trip cost; NBBO-based |
| 7 | Implementability (paper bot) | needs sub-second latency, unavailable data, manual judgment | feasible but data/fills uncertain | uses liquid index options, delayed 1-5 s signals, data available, defined risk |
| 8 | Economic rationale | none / pure pattern | plausible story | documented structural premium (e.g. risk transfer) with identifiable counterparty |

Interpretation (proposed): 13-16 = implement first; 9-12 = implement with reduced size / extended paper period; 5-8 = research more only; <5 = discard. Require paper-trading period meeting MinTRL-type logic before any promotion; a 3-month paper run can only falsify (e.g. detect a disaster), not confirm a Sharpe of 1-1.5.

Planning priors for paper expectation: set live Sharpe expectation = published/backtest SR x 0.4 (published) or x 0.3-0.5 (self-optimized, depending on N from section 2 table), then ask whether that still clears costs.

### Gaps
- Rubric weights/thresholds are not validated against any outcome data; they are design choices. No published scoring standard found to benchmark against.
- Aronson, "Evidence-Based Technical Analysis" (data-mining bias, White's Reality Check) was not retrieved or verified this session; no claims drawn from it.
- AQR/Alpha Architect cost-of-implementation research and Journal of Finance papers on index-option strategy decay (e.g. variance risk premium/put-writing post-publication) not covered; a follow-up researcher should check those for strategy-family-specific base rates.

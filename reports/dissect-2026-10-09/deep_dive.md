# 2026-10-09 deep dive, all 52 closed trades

R = 1 ATR = stop distance. Move = underlying close minus signal close, in signal ATR, + = trade's favour. Stop -1R, target +2R on a bar close.

### 1. IWM-VWAP PUT IWM261012P00278000: -230 (stop)

Signal 09:43 @ 278.08 · in 1.22 (q 1.2/1.22) · stop 278.36 / tgt 277.53 · ATR 0.277 (9.96 bp) · out 10:20 0.99 (q 0.99/1.0) at -1.48R · 37m · best +1.99 / worst -3.32

**Setup.** price closed across VWAP; side = cross direction (PUT); EMA9/21 pointed the other way. VWAP +0.8 ATR, EMA50 -1.1 ATR (+ = on trade's side). 
**Path.** Best +1.99R at 09:49 (passed +1R at 09:45). Below entry from 09:44. Worst close -3.32R at 10:09. Stop triggered on the 10:20 close (-1.48R), filled 10:20 at -1.48R (0.48R past the stop line).
**After exit (30 min).** Best +0.47R at 10:50, worst -2.29R. Kept going against the trade; the stop saved a bigger loss.
**Verdict.** Had 1R+ profit and gave it all back. Different: 1R target +1.0R; EMA9/21 side (CALL) -1.0R; 10 min time stop +0.3R; fill at stop line saves 0.48R.

### 2. IWM-EMA50 PUT IWM261012P00278000: -260 (stop)

Signal 09:46 @ 277.72 · in 1.42 (q 1.41/1.43) · stop 278.00 / tgt 277.17 · ATR 0.275 (9.92 bp) · out 09:55 1.16 (q 1.13/1.14) at -1.74R · 9m · best +0.69 / worst -1.74

**Setup.** price closed across EMA50; side = cross direction (PUT); EMA9/21 pointed the other way. VWAP +1.9 ATR, EMA50 +0.2 ATR (+ = on trade's side). Also open on IWM: IWM-VWAP PUT.
**Path.** Best +0.69R at 09:49. Below entry from 09:50. Worst close -1.74R at 09:55. Stop triggered on the 09:55 close (-1.74R), exit failed 1x, filled 09:55 at -1.74R (0.74R past the stop line).
**Fills.** Fill outside quote: logged -260 not real; at mids -285.
**After exit (30 min).** Best -1.58R at 09:56, worst -4.65R. Kept going against the trade; the stop saved a bigger loss.
**Verdict.** Chopped out: small favour, then stopped. Different: EMA9/21 side (CALL) +2.3R; 10 min time stop -1.3R; fill at stop line saves 0.74R; the exit order must not fail.

### 3. IWM-RANGE PUT IWM261012P00278000: -250 (stop)

Signal 09:47 @ 277.57 · in 1.51 (q 1.5/1.51) · stop 277.84 / tgt 277.03 · ATR 0.271 (9.78 bp) · out 09:52 1.26 (q 1.26/1.28) at -1.29R · 5m · best +0.15 / worst -1.44

**Setup.** price closed outside the 9:30-9:44 range; side = break direction (PUT); EMA9/21 agreed. VWAP +2.4 ATR, EMA50 +0.8 ATR (+ = on trade's side). Also open on IWM: IWM-VWAP PUT, IWM-EMA50 PUT.
**Path.** Best +0.15R at 09:49. Below entry from 09:48. Worst close -1.44R at 09:51. Stop triggered on the 09:52 close (-1.29R), exit failed 1x, filled 09:52 at -1.29R (0.29R past the stop line).
**After exit (30 min).** Best -1.55R at 09:53, worst -5.27R. Kept going against the trade; the stop saved a bigger loss.
**Verdict.** Wrong side from the first minute. Different: fill at stop line saves 0.29R; the exit order must not fail.

### 4. QQQ-RANGE PUT QQQ261012P00749000: +190 (stop)

Signal 09:47 @ 748.76 · in 3.20 (q 3.29/3.31) · stop 749.50 / tgt 747.28 · ATR 0.739 (9.87 bp) · out 09:53 3.39 (q 2.97/2.98) at -1.08R · 6m · best +0.21 / worst -1.08

**Setup.** price closed outside the 9:30-9:44 range; side = break direction (PUT); EMA9/21 pointed the other way. VWAP +2.9 ATR, EMA50 -0.1 ATR (+ = on trade's side). 
**Path.** Best +0.21R at 09:52. Below entry from 09:48. Worst close -1.08R at 09:53. Stop triggered on the 09:53 close (-1.08R), filled 09:53 at -1.08R (0.08R past the stop line).
**Fills.** Fill outside quote: logged +190 not real; at mids -325.
**After exit (30 min).** Best -0.03R at 09:55, worst -1.60R. Kept going against the trade; the stop saved a bigger loss.
**Verdict.** Wrong side from the first minute. Different: EMA9/21 side (CALL) +2.1R.

### 5. QQQ-EMA50 PUT QQQ261012P00749000: +230 (stop)

Signal 09:52 @ 748.61 · in 3.17 (q 3.22/3.24) · stop 749.31 / tgt 747.20 · ATR 0.704 (9.4 bp) · out 09:53 3.40 (q 2.96/2.97) at -1.36R · 1m · best +0.00 / worst -1.36

**Setup.** price closed across EMA50; side = cross direction (PUT); EMA9/21 agreed. VWAP +2.8 ATR, EMA50 +0.2 ATR (+ = on trade's side). Prior 5 min +0.2 ATR. Also open on QQQ: QQQ-RANGE PUT.
**Path.** Never moved in its favour. Below entry from 09:53. Worst close -1.36R at 09:53. Stop triggered on the 09:53 close (-1.36R), filled 09:53 at -1.36R (0.36R past the stop line).
**Fills.** Fill outside quote: logged +230 not real; at mids -265.
**After exit (30 min).** Best -0.25R at 09:55, worst -1.90R. Kept going against the trade; the stop saved a bigger loss.
**Verdict.** Wrong side from the first minute. Different: fill at stop line saves 0.36R.

### 6. IWM-RANGE CALL IWM261012C00279000: -130 (stop)

Signal 10:01 @ 278.88 · in 1.16 (q 1.16/1.17) · stop 278.64 / tgt 279.34 · ATR 0.233 (8.35 bp) · out 10:13 1.03 (q 1.03/1.04) at -1.14R · 12m · best +0.54 / worst -1.14

**Setup.** price closed outside the 9:30-9:44 range; side = break direction (CALL); EMA9/21 agreed. VWAP +2.8 ATR, EMA50 +4.0 ATR (+ = on trade's side). Prior 5 min +3.1 ATR = chasing. Also open on IWM: IWM-VWAP PUT.
**Path.** Best +0.54R at 10:09. Below entry from 10:02. Worst close -1.14R at 10:13. Stop triggered on the 10:13 close (-1.14R), filled 10:13 at -1.14R (0.14R past the stop line).
**After exit (30 min).** Best -0.36R at 10:16, worst -3.48R. Kept going against the trade; the stop saved a bigger loss.
**Verdict.** Chopped out: small favour, then stopped. Different: 10 min time stop -0.1R.

### 7. QQQ-EMA50 PUT QQQ261012P00749000: -320 (stop)

Signal 10:02 @ 748.83 · in 3.16 (q 3.15/3.16) · stop 749.43 / tgt 747.62 · ATR 0.603 (8.05 bp) · out 10:07 2.84 (q 2.84/2.85) at -1.08R · 5m · best +0.05 / worst -1.08

**Setup.** price closed across EMA50; side = cross direction (PUT); EMA9/21 agreed. VWAP +2.6 ATR, EMA50 +0.1 ATR (+ = on trade's side). Prior 5 min +0.7 ATR. Also open on QQQ: QQQ-RANGE PUT.
**Path.** Never moved in its favour. Below entry from 10:03. Worst close -1.08R at 10:07. Stop triggered on the 10:07 close (-1.08R), filled 10:07 at -1.08R (0.08R past the stop line).
**After exit (30 min).** Best -0.08R at 10:12, worst -2.79R. Kept going against the trade; the stop saved a bigger loss.
**Verdict.** Wrong side from the first minute. Different: no tested rule saves it.

### 8. QQQ-RANGE PUT QQQ261012P00749000: -270 (stop)

Signal 10:02 @ 748.83 · in 3.15 (q 3.13/3.15) · stop 749.43 / tgt 747.62 · ATR 0.603 (8.05 bp) · out 10:07 2.88 (q 2.88/2.89) at -1.08R · 5m · best +0.05 / worst -1.08

**Setup.** price closed outside the 9:30-9:44 range; side = break direction (PUT); EMA9/21 agreed. VWAP +2.6 ATR, EMA50 +0.1 ATR (+ = on trade's side). Prior 5 min +0.7 ATR. Also open on QQQ: QQQ-EMA50 PUT.
**Path.** Never moved in its favour. Below entry from 10:03. Worst close -1.08R at 10:07. Stop triggered on the 10:07 close (-1.08R), filled 10:07 at -1.08R (0.08R past the stop line).
**After exit (30 min).** Best -0.08R at 10:12, worst -2.79R. Kept going against the trade; the stop saved a bigger loss.
**Verdict.** Wrong side from the first minute. Different: no tested rule saves it.

### 9. SPY-VWAP CALL SPY261012C00776000: +360 (target)

Signal 10:08 @ 776.17 · in 2.11 (q 2.1/2.11) · stop 775.86 / tgt 776.79 · ATR 0.312 (4.01 bp) · out 10:52 2.47 (q 2.47/2.48) at +2.68R · 44m · best +2.68 / worst -0.58

**Setup.** price closed across VWAP; side = cross direction (CALL); EMA9/21 agreed. VWAP +0.4 ATR, EMA50 +2.6 ATR (+ = on trade's side). Prior 5 min +0.5 ATR. 
**Path.** Best +2.68R at 10:52 (passed +1R at 10:24). Worst close -0.58R at 10:42. Target triggered on the 10:52 close, filled 10:52 at +2.68R.
**After exit (30 min).** Best +4.83R at 11:19, worst +1.27R. Kept going the trade's way after the target.
**Verdict.** Worked as designed. Nothing to change on this trade. 

### 10. QQQ-EMA50 CALL QQQ261012C00749000: +380 (target)

Signal 10:13 @ 749.37 · in 3.30 (q 3.31/3.32) · stop 748.80 / tgt 750.51 · ATR 0.570 (7.61 bp) · out 10:56 3.68 (q 3.68/3.7) at +2.07R · 43m · best +2.07 / worst -0.83

**Setup.** price closed across EMA50; side = cross direction (CALL); EMA9/21 pointed the other way. VWAP -1.5 ATR, EMA50 +0.5 ATR (+ = on trade's side). Prior 5 min -0.8 ATR. 
**Path.** Best +2.07R at 10:56 (passed +1R at 10:30). Worst close -0.83R at 10:16. Target triggered on the 10:56 close, filled 10:56 at +2.07R.
**After exit (30 min).** Best +2.52R at 10:57, worst -0.45R. Kept going the trade's way after the target.
**Verdict.** Worked as designed. Nothing to change on this trade. Against VWAP; a VWAP-side rule would have flipped this winner.

### 11. QQQ-VWAP CALL QQQ261012C00750000: -310 (stop)

Signal 10:31 @ 750.34 · in 3.10 (q 3.1/3.12) · stop 749.91 / tgt 751.19 · ATR 0.426 (5.67 bp) · out 10:40 2.79 (q 2.79/2.8) at -1.22R · 9m · best +0.40 / worst -1.22

**Setup.** price closed across VWAP; side = cross direction (CALL); EMA9/21 agreed. VWAP +0.5 ATR, EMA50 +2.4 ATR (+ = on trade's side). Prior 5 min +1.6 ATR = chasing. Also open on QQQ: QQQ-EMA50 CALL.
**Path.** Best +0.40R at 10:35. Below entry from 10:32. Worst close -1.22R at 10:40. Stop triggered on the 10:40 close (-1.22R), filled 10:40 at -1.22R (0.22R past the stop line).
**After exit (30 min).** Best +1.10R at 10:57, worst -2.99R. Kept going against the trade; the stop saved a bigger loss.
**Verdict.** Chopped out: small favour, then stopped. Different: no tested rule saves it.

### 12. IWM-EMA50 PUT IWM261012P00278000: +180 (target)

Signal 10:32 @ 278.38 · in 0.98 (q 0.96/0.98) · stop 278.55 / tgt 278.03 · ATR 0.173 (6.22 bp) · out 10:49 1.16 (q 1.16/1.18) at +2.28R · 17m · best +2.28 / worst -0.50

**Setup.** price closed across EMA50; side = cross direction (PUT); EMA9/21 agreed. VWAP +0.1 ATR, EMA50 +0.3 ATR (+ = on trade's side). Prior 5 min +1.4 ATR = chasing. Also open on IWM: IWM-VWAP PUT.
**Path.** Best +2.28R at 10:49 (passed +1R at 10:39). Worst close -0.50R at 10:33. Target triggered on the 10:49 close, filled 10:49 at +2.28R.
**After exit (30 min).** Best +2.45R at 10:50, worst -2.60R. Reversed after the target; exit timing was good.
**Verdict.** Worked as designed. Nothing to change on this trade. 

### 13. IWM-VWAP PUT IWM261012P00278000: +190 (target)

Signal 10:32 @ 278.38 · in 0.98 (q 0.97/0.99) · stop 278.55 / tgt 278.03 · ATR 0.173 (6.22 bp) · out 10:49 1.17 (q 1.16/1.18) at +2.28R · 17m · best +2.28 / worst -0.50

**Setup.** price closed across VWAP; side = cross direction (PUT); EMA9/21 agreed. VWAP +0.1 ATR, EMA50 +0.3 ATR (+ = on trade's side). Prior 5 min +1.4 ATR = chasing. Also open on IWM: IWM-EMA50 PUT.
**Path.** Best +2.28R at 10:49 (passed +1R at 10:39). Worst close -0.50R at 10:33. Target triggered on the 10:49 close, filled 10:49 at +2.28R.
**After exit (30 min).** Best +2.45R at 10:50, worst -2.60R. Reversed after the target; exit timing was good.
**Verdict.** Worked as designed. Nothing to change on this trade. 

### 14. SPY-EMA50 PUT SPY261012P00776000: -110 (stop)

Signal 10:42 @ 775.99 · in 1.96 (q 1.95/1.96) · stop 776.20 / tgt 775.56 · ATR 0.213 (2.74 bp) · out 10:45 1.85 (q 1.84/1.85) at -1.23R · 3m · best +0.00 / worst -1.23

**Setup.** price closed across EMA50; side = cross direction (PUT); EMA9/21 agreed. VWAP +0.8 ATR, EMA50 +0.6 ATR (+ = on trade's side). Prior 5 min +1.4 ATR = chasing. ATR only 2.74 bp, stop 0.21 wide. Also open on SPY: SPY-VWAP CALL.
**Path.** Never moved in its favour. Below entry from 10:43. Worst close -1.23R at 10:45. Stop triggered on the 10:45 close (-1.23R), filled 10:45 at -1.23R (0.23R past the stop line).
**After exit (30 min).** Best -1.71R at 10:48, worst -7.09R. Kept going against the trade; the stop saved a bigger loss.
**Verdict.** Chased a move that was already done. Different: no tested rule saves it.

### 15. IWM-EMA50 CALL IWM261012C00278000: +110 (target)

Signal 10:52 @ 278.34 · in 1.29 (q 1.29/1.31) · stop 278.18 / tgt 278.66 · ATR 0.161 (5.79 bp) · out 11:03 1.40 (q 1.4/1.42) at +2.05R · 11m · best +2.05 / worst -0.90

**Setup.** price closed across EMA50; side = cross direction (CALL); EMA9/21 pointed the other way. VWAP +0.0 ATR, EMA50 +0.3 ATR (+ = on trade's side). Prior 5 min +1.2 ATR = chasing. Also open on IWM: IWM-VWAP CALL.
**Path.** Best +2.05R at 11:03 (passed +1R at 11:03). Worst close -0.90R at 10:55. Target triggered on the 11:03 close, filled 11:03 at +2.05R.
**After exit (30 min).** Best +3.26R at 11:32, worst -0.59R. Kept going the trade's way after the target.
**Verdict.** Worked as designed. Nothing to change on this trade. 

### 16. IWM-VWAP CALL IWM261012C00278000: +220 (target)

Signal 10:52 @ 278.34 · in 1.31 (q 1.3/1.32) · stop 278.18 / tgt 278.66 · ATR 0.161 (5.79 bp) · out 11:16 1.53 (q 1.53/1.55) at +2.48R · 24m · best +2.48 / worst -0.90

**Setup.** price closed across VWAP; side = cross direction (CALL); EMA9/21 pointed the other way. VWAP +0.0 ATR, EMA50 +0.3 ATR (+ = on trade's side). Prior 5 min +1.2 ATR = chasing. Also open on IWM: IWM-EMA50 CALL.
**Path.** Best +2.48R at 11:16 (passed +1R at 11:03). Worst close -0.90R at 10:55. Target triggered on the 11:16 close, filled 11:16 at +2.48R.
**After exit (30 min).** Best +3.26R at 11:32, worst +1.12R. Kept going the trade's way after the target.
**Verdict.** Worked as designed. Nothing to change on this trade. 

### 17. SPY-RANGE CALL SPY261012C00777000: +280 (target)

Signal 10:52 @ 777.00 · in 1.91 (q 1.9/1.91) · stop 776.77 / tgt 777.48 · ATR 0.236 (3.04 bp) · out 10:59 2.19 (q 2.19/2.21) at +2.10R · 7m · best +2.10 / worst +0.00

**Setup.** price closed outside the 9:30-9:44 range; side = break direction (CALL); EMA9/21 agreed. VWAP +3.4 ATR, EMA50 +3.2 ATR (+ = on trade's side). Prior 5 min +1.9 ATR = chasing. Also open on SPY: SPY-VWAP CALL.
**Path.** Best +2.10R at 10:59 (passed +1R at 10:57). Worst close +0.13R at 10:54. Target triggered on the 10:59 close, filled 10:59 at +2.10R.
**After exit (30 min).** Best +2.84R at 11:19, worst -1.86R. Kept going the trade's way after the target.
**Verdict.** Worked as designed. Nothing to change on this trade. 

### 18. IWM-EMA50 PUT IWM261012P00278000: -190 (stop)

Signal 11:07 @ 278.33 · in 1.00 (q 0.99/1.01) · stop 278.49 / tgt 278.01 · ATR 0.159 (5.71 bp) · out 11:16 0.81 (q 0.81/0.82) at -2.58R · 9m · best +0.54 / worst -2.58

**Setup.** price closed across EMA50; side = cross direction (PUT); EMA9/21 pointed the other way. VWAP +0.1 ATR, EMA50 +0.0 ATR (+ = on trade's side). Prior 5 min +0.2 ATR. Also open on IWM: IWM-VWAP CALL.
**Path.** Best +0.54R at 11:08. Below entry from 11:16. Worst close -2.58R at 11:16. Stop triggered on the 11:16 close (-2.58R), filled 11:16 at -2.58R (1.58R past the stop line).
**After exit (30 min).** Best -1.20R at 11:46, worst -3.37R. Kept going against the trade; the stop saved a bigger loss.
**Verdict.** Chopped out: small favour, then stopped. Different: EMA9/21 side (CALL) +2.6R; fill at stop line saves 1.58R.

### 19. QQQ-EMA50 PUT QQQ261012P00750000: -290 (stop)

Signal 11:07 @ 749.90 · in 2.98 (q 2.97/2.99) · stop 750.30 / tgt 749.11 · ATR 0.396 (5.27 bp) · out 11:27 2.69 (q 2.68/2.7) at -1.04R · 20m · best +1.98 / worst -1.04

**Setup.** price closed across EMA50; side = cross direction (PUT); EMA9/21 pointed the other way. VWAP +0.6 ATR, EMA50 +0.2 ATR (+ = on trade's side). Prior 5 min +1.4 ATR = chasing. Also open on QQQ: QQQ-VWAP PUT.
**Path.** Best +1.98R at 11:09 (passed +1R at 11:09). Below entry from 11:18. Worst close -1.04R at 11:27. Stop triggered on the 11:27 close (-1.04R), filled 11:27 at -1.04R.
**After exit (30 min).** Best +1.50R at 11:36, worst -1.77R. Kept going against the trade; the stop saved a bigger loss.
**Verdict.** Had 1R+ profit and gave it all back. Different: 1R target +2.0R; EMA9/21 side (CALL) -2.0R; 10 min time stop +0.3R.

### 20. QQQ-VWAP PUT QQQ261012P00750000: -300 (stop)

Signal 11:07 @ 749.90 · in 2.99 (q 2.98/2.99) · stop 750.30 / tgt 749.11 · ATR 0.396 (5.27 bp) · out 11:27 2.69 (q 2.68/2.69) at -1.04R · 20m · best +1.98 / worst -1.04

**Setup.** price closed across VWAP; side = cross direction (PUT); EMA9/21 pointed the other way. VWAP +0.6 ATR, EMA50 +0.2 ATR (+ = on trade's side). Prior 5 min +1.4 ATR = chasing. Also open on QQQ: QQQ-EMA50 PUT.
**Path.** Best +1.98R at 11:09 (passed +1R at 11:09). Below entry from 11:18. Worst close -1.04R at 11:27. Stop triggered on the 11:27 close (-1.04R), filled 11:27 at -1.04R.
**After exit (30 min).** Best +1.50R at 11:36, worst -1.77R. Kept going against the trade; the stop saved a bigger loss.
**Verdict.** Had 1R+ profit and gave it all back. Different: 1R target +2.0R; EMA9/21 side (CALL) -2.0R; 10 min time stop +0.3R.

### 21. SPY-EMA50 PUT SPY261012P00777000: -390 (stop)

Signal 11:09 @ 776.57 · in 2.17 (q 2.17/2.18) · stop 776.81 / tgt 776.07 · ATR 0.247 (3.18 bp) · out 11:16 1.78 (q 1.78/1.79) at -3.15R · 7m · best +0.00 / worst -3.15

**Setup.** price closed across EMA50; side = cross direction (PUT); EMA9/21 pointed the other way. VWAP -0.8 ATR, EMA50 +0.5 ATR (+ = on trade's side). Prior 5 min +2.5 ATR = chasing. 
**Path.** Never moved in its favour. Below entry from 11:16. Worst close -3.15R at 11:16. Stop triggered on the 11:16 close (-3.15R), filled 11:16 at -3.15R (2.15R past the stop line).
**After exit (30 min).** Best -1.03R at 11:34, worst -4.49R. Kept going against the trade; the stop saved a bigger loss.
**Verdict.** Chased a move that was already done. Different: VWAP side (CALL) +3.2R; EMA9/21 side (CALL) +3.2R; fill at stop line saves 2.15R.

### 22. IWM-RANGE CALL IWM261012C00279000: -60 (stop)

Signal 11:32 @ 278.87 · in 1.02 (q 1.01/1.03) · stop 278.76 / tgt 279.08 · ATR 0.106 (3.82 bp) · out 11:34 0.96 (q 0.96/0.97) at -1.27R · 2m · best +0.00 / worst -1.27

**Setup.** price closed outside the 9:30-9:44 range; side = break direction (CALL); EMA9/21 agreed. VWAP +4.5 ATR, EMA50 +2.6 ATR (+ = on trade's side). Prior 5 min +0.6 ATR. 
**Path.** Never moved in its favour. Below entry from 11:33. Worst close -1.27R at 11:34. Stop triggered on the 11:34 close (-1.27R), filled 11:34 at -1.27R (0.27R past the stop line).
**After exit (30 min).** Best -0.23R at 11:37, worst -3.43R. Kept going against the trade; the stop saved a bigger loss.
**Verdict.** Wrong side from the first minute. Different: fill at stop line saves 0.27R.

### 23. SPY-EMA50 PUT SPY261012P00777000: -80 (stop)

Signal 11:33 @ 776.98 · in 1.86 (q 1.86/1.87) · stop 777.16 / tgt 776.60 · ATR 0.187 (2.41 bp) · out 11:40 1.78 (q 1.76/1.77) at -1.20R · 7m · best +0.83 / worst -1.20

**Setup.** price closed across EMA50; side = cross direction (PUT); EMA9/21 agreed. VWAP -2.5 ATR, EMA50 +0.4 ATR (+ = on trade's side). Prior 5 min +2.2 ATR = chasing. ATR only 2.41 bp, stop 0.19 wide. 
**Path.** Best +0.83R at 11:34. Below entry from 11:39. Worst close -1.20R at 11:40. Stop triggered on the 11:40 close (-1.20R), filled 11:40 at -1.20R (0.20R past the stop line).
**After exit (30 min).** Best +0.51R at 12:03, worst -3.50R. Kept going against the trade; the stop saved a bigger loss.
**Verdict.** Chopped out: small favour, then stopped. Different: VWAP side (CALL) +2.8R.

### 24. SPY-RANGE CALL SPY261012C00777000: +210 (target)

Signal 11:35 @ 776.88 · in 1.83 (q 1.82/1.83) · stop 776.69 / tgt 777.27 · ATR 0.191 (2.46 bp) · out 11:51 2.04 (q 2.03/2.04) at +2.43R · 16m · best +2.43 / worst -0.29

**Setup.** price closed outside the 9:30-9:44 range; side = break direction (CALL); EMA9/21 pointed the other way. VWAP +1.9 ATR, EMA50 -0.8 ATR (+ = on trade's side). Prior 5 min -1.0 ATR. ATR only 2.46 bp, stop 0.19 wide. Also open on SPY: SPY-EMA50 PUT.
**Path.** Best +2.43R at 11:51 (passed +1R at 11:40). Worst close -0.29R at 11:36. Target triggered on the 11:51 close, filled 11:51 at +2.43R.
**After exit (30 min).** Best +5.69R at 12:18, worst -0.03R. Kept going the trade's way after the target.
**Verdict.** Worked as designed. Nothing to change on this trade. 

### 25. QQQ-EMA50 CALL QQQ261012C00750000: +150 (target)

Signal 11:39 @ 750.01 · in 2.83 (q 2.82/2.83) · stop 749.67 / tgt 750.70 · ATR 0.343 (4.57 bp) · out 11:58 2.98 (q 2.96/2.97) at +2.01R · 19m · best +2.01 / worst -0.40

**Setup.** price closed across EMA50; side = cross direction (CALL); EMA9/21 pointed the other way. VWAP -0.2 ATR, EMA50 +0.6 ATR (+ = on trade's side). Prior 5 min +1.9 ATR = chasing. 
**Path.** Best +2.01R at 11:58 (passed +1R at 11:51). Worst close -0.40R at 11:46. Target triggered on the 11:58 close, filled 11:58 at +2.01R.
**After exit (30 min).** Best +2.62R at 12:17, worst -1.41R. Kept going the trade's way after the target.
**Verdict.** Worked as designed. Nothing to change on this trade. Against VWAP; a VWAP-side rule would have flipped this winner.

### 26. IWM-EMA50 PUT IWM261012P00279000: -60 (stop)

Signal 11:41 @ 278.61 · in 1.28 (q 1.27/1.29) · stop 278.72 / tgt 278.39 · ATR 0.109 (3.9 bp) · out 11:59 1.22 (q 1.21/1.23) at -1.01R · 18m · best +1.01 / worst -1.01

**Setup.** price closed across EMA50; side = cross direction (PUT); EMA9/21 agreed. VWAP -1.9 ATR, EMA50 +0.2 ATR (+ = on trade's side). Prior 5 min +1.5 ATR = chasing. 
**Path.** Best +1.01R at 11:50 (passed +1R at 11:50). Below entry from 11:43. Worst close -1.01R at 11:59. Stop triggered on the 11:59 close (-1.01R), filled 11:59 at -1.01R.
**After exit (30 min).** Best +0.64R at 12:26, worst -1.56R. Kept going against the trade; the stop saved a bigger loss.
**Verdict.** Had 1R+ profit and gave it all back. Different: 1R target +1.0R; VWAP side (CALL) -1.0R; 10 min time stop -0.5R.

### 27. QQQ-VWAP CALL QQQ261012C00750000: -170 (stop)

Signal 11:43 @ 750.27 · in 2.86 (q 2.87/2.88) · stop 749.94 / tgt 750.93 · ATR 0.331 (4.41 bp) · out 11:46 2.69 (q 2.69/2.7) at -1.19R · 3m · best +0.00 / worst -1.19

**Setup.** price closed across VWAP; side = cross direction (CALL); EMA9/21 agreed. VWAP +0.6 ATR, EMA50 +1.2 ATR (+ = on trade's side). Prior 5 min +1.9 ATR = chasing. Also open on QQQ: QQQ-EMA50 CALL.
**Path.** Never moved in its favour. Below entry from 11:44. Worst close -1.19R at 11:46. Stop triggered on the 11:46 close (-1.19R), filled 11:46 at -1.19R (0.19R past the stop line).
**After exit (30 min).** Best +1.66R at 12:07, worst -2.24R. Kept going against the trade; the stop saved a bigger loss.
**Verdict.** Chased a move that was already done. Different: no tested rule saves it.

### 28. SPY-EMA50 PUT SPY261012P00777000: -130 (stop)

Signal 11:46 @ 776.92 · in 1.88 (q 1.87/1.88) · stop 777.11 / tgt 776.54 · ATR 0.192 (2.47 bp) · out 11:49 1.75 (q 1.75/1.76) at -1.46R · 3m · best +0.00 / worst -1.46

**Setup.** price closed across EMA50; side = cross direction (PUT); EMA9/21 agreed. VWAP -2.0 ATR, EMA50 +0.7 ATR (+ = on trade's side). Prior 5 min +1.3 ATR = chasing. ATR only 2.47 bp, stop 0.19 wide. Also open on SPY: SPY-RANGE CALL.
**Path.** Never moved in its favour. Below entry from 11:47. Worst close -1.46R at 11:49. Stop triggered on the 11:49 close (-1.46R), filled 11:49 at -1.46R (0.46R past the stop line).
**After exit (30 min).** Best +0.21R at 12:03, worst -5.47R. Kept going against the trade; the stop saved a bigger loss.
**Verdict.** Chased a move that was already done. Different: VWAP side (CALL) +2.2R; fill at stop line saves 0.46R.

### 29. QQQ-VWAP CALL QQQ261012C00750000: -310 (stop)

Signal 11:48 @ 750.08 · in 2.79 (q 2.78/2.79) · stop 749.77 / tgt 750.70 · ATR 0.311 (4.15 bp) · out 12:01 2.48 (q 2.48/2.49) at -1.77R · 13m · best +2.00 / worst -1.77

**Setup.** price closed across VWAP; side = cross direction (CALL); EMA9/21 agreed. VWAP +0.0 ATR, EMA50 +0.6 ATR (+ = on trade's side). Prior 5 min -0.6 ATR. Also open on QQQ: QQQ-EMA50 CALL.
**Path.** Best +2.00R at 11:58 (passed +1R at 11:52). Below entry from 12:00. Worst close -1.77R at 12:01. Stop triggered on the 12:01 close (-1.77R), exit failed 1x, filled 12:01 at -1.77R (0.77R past the stop line).
**After exit (30 min).** Best +2.68R at 12:17, worst -1.74R. Price reached the target after the stop: direction right, stop too tight for the noise.
**Verdict.** Right direction, stopped out by noise first. Different: 1R target +1.5R; 10 min time stop +2.0R; fill at stop line saves 0.77R; the exit order must not fail.

### 30. QQQ-EMA50 PUT QQQ261012P00750000: +350 (target)

Signal 12:00 @ 750.07 · in 2.69 (q 2.68/2.69) · stop 750.33 / tgt 749.53 · ATR 0.267 (3.55 bp) · out 12:01 3.04 (q 3.04/3.05) at +2.01R · 1m · best +2.01 / worst +0.00

**Setup.** price closed across EMA50; side = cross direction (PUT); EMA9/21 pointed the other way. VWAP +0.1 ATR, EMA50 +0.2 ATR (+ = on trade's side). Prior 5 min +1.5 ATR = chasing. Also open on QQQ: QQQ-VWAP CALL.
**Path.** Best +2.01R at 12:01 (passed +1R at 12:01). Worst close +2.01R at 12:01. Target triggered on the 12:01 close, filled 12:01 at +2.01R.
**After exit (30 min).** Best +1.97R at 12:02, worst -3.19R. Reversed after the target; exit timing was good.
**Verdict.** Worked as designed. Nothing to change on this trade. 

### 31. IWM-EMA50 PUT IWM261012P00279000: -70 (stop)

Signal 12:01 @ 278.55 · in 1.28 (q 1.27/1.28) · stop 278.63 / tgt 278.37 · ATR 0.086 (3.08 bp) · out 12:06 1.21 (q 1.21/1.23) at -1.46R · 5m · best +0.00 / worst -1.46

**Setup.** price closed across EMA50; side = cross direction (PUT); EMA9/21 agreed. VWAP -1.5 ATR, EMA50 +1.0 ATR (+ = on trade's side). Prior 5 min +1.7 ATR = chasing. 
**Path.** Never moved in its favour. Below entry from 12:03. Worst close -1.46R at 12:06. Stop triggered on the 12:06 close (-1.46R), filled 12:06 at -1.46R (0.46R past the stop line).
**After exit (30 min).** Best +0.06R at 12:26, worst -4.90R. Kept going against the trade; the stop saved a bigger loss.
**Verdict.** Chased a move that was already done. Different: VWAP side (CALL) +2.7R; fill at stop line saves 0.46R.

### 32. SPY-EMA50 PUT SPY261012P00777000: -250 (stop)

Signal 12:01 @ 776.91 · in 1.90 (q 1.9/1.91) · stop 777.08 / tgt 776.56 · ATR 0.174 (2.23 bp) · out 12:05 1.65 (q 1.65/1.66) at -2.53R · 4m · best +0.17 / worst -2.53

**Setup.** price closed across EMA50; side = cross direction (PUT); EMA9/21 pointed the other way. VWAP -1.8 ATR, EMA50 +1.6 ATR (+ = on trade's side). Prior 5 min +3.6 ATR = chasing. ATR only 2.23 bp, stop 0.17 wide. 
**Path.** Best +0.17R at 12:03. Below entry from 12:02. Worst close -2.53R at 12:05. Stop triggered on the 12:05 close (-2.53R), filled 12:05 at -2.53R (1.53R past the stop line).
**After exit (30 min).** Best -3.11R at 12:11, worst -7.03R. Kept going against the trade; the stop saved a bigger loss.
**Verdict.** Chased a move that was already done. Different: VWAP side (CALL) +2.5R; EMA9/21 side (CALL) +2.5R; fill at stop line saves 1.53R.

### 33. IWM-EMA50 PUT IWM261012P00279000: -90 (stop)

Signal 12:08 @ 278.57 · in 1.28 (q 1.28/1.29) · stop 278.66 / tgt 278.40 · ATR 0.086 (3.08 bp) · out 12:16 1.19 (q 1.19/1.2) at -1.28R · 8m · best +0.29 / worst -1.28

**Setup.** price closed across EMA50; side = cross direction (PUT); EMA9/21 agreed. VWAP -1.8 ATR, EMA50 +0.6 ATR (+ = on trade's side). Prior 5 min -0.1 ATR. 
**Path.** Best +0.29R at 12:09. Below entry from 12:11. Worst close -1.28R at 12:16. Stop triggered on the 12:16 close (-1.28R), filled 12:16 at -1.28R (0.28R past the stop line).
**After exit (30 min).** Best +0.41R at 12:26, worst -4.54R. Kept going against the trade; the stop saved a bigger loss.
**Verdict.** Chopped out: small favour, then stopped. Different: VWAP side (CALL) +2.3R; fill at stop line saves 0.28R.

### 34. IWM-EMA50 CALL IWM261012C00279000: +80 (target)

Signal 12:28 @ 278.69 · in 0.88 (q 0.88/0.89) · stop 278.61 / tgt 278.83 · ATR 0.070 (2.52 bp) · out 12:31 0.96 (q 0.96/0.98) at +2.84R · 3m · best +2.84 / worst +0.00

**Setup.** price closed across EMA50; side = cross direction (CALL); EMA9/21 pointed the other way. VWAP +3.6 ATR, EMA50 +0.8 ATR (+ = on trade's side). Prior 5 min +1.1 ATR = chasing. ATR only 2.52 bp, stop 0.07 wide. 
**Path.** Best +2.84R at 12:31 (passed +1R at 12:29). Worst close +1.35R at 12:29. Target triggered on the 12:31 close, filled 12:31 at +2.84R.
**After exit (30 min).** Best +4.71R at 12:52, worst +1.78R. Kept going the trade's way after the target.
**Verdict.** Worked as designed. Nothing to change on this trade. 

### 35. IWM-RANGE CALL IWM261012C00279000: -20 (stop)

Signal 12:31 @ 278.88 · in 0.97 (q 0.96/0.97) · stop 278.81 / tgt 279.03 · ATR 0.073 (2.62 bp) · out 12:43 0.95 (q 0.95/0.96) at -1.03R · 12m · best +1.10 / worst -1.03

**Setup.** price closed outside the 9:30-9:44 range; side = break direction (CALL); EMA9/21 agreed. VWAP +6.2 ATR, EMA50 +3.2 ATR (+ = on trade's side). Prior 5 min +4.7 ATR = chasing. ATR only 2.62 bp, stop 0.07 wide. Also open on IWM: IWM-EMA50 CALL.
**Path.** Best +1.10R at 12:32 (passed +1R at 12:32). Below entry from 12:34. Worst close -1.03R at 12:43. Stop triggered on the 12:43 close (-1.03R), filled 12:43 at -1.03R.
**After exit (30 min).** Best +2.05R at 13:04, worst -0.82R. Price reached the target after the stop: direction right, stop too tight for the noise.
**Verdict.** Right direction, stopped out by noise first. Different: 1R target +1.1R; 10 min time stop +0.3R.

### 36. QQQ-EMA50 PUT QQQ261012P00750000: -190 (stop)

Signal 12:36 @ 750.47 · in 2.49 (q 2.49/2.5) · stop 750.69 / tgt 750.04 · ATR 0.215 (2.87 bp) · out 12:47 2.30 (q 2.3/2.31) at -1.44R · 11m · best +1.16 / worst -1.44

**Setup.** price closed across EMA50; side = cross direction (PUT); EMA9/21 pointed the other way. VWAP -1.6 ATR, EMA50 +0.1 ATR (+ = on trade's side). Prior 5 min +1.9 ATR = chasing. ATR only 2.87 bp, stop 0.22 wide. 
**Path.** Best +1.16R at 12:43 (passed +1R at 12:43). Below entry from 12:38. Worst close -1.44R at 12:47. Stop triggered on the 12:47 close (-1.44R), filled 12:47 at -1.44R (0.44R past the stop line).
**After exit (30 min).** Best +1.06R at 13:11, worst -3.92R. Kept going against the trade; the stop saved a bigger loss.
**Verdict.** Had 1R+ profit and gave it all back. Different: 1R target +1.2R; VWAP side (CALL) -1.2R; EMA9/21 side (CALL) -1.2R; 10 min time stop -0.5R; fill at stop line saves 0.44R.

### 37. IWM-RANGE CALL IWM261012C00279000: -100 (stop)

Signal 12:46 @ 278.92 · in 1.02 (q 1.0/1.02) · stop 278.85 / tgt 279.04 · ATR 0.065 (2.32 bp) · out 13:14 0.92 (q 0.91/0.93) at -1.78R · 28m · best +1.86 / worst -1.78

**Setup.** price closed outside the 9:30-9:44 range; side = break direction (CALL); EMA9/21 agreed. VWAP +7.2 ATR, EMA50 +2.5 ATR (+ = on trade's side). Prior 5 min +0.1 ATR. ATR only 2.32 bp, stop 0.06 wide. 
**Path.** Best +1.86R at 13:04 (passed +1R at 12:52). Below entry from 12:48. Worst close -1.78R at 13:14. Stop triggered on the 13:14 close (-1.78R), filled 13:14 at -1.78R (0.78R past the stop line).
**After exit (30 min).** Best +2.71R at 13:44, worst -1.78R. Price reached the target after the stop: direction right, stop too tight for the noise.
**Verdict.** Right direction, stopped out by noise first. Different: 1R target +1.6R; 10 min time stop +1.0R; fill at stop line saves 0.78R.

### 38. QQQ-EMA50 PUT QQQ261012P00751000: +230 (target)

Signal 12:59 @ 750.65 · in 2.83 (q 2.83/2.85) · stop 750.85 / tgt 750.24 · ATR 0.204 (2.71 bp) · out 13:19 3.06 (q 3.06/3.08) at +2.49R · 20m · best +2.49 / worst -0.50

**Setup.** price closed across EMA50; side = cross direction (PUT); EMA9/21 pointed the other way. VWAP -1.9 ATR, EMA50 +0.0 ATR (+ = on trade's side). Prior 5 min +2.3 ATR = chasing. ATR only 2.71 bp, stop 0.20 wide. 
**Path.** Best +2.49R at 13:19 (passed +1R at 13:07). Worst close -0.50R at 13:02. Target triggered on the 13:19 close, filled 13:19 at +2.49R.
**After exit (30 min).** Best +1.76R at 13:23, worst -0.64R. Reversed after the target; exit timing was good.
**Verdict.** Worked as designed. Nothing to change on this trade. Against VWAP; a VWAP-side rule would have flipped this winner.

### 39. IWM-EMA50 PUT IWM261012P00279000: -50 (stop)

Signal 13:11 @ 278.88 · in 1.08 (q 1.07/1.08) · stop 278.94 / tgt 278.76 · ATR 0.059 (2.13 bp) · out 13:20 1.03 (q 1.03/1.05) at -1.52R · 9m · best +1.35 / worst -1.52

**Setup.** price closed across EMA50; side = cross direction (PUT); EMA9/21 pointed the other way. VWAP -6.5 ATR, EMA50 +0.1 ATR (+ = on trade's side). Prior 5 min +1.9 ATR = chasing. ATR only 2.13 bp, stop 0.06 wide. Also open on IWM: IWM-RANGE CALL.
**Path.** Best +1.35R at 13:14 (passed +1R at 13:14). Below entry from 13:12. Worst close -1.52R at 13:20. Stop triggered on the 13:20 close (-1.52R), filled 13:20 at -1.52R (0.52R past the stop line).
**After exit (30 min).** Best +0.88R at 13:28, worst -3.88R. Kept going against the trade; the stop saved a bigger loss.
**Verdict.** Had 1R+ profit and gave it all back. Different: 1R target +1.3R; VWAP side (CALL) -1.3R; EMA9/21 side (CALL) -1.3R; fill at stop line saves 0.52R.

### 40. IWM-RANGE CALL IWM261012C00279000: +50 (target)

Signal 13:18 @ 278.88 · in 0.96 (q 0.95/0.96) · stop 278.81 / tgt 279.01 · ATR 0.067 (2.4 bp) · out 13:40 1.01 (q 1.01/1.02) at +2.47R · 22m · best +2.47 / worst -0.78

**Setup.** price closed outside the 9:30-9:44 range; side = break direction (CALL); EMA9/21 pointed the other way. VWAP +5.6 ATR, EMA50 +0.0 ATR (+ = on trade's side). Prior 5 min +0.1 ATR. ATR only 2.4 bp, stop 0.07 wide. Also open on IWM: IWM-EMA50 PUT.
**Path.** Best +2.47R at 13:40 (passed +1R at 13:20). Worst close -0.78R at 13:28. Target triggered on the 13:40 close, filled 13:40 at +2.47R.
**After exit (30 min).** Best +7.26R at 14:01, worst +2.40R. Kept going the trade's way after the target.
**Verdict.** Worked as designed. Nothing to change on this trade. 

### 41. QQQ-EMA50 CALL QQQ261012C00751000: -90 (stop)

Signal 13:22 @ 750.61 · in 2.39 (q 2.38/2.39) · stop 750.42 / tgt 750.98 · ATR 0.189 (2.52 bp) · out 13:23 2.30 (q 2.28/2.29) at -1.66R · 1m · best +0.00 / worst -1.66

**Setup.** price closed across EMA50; side = cross direction (CALL); EMA9/21 pointed the other way. VWAP +1.8 ATR, EMA50 +0.4 ATR (+ = on trade's side). Prior 5 min +0.8 ATR. ATR only 2.52 bp, stop 0.19 wide. 
**Path.** Never moved in its favour. Below entry from 13:23. Worst close -1.66R at 13:23. Stop triggered on the 13:23 close (-1.66R), filled 13:23 at -1.66R (0.66R past the stop line).
**After exit (30 min).** Best +1.43R at 13:52, worst -1.08R. Drifted; no clear follow-through either way.
**Verdict.** Wrong side from the first minute. Different: EMA9/21 side (PUT) -1.2R; fill at stop line saves 0.66R.

### 42. IWM-EMA50 PUT IWM261012P00279000: -20 (stop)

Signal 13:23 @ 278.88 · in 1.07 (q 1.06/1.07) · stop 278.94 / tgt 278.75 · ATR 0.063 (2.26 bp) · out 13:33 1.05 (q 1.05/1.06) at -1.11R · 10m · best +0.83 / worst -1.19

**Setup.** price closed across EMA50; side = cross direction (PUT); EMA9/21 agreed. VWAP -5.9 ATR, EMA50 +0.2 ATR (+ = on trade's side). Prior 5 min -0.0 ATR. ATR only 2.26 bp, stop 0.06 wide. Also open on IWM: IWM-RANGE CALL.
**Path.** Best +0.83R at 13:28. Below entry from 13:24. Worst close -1.19R at 13:32. Stop triggered on the 13:33 close (-1.11R), exit failed 1x, filled 13:33 at -1.11R (0.11R past the stop line).
**After exit (30 min).** Best -0.00R at 13:35, worst -7.71R. Kept going against the trade; the stop saved a bigger loss.
**Verdict.** Chopped out: small favour, then stopped. Different: VWAP side (CALL) +2.6R; the exit order must not fail.

### 43. QQQ-EMA50 PUT QQQ261012P00750000: -160 (stop)

Signal 13:25 @ 750.42 · in 2.40 (q 2.41/2.42) · stop 750.62 / tgt 750.01 · ATR 0.204 (2.72 bp) · out 13:28 2.24 (q 2.23/2.24) at -1.76R · 3m · best +0.00 / worst -1.76

**Setup.** price closed across EMA50; side = cross direction (PUT); EMA9/21 agreed. VWAP -0.7 ATR, EMA50 +0.5 ATR (+ = on trade's side). Prior 5 min -0.5 ATR. ATR only 2.72 bp, stop 0.20 wide. 
**Path.** Never moved in its favour. Below entry from 13:26. Worst close -1.76R at 13:28. Stop triggered on the 13:28 close (-1.76R), filled 13:28 at -1.76R (0.76R past the stop line).
**After exit (30 min).** Best +0.10R at 13:36, worst -2.40R. Kept going against the trade; the stop saved a bigger loss.
**Verdict.** Wrong side from the first minute. Different: VWAP side (CALL) +2.0R; fill at stop line saves 0.76R.

### 44. QQQ-EMA50 PUT QQQ261012P00751000: -200 (stop)

Signal 13:33 @ 750.51 · in 2.93 (q 2.94/2.96) · stop 750.71 / tgt 750.10 · ATR 0.203 (2.71 bp) · out 13:43 2.73 (q 2.73/2.74) at -1.06R · 10m · best +0.54 / worst -1.06

**Setup.** price closed across EMA50; side = cross direction (PUT); EMA9/21 pointed the other way. VWAP -1.1 ATR, EMA50 +0.2 ATR (+ = on trade's side). Prior 5 min +1.3 ATR = chasing. ATR only 2.71 bp, stop 0.20 wide. 
**Path.** Best +0.54R at 13:36. Below entry from 13:34. Worst close -1.06R at 13:43. Stop triggered on the 13:43 close (-1.06R), filled 13:43 at -1.06R (0.06R past the stop line).
**After exit (30 min).** Best +0.35R at 13:45, worst -3.05R. Kept going against the trade; the stop saved a bigger loss.
**Verdict.** Chopped out: small favour, then stopped. Different: VWAP side (CALL) +2.1R; EMA9/21 side (CALL) +2.1R.

### 45. IWM-EMA50 PUT IWM261012P00279000: -50 (stop)

Signal 13:35 @ 278.88 · in 1.05 (q 1.04/1.06) · stop 278.95 / tgt 278.75 · ATR 0.065 (2.35 bp) · out 13:37 1.00 (q 1.0/1.02) at -1.83R · 2m · best +0.00 / worst -1.83

**Setup.** price closed across EMA50; side = cross direction (PUT); EMA9/21 pointed the other way. VWAP -5.5 ATR, EMA50 +0.2 ATR (+ = on trade's side). Prior 5 min -0.1 ATR. ATR only 2.35 bp, stop 0.07 wide. Also open on IWM: IWM-RANGE CALL.
**Path.** Never moved in its favour. Below entry from 13:36. Worst close -1.83R at 13:37. Stop triggered on the 13:37 close (-1.83R), filled 13:37 at -1.83R (0.83R past the stop line).
**After exit (30 min).** Best -1.22R at 13:39, worst -7.42R. Kept going against the trade; the stop saved a bigger loss.
**Verdict.** Wrong side from the first minute. Different: VWAP side (CALL) +2.5R; EMA9/21 side (CALL) +2.5R; fill at stop line saves 0.83R.

### 46. QQQ-EMA50 PUT QQQ261012P00750000: -140 (stop)

Signal 13:45 @ 750.44 · in 2.38 (q 2.38/2.39) · stop 750.62 / tgt 750.09 · ATR 0.177 (2.35 bp) · out 13:48 2.24 (q 2.23/2.24) at -1.42R · 3m · best +0.00 / worst -1.73

**Setup.** price closed across EMA50; side = cross direction (PUT); EMA9/21 pointed the other way. VWAP -0.9 ATR, EMA50 +0.6 ATR (+ = on trade's side). Prior 5 min +1.0 ATR = chasing. ATR only 2.35 bp, stop 0.18 wide. 
**Path.** Never moved in its favour. Below entry from 13:46. Worst close -1.73R at 13:47. Stop triggered on the 13:48 close (-1.42R), exit failed 1x, filled 13:48 at -1.42R (0.42R past the stop line).
**After exit (30 min).** Best -0.68R at 14:04, worst -3.91R. Kept going against the trade; the stop saved a bigger loss.
**Verdict.** Chased a move that was already done. Different: VWAP side (CALL) +2.2R; EMA9/21 side (CALL) +2.2R; fill at stop line saves 0.42R; the exit order must not fail.

### 47. QQQ-EMA50 PUT QQQ261012P00751000: -150 (stop)

Signal 14:03 @ 750.62 · in 2.74 (q 2.72/2.74) · stop 750.78 / tgt 750.32 · ATR 0.153 (2.04 bp) · out 14:08 2.59 (q 2.59/2.61) at -2.01R · 5m · best +0.40 / worst -2.01

**Setup.** price closed across EMA50; side = cross direction (PUT); EMA9/21 pointed the other way. VWAP -2.1 ATR, EMA50 +0.3 ATR (+ = on trade's side). Prior 5 min +1.9 ATR = chasing. ATR only 2.04 bp, stop 0.15 wide. 
**Path.** Best +0.40R at 14:04. Below entry from 14:06. Worst close -2.01R at 14:08. Stop triggered on the 14:08 close (-2.01R), filled 14:08 at -2.01R (1.01R past the stop line).
**After exit (30 min).** Best -1.75R at 14:35, worst -6.32R. Kept going against the trade; the stop saved a bigger loss.
**Verdict.** Chopped out: small favour, then stopped. Different: VWAP side (CALL) +2.0R; EMA9/21 side (CALL) +2.0R; fill at stop line saves 1.01R.

### 48. IWM-EMA50 PUT IWM261012P00279000: -30 (stop)

Signal 14:31 @ 279.20 · in 0.90 (q 0.88/0.9) · stop 279.24 / tgt 279.12 · ATR 0.041 (1.46 bp) · out 14:32 0.87 (q 0.87/0.88) at -1.35R · 1m · best +0.00 / worst -1.35

**Setup.** price closed across EMA50; side = cross direction (PUT); EMA9/21 agreed. VWAP -14.0 ATR, EMA50 +0.1 ATR (+ = on trade's side). Prior 5 min +2.0 ATR = chasing. ATR only 1.46 bp, stop 0.04 wide. 
**Path.** Never moved in its favour. Below entry from 14:32. Worst close -1.35R at 14:32. Stop triggered on the 14:32 close (-1.35R), filled 14:32 at -1.35R (0.35R past the stop line).
**After exit (30 min).** Best -1.23R at 14:33, worst -15.44R. Kept going against the trade; the stop saved a bigger loss.
**Verdict.** Chased a move that was already done. Different: VWAP side (CALL) +2.2R; fill at stop line saves 0.35R.

### 49. QQQ-EMA50 PUT QQQ261012P00751000: -130 (stop)

Signal 14:34 @ 751.02 · in 2.52 (q 2.51/2.52) · stop 751.16 / tgt 750.74 · ATR 0.139 (1.86 bp) · out 14:47 2.39 (q 2.39/2.4) at -2.70R · 13m · best +1.15 / worst -2.70

**Setup.** price closed across EMA50; side = cross direction (PUT); EMA9/21 pointed the other way. VWAP -4.6 ATR, EMA50 +0.1 ATR (+ = on trade's side). Prior 5 min +2.0 ATR = chasing. ATR only 1.86 bp, stop 0.14 wide. 
**Path.** Best +1.15R at 14:43 (passed +1R at 14:43). Below entry from 14:36. Worst close -2.70R at 14:47. Stop triggered on the 14:47 close (-2.70R), filled 14:47 at -2.70R (1.70R past the stop line).
**After exit (30 min).** Best -0.00R at 15:06, worst -6.53R. Kept going against the trade; the stop saved a bigger loss.
**Verdict.** Had 1R+ profit and gave it all back. Different: 1R target +1.1R; VWAP side (CALL) -1.1R; EMA9/21 side (CALL) -1.1R; 10 min time stop +0.6R; fill at stop line saves 1.70R.

### 50. QQQ-EMA50 PUT QQQ261012P00751000: -160 (stop)

Signal 14:56 @ 751.09 · in 2.51 (q 2.52/2.53) · stop 751.30 / tgt 750.67 · ATR 0.212 (2.82 bp) · out 15:12 2.35 (q 2.35/2.36) at -1.09R · 16m · best +0.33 / worst -1.09

**Setup.** price closed across EMA50; side = cross direction (PUT); EMA9/21 pointed the other way. VWAP -3.1 ATR, EMA50 +0.3 ATR (+ = on trade's side). Prior 5 min +4.0 ATR = chasing. ATR only 2.82 bp, stop 0.21 wide. 
**Path.** Best +0.33R at 15:06. Below entry from 14:57. Worst close -1.09R at 15:12. Stop triggered on the 15:12 close (-1.09R), filled 15:12 at -1.09R (0.09R past the stop line).
**After exit (30 min).** Best +1.51R at 15:40, worst -3.44R. Kept going against the trade; the stop saved a bigger loss.
**Verdict.** Chopped out: small favour, then stopped. Different: VWAP side (CALL) +2.0R; EMA9/21 side (CALL) +2.0R; 10 min time stop +0.3R.

### 51. IWM-EMA50 PUT IWM261012P00279000: +60 (target)

Signal 15:06 @ 279.36 · in 0.83 (q 0.82/0.83) · stop 279.44 / tgt 279.19 · ATR 0.083 (2.96 bp) · out 15:25 0.89 (q 0.89/0.9) at +2.06R · 19m · best +2.06 / worst -0.85

**Setup.** price closed across EMA50; side = cross direction (PUT); EMA9/21 agreed. VWAP -7.8 ATR, EMA50 +0.2 ATR (+ = on trade's side). Prior 5 min +1.6 ATR = chasing. ATR only 2.96 bp, stop 0.08 wide. 
**Path.** Best +2.06R at 15:25 (passed +1R at 15:17). Worst close -0.85R at 15:08. Target triggered on the 15:25 close, filled 15:25 at +2.06R.
**After exit (30 min).** Best +6.17R at 15:52, worst +1.45R. Kept going the trade's way after the target.
**Verdict.** Worked as designed. Nothing to change on this trade. Against VWAP; a VWAP-side rule would have flipped this winner.

### 52. QQQ-EMA50 PUT QQQ261012P00751000: +220 (target)

Signal 15:30 @ 751.37 · in 2.30 (q 2.3/2.32) · stop 751.52 / tgt 751.08 · ATR 0.145 (1.94 bp) · out 15:36 2.52 (q 2.52/2.54) at +2.87R · 6m · best +2.87 / worst -0.14

**Setup.** price closed across EMA50; side = cross direction (PUT); EMA9/21 pointed the other way. VWAP -5.6 ATR, EMA50 +0.2 ATR (+ = on trade's side). Prior 5 min +2.3 ATR = chasing. ATR only 1.94 bp, stop 0.15 wide. 
**Path.** Best +2.87R at 15:36 (passed +1R at 15:36). Worst close -0.14R at 15:35. Target triggered on the 15:36 close, filled 15:36 at +2.87R.
**After exit (30 min).** Best +4.47R at 15:45, worst -0.21R. Kept going the trade's way after the target.
**Verdict.** Worked as designed. Nothing to change on this trade. Against VWAP; a VWAP-side rule would have flipped this winner.


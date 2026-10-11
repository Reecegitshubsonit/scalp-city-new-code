**1. IWM-VWAP PUT 09:43→10:20 -230** (stop, gave back a 1r+ gain)
  + with VWAP (+0.8 ATR); ATR 10.0 bp; reached +2.0 ATR
  − exit filled -1.48 ATR (past stop)
  → take profit at 1R (+1.0R); breakeven stop (-0.4R); 10 min time stop (+0.3R); exit at the stop line

**2. IWM-EMA50 PUT 09:46→09:55 -260** (stop, chopped out)
  + with VWAP (+1.9 ATR); ATR 9.9 bp
  − exit filled -1.74 ATR (past stop); exit order failed first; fill outside bid/ask, P&L not real
  → breakeven stop (-1.3R); 10 min time stop (-1.3R); exit at the stop line

**3. IWM-RANGE PUT 09:47→09:52 -250** (stop, wrong side from the start)
  + with VWAP (+2.4 ATR); ATR 9.8 bp
  − never went its way; exit filled -1.29 ATR (past stop); exit order failed first
  → exit at the stop line

**4. QQQ-RANGE PUT 09:47→09:53 +190** (stop, wrong side from the start)
  + with VWAP (+2.9 ATR); ATR 9.9 bp
  − never went its way; fill outside bid/ask, P&L not real
  → no tested rule saves it

**5. QQQ-EMA50 PUT 09:52→09:53 +230** (stop, wrong side from the start)
  + with VWAP (+2.8 ATR); not extended (+0.2 ATR in 5 min); ATR 9.4 bp
  − never went its way; exit filled -1.36 ATR (past stop); fill outside bid/ask, P&L not real
  → exit at the stop line

**6. IWM-RANGE CALL 10:01→10:13 -130** (stop, chopped out)
  + with VWAP (+2.8 ATR); ATR 8.3 bp
  − chased: already ran +3.1 ATR in 5 min; another bot held the other side
  → 10 min time stop (-0.1R)

**7. QQQ-EMA50 PUT 10:02→10:07 -320** (stop, wrong side from the start)
  + with VWAP (+2.6 ATR); not extended (+0.7 ATR in 5 min); ATR 8.1 bp
  − never went its way; same idea as another bot, double size
  → no tested rule saves it

**8. QQQ-RANGE PUT 10:02→10:07 -270** (stop, wrong side from the start)
  + with VWAP (+2.6 ATR); not extended (+0.7 ATR in 5 min); ATR 8.1 bp
  − never went its way; same idea as another bot, double size
  → no tested rule saves it

**9. SPY-VWAP CALL 10:08→10:52 +360** (target, worked)
  + with VWAP (+0.4 ATR); not extended (+0.5 ATR in 5 min); ATR 4.0 bp; reached +2.7 ATR
  − none
  → keep as is

**10. QQQ-EMA50 CALL 10:13→10:56 +380** (target, worked)
  + not extended (-0.8 ATR in 5 min); ATR 7.6 bp; reached +2.1 ATR
  − against VWAP (-1.5 ATR)
  → keep as is

**11. QQQ-VWAP CALL 10:31→10:40 -310** (stop, chopped out)
  + with VWAP (+0.5 ATR); ATR 5.7 bp
  − chased: already ran +1.6 ATR in 5 min
  → no tested rule saves it

**12. IWM-EMA50 PUT 10:32→10:49 +180** (target, worked)
  + with VWAP (+0.1 ATR); ATR 6.2 bp; reached +2.3 ATR
  − chased: already ran +1.4 ATR in 5 min; same idea as another bot, double size
  → keep as is

**13. IWM-VWAP PUT 10:32→10:49 +190** (target, worked)
  + with VWAP (+0.1 ATR); ATR 6.2 bp; reached +2.3 ATR
  − chased: already ran +1.4 ATR in 5 min; same idea as another bot, double size
  → keep as is

**14. SPY-EMA50 PUT 10:42→10:45 -110** (stop, chased an extended move)
  + with VWAP (+0.8 ATR)
  − chased: already ran +1.4 ATR in 5 min; small ATR 2.7 bp, stop inside noise; never went its way; another bot held the other side
  → no tested rule saves it

**15. IWM-EMA50 CALL 10:52→11:03 +110** (target, worked)
  + with VWAP (+0.0 ATR); ATR 5.8 bp; reached +2.0 ATR
  − chased: already ran +1.2 ATR in 5 min; same idea as another bot, double size
  → keep as is

**16. IWM-VWAP CALL 10:52→11:16 +220** (target, worked)
  + with VWAP (+0.0 ATR); ATR 5.8 bp; reached +2.5 ATR
  − chased: already ran +1.2 ATR in 5 min; exit order failed first; same idea as another bot, double size
  → keep as is

**17. SPY-RANGE CALL 10:52→10:59 +280** (target, worked)
  + with VWAP (+3.4 ATR); reached +2.1 ATR
  − chased: already ran +1.9 ATR in 5 min
  → keep as is

**18. IWM-EMA50 PUT 11:07→11:16 -190** (stop, chopped out)
  + with VWAP (+0.1 ATR); not extended (+0.2 ATR in 5 min); ATR 5.7 bp
  − exit filled -2.58 ATR (past stop); another bot held the other side
  → exit at the stop line

**19. QQQ-EMA50 PUT 11:07→11:27 -290** (stop, gave back a 1r+ gain)
  + with VWAP (+0.6 ATR); ATR 5.3 bp; reached +2.0 ATR
  − chased: already ran +1.4 ATR in 5 min; same idea as another bot, double size
  → take profit at 1R (+2.0R); 10 min time stop (+0.3R)

**20. QQQ-VWAP PUT 11:07→11:27 -300** (stop, gave back a 1r+ gain)
  + with VWAP (+0.6 ATR); ATR 5.3 bp; reached +2.0 ATR
  − chased: already ran +1.4 ATR in 5 min; same idea as another bot, double size
  → take profit at 1R (+2.0R); 10 min time stop (+0.3R)

**21. SPY-EMA50 PUT 11:09→11:16 -390** (stop, chased an extended move)
  + none
  − against VWAP (-0.8 ATR); chased: already ran +2.5 ATR in 5 min; never went its way; exit filled -3.15 ATR (past stop)
  → VWAP side (CALL) wins +3.2R; exit at the stop line

**22. IWM-RANGE CALL 11:32→11:34 -60** (stop, wrong side from the start)
  + with VWAP (+4.5 ATR); not extended (+0.6 ATR in 5 min)
  − never went its way; exit filled -1.27 ATR (past stop)
  → exit at the stop line

**23. SPY-EMA50 PUT 11:33→11:40 -80** (stop, chopped out)
  + none
  − against VWAP (-2.5 ATR), fighting the day's move; chased: already ran +2.2 ATR in 5 min; small ATR 2.4 bp, stop inside noise
  → VWAP side (CALL) wins +2.8R

**24. SPY-RANGE CALL 11:35→11:51 +210** (target, worked)
  + with VWAP (+1.9 ATR); not extended (-1.0 ATR in 5 min); reached +2.4 ATR
  − small ATR 2.5 bp, stop inside noise; another bot held the other side
  → keep as is

**25. QQQ-EMA50 CALL 11:39→11:58 +150** (target, worked)
  + ATR 4.6 bp; reached +2.0 ATR
  − against VWAP (-0.2 ATR); chased: already ran +1.9 ATR in 5 min
  → keep as is

**26. IWM-EMA50 PUT 11:41→11:59 -60** (stop, gave back a 1r+ gain)
  + reached +1.0 ATR
  − against VWAP (-1.9 ATR); chased: already ran +1.5 ATR in 5 min
  → take profit at 1R (+1.0R); breakeven stop (-0.5R); 10 min time stop (-0.5R)

**27. QQQ-VWAP CALL 11:43→11:46 -170** (stop, chased an extended move)
  + with VWAP (+0.6 ATR); ATR 4.4 bp
  − chased: already ran +1.9 ATR in 5 min; never went its way
  → no tested rule saves it

**28. SPY-EMA50 PUT 11:46→11:49 -130** (stop, chased an extended move)
  + none
  − against VWAP (-2.0 ATR); chased: already ran +1.3 ATR in 5 min; small ATR 2.5 bp, stop inside noise; never went its way; exit filled -1.46 ATR (past stop); another bot held the other side
  → VWAP side (CALL) wins +2.2R; exit at the stop line

**29. QQQ-VWAP CALL 11:48→12:01 -310** (stop, right side, stopped first)
  + with VWAP (+0.0 ATR); not extended (-0.6 ATR in 5 min); ATR 4.2 bp; reached +2.0 ATR; direction was right (hit target after exit)
  − exit filled -1.77 ATR (past stop); exit order failed first; re-entry right after its own stop
  → take profit at 1R (+1.5R); breakeven stop (+2.0R); 10 min time stop (+2.0R); exit at the stop line

**30. QQQ-EMA50 PUT 12:00→12:01 +350** (target, worked)
  + with VWAP (+0.1 ATR); reached +2.0 ATR
  − chased: already ran +1.5 ATR in 5 min; another bot held the other side
  → keep as is

**31. IWM-EMA50 PUT 12:01→12:06 -70** (stop, chased an extended move)
  + none
  − against VWAP (-1.5 ATR); chased: already ran +1.7 ATR in 5 min; never went its way; exit filled -1.46 ATR (past stop); re-entry right after its own stop
  → VWAP side (CALL) wins +2.7R; exit at the stop line

**32. SPY-EMA50 PUT 12:01→12:05 -250** (stop, chased an extended move)
  + none
  − against VWAP (-1.8 ATR); chased: already ran +3.6 ATR in 5 min; small ATR 2.2 bp, stop inside noise; never went its way; exit filled -2.53 ATR (past stop)
  → VWAP side (CALL) wins +2.5R; exit at the stop line

**33. IWM-EMA50 PUT 12:08→12:16 -90** (stop, chopped out)
  + not extended (-0.1 ATR in 5 min)
  − against VWAP (-1.8 ATR); exit filled -1.28 ATR (past stop); re-entry right after its own stop
  → VWAP side (CALL) wins +2.3R; exit at the stop line

**34. IWM-EMA50 CALL 12:28→12:31 +80** (target, worked)
  + with VWAP (+3.6 ATR); reached +2.8 ATR
  − chased: already ran +1.1 ATR in 5 min; small ATR 2.5 bp, stop inside noise
  → keep as is

**35. IWM-RANGE CALL 12:31→12:43 -20** (stop, right side, stopped first)
  + with VWAP (+6.2 ATR); reached +1.1 ATR; direction was right (hit target after exit)
  − chased: already ran +4.7 ATR in 5 min; small ATR 2.6 bp, stop inside noise
  → take profit at 1R (+1.1R); breakeven stop (-0.3R); 10 min time stop (+0.3R)

**36. QQQ-EMA50 PUT 12:36→12:47 -190** (stop, gave back a 1r+ gain)
  + reached +1.2 ATR
  − against VWAP (-1.6 ATR); chased: already ran +1.9 ATR in 5 min; small ATR 2.9 bp, stop inside noise; exit filled -1.44 ATR (past stop)
  → take profit at 1R (+1.2R); breakeven stop (-0.5R); 10 min time stop (-0.5R); exit at the stop line

**37. IWM-RANGE CALL 12:46→13:14 -100** (stop, right side, stopped first)
  + with VWAP (+7.2 ATR); not extended (+0.1 ATR in 5 min); reached +1.9 ATR; direction was right (hit target after exit)
  − small ATR 2.3 bp, stop inside noise; exit filled -1.78 ATR (past stop); re-entry right after its own stop
  → take profit at 1R (+1.6R); breakeven stop (-0.1R); 10 min time stop (+1.0R); exit at the stop line

**38. QQQ-EMA50 PUT 12:59→13:19 +230** (target, worked)
  + reached +2.5 ATR
  − against VWAP (-1.9 ATR); chased: already ran +2.3 ATR in 5 min; small ATR 2.7 bp, stop inside noise
  → keep as is

**39. IWM-EMA50 PUT 13:11→13:20 -50** (stop, gave back a 1r+ gain)
  + reached +1.4 ATR
  − against VWAP (-6.5 ATR), fighting the day's move; chased: already ran +1.9 ATR in 5 min; small ATR 2.1 bp, stop inside noise; exit filled -1.52 ATR (past stop); another bot held the other side
  → take profit at 1R (+1.3R); breakeven stop (-0.0R); exit at the stop line

**40. IWM-RANGE CALL 13:18→13:40 +50** (target, worked)
  + with VWAP (+5.6 ATR); not extended (+0.1 ATR in 5 min); reached +2.5 ATR
  − small ATR 2.4 bp, stop inside noise; another bot held the other side; re-entry right after its own stop
  → keep as is

**41. QQQ-EMA50 CALL 13:22→13:23 -90** (stop, wrong side from the start)
  + with VWAP (+1.8 ATR); not extended (+0.8 ATR in 5 min)
  − small ATR 2.5 bp, stop inside noise; never went its way; exit filled -1.66 ATR (past stop)
  → exit at the stop line

**42. IWM-EMA50 PUT 13:23→13:33 -20** (stop, chopped out)
  + not extended (-0.0 ATR in 5 min)
  − against VWAP (-5.9 ATR), fighting the day's move; small ATR 2.3 bp, stop inside noise; exit order failed first; another bot held the other side; re-entry right after its own stop
  → VWAP side (CALL) wins +2.6R

**43. QQQ-EMA50 PUT 13:25→13:28 -160** (stop, wrong side from the start)
  + not extended (-0.5 ATR in 5 min)
  − against VWAP (-0.7 ATR); small ATR 2.7 bp, stop inside noise; never went its way; exit filled -1.76 ATR (past stop)
  → VWAP side (CALL) wins +2.0R; exit at the stop line

**44. QQQ-EMA50 PUT 13:33→13:43 -200** (stop, chopped out)
  + none
  − against VWAP (-1.1 ATR); chased: already ran +1.3 ATR in 5 min; small ATR 2.7 bp, stop inside noise; re-entry right after its own stop
  → VWAP side (CALL) wins +2.1R

**45. IWM-EMA50 PUT 13:35→13:37 -50** (stop, wrong side from the start)
  + not extended (-0.1 ATR in 5 min)
  − against VWAP (-5.5 ATR), fighting the day's move; small ATR 2.4 bp, stop inside noise; never went its way; exit filled -1.83 ATR (past stop); another bot held the other side; re-entry right after its own stop
  → VWAP side (CALL) wins +2.5R; exit at the stop line

**46. QQQ-EMA50 PUT 13:45→13:48 -140** (stop, chased an extended move)
  + none
  − against VWAP (-0.9 ATR); chased: already ran +1.0 ATR in 5 min; small ATR 2.4 bp, stop inside noise; never went its way; exit filled -1.42 ATR (past stop); exit order failed first; re-entry right after its own stop
  → VWAP side (CALL) wins +2.2R; exit at the stop line

**47. QQQ-EMA50 PUT 14:03→14:08 -150** (stop, chopped out)
  + none
  − against VWAP (-2.1 ATR), fighting the day's move; chased: already ran +1.9 ATR in 5 min; small ATR 2.0 bp, stop inside noise; exit filled -2.01 ATR (past stop)
  → VWAP side (CALL) wins +2.0R; exit at the stop line

**48. IWM-EMA50 PUT 14:31→14:32 -30** (stop, chased an extended move)
  + none
  − against VWAP (-14.0 ATR), fighting the day's move; chased: already ran +2.0 ATR in 5 min; small ATR 1.5 bp, stop inside noise; never went its way; exit filled -1.35 ATR (past stop)
  → VWAP side (CALL) wins +2.2R; exit at the stop line

**49. QQQ-EMA50 PUT 14:34→14:47 -130** (stop, gave back a 1r+ gain)
  + reached +1.1 ATR
  − against VWAP (-4.6 ATR), fighting the day's move; chased: already ran +2.0 ATR in 5 min; small ATR 1.9 bp, stop inside noise; exit filled -2.70 ATR (past stop)
  → take profit at 1R (+1.1R); breakeven stop (-0.1R); 10 min time stop (+0.6R); exit at the stop line

**50. QQQ-EMA50 PUT 14:56→15:12 -160** (stop, chopped out)
  + none
  − against VWAP (-3.1 ATR), fighting the day's move; chased: already ran +4.0 ATR in 5 min; small ATR 2.8 bp, stop inside noise
  → VWAP side (CALL) wins +2.0R; 10 min time stop (+0.3R)

**51. IWM-EMA50 PUT 15:06→15:25 +60** (target, worked)
  + reached +2.1 ATR
  − against VWAP (-7.8 ATR), fighting the day's move; chased: already ran +1.6 ATR in 5 min; small ATR 3.0 bp, stop inside noise
  → keep as is

**52. QQQ-EMA50 PUT 15:30→15:36 +220** (target, worked)
  + reached +2.9 ATR
  − against VWAP (-5.6 ATR), fighting the day's move; chased: already ran +2.3 ATR in 5 min; small ATR 1.9 bp, stop inside noise
  → keep as is


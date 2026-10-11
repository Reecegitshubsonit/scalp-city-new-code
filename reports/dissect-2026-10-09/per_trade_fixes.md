| # | bot | side | in→out | P&L | why lost | pre-5m run | vs VWAP | ATR bp | best/worst | live R | take 1R | BE stop | 10m stop | opposite | what was needed |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | IWM-VWAP | PUT | 09:43→10:20 | -230 | gave back a 1r+ gain | – | +0.75 | 9.96 | +1.99/-3.32 | -2.17 | +1.03 | -0.43 | +0.33 | -1.03 | take profit at 1R; 10 min time stop; exit at stop line (filled -1.48) |
| 2 | SPY-VWAP | PUT | 09:43→– | lost | lost at restart | – | +0.47 | 5.36 | +1.89/-7.42 | -1.10 | +1.50 | -0.07 | +0.65 | -1.50 | restart must keep position |
| 3 | IWM-EMA50 | PUT | 09:46→09:55 | -260 | chopped out | – | +1.86 | 9.92 | +0.69/-1.74 | -1.27 | -1.27 | -1.27 | -1.27 | +2.31 | exit at stop line (filled -1.74) |
| 4 | IWM-RANGE | PUT | 09:47→09:52 | -250 | wrong side from the start | – | +2.38 | 9.78 | +0.15/-1.44 | -1.44 | -1.44 | -1.44 | -1.44 | +2.32 | other side; exit at stop line (filled -1.29) |
| 5 | QQQ-RANGE | PUT | 09:47→09:53 | +190 | wrong side from the start | – | +2.92 | 9.87 | +0.21/-1.08 | -1.08 | -1.08 | -1.08 | -1.08 | +2.13 | other side |
| 6 | QQQ-EMA50 | PUT | 09:52→09:53 | +230 | wrong side from the start | 0.22 | +2.84 | 9.4 | +0/-1.36 | -1.36 | -1.36 | -1.36 | -1.36 | +2.46 | other side; exit at stop line (filled -1.36) |
| 7 | QQQ-EMA50 | PUT | 09:55→– | lost | lost at restart | 0.55 | +2.48 | 9.29 | +0/-4.53 | -1.07 | -1.07 | -1.07 | -1.07 | +2.24 | restart must keep position |
| 8 | QQQ-RANGE | PUT | 09:55→– | lost | lost at restart | 0.55 | +2.48 | 9.29 | +0/-4.53 | -1.07 | -1.07 | -1.07 | -1.07 | +2.24 | restart must keep position |
| 9 | IWM-RANGE | CALL | 10:01→10:13 | -130 | chopped out | 3.09 | +2.84 | 8.35 | +0.54/-1.14 | -1.14 | -1.14 | -1.14 | -0.13 | +2.15 | 10 min time stop |
| 10 | QQQ-EMA50 | PUT | 10:02→10:07 | -320 | wrong side from the start | 0.71 | +2.57 | 8.05 | +0.05/-1.08 | -1.08 | -1.08 | -1.08 | -1.08 | +2.50 | other side |
| 11 | QQQ-RANGE | PUT | 10:02→10:07 | -270 | wrong side from the start | 0.71 | +2.57 | 8.05 | +0.05/-1.08 | -1.08 | -1.08 | -1.08 | -1.08 | +2.50 | other side |
| 12 | SPY-VWAP | CALL | 10:08→10:52 | +360 | worked | 0.52 | +0.42 | 4.01 | +2.68/-0.58 | +2.68 | +1.30 | -0.58 | +0.64 | -1.30 | nothing |
| 13 | QQQ-EMA50 | CALL | 10:13→10:56 | +380 | worked | -0.77 | -1.49 | 7.61 | +2.07/-0.83 | +2.07 | +1.05 | -0.32 | -0.07 | -1.05 | nothing |
| 14 | QQQ-VWAP | CALL | 10:31→10:40 | -310 | chopped out | 1.57 | +0.52 | 5.67 | +0.4/-1.22 | -1.22 | -1.22 | -1.22 | -1.22 | +2.70 | no rule helps; skip |
| 15 | IWM-EMA50 | PUT | 10:32→10:49 | +180 | worked | 1.41 | +0.1 | 6.22 | +2.28/-0.5 | +2.28 | +1.07 | +2.28 | +1.50 | -1.07 | nothing |
| 16 | IWM-VWAP | PUT | 10:32→10:49 | +190 | worked | 1.41 | +0.1 | 6.22 | +2.28/-0.5 | +2.28 | +1.07 | +2.28 | +1.50 | -1.07 | nothing |
| 17 | SPY-EMA50 | PUT | 10:42→10:45 | -110 | chased an extended move | 1.41 | +0.78 | 2.74 | +0/-1.23 | -1.23 | -1.23 | -1.23 | -1.23 | +2.16 | no entry after 1+ ATR run; other side |
| 18 | IWM-EMA50 | CALL | 10:52→11:03 | +110 | worked | 1.24 | +0.02 | 5.79 | +2.05/-0.9 | +2.05 | +2.05 | +2.05 | +0.19 | -2.05 | nothing |
| 19 | IWM-VWAP | CALL | 10:52→11:16 | +220 | worked | 1.24 | +0.02 | 5.79 | +2.48/-0.9 | +2.05 | +2.05 | +2.05 | +0.19 | -2.05 | nothing |
| 20 | SPY-RANGE | CALL | 10:52→10:59 | +280 | worked | 1.92 | +3.42 | 3.04 | +2.1/+0 | +2.10 | +1.12 | +2.10 | +2.10 | -1.12 | nothing |
| 21 | IWM-EMA50 | PUT | 11:07→11:16 | -190 | chopped out | 0.25 | +0.09 | 5.71 | +0.54/-2.58 | -2.58 | -2.58 | -2.58 | -2.58 | +2.58 | exit at stop line (filled -2.58) |
| 22 | QQQ-EMA50 | PUT | 11:07→11:27 | -290 | gave back a 1r+ gain | 1.39 | +0.55 | 5.27 | +1.98/-1.04 | -1.04 | +1.98 | -0.75 | +0.28 | -1.98 | take profit at 1R; 10 min time stop |
| 23 | QQQ-VWAP | PUT | 11:07→11:27 | -300 | gave back a 1r+ gain | 1.39 | +0.55 | 5.27 | +1.98/-1.04 | -1.04 | +1.98 | -0.75 | +0.28 | -1.98 | take profit at 1R; 10 min time stop |
| 24 | SPY-EMA50 | PUT | 11:09→11:16 | -390 | chased an extended move | 2.49 | -0.75 | 3.18 | +0/-3.15 | -3.15 | -3.15 | -3.15 | -3.15 | +3.15 | no entry after 1+ ATR run; other side; exit at stop line (filled -3.15) |
| 25 | IWM-RANGE | CALL | 11:32→11:34 | -60 | wrong side from the start | 0.56 | +4.5 | 3.82 | +0/-1.27 | -1.27 | -1.27 | -1.27 | -1.27 | +2.39 | other side; exit at stop line (filled -1.27) |
| 26 | SPY-EMA50 | PUT | 11:33→11:40 | -80 | chopped out | 2.22 | -2.47 | 2.41 | +0.83/-1.2 | -1.20 | -1.20 | -1.20 | -1.20 | +2.75 | no rule helps; skip |
| 27 | SPY-RANGE | CALL | 11:35→11:51 | +210 | worked | -1.02 | +1.94 | 2.46 | +2.43/-0.29 | +2.43 | +1.65 | +2.43 | +1.60 | -1.65 | nothing |
| 28 | QQQ-EMA50 | CALL | 11:39→11:58 | +150 | worked | 1.85 | -0.16 | 4.57 | +2.01/-0.4 | +2.01 | +1.04 | +2.01 | +0.71 | -1.04 | nothing |
| 29 | IWM-EMA50 | PUT | 11:41→11:59 | -60 | gave back a 1r+ gain | 1.52 | -1.89 | 3.9 | +1.01/-1.01 | -1.01 | +1.01 | -0.46 | -0.46 | -1.01 | take profit at 1R; 10 min time stop |
| 30 | QQQ-VWAP | CALL | 11:43→11:46 | -170 | chased an extended move | 1.87 | +0.6 | 4.41 | +0/-1.19 | -1.19 | -1.19 | -1.19 | -1.19 | -1.32 | no entry after 1+ ATR run |
| 31 | SPY-EMA50 | PUT | 11:46→11:49 | -130 | chased an extended move | 1.3 | -1.99 | 2.47 | +0/-1.46 | -1.46 | -1.46 | -1.46 | -1.46 | +2.23 | no entry after 1+ ATR run; other side; exit at stop line (filled -1.46) |
| 32 | QQQ-VWAP | CALL | 11:48→12:01 | -310 | right side, stopped first | -0.6 | +0.04 | 4.15 | +2.0/-1.77 | +2.00 | +1.49 | +2.00 | +2.00 | -1.49 | take profit at 1R; exit at stop line (filled -1.77) |
| 33 | QQQ-EMA50 | PUT | 12:00→12:01 | +350 | worked | 1.48 | +0.09 | 3.55 | +2.01/+0 | +2.01 | +2.01 | +2.01 | +2.01 | -2.01 | nothing |
| 34 | IWM-EMA50 | PUT | 12:01→12:06 | -70 | chased an extended move | 1.69 | -1.51 | 3.08 | +0/-1.46 | -1.46 | -1.46 | -1.46 | -1.46 | +2.68 | no entry after 1+ ATR run; other side; exit at stop line (filled -1.46) |
| 35 | SPY-EMA50 | PUT | 12:01→12:05 | -250 | chased an extended move | 3.57 | -1.84 | 2.23 | +0.17/-2.53 | -2.53 | -2.53 | -2.53 | -2.53 | +2.53 | no entry after 1+ ATR run; other side; exit at stop line (filled -2.53) |
| 36 | IWM-EMA50 | PUT | 12:08→12:16 | -90 | chopped out | -0.06 | -1.83 | 3.08 | +0.29/-1.28 | -1.28 | -1.28 | -1.28 | -1.28 | +2.33 | exit at stop line (filled -1.28) |
| 37 | IWM-EMA50 | CALL | 12:28→12:31 | +80 | worked | 1.07 | +3.6 | 2.52 | +2.84/+0 | +2.84 | +1.35 | +2.84 | +2.84 | -1.35 | nothing |
| 38 | IWM-RANGE | CALL | 12:31→12:43 | -20 | right side, stopped first | 4.73 | +6.16 | 2.62 | +1.1/-1.03 | -1.03 | +1.10 | -0.27 | +0.27 | -1.10 | take profit at 1R; 10 min time stop |
| 39 | QQQ-EMA50 | PUT | 12:36→12:47 | -190 | gave back a 1r+ gain | 1.86 | -1.56 | 2.87 | +1.16/-1.44 | -1.44 | +1.16 | -0.46 | -0.46 | -1.16 | take profit at 1R; 10 min time stop; exit at stop line (filled -1.44) |
| 40 | IWM-RANGE | CALL | 12:46→13:14 | -100 | right side, stopped first | 0.15 | +7.16 | 2.32 | +1.86/-1.78 | -1.78 | +1.57 | -0.08 | +1.01 | -1.57 | take profit at 1R; 10 min time stop; exit at stop line (filled -1.78) |
| 41 | QQQ-EMA50 | PUT | 12:59→13:19 | +230 | worked | 2.26 | -1.89 | 2.71 | +2.49/-0.5 | +2.49 | +1.22 | +2.49 | +0.73 | -1.22 | nothing |
| 42 | IWM-EMA50 | PUT | 13:11→13:20 | -50 | gave back a 1r+ gain | 1.85 | -6.49 | 2.13 | +1.35/-1.52 | -1.52 | +1.35 | -0.00 | -1.52 | -1.35 | take profit at 1R; breakeven stop; exit at stop line (filled -1.52) |
| 43 | IWM-RANGE | CALL | 13:18→13:40 | +50 | worked | 0.07 | +5.64 | 2.4 | +2.47/-0.78 | +2.47 | +1.35 | +0.00 | -0.78 | -1.35 | nothing |
| 44 | QQQ-EMA50 | CALL | 13:22→13:23 | -90 | wrong side from the start | 0.82 | +1.76 | 2.52 | +0/-1.66 | -1.66 | -1.66 | -1.66 | -1.66 | -1.19 | exit at stop line (filled -1.66) |
| 45 | IWM-EMA50 | PUT | 13:23→13:33 | -20 | chopped out | -0.0 | -5.93 | 2.26 | +0.83/-1.19 | -1.19 | -1.19 | -1.19 | -1.19 | +2.62 | no rule helps; skip |
| 46 | QQQ-EMA50 | PUT | 13:25→13:28 | -160 | wrong side from the start | -0.46 | -0.72 | 2.72 | +0/-1.76 | -1.76 | -1.76 | -1.76 | -1.76 | +2.01 | other side; exit at stop line (filled -1.76) |
| 47 | QQQ-EMA50 | PUT | 13:33→13:43 | -200 | chopped out | 1.33 | -1.15 | 2.71 | +0.54/-1.06 | -1.06 | -1.06 | -1.06 | -1.06 | +2.07 | no rule helps; skip |
| 48 | IWM-EMA50 | PUT | 13:35→13:37 | -50 | wrong side from the start | -0.08 | -5.53 | 2.35 | +0/-1.83 | -1.83 | -1.83 | -1.83 | -1.83 | +2.52 | other side; exit at stop line (filled -1.83) |
| 49 | QQQ-EMA50 | PUT | 13:45→13:48 | -140 | chased an extended move | 1.02 | -0.9 | 2.35 | +0/-1.73 | -1.73 | -1.73 | -1.73 | -1.73 | +2.21 | no entry after 1+ ATR run; other side; exit at stop line (filled -1.42) |
| 50 | QQQ-EMA50 | PUT | 14:03→14:08 | -150 | chopped out | 1.88 | -2.14 | 2.04 | +0.4/-2.01 | -2.01 | -2.01 | -2.01 | -2.01 | +2.01 | exit at stop line (filled -2.01) |
| 51 | IWM-EMA50 | PUT | 14:31→14:32 | -30 | chased an extended move | 1.96 | -14.02 | 1.46 | +0/-1.35 | -1.35 | -1.35 | -1.35 | -1.35 | +2.21 | no entry after 1+ ATR run; other side; exit at stop line (filled -1.35) |
| 52 | QQQ-EMA50 | PUT | 14:34→14:47 | -130 | gave back a 1r+ gain | 2.02 | -4.59 | 1.86 | +1.15/-2.7 | -2.70 | +1.15 | -0.07 | +0.65 | -1.15 | take profit at 1R; 10 min time stop; exit at stop line (filled -2.70) |
| 53 | QQQ-EMA50 | PUT | 14:56→15:12 | -160 | chopped out | 3.96 | -3.06 | 2.82 | +0.33/-1.09 | -1.09 | -1.09 | -1.09 | +0.33 | +2.03 | 10 min time stop |
| 54 | IWM-EMA50 | PUT | 15:06→15:25 | +60 | worked | 1.63 | -7.76 | 2.96 | +2.06/-0.85 | +2.06 | +1.57 | +2.06 | +0.85 | -1.57 | nothing |
| 55 | QQQ-EMA50 | PUT | 15:30→15:36 | +220 | worked | 2.27 | -5.56 | 1.94 | +2.87/-0.14 | +2.87 | +2.87 | +2.87 | +2.87 | -2.87 | nothing |

Totals in ATR (55 entries, each replayed alone on logged closes): live -21.0, t1 -4.7, be -17.6, opp +23.4, t10 -20.5

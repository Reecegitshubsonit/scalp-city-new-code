import requests, json, time, sys
env={}
for l in open('.env'):
    l=l.strip()
    if '=' in l and not l.startswith('#'):
        k,v=l.split('=',1); env[k]=v.strip().strip('"\'')
h={"APCA-API-KEY-ID":env['ALPACA_API_KEY'],"APCA-API-SECRET-KEY":env['ALPACA_SECRET_KEY']}
START,END="2026-06-01T00:00:00Z","2026-10-07T23:00:00Z"
for t in ["QQQ","SPY","IWM"]:
    bars=[];tok=None
    while True:
        p=dict(timeframe="1Min",start=START,end=END,feed="sip",limit=10000,adjustment="raw")
        if tok:p["page_token"]=tok
        r=requests.get(f"https://data.alpaca.markets/v2/stocks/{t}/bars",headers=h,params=p)
        if r.status_code==429: time.sleep(15); continue
        if r.status_code!=200: print(t,r.status_code,r.text[:200]); break
        time.sleep(1)
        j=r.json(); bars+=j["bars"] or []; tok=j.get("next_page_token")
        if not tok: break
    json.dump(bars,open(f"backtest/data/{t}_1m.json","w")); print(t,len(bars))

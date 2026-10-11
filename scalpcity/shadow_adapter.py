"""Local quote-driven shadow broker. Has no network/order client reference."""
from datetime import datetime
import threading
from .types import ET

class ShadowAdapter:
    capability='PAPER'
    fill_source='shadow_bid_ask'
    def __init__(self,quotes,now_fn=None,fee_per_contract=.65):
        self.quotes=quotes;self.now_fn=now_fn or (lambda:datetime.now(ET))
        self.fee=fee_per_contract;self.orders={};self.positions={};self.lock=threading.RLock()
    def submit(self,order):
        with self.lock:
            oid=order['client_order_id']
            if oid in self.orders:raise ValueError('duplicate order ID')
            self.orders[oid]={**order,'status':'SUBMITTED','filled_qty':0,'avg_price':None,'fees':0,'fill_time':None}
            return self.poll(oid)
    def poll(self,oid):
        with self.lock:
            o=self.orders[oid];now=self.now_fn();q=self.quotes.get(o['contract'],now)
            if o['status']=='SUBMITTED' and q and 0<=(now-q.ts).total_seconds()<=2:
                buy=o['kind']=='BUY_OPEN';px=q.ask if buy else q.bid
                # This is explicitly a shadow assumption, not proof of fillability.
                if (buy and px<=o['limit']) or (not buy and px>=o['limit']):
                    signed=o['qty'] if buy else -o['qty']
                    if not buy and self.positions.get(o['contract'],0)<o['qty']:raise ValueError('shadow oversell')
                    self.positions[o['contract']]=self.positions.get(o['contract'],0)+signed
                    o.update(status='FILLED',filled_qty=o['qty'],avg_price=px,fees=self.fee*o['qty'],fill_time=now.isoformat())
            return {k:o[k] for k in ('client_order_id','status','filled_qty','avg_price','fees','fill_time')}
    def cancel(self,oid):
        with self.lock:
            self.poll(oid)
            if self.orders[oid]['status']=='SUBMITTED':self.orders[oid]['status']='CANCELLED'
            return self.poll(oid)
    def snapshot(self,tracked_ids=()):
        with self.lock:
            return dict(observed_at=self.now_fn().isoformat(),orders=[self.poll(oid) for oid in self.orders],positions={k:v for k,v in self.positions.items() if v})

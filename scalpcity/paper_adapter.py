"""Guarded Webull sandbox adapter for SafeEngine. No modeled fallback.
This module is packaged for review; submission methods are tested with fakes only.
"""
from datetime import datetime
from .guard import assert_paper_only,SANDBOX_HOST
from .types import ET
from .webull_parse import parse_occ
from .order_records import normalize_order,normalize_positions

class PaperAdapter:
    capability='PAPER'
    def __init__(self,client,env,accounts,host):
        self.account_id=assert_paper_only(env,host,accounts)['account_id']
        self.client=client

    @classmethod
    def from_environment(cls,env):
        from .webull_client import WebullClient
        client=WebullClient.from_env(env)
        return cls(client,env,client.accounts(),SANDBOX_HOST)

    @staticmethod
    def _json(response):
        if getattr(response,'status_code',200)!=200:raise RuntimeError('sandbox request failed')
        return response.json() if hasattr(response,'json') else response

    def submit(self,o):
        root,expiry,right,strike=parse_occ(o['contract'])
        side='BUY' if o['kind']=='BUY_OPEN' else 'SELL'
        row={'client_order_id':o['client_order_id'],'combo_type':'NORMAL','order_type':'LIMIT',
             'quantity':str(o['qty']),'limit_price':f"{o['limit']:.2f}",'option_strategy':'SINGLE',
             'side':side,'time_in_force':'DAY','entrust_type':'QTY',
             'orders':[{'side':side,'quantity':str(o['qty']),'symbol':root,'strike_price':f'{strike:.3f}',
                        'init_exp_date':str(expiry),'instrument_type':'OPTION','option_type':right,'market':'US'}]}
        # One submission attempt only. A timeout is unknown, never permission to fabricate a fill.
        self._json(self.client.trade.order_v2.place_option(self.account_id,[row]))
        return self.poll(o['client_order_id'])

    def poll(self,oid):
        body=self._json(self.client.order_detail(self.account_id,oid))
        if body.get('client_order_id',oid)!=oid:raise ValueError('order identity mismatch')
        body=dict(body,client_order_id=oid)
        result=normalize_order(body)
        return result

    def cancel(self,oid):
        self.client.cancel_option(self.account_id,oid)
        # Cancellation acknowledgement is not proof of final quantity/status.
        return self.poll(oid)

    def snapshot(self,tracked_ids):
        orders={}
        # Include all open orders, not just those owned by this process.
        last=None
        for _ in range(100):
            page=self._json(self.client._call(self.client.trade.order_v2.get_order_open,self.account_id,page_size=100,last_client_order_id=last))
            if not isinstance(page,list):raise ValueError('unknown open-order schema')
            for record in page:
                order=normalize_order(record);orders[order['client_order_id']]=order
            if len(page)<100:break
            nxt=page[-1].get('client_order_id')
            if not nxt or nxt==last:raise ValueError('incomplete open-order pagination')
            last=nxt
        else:raise ValueError('open-order pagination exceeded')
        for oid in tracked_ids:orders[oid]=self.poll(oid)
        rows=self._json(self.client._call(self.client.trade.account_v2.get_account_position,self.account_id))
        positions,other=normalize_positions(rows)
        if other:raise ValueError('dedicated paper account required: non-option holdings')
        return dict(observed_at=datetime.now(ET).isoformat(),orders=list(orders.values()),positions=positions)

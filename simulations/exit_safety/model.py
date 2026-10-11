"""Offline exit-controller prototype. No network or production imports.
Broker observations are injected; this is NOT a deployable broker adapter.
"""
from dataclasses import dataclass, asdict
import json

TERMINAL = {'FILLED', 'CANCELLED', 'REJECTED', 'EXPIRED'}

@dataclass
class ExitController:
    qty: int
    stop: float
    target: float
    side: int = 1
    reason: str | None = None
    order_id: str | None = None
    order_qty: int = 0
    accounted: int = 0
    status: str = 'NONE'
    reconciled: bool = True

    def observe(self, price, age_s=0, flat_due=False):
        if self.qty <= 0:
            return
        # Existing exit intent survives reversals and missing/stale data.
        if self.reason is None:
            if flat_due:
                self.reason = 'TIME'
            elif price is not None and 0 <= age_s <= 2:
                if self.side * (price-self.stop) <= 0:
                    self.reason = 'STOP'
                elif self.side * (price-self.target) >= 0:
                    self.reason = 'TARGET'

    def ready(self, quote_age=0, bid=1):
        return bool(self.qty and self.reason and self.reconciled and
                    self.status in {'NONE', *TERMINAL} and
                    0 <= quote_age <= 2 and bid > 0)

    def submit(self, client_id, quote_age=0, bid=1):
        if not self.ready(quote_age, bid):
            return None
        self.order_id, self.order_qty, self.accounted = client_id, self.qty, 0
        self.status = 'SUBMITTING'  # persist before external submission
        return self.order_qty

    def uncertain(self):
        self.status, self.reconciled = 'UNKNOWN', False

    def cancel_requested(self):
        if self.status not in TERMINAL:
            self.status = 'CANCEL_PENDING'

    def broker_update(self, order_id, status, cumulative_filled):
        if order_id != self.order_id:
            raise ValueError('unmatched order requires reconciliation')
        if not self.accounted <= cumulative_filled <= self.order_qty:
            raise ValueError('invalid cumulative quantity')
        if status == 'FILLED' and cumulative_filled != self.order_qty:
            raise ValueError('inconsistent full-fill status')
        self.qty -= cumulative_filled-self.accounted
        self.accounted = cumulative_filled
        self.status = status
        self.reconciled = True

    def reconcile(self, broker_qty, active_orders):
        # Per-position ownership must be resolved by a future adapter.
        if broker_qty != self.qty or active_orders != (0 if self.status in TERMINAL | {'NONE'} else 1):
            self.reconciled = False
            return False
        self.reconciled = True
        return True

    def snapshot(self):
        return json.dumps(asdict(self))

    @classmethod
    def restore(cls, snapshot):
        result = cls(**json.loads(snapshot))
        result.reconciled = False  # never submit after restart before broker reconciliation
        return result

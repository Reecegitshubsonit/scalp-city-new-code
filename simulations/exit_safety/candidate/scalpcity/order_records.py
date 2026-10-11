"""Strict normalization of single-leg Webull paper-order records."""
from datetime import datetime,date
from decimal import Decimal
from .contracts import occ_symbol

def integer(value):
    d=Decimal(str(value))
    if not d.is_finite() or d!=int(d) or d<0:raise ValueError('invalid contract quantity')
    return int(d)

def contract_of(leg):
    if leg.get('option_contract_multiplier') not in ('100',100):raise ValueError('nonstandard multiplier')
    right=leg['option_type']
    if right not in ('CALL','PUT'):raise ValueError('invalid option type')
    strike=float(leg.get('strike_price',leg.get('option_exercise_price')))
    return occ_symbol(leg['symbol'],date.fromisoformat(leg['option_expire_date']),right,strike)

def normalize_order(record):
    rows=record.get('orders',[])
    if len(rows)!=1:raise ValueError('single order required')
    row=rows[0]
    if row.get('instrument_type')!='OPTION':raise ValueError('option order required')
    legs=row.get('legs',[])
    if len(legs)!=1:raise ValueError('single leg required')
    qty=integer(row.get('filled_quantity',0));total=integer(row['total_quantity'])
    if qty>total:raise ValueError('fill exceeds order')
    fees=sum(Decimal(str(f['actual_value'])) for f in row.get('fees',[]))
    commission=row.get('commission') or {}
    if commission:
        if 'actual_value' not in commission:raise ValueError('unknown commission schema')
        fees+=Decimal(str(commission['actual_value']))
    stamp=row.get('filled_time_at')
    if qty and not stamp:raise ValueError('missing broker fill time')
    if stamp:datetime.fromisoformat(stamp.replace('Z','+00:00'))
    return dict(client_order_id=record['client_order_id'],status=row['status'],
                filled_qty=qty,qty=total,avg_price=float(row['filled_price']) if qty else None,
                fees=float(fees),fill_time=stamp,contract=contract_of(legs[0]),
                side=row['side'],placed_at=row.get('place_time_at'))

def normalize_positions(records):
    result={};unsupported=[]
    for row in records:
        if row.get('instrument_type')!='OPTION':unsupported.append(row.get('symbol'));continue
        if len(row.get('legs',[]))!=1:raise ValueError('multi-leg position unsupported')
        symbol=contract_of(row['legs'][0]);qty=integer(row['quantity'])
        result[symbol]=result.get(symbol,0)+qty
    return result,unsupported

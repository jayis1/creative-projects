"""Append-only event ledger with deterministic replay and snapshots."""
from __future__ import annotations
import argparse, json, hashlib
from pathlib import Path
from typing import Any

class LedgerError(ValueError):
    """Invalid event or corrupted ledger."""

class Ledger:
    """Account ledger. Events are validated before changing state."""
    def __init__(self, events=()):
        self.events=[]
        self.balances={}
        self.seen=set()
        for event in events: self.append(event)
    def append(self, event: dict[str, Any]) -> None:
        if not isinstance(event, dict): raise LedgerError('event must be an object')
        required={'id','account','amount'}
        if not required <= event.keys(): raise LedgerError('event requires id, account, amount')
        ident, account, amount=event['id'], event['account'], event['amount']
        if not isinstance(ident,str) or not ident: raise LedgerError('id must be non-empty text')
        if ident in self.seen: raise LedgerError(f'duplicate event id: {ident}')
        if not isinstance(account,str) or not account: raise LedgerError('account must be non-empty text')
        if isinstance(amount,bool) or not isinstance(amount,int): raise LedgerError('amount must be an integer number of minor units')
        if abs(amount)>10**12: raise LedgerError('amount exceeds supported range')
        self.balances[account]=self.balances.get(account,0)+amount
        self.seen.add(ident)
        self.events.append(dict(event))
    def transfer(self, ident: str, source: str, target: str, amount: int) -> None:
        if not isinstance(amount,int) or isinstance(amount,bool) or amount<=0: raise LedgerError('transfer amount must be a positive integer')
        if source==target: raise LedgerError('source and target must differ')
        if self.balances.get(source,0)<amount: raise LedgerError('insufficient funds')
        # Reject collisions for both legs before mutating the ledger, so a failed transfer is atomic.
        if ident+':debit' in self.seen or ident+':credit' in self.seen:
            raise LedgerError('transfer event ID already exists')
        self.append({'id':ident+':debit','account':source,'amount':-amount})
        self.append({'id':ident+':credit','account':target,'amount':amount})
    def verify(self) -> bool:
        return sum(self.balances.values()) == sum(e['amount'] for e in self.events)
    def snapshot(self) -> dict[str,Any]:
        body={'events':self.events,'balances':dict(sorted(self.balances.items()))}
        body['sha256']=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        return body
    @classmethod
    def load(cls, path: Path) -> 'Ledger':
        try:
            data=json.loads(path.read_text(encoding='utf-8'))
        except (OSError,UnicodeError,json.JSONDecodeError) as exc: raise LedgerError(f'cannot read ledger: {exc}') from exc
        if isinstance(data,dict):
            digest=data.pop('sha256',None)
            actual=hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':')).encode()).hexdigest()
            if digest != actual: raise LedgerError('snapshot checksum mismatch')
            events=data.get('events')
        else: events=data
        if not isinstance(events,list): raise LedgerError('ledger must contain an event list')
        result=cls(events)
        if isinstance(data,dict) and data.get('balances') != dict(sorted(result.balances.items())): raise LedgerError('snapshot balances do not match replay')
        return result
    def save(self,path:Path) -> None:
        path.write_text(json.dumps(self.snapshot(),indent=2,sort_keys=True)+'\n',encoding='utf-8')

def main(argv=None):
    p=argparse.ArgumentParser(description='Inspect and verify an append-only account ledger')
    p.add_argument('file',type=Path,nargs='?'); p.add_argument('--demo',action='store_true')
    a=p.parse_args(argv)
    try:
        ledger=Ledger(); ledger.append({'id':'seed','account':'savings','amount':10000}); ledger.transfer('rent','savings','checking',2500)
        if a.file:
            ledger=Ledger.load(a.file)
        elif not a.demo: p.error('provide a file or use --demo')
        print(json.dumps({'valid':ledger.verify(),'balances':dict(sorted(ledger.balances.items()))},indent=2))
    except LedgerError as exc: p.exit(2,f'ledger: {exc}\n')
if __name__=='__main__': main()

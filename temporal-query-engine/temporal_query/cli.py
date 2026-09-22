from __future__ import annotations
import argparse, json
from . import Event, IntervalIndex

def main() -> int:
    p=argparse.ArgumentParser(description='Query labelled half-open time intervals')
    p.add_argument('start',type=float); p.add_argument('end',type=float)
    p.add_argument('--event',action='append',default=[],metavar='ID:START:END:LABEL')
    p.add_argument('--label', help='only return events with this exact label')
    args=p.parse_args(); idx=IntervalIndex()
    try:
        for raw in args.event:
            bits=raw.split(':',3)
            if len(bits)<3: raise ValueError('event must be ID:START:END[:LABEL]')
            idx.add(Event(bits[0],float(bits[1]),float(bits[2]),bits[3] if len(bits)==4 else ''))
        print(json.dumps([e.__dict__ if hasattr(e,'__dict__') else {'id':e.id,'start':e.start,'end':e.end,'label':e.label} for e in idx.overlaps(args.start,args.end,args.label)], sort_keys=True))
        return 0
    except ValueError as exc:
        p.error(str(exc)); return 2
if __name__=='__main__': raise SystemExit(main())

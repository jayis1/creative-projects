#!/usr/bin/env python3
"""Small, dependency-free causal DAG simulator and intervention workbench."""
from __future__ import annotations
import argparse
import json
import random
from collections import deque

class CausalGraph:
    """Acyclic structural causal model with linear equations and noise."""
    def __init__(self, equations: dict[str, dict]):
        if not isinstance(equations, dict) or not equations:
            raise ValueError("model must be a non-empty object")
        self.equations = {}
        for node, spec in equations.items():
            if not isinstance(node, str) or not node or not isinstance(spec, dict):
                raise ValueError("each node needs a name and equation object")
            parents = spec.get("parents", {})
            if not isinstance(parents, dict) or any(p not in equations for p in parents):
                raise ValueError(f"invalid parents for {node}")
            intercept, noise = spec.get("intercept", 0), spec.get("noise", 0)
            if not isinstance(intercept, (int, float)) or not isinstance(noise, (int,float)) or noise < 0:
                raise ValueError(f"invalid intercept/noise for {node}")
            if any(not isinstance(w,(int,float)) for w in parents.values()):
                raise ValueError(f"invalid coefficient for {node}")
            self.equations[node] = {"parents": dict(parents), "intercept": float(intercept), "noise": float(noise)}
        self.order = self._topological_order()

    def _topological_order(self):
        indegree = {n: len(s['parents']) for n,s in self.equations.items()}
        children = {n: [] for n in indegree}
        for child,s in self.equations.items():
            for p in s['parents']: children[p].append(child)
        q = deque(n for n in self.equations if indegree[n] == 0)
        order=[]
        while q:
            n=q.popleft(); order.append(n)
            for c in children[n]:
                indegree[c]-=1
                if indegree[c] == 0: q.append(c)
        if len(order) != len(indegree): raise ValueError("causal graph contains a cycle")
        return order

    def sample(self, count=1, seed=0, interventions=None):
        if not isinstance(count,int) or isinstance(count,bool) or count < 1 or count > 1_000_000:
            raise ValueError("count must be an integer in [1, 1000000]")
        interventions = interventions or {}
        if not isinstance(interventions,dict) or set(interventions)-set(self.equations):
            raise ValueError("interventions must map known variables to numeric values")
        if any(not isinstance(v,(int,float)) for v in interventions.values()):
            raise ValueError("intervention values must be numeric")
        rng=random.Random(seed); rows=[]
        for _ in range(count):
            row={}
            for n in self.order:
                if n in interventions: row[n]=float(interventions[n]); continue
                eq=self.equations[n]
                row[n]=eq['intercept']+sum(w*row[p] for p,w in eq['parents'].items())+rng.gauss(0,eq['noise'])
            rows.append(row)
        return rows

    def expected_values(self, interventions=None):
        """Return exact means under the model's zero-mean noise assumptions."""
        interventions = interventions or {}
        if not isinstance(interventions, dict) or set(interventions) - set(self.equations):
            raise ValueError("interventions must map known variables to numeric values")
        if any(not isinstance(v, (int, float)) for v in interventions.values()):
            raise ValueError("intervention values must be numeric")
        values = {}
        for n in self.order:
            if n in interventions:
                values[n] = float(interventions[n])
            else:
                eq = self.equations[n]
                values[n] = eq["intercept"] + sum(w * values[p] for p, w in eq["parents"].items())
        return values

    @staticmethod
    def means(rows):
        return {k: sum(r[k] for r in rows)/len(rows) for k in rows[0]}

def demo():
    model=CausalGraph({'study':{'intercept':2,'noise':1},'score':{'parents':{'study':3},'intercept':10,'noise':1}})
    obs=model.sample(5000,seed=7)
    treated=model.sample(5000,seed=7,interventions={'study':4})
    print(json.dumps({'observational_means':model.means(obs),'do_study_4_means':model.means(treated)},indent=2))

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--demo',action='store_true'); p.add_argument('--model'); p.add_argument('--count',type=int,default=1); p.add_argument('--seed',type=int,default=0); p.add_argument('--do',action='append',default=[],metavar='NAME=VALUE')
    a=p.parse_args(argv)
    try:
        if a.demo or not a.model: demo(); return 0
        with open(a.model,encoding='utf8') as f: model=CausalGraph(json.load(f))
        interventions={}
        for item in a.do:
            k,v=item.split('=',1); interventions[k]=float(v)
        print(json.dumps(model.sample(a.count,a.seed,interventions)))
        return 0
    except (ValueError, OSError, json.JSONDecodeError) as e:
        p.error(str(e))

if __name__=='__main__': raise SystemExit(main())

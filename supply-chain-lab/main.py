#!/usr/bin/env python3
"""Discrete-event inventory simulator for periodic-review supply chains."""
from __future__ import annotations
import argparse
import json
import random
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class Node:
    name: str
    lead_time: int
    reorder_point: int
    order_up_to: int
    stock: int
    pipeline: list[tuple[int, int]] = field(default_factory=list)
    backlog: int = 0
    holding: int = 0
    shortage: int = 0
    orders: int = 0

    def __post_init__(self):
        if not self.name or self.lead_time < 1 or self.reorder_point < 0 or self.order_up_to <= self.reorder_point or self.stock < 0:
            raise ValueError(f"invalid inventory node: {self.name!r}")

    def receive(self, day: int) -> None:
        arrived = sum(q for due, q in self.pipeline if due <= day)
        self.pipeline = [(due, q) for due, q in self.pipeline if due > day]
        self.stock += arrived

    def fulfill(self, demand: int) -> int:
        served = min(self.stock, demand)
        self.stock -= served
        self.shortage += demand - served
        self.backlog += demand - served
        return served

    def review(self, day: int, demand: int) -> int:
        """Order to an order-up-to position using inventory position."""
        position = self.stock + sum(q for _, q in self.pipeline) - self.backlog
        qty = max(0, self.order_up_to - position) if position <= self.reorder_point else 0
        if qty:
            self.pipeline.append((day + self.lead_time, qty))
            self.orders += qty
        self.holding += self.stock
        return qty

@dataclass
class Chain:
    nodes: list[Node]
    seed: int = 1

    def __post_init__(self):
        if not self.nodes:
            raise ValueError("chain must have at least one node")
        if len({n.name for n in self.nodes}) != len(self.nodes):
            raise ValueError("node names must be unique")

    def run(self, demand: list[int]) -> dict:
        if not demand or any(type(x) is not int or x < 0 for x in demand):
            raise ValueError("demand must be a non-empty list of non-negative integers")
        rng = random.Random(self.seed)
        daily = []
        for day, customer_demand in enumerate(demand):
            for node in self.nodes:
                node.receive(day)
            flow = customer_demand
            # Customer faces the last node; replenishment signal travels upstream.
            for node in reversed(self.nodes):
                flow = node.fulfill(flow)
            for i in range(len(self.nodes) - 1, -1, -1):
                downstream_need = customer_demand if i == len(self.nodes)-1 else self.nodes[i+1].orders
                self.nodes[i].review(day, downstream_need)
            daily.append({"day": day, "demand": customer_demand, "unfilled": self.nodes[-1].backlog})
        return {"seed": self.seed, "days": len(demand), "daily": daily,
                "nodes": [{"name": n.name, "ending_stock": n.stock, "backlog": n.backlog,
                           "shortage_units": n.shortage, "holding_stock_days": n.holding,
                           "ordered_units": n.orders, "in_transit": sum(q for _, q in n.pipeline)} for n in self.nodes]}

def load_scenario(path: str) -> tuple[Chain, list[int]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("nodes"), list) or not isinstance(data.get("demand"), list):
        raise ValueError("scenario requires nodes and demand arrays")
    nodes = [Node(**item) for item in data["nodes"]]
    return Chain(nodes, data.get("seed", 1)), data["demand"]

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", help="JSON scenario file")
    parser.add_argument("--output", "-o", help="write JSON report to this path")
    args = parser.parse_args(argv)
    try:
        chain, demand = load_scenario(args.scenario)
        result = chain.run(demand)
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        parser.error(str(exc))
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

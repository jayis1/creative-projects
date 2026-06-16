#!/usr/bin/env python3
"""Check delete-all case more thoroughly."""

from bplus_db.bplus_tree import BPlusTree
import random

print("=== Delete all keys thorough test ===")

random.seed(42)
for order in [3, 4, 5, 8, 16]:
    for n in [5, 10, 20, 50, 100]:
        tree = BPlusTree(order=order)
        for i in range(n):
            tree.insert(i, i * 10)
        
        keys = list(range(n))
        random.shuffle(keys)
        all_deleted = True
        for k in keys:
            result = tree.delete(k)
            if not result:
                print(f"  BUG: Failed to delete key {k} from tree with order={order}, n={n}")
                all_deleted = False
                break
        
        if not all_deleted:
            continue
            
        if tree.size != 0:
            print(f"  BUG: Tree size={tree.size} after deleting all keys (order={order}, n={n})")
            continue
            
        # Check that searching for deleted keys returns None
        for k in range(n):
            if tree.search(k) is not None:
                print(f"  BUG: Found deleted key {k} (order={order}, n={n})")
        
        # Validate empty tree
        violations = tree.validate()
        if violations:
            print(f"  VIOLATIONS on empty tree: order={order}, n={n}: {violations}")

print("Done!")
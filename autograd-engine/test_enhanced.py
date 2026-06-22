#!/usr/bin/env python3
"""Quick verification of all enhanced features."""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from autograd_engine import Value, MLP
from autograd_engine.ops import softmax, cross_entropy, log_softmax, dot, matvec
from autograd_engine.train import (
    SGD, Adam, train, mean_squared_error, numerical_grad_check,
    binary_cross_entropy_with_logits, hinge_loss, accuracy
)

# 1. gradient check
def f(inputs):
    x, y = inputs
    return (x * y + x.tanh()).exp().log() + x**2

inputs = [Value(1.5), Value(0.7)]
ok = numerical_grad_check(f, inputs, tol=1e-3)
print("gradient check passed:", ok)
assert ok

# 2. XOR with Adam + relu + he init
xs = [[0,0],[0,1],[1,0],[1,1]]
ys = [0,1,1,0]
model = MLP(2, [8, 8, 1], activation="relu", init="he")
opt = Adam(model.parameters(), lr=0.01)
hist = train(model, xs, ys, epochs=300, optimizer=opt)
print("XOR (Adam, relu) final loss:", round(hist[-1], 6))
assert hist[-1] < 0.05, f"XOR loss too high: {hist[-1]}"

# 3. softmax + cross entropy
logits = [Value(2.0), Value(1.0), Value(0.1)]
sm = softmax(logits)
print("softmax:", [round(v.data, 4) for v in sm], "sum=", round(sum(v.data for v in sm), 6))
loss = cross_entropy(logits, 0)
loss.backward()
print("CE loss:", round(loss.data, 4))
print("logit grads:", [round(v.grad, 4) for v in logits])
assert abs(sum(v.data for v in sm) - 1.0) < 1e-6

# 4. BCE with logits (numerically stable)
logit = [Value(2.0), Value(-3.0)]
targets = [1.0, 0.0]
bce = binary_cross_entropy_with_logits(logit, targets)
bce.backward()
print("BCE loss:", round(bce.data, 4))
assert bce.data >= 0

# 5. SGD with momentum
model2 = MLP(2, [4, 4, 1], activation="tanh")
opt2 = SGD(model2.parameters(), lr=0.1, momentum=0.9, weight_decay=0.001)
hist2 = train(model2, xs, ys, epochs=200, optimizer=opt2)
print("XOR (SGD+momentum) final loss:", round(hist2[-1], 6))
assert hist2[-1] < 0.05

# 6. dot / matvec
a = [Value(1.0), Value(2.0), Value(3.0)]
b = [Value(4.0), Value(5.0), Value(6.0)]
d = dot(a, b)
assert abs(d.data - 32.0) < 1e-6  # 1*4 + 2*5 + 3*6 = 32
print("dot product:", d.data)

W = [[Value(1.0), Value(0.0)], [Value(0.0), Value(1.0)]]
x = [Value(3.0), Value(5.0)]
result = matvec(W, x)
assert result[0].data == 3.0 and result[1].data == 5.0
print("matvec:", [v.data for v in result])

print("\nALL ENHANCEMENT TESTS PASSED")
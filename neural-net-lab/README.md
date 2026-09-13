# Neural Net Lab

A dependency-free multilayer perceptron for studying neural networks from first principles. It implements dense layers, ReLU/tanh/sigmoid/linear activations, mini-batch backpropagation, mean-squared error, deterministic initialization, Adam or SGD optimization, validation loss tracking, and JSON model persistence.

## How it works
Each layer computes `activation(Wx + b)` and caches its input and activation slope. Training applies the chain rule from output to input, averages gradients over each mini-batch, and updates parameters. Adam maintains first and second moment estimates per layer; no NumPy or framework is required.

## Usage
```bash
PYTHONPATH=. python3 -m neural_net_lab.cli --epochs 2000 --save xor.json
```

Python API:
```python
from neural_net_lab import MLP, Adam
x=[[0,0],[0,1],[1,0],[1,1]]; y=[[0],[1],[1],[0]]
net=MLP([2, 4, 1], seed=7)
history=net.train(x, y, epochs=2000, lr=.08, batch_size=4, optimizer=Adam())
print(net.predict([1, 0]), history.losses[-1])
restored=MLP.load('xor.json')
```

Inputs and targets are numeric sequences. Every layer has an explicit positive width; malformed dimensions, empty datasets, mismatched widths, and invalid optimizer parameters raise `ValueError` rather than failing deep inside training. `predict_batch` preserves row order. Training also supports gradient-norm clipping (`clip=`) and validation-based early stopping (`patience=`), useful when experimenting with unstable or noisy datasets.

## Known limitations
The reference implementation intentionally trains with scalar Python loops, so it favors transparency over large-dataset speed. MSE is currently the only loss; classification targets should be encoded as one-hot or sigmoid-compatible values.

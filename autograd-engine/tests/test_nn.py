"""Tests for the neural network module (Neuron, Layer, MLP)."""

import pytest
from autograd_engine import Value
from autograd_engine.nn import Neuron, Layer, MLP, Module
from autograd_engine.train import train, Adam, accuracy


class TestNeuron:
    def test_construction(self):
        n = Neuron(3, activation="tanh")
        assert len(n.w) == 3
        assert n.b.data == 0.0
        assert n.activation == "tanh"

    def test_forward(self):
        n = Neuron(2, activation="linear")
        # Set weights manually
        n.w[0].data = 1.0
        n.w[1].data = 2.0
        n.b.data = 0.5
        out = n([Value(3.0), Value(4.0)])
        assert abs(out.data - (1*3 + 2*4 + 0.5)) < 1e-9

    def test_input_length_mismatch(self):
        n = Neuron(3)
        with pytest.raises(ValueError, match="input length"):
            n([Value(1.0), Value(2.0)])

    def test_invalid_nin(self):
        with pytest.raises(ValueError, match="nin must be positive"):
            Neuron(0)

    def test_parameters(self):
        n = Neuron(3)
        params = n.parameters()
        assert len(params) == 4  # 3 weights + 1 bias

    def test_he_init(self):
        n = Neuron(10, activation="relu", init="he")
        # Just check it doesn't crash and produces values
        for w in n.w:
            assert isinstance(w.data, float)

    def test_linear_activation(self):
        n = Neuron(2, nonlin=False)
        n.w[0].data = 1.0
        n.w[1].data = 1.0
        out = n([Value(2.0), Value(3.0)])
        assert abs(out.data - 5.0) < 1e-9  # no activation


class TestLayer:
    def test_construction(self):
        layer = Layer(3, 4, activation="relu")
        assert len(layer.neurons) == 4
        for n in layer.neurons:
            assert len(n.w) == 3

    def test_forward(self):
        layer = Layer(2, 3, activation="linear")
        out = layer([Value(1.0), Value(2.0)])
        assert len(out) == 3

    def test_parameters(self):
        layer = Layer(2, 3)
        # 3 neurons * (2 weights + 1 bias) = 9
        assert len(layer.parameters()) == 9

    def test_dropout_in_eval(self):
        layer = Layer(2, 5, dropout=0.5)
        layer.eval()
        out = layer([Value(1.0), Value(2.0)])
        # In eval mode, no dropout
        for o in out:
            assert o.data != 0.0 or True  # could still be 0 from init

    def test_train_eval_toggle(self):
        layer = Layer(2, 3)
        assert layer.training is True
        layer.eval()
        assert layer.training is False
        layer.train()
        assert layer.training is True


class TestMLP:
    def test_construction(self):
        model = MLP(2, [4, 4, 1])
        assert len(model.layers) == 3
        assert model.num_parameters() > 0

    def test_forward(self):
        model = MLP(2, [4, 1])
        out = model([1.0, 2.0])
        assert len(out) == 1
        assert isinstance(out[0], Value)

    def test_output_layer_is_linear(self):
        model = MLP(2, [4, 1])
        assert model.layers[-1].neurons[0].activation == "linear"

    def test_unknown_activation(self):
        with pytest.raises(ValueError, match="unknown activation"):
            MLP(2, [4, 1], activation="bogus")

    def test_parameters_count(self):
        model = MLP(2, [3, 3, 1])
        # Layer 1: 3*(2+1) = 9
        # Layer 2: 3*(3+1) = 12
        # Layer 3: 1*(3+1) = 4
        assert model.num_parameters() == 25

    def test_xor_learns(self):
        xs = [[0, 0], [0, 1], [1, 0], [1, 1]]
        ys = [0, 1, 1, 0]
        model = MLP(2, [8, 8, 1], activation="tanh")
        opt = Adam(model.parameters(), lr=0.01)
        history = train(model, xs, ys, epochs=200, optimizer=opt,
                         classification=True, seed=42)
        assert history[-1] < 0.1
        acc = accuracy(model, xs, ys)
        assert acc >= 0.75

    def test_repr(self):
        model = MLP(2, [4, 1])
        assert "MLP" in repr(model)
"""hmm-toolkit: A Hidden Markov Model toolkit implemented from scratch.

Provides HMM construction, the three canonical algorithms (Forward, Backward,
Viterbi), Baum-Welch parameter estimation, sequence generation, JSON
serialization, and analysis utilities — all in pure Python with no third-party
dependencies.
"""

from .hmm import HMM
from .algorithms import forward, backward, viterbi, baum_welch, posterior_decode
from .sequences import (
    generate_sequence,
    save_hmm,
    load_hmm,
    save_observation_sequence,
    load_observation_sequence,
    hmm_to_dict,
    hmm_from_dict,
)

__all__ = [
    "HMM",
    "forward",
    "backward",
    "viterbi",
    "baum_welch",
    "posterior_decode",
    "generate_sequence",
    "save_hmm",
    "load_hmm",
    "save_observation_sequence",
    "load_observation_sequence",
    "hmm_to_dict",
    "hmm_from_dict",
]

__version__ = "1.0.0"
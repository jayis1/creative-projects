"""hmm-toolkit: A Hidden Markov Model toolkit implemented from scratch.

Provides HMM construction, the three canonical algorithms (Forward, Backward,
Viterbi), Baum-Welch parameter estimation (single and multi-sequence), sequence
generation, analysis utilities (classification, entropy, dwell time), and JSON
serialization — all in pure Python with no third-party dependencies.
"""

from .hmm import HMM
from .algorithms import (
    forward,
    backward,
    viterbi,
    baum_welch,
    baum_welch_multi,
    posterior_decode,
)
from .sequences import (
    generate_sequence,
    save_hmm,
    load_hmm,
    save_observation_sequence,
    load_observation_sequence,
    hmm_to_dict,
    hmm_from_dict,
)
from .analysis import (
    sequence_log_likelihood,
    classify_sequence,
    state_entropy,
    symmetric_kl,
    state_durations,
    expected_state_dwell_time,
)

__all__ = [
    # Core
    "HMM",
    # Algorithms
    "forward",
    "backward",
    "viterbi",
    "baum_welch",
    "baum_welch_multi",
    "posterior_decode",
    # Generation & I/O
    "generate_sequence",
    "save_hmm",
    "load_hmm",
    "save_observation_sequence",
    "load_observation_sequence",
    "hmm_to_dict",
    "hmm_from_dict",
    # Analysis
    "sequence_log_likelihood",
    "classify_sequence",
    "state_entropy",
    "symmetric_kl",
    "state_durations",
    "expected_state_dwell_time",
]

__version__ = "2.0.0"
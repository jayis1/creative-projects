"""hmm-toolkit: A Hidden Markov Model toolkit implemented from scratch.

Provides HMM construction, the three canonical algorithms (Forward, Backward,
Viterbi), Baum-Welch parameter estimation (single and multi-sequence), sequence
generation, analysis utilities (classification, entropy, dwell time), JSON
serialization, Gaussian-emission HMMs, Profile HMMs for bioinformatics,
text-based visualisation, advanced training (cross-validation, restarts,
constrained EM, grid search), and a CLI — all in pure Python with no
third-party dependencies.
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
from .gaussian import GaussianHMM, random_gaussian_hmm
from .profile import ProfileHMM, build_profile_hmm
from .viz import (
    transition_diagram,
    viterbi_path_visualization,
    posterior_heatmap,
    entropy_sparkline,
    format_model,
)
from .training import (
    k_fold_cross_validation,
    summarize_cv_results,
    train_with_restarts,
    constrained_baum_welch,
    grid_search,
)
from .config import load_config, save_config
from .logging_config import get_logger, configure_logging

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
    # Gaussian HMM
    "GaussianHMM",
    "random_gaussian_hmm",
    # Profile HMM
    "ProfileHMM",
    "build_profile_hmm",
    # Visualisation
    "transition_diagram",
    "viterbi_path_visualization",
    "posterior_heatmap",
    "entropy_sparkline",
    "format_model",
    # Advanced training
    "k_fold_cross_validation",
    "summarize_cv_results",
    "train_with_restarts",
    "constrained_baum_welch",
    "grid_search",
    # Config & logging
    "load_config",
    "save_config",
    "get_logger",
    "configure_logging",
]

__version__ = "3.0.0"
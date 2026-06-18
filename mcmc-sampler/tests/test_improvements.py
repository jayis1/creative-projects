"""Tests for v2.0 comprehensive improvements: NUTS, Bayesian models,
new distributions, config, analysis, parallel chains."""

import math
import numpy as np
import pytest

from mcmc_sampler import (
    # New samplers
    NUTS,
    # New distributions
    Dirichlet,
    Poisson,
    Bernoulli,
    Categorical,
    TruncatedNormal,
    Logistic,
    Weibull,
    ChiSquared,
    # Bayesian
    BayesianModel,
    # Analysis
    map_estimate,
    laplace_approximation,
    gaussian_kde,
    kde_log_pdf,
    acceptance_rate_diagnostic,
    compare_samplers,
    format_comparison,
    # Config
    MCMCConfig,
    load_config,
    ConfigError,
    # Parallel
    run_chains_parallel,
    ParallelChainResult,
    # Existing
    Normal,
    MultivariateNormal,
    Mixture,
    MetropolisHastings,
    HMCWithAdaptation,
    SliceSampler,
    Target,
    Trace,
    effective_sample_size,
)
from mcmc_sampler.config import TargetConfig, SamplerConfig


# Module-level factory functions for parallel tests (must be picklable)
def _mh_factory(seed):
    return MetropolisHastings(Normal(0, 1), proposal_std=1.0,
                              rng=np.random.default_rng(seed))


def _mh_factory_small(seed):
    return MetropolisHastings(Normal(0, 1), rng=np.random.default_rng(seed))


# =================== NUTS =================== #


class TestNUTS:
    def test_nuts_converges_normal(self):
        target = Normal(3.0, 1.0)
        s = NUTS(target, target_accept=0.65, init_step_size=0.5,
                 rng=np.random.default_rng(1))
        t = s.sample([0.0], n_samples=2000, burn=1000)
        assert abs(t.mean()[0] - 3.0) < 0.3
        assert abs(t.std()[0] - 1.0) < 0.3

    def test_nuts_converges_mvn(self):
        target = MultivariateNormal([1.0, -1.0], [[1.0, 0.0], [0.0, 0.5]])
        s = NUTS(target, target_accept=0.8, init_step_size=0.1,
                 rng=np.random.default_rng(2))
        t = s.sample([0.0, 0.0], n_samples=2000, burn=1000)
        assert abs(t.mean()[0] - 1.0) < 0.35
        assert abs(t.mean()[1] + 1.0) < 0.35

    def test_nuts_step_size_adapts(self):
        target = Normal(0, 1)
        s = NUTS(target, init_step_size=0.5, rng=np.random.default_rng(3))
        s.sample([0.0], n_samples=500, burn=500)
        # Step size should have changed from initial
        assert s.step_size != 0.5

    def test_nuts_mean_tree_depth(self):
        target = Normal(0, 1)
        s = NUTS(target, rng=np.random.default_rng(4))
        s.sample([0.0], n_samples=200, burn=100)
        assert s.mean_tree_depth > 0

    def test_nuts_max_tree_depth_validation(self):
        target = Normal(0, 1)
        with pytest.raises(ValueError, match="max_tree_depth"):
            NUTS(target, max_tree_depth=0)

    def test_nuts_target_accept_validation(self):
        target = Normal(0, 1)
        with pytest.raises(ValueError, match="target_accept"):
            NUTS(target, target_accept=1.5)

    def test_nuts_bad_x0_raises(self):
        target = Normal(0, 1)
        s = NUTS(target, rng=np.random.default_rng(5))
        with pytest.raises(ValueError, match="log_pdf = -inf"):
            # Use Exponential which has -inf at negative values
            from mcmc_sampler import Exponential
            s2 = NUTS(Exponential(1.0), rng=np.random.default_rng(5))
            s2.sample([-1.0], n_samples=100)


# =================== New Distributions =================== #


class TestNewDistributions:
    def test_dirichlet_logpdf(self):
        d = Dirichlet([1.0, 1.0, 1.0])
        # Uniform on simplex: log_pdf([1/3, 1/3, 1/3]) = -log(Z)
        # Z = Gamma(3) / (Gamma(1)*Gamma(1)*Gamma(1)) = 2! = 2
        val = d.log_pdf([1/3, 1/3, 1/3])
        assert math.isfinite(val)

    def test_dirichlet_outside_simplex(self):
        d = Dirichlet([2.0, 2.0])
        assert d.log_pdf([-0.1, 1.1]) == -math.inf
        assert d.log_pdf([0.3, 0.8]) == -math.inf  # sum != 1

    def test_dirichlet_validation(self):
        with pytest.raises(ValueError, match="alpha"):
            Dirichlet([1.0])
        with pytest.raises(ValueError, match="positive"):
            Dirichlet([-1.0, 1.0])

    def test_poisson_logpdf(self):
        d = Poisson(lam=2.0)
        # log P(X=0) = -lambda = -2
        assert d.log_pdf([0.0]) == pytest.approx(-2.0)
        # log P(X=1) = ln(2) - 2
        assert d.log_pdf([1.0]) == pytest.approx(math.log(2) - 2.0)

    def test_poisson_negative(self):
        d = Poisson(1.0)
        assert d.log_pdf([-1.0]) == -math.inf

    def test_bernoulli_logpdf(self):
        d = Bernoulli(p=0.3)
        assert d.log_pdf([1]) == pytest.approx(math.log(0.3))
        assert d.log_pdf([0]) == pytest.approx(math.log(0.7))
        assert d.log_pdf([2]) == -math.inf

    def test_bernoulli_validation(self):
        with pytest.raises(ValueError):
            Bernoulli(p=0.0)
        with pytest.raises(ValueError):
            Bernoulli(p=1.0)

    def test_categorical_logpdf(self):
        d = Categorical([0.2, 0.3, 0.5])
        assert d.log_pdf([0]) == pytest.approx(math.log(0.2))
        assert d.log_pdf([1]) == pytest.approx(math.log(0.3))
        assert d.log_pdf([2]) == pytest.approx(math.log(0.5))
        assert d.log_pdf([3]) == -math.inf

    def test_categorical_validation(self):
        with pytest.raises(ValueError):
            Categorical([0.5])  # too short
        with pytest.raises(ValueError):
            Categorical([0.5, 0.6])  # sum > 1
        with pytest.raises(ValueError):
            Categorical([-0.1, 1.1])  # negative

    def test_truncated_normal_within_bounds(self):
        d = TruncatedNormal(mu=0.0, sigma=1.0, a=-1.0, b=1.0)
        val = d.log_pdf([0.0])
        assert math.isfinite(val)
        # Should be higher than standard normal at 0 (truncation concentrates mass)
        std = Normal(0, 1)
        assert val > std.log_pdf([0.0])

    def test_truncated_normal_outside_bounds(self):
        d = TruncatedNormal(0, 1, 0, 1)
        assert d.log_pdf([-0.1]) == -math.inf
        assert d.log_pdf([1.1]) == -math.inf

    def test_logistic_logpdf(self):
        d = Logistic(0, 1)
        val = d.log_pdf([0.0])
        # Logistic(0,1) pdf at 0 = 1/4, so log = -ln(4)
        assert val == pytest.approx(-math.log(4), abs=1e-6)

    def test_logistic_validation(self):
        with pytest.raises(ValueError):
            Logistic(0, -1)

    def test_weibull_logpdf(self):
        d = Weibull(k=2.0, lam=1.0)
        # Weibull(2,1) pdf at x=1: 2*1*exp(-1) = 2/e
        expected_logpdf = math.log(2) - 1
        assert d.log_pdf([1.0]) == pytest.approx(expected_logpdf, abs=1e-6)

    def test_weibull_negative(self):
        d = Weibull(1, 1)
        assert d.log_pdf([-1.0]) == -math.inf

    def test_chisquared_logpdf(self):
        d = ChiSquared(k=2)
        # Chi-sq(2) is Exp(1/2): pdf(x) = 0.5*exp(-x/2)
        # log_pdf(2) = ln(0.5) - 1
        assert d.log_pdf([2.0]) == pytest.approx(math.log(0.5) - 1.0, abs=1e-6)

    def test_chisquared_non_positive(self):
        d = ChiSquared(3)
        assert d.log_pdf([0.0]) == -math.inf
        assert d.log_pdf([-1.0]) == -math.inf


# =================== Bayesian Model =================== #


class TestBayesianModel:
    def test_bayesian_model_basic(self):
        model = BayesianModel(dim=2)
        model.set_prior(lambda w: 0.0)  # flat
        model.set_likelihood(lambda w: -0.5 * sum(w ** 2))
        target = model.as_target()
        assert target.dim == 2
        val = target.log_pdf([0.0, 0.0])
        assert val == pytest.approx(0.0)

    def test_bayesian_model_dim_mismatch(self):
        model = BayesianModel(dim=3)
        with pytest.raises(ValueError, match="dim"):
            model.log_posterior([1.0, 2.0])

    def test_bayesian_model_inf_minus_inf(self):
        model = BayesianModel(dim=1)
        model.set_prior(lambda w: math.inf)
        model.set_likelihood(lambda w: -math.inf)
        # inf + (-inf) = nan, should return -inf
        assert model.log_posterior([0.0]) == -math.inf

    def test_linear_regression(self):
        rng = np.random.default_rng(42)
        n, d = 50, 2
        true_w = np.array([1.0, -1.0])
        X = rng.normal(0, 1, size=(n, d))
        y = X @ true_w + rng.normal(0, 0.1, size=n)
        model = BayesianModel.linear_regression(X, y, prior_std=10.0, noise_std=0.1)
        assert model.dim == d
        # MAP should be close to true_w
        x_map = map_estimate(model.as_target(), x0=np.zeros(d), lr=0.01, max_iter=500)
        assert abs(x_map[0] - 1.0) < 0.2
        assert abs(x_map[1] + 1.0) < 0.2

    def test_logistic_regression(self):
        rng = np.random.default_rng(42)
        n = 100
        X = rng.normal(0, 1, size=(n, 1))
        true_w = np.array([-0.5, 1.5])  # intercept + slope
        logits = true_w[0] + true_w[1] * X.ravel()
        p = 1.0 / (1.0 + np.exp(-logits))
        y = (rng.random(n) < p).astype(int)
        model = BayesianModel.logistic_regression(X, y, prior_std=5.0)
        assert model.dim == 2  # intercept + 1 slope
        # Should not crash
        val = model.log_posterior([0.0, 0.0])
        assert math.isfinite(val)


# =================== Analysis =================== #


class TestAnalysis:
    def test_map_estimate_normal(self):
        target = Normal(5.0, 1.0)
        x_map = map_estimate(target, x0=[0.0], lr=0.01, max_iter=500)
        assert abs(x_map[0] - 5.0) < 0.5

    def test_map_estimate_bad_x0(self):
        from mcmc_sampler import Exponential
        target = Exponential(1.0)
        with pytest.raises(ValueError, match="-inf"):
            map_estimate(target, x0=[-1.0])

    def test_laplace_approximation(self):
        target = Normal(2.0, 3.0)
        laplace = laplace_approximation(target, x0=[0.0], lr=0.01, max_iter=500)
        assert abs(laplace.mu[0] - 2.0) < 0.5
        assert abs(np.sqrt(laplace.cov[0, 0]) - 3.0) < 1.0

    def test_gaussian_kde(self):
        rng = np.random.default_rng(0)
        samples = rng.normal(0, 1, size=500)
        kde = gaussian_kde(samples)
        # KDE at 0 should be near 1/sqrt(2*pi) ≈ 0.399
        assert abs(kde(0.0) - 0.399) < 0.1
        # KDE at 5 should be near 0
        assert kde(5.0) < 0.01

    def test_kde_log_pdf(self):
        rng = np.random.default_rng(0)
        samples = rng.normal(0, 1, size=500)
        log_density = kde_log_pdf(samples)
        val = log_density([0.0])
        assert math.isfinite(val)
        # Should be close to log(1/sqrt(2*pi)) ≈ -0.919
        assert abs(val - (-0.919)) < 0.3

    def test_kde_empty_raises(self):
        with pytest.raises(ValueError):
            gaussian_kde(np.array([]))

    def test_acceptance_rate_diagnostic_mh(self):
        msg = acceptance_rate_diagnostic(0.05, "mh")
        assert "low" in msg.lower()
        msg = acceptance_rate_diagnostic(0.7, "mh")
        assert "high" in msg.lower()
        msg = acceptance_rate_diagnostic(0.25, "mh")
        assert "good" in msg.lower()

    def test_acceptance_rate_diagnostic_hmc(self):
        msg = acceptance_rate_diagnostic(0.1, "hmc")
        assert "low" in msg.lower()
        msg = acceptance_rate_diagnostic(0.98, "hmc")
        assert "high" in msg.lower()

    def test_acceptance_rate_diagnostic_slice(self):
        msg = acceptance_rate_diagnostic(1.0, "slice")
        assert "ESS" in msg

    def test_compare_samplers(self):
        target = Normal(0, 1)
        samplers = {
            "MH": MetropolisHastings(target, proposal_std=1.0,
                                     rng=np.random.default_rng(0)),
            "NUTS": NUTS(target, rng=np.random.default_rng(0)),
        }
        results = compare_samplers(target, [0.0], samplers,
                                   n_samples=1000, burn=500)
        assert "MH" in results
        assert "NUTS" in results
        assert "ess" in results["MH"]
        assert "time" in results["MH"]

    def test_format_comparison(self):
        target = Normal(0, 1)
        samplers = {
            "MH": MetropolisHastings(target, rng=np.random.default_rng(0)),
        }
        results = compare_samplers(target, [0.0], samplers,
                                   n_samples=500, burn=200)
        text = format_comparison(results)
        assert "Sampler" in text
        assert "MH" in text


# =================== Config =================== #


class TestConfig:
    def test_config_from_dict(self):
        data = {
            "target": {"kind": "normal", "params": {"mu": 2.0, "sigma": 1.0}},
            "sampler": {"algo": "nuts", "params": {"target_accept": 0.8}},
            "run": {"n_samples": 1000, "burn": 500, "seed": 42},
            "output": {"diagnostics": True},
        }
        cfg = MCMCConfig.from_dict(data)
        assert cfg.target.kind == "normal"
        assert cfg.sampler.algo == "nuts"
        assert cfg.run.n_samples == 1000
        assert cfg.run.seed == 42

    def test_config_validate_bad_algo(self):
        data = {"sampler": {"algo": "invalid"}}
        with pytest.raises(ConfigError, match="algo"):
            MCMCConfig.from_dict(data)

    def test_config_validate_bad_n_samples(self):
        data = {"run": {"n_samples": -1}}
        with pytest.raises(ConfigError, match="n_samples"):
            MCMCConfig.from_dict(data)

    def test_config_from_json_file(self, tmp_path):
        import json
        data = {
            "target": {"kind": "normal", "params": {"mu": 1.0}},
            "sampler": {"algo": "mh"},
            "run": {"n_samples": 100, "burn": 50},
        }
        p = tmp_path / "cfg.json"
        p.write_text(json.dumps(data))
        cfg = load_config(str(p))
        assert cfg.target.kind == "normal"

    def test_config_from_yaml_file(self, tmp_path):
        pytest.importorskip("yaml")
        import yaml
        data = {
            "target": {"kind": "beta", "params": {"alpha": 2.0, "beta": 3.0}},
            "sampler": {"algo": "slice"},
            "run": {"n_samples": 100, "burn": 50},
        }
        p = tmp_path / "cfg.yaml"
        p.write_text(yaml.dump(data))
        cfg = load_config(str(p))
        assert cfg.target.kind == "beta"
        assert cfg.sampler.algo == "slice"

    def test_config_from_toml_file(self, tmp_path):
        try:
            import tomllib
        except ImportError:
            try:
                import tomli
            except ImportError:
                pytest.skip("No TOML support")
        toml_text = """
target.kind = "normal"
target.params.mu = 1.0
sampler.algo = "mh"
run.n_samples = 100
run.burn = 50
"""
        p = tmp_path / "cfg.toml"
        p.write_text(toml_text)
        cfg = load_config(str(p))
        assert cfg.target.kind == "normal"

    def test_config_unsupported_format(self, tmp_path):
        p = tmp_path / "cfg.txt"
        p.write_text("hello")
        with pytest.raises(ConfigError, match="Unsupported"):
            load_config(str(p))

    def test_config_to_json(self):
        cfg = MCMCConfig()
        text = cfg.to_json()
        import json
        data = json.loads(text)
        assert "target" in data
        assert "sampler" in data

    def test_config_to_dict_roundtrip(self):
        cfg = MCMCConfig()
        d = cfg.to_dict()
        cfg2 = MCMCConfig.from_dict(d)
        assert cfg2.target.kind == cfg.target.kind
        assert cfg2.sampler.algo == cfg.sampler.algo


# =================== Parallel Chains =================== #


class TestParallelChains:
    def test_run_chains_parallel(self):
        result = run_chains_parallel(_mh_factory, [[-5.0], [0.0], [5.0]],
                                     n_samples=1000, burn=500)
        assert result.n_chains == 3
        rhats = result.rhat()
        assert all(r < 1.1 for r in rhats)

    def test_parallel_needs_two_chains(self):
        with pytest.raises(ValueError, match="at least 2"):
            run_chains_parallel(_mh_factory_small, [[0.0]])

    def test_parallel_summary(self):
        result = run_chains_parallel(_mh_factory, [[-3.0], [3.0]],
                                     n_samples=1000, burn=500)
        summary = result.summary()
        assert "n_chains" in summary
        assert "rhat" in summary
        assert summary["n_chains"] == 2

    def test_parallel_combined_trace(self):
        result = run_chains_parallel(_mh_factory, [[0.0], [1.0]],
                                     n_samples=500, burn=200)
        combined = result.combined_trace()
        assert combined.n_samples == 1000


# =================== CLI =================== #


class TestCLI:
    def test_cli_sample_nuts(self):
        from mcmc_sampler.cli import main
        ret = main(["sample", "--algo", "nuts", "--dist", "normal",
                    "--mu", "2", "--n", "500", "--burn", "200", "--seed", "42"])
        assert ret == 0

    def test_cli_map(self):
        from mcmc_sampler.cli import main
        ret = main(["map", "--dist", "normal", "--mu", "5"])
        assert ret == 0

    def test_cli_diagnostics(self, tmp_path):
        from mcmc_sampler.cli import main
        # First create a trace
        target = Normal(0, 1)
        s = MetropolisHastings(target, rng=np.random.default_rng(0))
        trace = s.sample([0.0], n_samples=500, burn=100)
        p = tmp_path / "t.json"
        trace.to_json(str(p))
        ret = main(["diagnostics", str(p)])
        assert ret == 0

    def test_cli_compare(self):
        from mcmc_sampler.cli import main
        ret = main(["compare", "--dist", "normal", "--n", "500", "--burn", "200",
                    "--algos", "mh", "slice"])
        assert ret == 0
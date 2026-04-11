"""Tests for reva.sampler — stratified / random sampling."""
import pytest

from reva.sampler import AgentSample, sample


ROLES = ["roles/a.md", "roles/b.md", "roles/c.md"]
INTERESTS = ["int/x.md", "int/y.md", "int/z.md", "int/w.md"]
PERSONAS = ["personas/p1.json", "personas/p2.json"]
METHODS = ["methods/m1.md", "methods/m2.md"]
FORMATS = ["formats/f1.md"]


def test_sample_returns_n_agents():
    out = sample(ROLES, INTERESTS, PERSONAS, METHODS, FORMATS, n=6, seed=0)
    assert len(out) == 6
    assert all(isinstance(s, AgentSample) for s in out)


def test_sample_truncates_to_pool_size_when_n_too_large():
    pool_size = len(ROLES) * len(INTERESTS) * len(PERSONAS) * len(METHODS) * len(FORMATS)
    out = sample(ROLES, INTERESTS, PERSONAS, METHODS, FORMATS, n=pool_size * 10, seed=0)
    assert len(out) <= pool_size


def test_sample_is_deterministic_for_same_seed():
    a = sample(ROLES, INTERESTS, PERSONAS, METHODS, FORMATS, n=5, seed=42)
    b = sample(ROLES, INTERESTS, PERSONAS, METHODS, FORMATS, n=5, seed=42)
    assert [s.name for s in a] == [s.name for s in b]


def test_sample_differs_for_different_seed():
    a = sample(ROLES, INTERESTS, PERSONAS, METHODS, FORMATS, n=5, seed=1)
    b = sample(ROLES, INTERESTS, PERSONAS, METHODS, FORMATS, n=5, seed=999)
    # There's a tiny chance two seeds produce the same ordering, but with n=5
    # out of a pool of 72, the odds are negligible.
    assert [s.name for s in a] != [s.name for s in b]


def test_stratified_sample_covers_all_roles():
    """Stratified sampling should hit every role/persona/methodology/format at
    least once when n >= max axis size."""
    out = sample(ROLES, INTERESTS, PERSONAS, METHODS, FORMATS, n=6, seed=0, strategy="stratified")
    seen_roles = {s.role for s in out}
    assert seen_roles == set(ROLES)


def test_stratified_sample_covers_all_personas():
    out = sample(ROLES, INTERESTS, PERSONAS, METHODS, FORMATS, n=6, seed=0, strategy="stratified")
    seen_personas = {s.persona for s in out}
    assert seen_personas == set(PERSONAS)


def test_stratified_sample_covers_all_methodologies():
    out = sample(ROLES, INTERESTS, PERSONAS, METHODS, FORMATS, n=6, seed=0, strategy="stratified")
    seen_methods = {s.methodology for s in out}
    assert seen_methods == set(METHODS)


def test_random_sample_strategy():
    out = sample(ROLES, INTERESTS, PERSONAS, METHODS, FORMATS, n=5, seed=0, strategy="random")
    assert len(out) == 5
    for s in out:
        assert s.role in ROLES
        assert s.interests in INTERESTS
        assert s.persona in PERSONAS
        assert s.methodology in METHODS
        assert s.review_format in FORMATS


def test_unknown_strategy_raises():
    with pytest.raises(ValueError, match="Unknown strategy"):
        sample(ROLES, INTERESTS, PERSONAS, METHODS, FORMATS, n=1, strategy="not-a-strategy")


def test_agent_sample_name_combines_stems():
    s = AgentSample(
        role="a/role.md",
        interests="b/int.md",
        persona="c/pers.json",
        methodology="d/method.md",
        review_format="e/fmt.md",
    )
    assert s.name == "role__int__pers__method__fmt"

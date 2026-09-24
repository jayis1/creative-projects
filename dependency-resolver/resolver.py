#!/usr/bin/env python3
"""Small, deterministic dependency resolver with semver constraints."""
from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
from dataclasses import dataclass, field
from functools import total_ordering
from typing import Iterable


@total_ordering
@dataclass(frozen=True)
class Version:
    """Semantic version with prerelease ordering (build metadata is ignored)."""
    major: int
    minor: int = 0
    patch: int = 0
    prerelease: tuple[str, ...] = ()

    _pattern = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?$")

    @classmethod
    def parse(cls, value: str) -> "Version":
        match = cls._pattern.fullmatch(value.strip())
        if not match:
            raise ValueError(f"invalid semantic version: {value!r}")
        pre = tuple(match.group(4).split(".")) if match.group(4) else ()
        return cls(int(match.group(1)), int(match.group(2)), int(match.group(3)), pre)

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}" + ("-" + ".".join(self.prerelease) if self.prerelease else "")

    def _key(self):
        # Release versions sort after all prereleases of the same core version.
        pre = (1,) if not self.prerelease else (0, tuple((0, int(x)) if x.isdigit() else (1, x) for x in self.prerelease))
        return self.major, self.minor, self.patch, pre

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return self._key() < other._key()


@dataclass(frozen=True)
class Requirement:
    name: str
    expression: str = "*"

    def matches(self, version: Version) -> bool:
        expr = self.expression.strip()
        if expr in ("", "*"):
            return not version.prerelease
        # Space/comma separated comparisons are an AND.
        terms = [t for t in re.split(r"\s*,\s*|\s+", expr) if t]
        return all(self._term_matches(term, version) for term in terms)

    @staticmethod
    def _term_matches(term: str, version: Version) -> bool:
        for op in ("^", "~", ">=", "<=", ">", "<", "="):
            if term.startswith(op):
                target = Version.parse(term[len(op):])
                if op == "^":
                    upper = Version(target.major + 1, 0, 0) if target.major else Version(0, target.minor + 1, 0)
                    return version >= target and version < upper
                if op == "~":
                    return version >= target and version < Version(target.major, target.minor + 1, 0)
                return {">=": version >= target, "<=": version <= target, ">": version > target, "<": version < target, "=": version == target}[op]
        if "x" in term.lower() or "*" in term:
            fields = term.replace("*", "x").split(".")
            vals = (version.major, version.minor, version.patch)
            return all(part.lower() == "x" or int(part) == vals[i] for i, part in enumerate(fields))
        return version == Version.parse(term)


@dataclass(frozen=True)
class Package:
    name: str
    version: Version
    dependencies: tuple[Requirement, ...] = ()

    @classmethod
    def from_dict(cls, data: dict) -> "Package":
        deps = tuple(Requirement(n, e) for n, e in data.get("dependencies", {}).items())
        return cls(data["name"], Version.parse(data["version"]), deps)


class ResolutionError(Exception):
    """Raised when no version assignment satisfies all requirements."""


@dataclass
class PackageIndex:
    packages: dict[str, list[Package]] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "PackageIndex":
        index = cls()
        for item in data.get("packages", []):
            package = Package.from_dict(item)
            if any(existing.version == package.version for existing in index.packages.get(package.name, [])):
                raise ValueError(f"duplicate package version: {package.name}@{package.version}")
            index.packages.setdefault(package.name, []).append(package)
        for versions in index.packages.values():
            versions.sort(key=lambda p: p.version, reverse=True)
        return index

    def candidates(self, name: str, requirements: Iterable[Requirement]) -> list[Package]:
        reqs = list(requirements)
        return [p for p in self.packages.get(name, []) if all(r.matches(p.version) for r in reqs)]


class Resolver:
    """Backtracking resolver using most-constrained-first package selection."""

    def __init__(self, index: PackageIndex):
        self.index = index
        self.decisions = 0

    def resolve(self, roots: Iterable[Requirement]) -> dict[str, Package]:
        requirements: dict[str, list[Requirement]] = {}
        for req in roots:
            requirements.setdefault(req.name, []).append(req)
        result = self._search(requirements, {})
        if result is None:
            details = "; ".join(f"{n}: {', '.join(r.expression for r in rs)}" for n, rs in sorted(requirements.items()))
            raise ResolutionError(f"no compatible solution ({details})")
        return result

    def _search(self, requirements: dict[str, list[Requirement]], chosen: dict[str, Package]) -> dict[str, Package] | None:
        pending = [n for n in requirements if n not in chosen]
        if not pending:
            return chosen
        candidates = {n: self.index.candidates(n, requirements[n]) for n in pending}
        name = min(pending, key=lambda n: (len(candidates[n]), n))
        if not candidates[name]:
            return None
        for package in candidates[name]:
            self.decisions += 1
            next_requirements = {n: list(rs) for n, rs in requirements.items()}
            valid = True
            for req in package.dependencies:
                next_requirements.setdefault(req.name, []).append(req)
                if req.name in chosen and not req.matches(chosen[req.name].version):
                    valid = False
                    break
            if valid:
                attempt = self._search(next_requirements, {**chosen, name: package})
                if attempt is not None:
                    return attempt
        return None


def load_requirements(data: dict) -> list[Requirement]:
    return [Requirement(name, expression) for name, expression in data.get("dependencies", {}).items()]


def write_lockfile(path: str, resolved: dict[str, Package], decisions: int) -> None:
    """Write a lockfile atomically so an interrupted run cannot truncate it."""
    target = os.path.abspath(path)
    directory = os.path.dirname(target) or "."
    payload = {"packages": {name: {"version": str(pkg.version), "dependencies": {r.name: r.expression for r in pkg.dependencies}} for name, pkg in sorted(resolved.items())}, "decisions": decisions}
    fd, temporary = tempfile.mkstemp(prefix=".resolver-", suffix=".tmp", dir=directory, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temporary, target)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Resolve a package graph deterministically")
    parser.add_argument("manifest", help="JSON file with dependencies and packages")
    parser.add_argument("--lockfile", help="also write an atomic JSON lockfile")
    args = parser.parse_args(argv)
    try:
        with open(args.manifest, encoding="utf-8") as handle:
            document = json.load(handle)
        resolver = Resolver(PackageIndex.from_dict(document))
        resolved = resolver.resolve(load_requirements(document))
        if args.lockfile:
            write_lockfile(args.lockfile, resolved, resolver.decisions)
    except (OSError, json.JSONDecodeError, ValueError, ResolutionError) as exc:
        parser.error(str(exc))
    print(json.dumps({name: str(pkg.version) for name, pkg in sorted(resolved.items())}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

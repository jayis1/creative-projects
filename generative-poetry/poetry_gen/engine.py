"""High-level PoetryEngine: compose poems with metadata."""

from __future__ import annotations
import random
from dataclasses import dataclass
from .vocabulary import Vocabulary
from . import forms


FORMS = ["haiku", "limerick", "free_verse", "acrostic", "sonnet"]


@dataclass
class Poem:
    form: str
    theme: str
    text: str
    keyword: str | None = None  # for acrostic

    def __str__(self) -> str:
        header = f"[{self.form.upper()} / {self.theme}]"
        if self.keyword:
            header += f"  keyword: {self.keyword}"
        return f"{header}\n\n{self.text}"


class PoetryEngine:
    """Generate poems across forms and themes.

    Parameters
    ----------
    theme:
        One of the built-in themes (``Vocabulary.themes()``) or None for random.
    seed:
        Optional random seed for reproducibility.
    """

    def __init__(self, theme: str | None = None, seed: int | None = None) -> None:
        if seed is not None:
            random.seed(seed)
        if theme is None:
            theme = random.choice(Vocabulary.themes())
        self.theme = theme
        self._vocab = Vocabulary(theme=theme)

    # ------------------------------------------------------------------ #
    # Per-form methods                                                     #
    # ------------------------------------------------------------------ #

    def haiku(self) -> Poem:
        text = forms.haiku(self._vocab)
        return Poem(form="haiku", theme=self.theme, text=text)

    def limerick(self) -> Poem:
        text = forms.limerick(self._vocab)
        return Poem(form="limerick", theme=self.theme, text=text)

    def free_verse(self, n_lines: int | None = None) -> Poem:
        text = forms.free_verse(self._vocab, n_lines=n_lines)
        return Poem(form="free_verse", theme=self.theme, text=text)

    def acrostic(self, keyword: str | None = None) -> Poem:
        if keyword is None:
            keyword = random.choice(self._vocab.nouns)
        text = forms.acrostic(self._vocab, keyword=keyword)
        return Poem(form="acrostic", theme=self.theme, text=text, keyword=keyword)

    def sonnet(self) -> Poem:
        text = forms.sonnet(self._vocab)
        return Poem(form="sonnet", theme=self.theme, text=text)

    # ------------------------------------------------------------------ #
    # Convenience                                                          #
    # ------------------------------------------------------------------ #

    def random_poem(self, form: str | None = None) -> Poem:
        """Return a poem in *form* (or a randomly chosen form)."""
        if form is None:
            form = random.choice(FORMS)
        method = getattr(self, form, None)
        if method is None:
            raise ValueError(f"Unknown form {form!r}. Choose from {FORMS}")
        return method()

    def collection(self, n: int = 5, form: str | None = None) -> list[Poem]:
        """Generate *n* poems."""
        return [self.random_poem(form=form) for _ in range(n)]

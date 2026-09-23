"""Forms package — expose all generators."""

from .haiku import generate as haiku
from .limerick import generate as limerick
from .free_verse import generate as free_verse
from .acrostic import generate as acrostic
from .sonnet import generate as sonnet

__all__ = ["haiku", "limerick", "free_verse", "acrostic", "sonnet"]

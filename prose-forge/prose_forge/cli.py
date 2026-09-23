"""CLI for Prose Forge — 10 subcommands for procedural narrative generation."""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .character import CharacterForge
from .grammar import Grammar, BUILTIN_GRAMMAR
from .markov import MarkovChain
from .names import NameGenerator
from .poetry import Poet
from .scene import SceneAssembler
from .story import StoryArchitect
from .world import WorldSeeder


def _json_output(obj) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False)


def cmd_story(args: argparse.Namespace) -> None:
    architect = StoryArchitect(seed=args.seed)
    story = architect.generate()
    if args.json:
        print(_json_output(story.to_dict()))
    else:
        print(story.outline())


def cmd_character(args: argparse.Namespace) -> None:
    forge = CharacterForge(seed=args.seed)
    if args.count > 1:
        cast = forge.generate_cast(count=args.count)
        if args.json:
            print(_json_output([c.to_dict() for c in cast]))
        else:
            for c in cast:
                print(c.summary())
                print()
    else:
        char = forge.generate()
        if args.json:
            print(_json_output(char.to_dict()))
        else:
            print(char.summary())


def cmd_poem(args: argparse.Namespace) -> None:
    poet = Poet(seed=args.seed)
    if args.form == "haiku":
        result = poet.haiku()
    elif args.form == "tanka":
        result = poet.tanka()
    elif args.form == "limerick":
        result = poet.limerick()
    elif args.form == "sonnet":
        result = poet.sonnet()
    elif args.form == "free":
        result = poet.free_verse(lines=args.lines)
    else:
        print(f"Unknown form: {args.form}", file=sys.stderr)
        sys.exit(1)
    print(result)


def cmd_names(args: argparse.Namespace) -> None:
    gen = NameGenerator(seed=args.seed)
    names = gen.generate_many(culture=args.culture, count=args.count, with_family=not args.first_only)
    if args.json:
        print(_json_output(names))
    else:
        for name in names:
            print(name)


def cmd_markov(args: argparse.Namespace) -> None:
    if not args.train:
        print("Error: --train FILE is required for markov", file=sys.stderr)
        sys.exit(1)
    with open(args.train, "r", encoding="utf-8", errors="replace") as f:
        corpus = f.read()
    chain = MarkovChain(order=args.order, level=args.level, seed=args.seed)
    chain.train(corpus)
    text = chain.generate(length=args.length)
    print(text)


def cmd_scene(args: argparse.Namespace) -> None:
    assembler = SceneAssembler(seed=args.seed)
    scene = assembler.generate(num_paragraphs=args.paragraphs)
    if args.json:
        print(_json_output(scene.to_dict()))
    else:
        print(scene.text())


def cmd_world(args: argparse.Namespace) -> None:
    seeder = WorldSeeder(seed=args.seed)
    world = seeder.generate()
    if args.json:
        print(_json_output(world.to_dict()))
    else:
        print(world.description())


def cmd_grammar(args: argparse.Namespace) -> None:
    grammar = Grammar(BUILTIN_GRAMMAR, seed=args.seed)
    result = grammar.generate(start="start")
    if args.json:
        print(_json_output({"generated": result}))
    else:
        print(result)


def cmd_version(args: argparse.Namespace) -> None:
    print(f"prose-forge {__version__}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="prose-forge",
        description="Procedural narrative and text generation engine",
    )
    parser.add_argument("--version", action="store_true", help="Show version and exit")
    subparsers = parser.add_subparsers(dest="command")

    # story
    p_story = subparsers.add_parser("story", help="Generate a three-act story outline")
    p_story.add_argument("--seed", type=int, default=None)
    p_story.add_argument("--json", action="store_true", help="Output as JSON")
    p_story.set_defaults(func=cmd_story)

    # character
    p_char = subparsers.add_parser("character", help="Generate procedural characters")
    p_char.add_argument("--seed", type=int, default=None)
    p_char.add_argument("--count", type=int, default=1, help="Number of characters")
    p_char.add_argument("--json", action="store_true")
    p_char.set_defaults(func=cmd_character)

    # poem
    p_poem = subparsers.add_parser("poem", help="Generate poetry")
    p_poem.add_argument("--form", choices=["haiku", "tanka", "limerick", "sonnet", "free"], default="haiku")
    p_poem.add_argument("--seed", type=int, default=None)
    p_poem.add_argument("--lines", type=int, default=6, help="Lines for free verse")
    p_poem.set_defaults(func=cmd_poem)

    # names
    p_names = subparsers.add_parser("names", help="Generate culture-aware names")
    p_names.add_argument("--culture", default="fantasy", help="Culture: fantasy, sci_fi, norse, japanese, arabic")
    p_names.add_argument("--count", type=int, default=5)
    p_names.add_argument("--seed", type=int, default=None)
    p_names.add_argument("--first-only", action="store_true", help="Omit family name")
    p_names.add_argument("--json", action="store_true")
    p_names.set_defaults(func=cmd_names)

    # markov
    p_markov = subparsers.add_parser("markov", help="Markov chain text synthesis")
    p_markov.add_argument("--train", metavar="FILE", help="Training corpus file")
    p_markov.add_argument("--order", type=int, default=2, help="N-gram order")
    p_markov.add_argument("--level", choices=["word", "char"], default="word")
    p_markov.add_argument("--length", type=int, default=100, help="Output length (tokens)")
    p_markov.add_argument("--seed", type=int, default=None)
    p_markov.set_defaults(func=cmd_markov)

    # scene
    p_scene = subparsers.add_parser("scene", help="Assemble a narrative scene")
    p_scene.add_argument("--seed", type=int, default=None)
    p_scene.add_argument("--paragraphs", type=int, default=5)
    p_scene.add_argument("--json", action="store_true")
    p_scene.set_defaults(func=cmd_scene)

    # world
    p_world = subparsers.add_parser("world", help="Generate a world setting")
    p_world.add_argument("--seed", type=int, default=None)
    p_world.add_argument("--json", action="store_true")
    p_world.set_defaults(func=cmd_world)

    # grammar
    p_gram = subparsers.add_parser("grammar", help="Generate text from the built-in grammar")
    p_gram.add_argument("--seed", type=int, default=None)
    p_gram.add_argument("--json", action="store_true")
    p_gram.set_defaults(func=cmd_grammar)

    # version
    p_ver = subparsers.add_parser("version", help="Show version")
    p_ver.set_defaults(func=cmd_version)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.version:
        print(f"prose-forge {__version__}")
        return 0
    if not hasattr(args, "func"):
        parser.print_help()
        return 1
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
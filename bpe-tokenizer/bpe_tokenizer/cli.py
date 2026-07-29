"""Command-line interface for the BPE tokenizer.

Provides 12 subcommands for training, encoding, decoding, analysis,
comparison, and configuration management.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from .tokenizer import BPETokenizer, TrainingConfig
from .encoder import bpe_dropout, BPESentencePiece
from .exceptions import BPETokenizerError
from .logging_setup import configure_logging

logger = logging.getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="bpe-tokenizer",
        description="Byte Pair Encoding tokenizer — train, encode, decode, analyze, compare.",
        epilog="Use 'bpe-tokenizer <command> --help' for command-specific options.",
    )
    p.add_argument("-v", "--verbose", action="count", default=0,
                   help="Increase logging verbosity (-v: INFO, -vv: DEBUG).")
    p.add_argument("-q", "--quiet", action="store_true",
                   help="Suppress all logging output except errors.")
    sub = p.add_subparsers(dest="command", required=True)

    # train
    pt = sub.add_parser("train", help="Train a tokenizer on a text file.")
    pt.add_argument("input", help="Input text file (UTF-8).")
    pt.add_argument("-o", "--output", required=True, help="Output tokenizer JSON path.")
    pt.add_argument("--vocab-size", type=int, default=1000)
    pt.add_argument("--byte-mode", action="store_true", help="Use byte-level BPE (GPT-2 style).")
    pt.add_argument("--pretokenizer", default="gpt4",
                    choices=["gpt2", "gpt4", "llama3", "whitespace", "none"])
    pt.add_argument("--min-frequency", type=int, default=2)
    pt.add_argument("--verbose", action="store_true", help="Verbose training output.")
    pt.add_argument("--no-specials", action="store_true", help="Don't reserve special tokens.")
    pt.add_argument("--lowercase", action="store_true", help="Lowercase all text during training.")
    pt.add_argument("--strip-accents", action="store_true", help="Strip accents (NFD + remove diacritics).")
    pt.add_argument("--nfc", action="store_true", help="Apply NFC Unicode normalization.")
    pt.add_argument("--progress", action="store_true", help="Print progress during training.")

    # train-config
    ptc = sub.add_parser("train-config", help="Train using a JSON/TOML config file.")
    ptc.add_argument("config", help="Config file path (.json or .toml).")
    ptc.add_argument("input", help="Input corpus text file (UTF-8).")
    ptc.add_argument("-o", "--output", required=True, help="Output tokenizer JSON path.")
    ptc.add_argument("--progress", action="store_true", help="Print progress during training.")

    # encode
    pe = sub.add_parser("encode", help="Encode text to token ids.")
    pe.add_argument("text", help="Text to encode (or use --file).")
    pe.add_argument("--file", help="Read text from a file instead.")
    pe.add_argument("-m", "--model", required=True, help="Tokenizer JSON path.")
    pe.add_argument("--bos", action="store_true", help="Add BOS token.")
    pe.add_argument("--eos", action="store_true", help="Add EOS token.")
    pe.add_argument("--pieces", action="store_true", help="Print pieces alongside ids.")
    pe.add_argument("--max-length", type=int, default=None, help="Truncate to this length.")
    pe.add_argument("--pad", action="store_true", help="Pad to max-length.")
    pe.add_argument("--attention-mask", action="store_true", help="Generate attention mask.")

    # decode
    pd = sub.add_parser("decode", help="Decode token ids to text.")
    pd.add_argument("ids", nargs="*", type=int, help="Token ids to decode.")
    pd.add_argument("-m", "--model", required=True, help="Tokenizer JSON path.")
    pd.add_argument("--file", help="Read ids from a JSON file (list of ints).")

    # batch
    pb = sub.add_parser("batch", help="Encode multiple texts from a file.")
    pb.add_argument("input", help="Input file (one text per line).")
    pb.add_argument("-o", "--output", help="Output JSON file (default: stdout).")
    pb.add_argument("-m", "--model", required=True, help="Tokenizer JSON path.")
    pb.add_argument("--bos", action="store_true")
    pb.add_argument("--eos", action="store_true")
    pb.add_argument("--pad", action="store_true", help="Pad to max length.")
    pb.add_argument("--max-length", type=int, default=None)

    # dropout
    pdo = sub.add_parser("dropout", help="BPE-dropout encoding (stochastic).")
    pdo.add_argument("text", help="Text to encode.")
    pdo.add_argument("-m", "--model", required=True, help="Tokenizer JSON path.")
    pdo.add_argument("--p", type=float, default=0.1, help="Dropout probability.")
    pdo.add_argument("--n", type=int, default=5, help="Number of stochastic samples.")
    pdo.add_argument("--seed", type=int, default=None)

    # viterbi
    pv = sub.add_parser("viterbi", help="Viterbi (Unigram) encoding.")
    pv.add_argument("text", help="Text to encode.")
    pv.add_argument("-m", "--model", required=True, help="Tokenizer JSON path.")

    # wordpiece
    pw = sub.add_parser("wordpiece", help="WordPiece (BERT-style) encoding.")
    pw.add_argument("text", help="Text to encode.")
    pw.add_argument("-m", "--model", required=True, help="Tokenizer JSON path.")
    pw.add_argument("--no-continuation-marker", action="store_true",
                    help="Don't use ## continuation markers.")

    # stats
    ps = sub.add_parser("stats", help="Show tokenizer statistics.")
    ps.add_argument("-m", "--model", required=True, help="Tokenizer JSON path.")

    # roundtrip
    pr = sub.add_parser("roundtrip", help="Round-trip test: encode then decode.")
    pr.add_argument("text", help="Text to test.")
    pr.add_argument("-m", "--model", required=True, help="Tokenizer JSON path.")

    # analyze
    pa = sub.add_parser("analyze", help="Analyze tokenizer quality on a corpus.")
    pa.add_argument("input", help="Corpus text file for analysis.")
    pa.add_argument("-m", "--model", required=True, help="Tokenizer JSON path.")

    # compare
    pcm = sub.add_parser("compare", help="Compare two tokenizers on a corpus.")
    pcm.add_argument("input", help="Corpus text file (one text per line).")
    pcm.add_argument("-a", "--model-a", required=True, help="First tokenizer JSON.")
    pcm.add_argument("-b", "--model-b", required=True, help="Second tokenizer JSON.")

    return p


def _setup_logging(args: argparse.Namespace) -> None:
    if args.quiet:
        level = logging.ERROR
    elif args.verbose >= 2:
        level = logging.DEBUG
    elif args.verbose >= 1:
        level = logging.INFO
    else:
        level = logging.WARNING
    configure_logging(level=level)


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    _setup_logging(args)

    try:
        return _dispatch(args, parser)
    except BPETokenizerError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except FileNotFoundError as e:
        print(f"File not found: {e}", file=sys.stderr)
        return 1


def _dispatch(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if args.command == "train":
        return _cmd_train(args)
    elif args.command == "train-config":
        return _cmd_train_config(args)
    elif args.command == "encode":
        return _cmd_encode(args)
    elif args.command == "decode":
        return _cmd_decode(args)
    elif args.command == "batch":
        return _cmd_batch(args)
    elif args.command == "dropout":
        return _cmd_dropout(args)
    elif args.command == "viterbi":
        return _cmd_viterbi(args)
    elif args.command == "wordpiece":
        return _cmd_wordpiece(args)
    elif args.command == "stats":
        return _cmd_stats(args)
    elif args.command == "roundtrip":
        return _cmd_roundtrip(args)
    elif args.command == "analyze":
        return _cmd_analyze(args)
    elif args.command == "compare":
        return _cmd_compare(args)
    else:
        parser.print_help()
        return 1


def _cmd_train(args: argparse.Namespace) -> int:
    from .vocab import DEFAULT_SPECIALS
    from .normalizer import Normalization
    from .progress import create_print_callback
    text = Path(args.input).read_text(encoding="utf-8")
    specials = () if args.no_specials else DEFAULT_SPECIALS
    # Build normalizer flags.
    norm = Normalization.NONE
    if args.lowercase:
        norm |= Normalization.LOWERCASE
    if args.strip_accents:
        norm |= Normalization.NFD | Normalization.STRIP_ACCENTS
    if args.nfc:
        norm |= Normalization.NFC
    cfg = TrainingConfig(
        vocab_size=args.vocab_size,
        byte_mode=args.byte_mode,
        pretokenizer=args.pretokenizer,
        specials=specials,
        min_frequency=args.min_frequency,
        verbose=args.verbose,
        normalizer_flags=int(norm.value),
    )
    callback = create_print_callback(every=50) if args.progress else None
    tok = BPETokenizer()
    tok.train(text, cfg, progress_callback=callback)
    tok.save(args.output)
    st = tok.stats()
    print(f"Trained: vocab_size={st.vocab_size}, merges={st.n_merges}, "
          f"specials={st.n_specials}, byte_mode={st.byte_mode}")
    print(f"Saved to: {args.output}")
    return 0


def _cmd_train_config(args: argparse.Namespace) -> int:
    from .config import load_config
    from .progress import create_print_callback
    config = load_config(args.config)
    cfg = config.to_training_config()
    callback = create_print_callback(every=50) if args.progress else None
    tok = BPETokenizer()
    tok.train_from_file(args.input, cfg, progress_callback=callback)
    tok.save(args.output)
    st = tok.stats()
    print(f"Trained: vocab_size={st.vocab_size}, merges={st.n_merges}, "
          f"specials={st.n_specials}, byte_mode={st.byte_mode}")
    print(f"Saved to: {args.output}")
    return 0


def _cmd_encode(args: argparse.Namespace) -> int:
    tok = BPETokenizer.load(args.model)
    text = Path(args.file).read_text(encoding="utf-8") if args.file else args.text

    if args.max_length or args.attention_mask or args.pad:
        result = tok.encode_advanced(
            text,
            max_length=args.max_length,
            return_attention_mask=args.attention_mask,
            pad_id=0 if args.pad else None,
        )
        if args.pieces:
            pieces = tok.id_to_pieces(result["input_ids"])
            for i, (tid, piece) in enumerate(zip(result["input_ids"], pieces)):
                print(f"{i:4d}  {tid:6d}  {piece!r}")
        else:
            print(json.dumps(result))
    else:
        ids = tok.encode(text, add_bos=args.bos, add_eos=args.eos)
        if args.pieces:
            pieces = tok.id_to_pieces(ids)
            for i, (tid, piece) in enumerate(zip(ids, pieces)):
                print(f"{i:4d}  {tid:6d}  {piece!r}")
        else:
            print(json.dumps(ids))
    return 0


def _cmd_decode(args: argparse.Namespace) -> int:
    tok = BPETokenizer.load(args.model)
    if args.file:
        ids = json.loads(Path(args.file).read_text())
    else:
        ids = args.ids
    text = tok.decode(ids)
    print(text)
    return 0


def _cmd_batch(args: argparse.Namespace) -> int:
    tok = BPETokenizer.load(args.model)
    lines = Path(args.input).read_text(encoding="utf-8").splitlines()
    results = tok.encode_batch(
        lines, add_bos=args.bos, add_eos=args.eos,
        padding=args.pad, max_length=args.max_length,
    )
    output = json.dumps(results, indent=2)
    if args.output:
        Path(args.output).write_text(output)
        print(f"Wrote {len(results)} encodings to {args.output}")
    else:
        print(output)
    return 0


def _cmd_dropout(args: argparse.Namespace) -> int:
    import random
    tok = BPETokenizer.load(args.model)
    rng = random.Random(args.seed)
    for _ in range(args.n):
        ids = bpe_dropout(tok, args.text, dropout=args.p, rng=rng)
        pieces = tok.id_to_pieces(ids)
        print(f"  ids={ids}")
        print(f"  pieces={pieces}")
    return 0


def _cmd_viterbi(args: argparse.Namespace) -> int:
    tok = BPETokenizer.load(args.model)
    sp = BPESentencePiece(tok)
    ids = sp.encode(args.text)
    pieces = tok.id_to_pieces(ids)
    print(f"ids: {ids}")
    print(f"pieces: {pieces}")
    print(f"decoded: {tok.decode(ids)!r}")
    return 0


def _cmd_wordpiece(args: argparse.Namespace) -> int:
    from .wordpiece import WordPieceEncoder
    tok = BPETokenizer.load(args.model)
    wp = WordPieceEncoder(tok, use_continuation_marker=not args.no_continuation_marker)
    ids = wp.encode(args.text)
    pieces = wp.tokenize(args.text)
    print(f"ids: {ids}")
    print(f"pieces: {pieces}")
    print(f"decoded: {tok.decode(ids)!r}")
    return 0


def _cmd_stats(args: argparse.Namespace) -> int:
    tok = BPETokenizer.load(args.model)
    st = tok.stats()
    print(f"Vocab size:    {st.vocab_size}")
    print(f"  Specials:   {st.n_specials}")
    print(f"  Regulars:   {st.n_regulars}")
    print(f"  Merges:     {st.n_merges}")
    print(f"Byte mode:    {st.byte_mode}")
    print(f"Cache size:   {st.cache_size}")
    print(f"Cache hits:   {st.cache_hits}")
    print(f"Cache misses: {st.cache_misses}")
    return 0


def _cmd_roundtrip(args: argparse.Namespace) -> int:
    tok = BPETokenizer.load(args.model)
    ids = tok.encode(args.text)
    decoded = tok.decode(ids)
    print(f"Original: {args.text!r}")
    print(f"Ids:      {ids}")
    print(f"Decoded:  {decoded!r}")
    print(f"Match:    {args.text == decoded}")
    return 0


def _cmd_analyze(args: argparse.Namespace) -> int:
    from .analyzer import TokenizerAnalyzer
    tok = BPETokenizer.load(args.model)
    text = Path(args.input).read_text(encoding="utf-8")
    texts = text.splitlines()
    analyzer = TokenizerAnalyzer(tok)
    print(analyzer.summary(texts))
    return 0


def _cmd_compare(args: argparse.Namespace) -> int:
    from .comparison import TokenizerComparison
    tok_a = BPETokenizer.load(args.model_a)
    tok_b = BPETokenizer.load(args.model_b)
    text = Path(args.input).read_text(encoding="utf-8")
    texts = text.splitlines()
    comp = TokenizerComparison(tok_a, tok_b)
    print(comp.summary(texts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
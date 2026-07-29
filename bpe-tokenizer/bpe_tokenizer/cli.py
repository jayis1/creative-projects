"""Command-line interface for the BPE tokenizer."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .tokenizer import BPETokenizer, TrainingConfig
from .encoder import bpe_dropout, BPESentencePiece


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="bpe-tokenizer",
        description="Byte Pair Encoding tokenizer — train, encode, decode, analyze.",
    )
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
    pt.add_argument("--verbose", action="store_true")
    pt.add_argument("--no-specials", action="store_true", help="Don't reserve special tokens.")

    # encode
    pe = sub.add_parser("encode", help="Encode text to token ids.")
    pe.add_argument("text", help="Text to encode (or use --file).")
    pe.add_argument("--file", help="Read text from a file instead.")
    pe.add_argument("-m", "--model", required=True, help="Tokenizer JSON path.")
    pe.add_argument("--bos", action="store_true", help="Add BOS token.")
    pe.add_argument("--eos", action="store_true", help="Add EOS token.")
    pe.add_argument("--pieces", action="store_true", help="Print pieces alongside ids.")

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

    # stats
    ps = sub.add_parser("stats", help="Show tokenizer statistics.")
    ps.add_argument("-m", "--model", required=True, help="Tokenizer JSON path.")

    # roundtrip
    pr = sub.add_parser("roundtrip", help="Round-trip test: encode then decode.")
    pr.add_argument("text", help="Text to test.")
    pr.add_argument("-m", "--model", required=True, help="Tokenizer JSON path.")

    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "train":
        from .vocab import DEFAULT_SPECIALS
        text = Path(args.input).read_text(encoding="utf-8")
        specials = () if args.no_specials else DEFAULT_SPECIALS
        cfg = TrainingConfig(
            vocab_size=args.vocab_size,
            byte_mode=args.byte_mode,
            pretokenizer=args.pretokenizer,
            specials=specials,
            min_frequency=args.min_frequency,
            verbose=args.verbose,
        )
        tok = BPETokenizer()
        tok.train(text, cfg)
        tok.save(args.output)
        st = tok.stats()
        print(f"Trained: vocab_size={st.vocab_size}, merges={st.n_merges}, "
              f"specials={st.n_specials}, byte_mode={st.byte_mode}")
        print(f"Saved to: {args.output}")
        return 0

    elif args.command == "encode":
        tok = BPETokenizer.load(args.model)
        text = Path(args.file).read_text(encoding="utf-8") if args.file else args.text
        ids = tok.encode(text, add_bos=args.bos, add_eos=args.eos)
        if args.pieces:
            pieces = tok.id_to_pieces(ids)
            for i, (tid, piece) in enumerate(zip(ids, pieces)):
                print(f"{i:4d}  {tid:6d}  {piece!r}")
        else:
            print(json.dumps(ids))
        return 0

    elif args.command == "decode":
        tok = BPETokenizer.load(args.model)
        if args.file:
            ids = json.loads(Path(args.file).read_text())
        else:
            ids = args.ids
        text = tok.decode(ids)
        print(text)
        return 0

    elif args.command == "batch":
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

    elif args.command == "dropout":
        import random
        tok = BPETokenizer.load(args.model)
        rng = random.Random(args.seed)
        for _ in range(args.n):
            ids = bpe_dropout(tok, args.text, dropout=args.p, rng=rng)
            pieces = tok.id_to_pieces(ids)
            print(f"  ids={ids}")
            print(f"  pieces={pieces}")
        return 0

    elif args.command == "viterbi":
        tok = BPETokenizer.load(args.model)
        sp = BPESentencePiece(tok)
        ids = sp.encode(args.text)
        pieces = tok.id_to_pieces(ids)
        print(f"ids: {ids}")
        print(f"pieces: {pieces}")
        print(f"decoded: {tok.decode(ids)!r}")
        return 0

    elif args.command == "stats":
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

    elif args.command == "roundtrip":
        tok = BPETokenizer.load(args.model)
        ids = tok.encode(args.text)
        decoded = tok.decode(ids)
        print(f"Original: {args.text!r}")
        print(f"Ids:      {ids}")
        print(f"Decoded:  {decoded!r}")
        print(f"Match:    {args.text == decoded}")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
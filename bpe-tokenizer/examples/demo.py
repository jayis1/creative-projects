"""Demo script: train a BPE tokenizer on a sample corpus."""

from bpe_tokenizer import BPETokenizer, TrainingConfig

CORPUS = """
The quick brown fox jumps over the lazy dog.
The quick brown fox is very quick indeed.
Lazy dogs sleep while quick foxes jump.
The dog and the fox are friends.
Quick quick quick lazy lazy lazy.
A quick brown fox jumped over a lazy dog today.
The fox and the dog became quick friends.
Lazy lazy lazy quick quick quick the end.
"""

def main():
    # Train
    tok = BPETokenizer()
    cfg = TrainingConfig(vocab_size=100, min_frequency=1, verbose=True)
    tok.train(CORPUS, cfg)

    # Encode
    text = "the quick brown fox"
    ids = tok.encode(text)
    pieces = tok.id_to_pieces(ids)
    print(f"\nText:    {text!r}")
    print(f"Ids:     {ids}")
    print(f"Pieces:  {pieces}")
    print(f"Decoded: {tok.decode(ids)!r}")

    # Batch with padding
    texts = ["quick fox", "lazy dog", "the"]
    batch = tok.encode_batch(texts, padding=True)
    print(f"\nBatch (padded): {batch}")

    # Stats
    st = tok.stats()
    print(f"\nStats: vocab={st.vocab_size}, merges={st.n_merges}, "
          f"regulars={st.n_regulars}, specials={st.n_specials}")

    # Viterbi
    from bpe_tokenizer.encoder import BPESentencePiece
    sp = BPESentencePiece(tok)
    viterbi_ids = sp.encode(text)
    print(f"\nViterbi: {viterbi_ids}")
    print(f"Viterbi pieces: {tok.id_to_pieces(viterbi_ids)}")


if __name__ == "__main__":
    main()
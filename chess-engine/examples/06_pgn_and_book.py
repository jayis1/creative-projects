"""Example: PGN read/write and opening book usage."""

from chess_engine import Board, PGNGame, create_default_book
from chess_engine.notation import parse_algebraic, to_algebraic

def main():
    # ── Opening Book ──
    board = Board()
    book = create_default_book()
    book_move = book.probe(board)
    if book_move:
        san = to_algebraic(book_move, board)
        print(f"Book suggests: {san} ({book_move.uci()})")

    # Play a few book moves
    moves_played = []
    for _ in range(6):
        mv = book.probe(board)
        if mv is None:
            break
        san = to_algebraic(mv, board)
        moves_played.append(san)
        board.push(mv)

    print(f"Book sequence: {' '.join(moves_played)}")
    print(board.to_string(unicode=True))
    print()

    # ── PGN ──
    # Create a PGN game
    game = PGNGame()
    game.add_header("Event", "Example Game")
    game.add_header("White", "Player A")
    game.add_header("Black", "Player B")
    game.add_move("e4")
    game.add_move("e5")
    game.add_move("Nf3")
    game.add_move("Nc6")
    game.add_move("Bb5")
    game.add_move("a6")
    game.result = "*"

    pgn_text = game.to_string()
    print("Generated PGN:")
    print(pgn_text)
    print()

    # Parse PGN back
    parsed = PGNGame.from_string(pgn_text)
    print(f"Parsed {len(parsed.moves)} moves: {parsed.moves}")
    print(f"Headers: {parsed.headers}")

    # Replay on a board
    board2 = parsed.play_on_board()
    print(f"\nFinal position after replay:")
    print(board2.to_string(unicode=True))


if __name__ == "__main__":
    main()
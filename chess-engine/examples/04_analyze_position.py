"""Example: Analyze a position and show evaluation breakdown."""

from chess_engine import Board, Evaluator, Search

def main():
    # A complex middlegame position (Kiwipete)
    fen = "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"
    board = Board.from_fen(fen)

    print("Position (Kiwipete):")
    print(board.to_string(unicode=True))
    print(f"FEN: {board.fen()}")
    print()

    # Static evaluation
    evaluator = Evaluator()
    score = evaluator.evaluate(board)
    print(f"Static evaluation: {score} (from {board.turn}'s perspective)")
    print(f"Endgame? {evaluator.is_endgame(board)}")
    print()

    # Search
    search = Search()
    move, sc = search.search(board, depth=4)
    if move:
        from chess_engine.notation import to_algebraic
        san = to_algebraic(move, board)
        print(f"Best move: {san} ({move.uci()})  score: {sc}")
        print(f"Nodes: {search.nodes}")
        info = search.get_info()
        if info.get("pv"):
            print(f"PV: {' '.join(info['pv'])}")


if __name__ == "__main__":
    main()
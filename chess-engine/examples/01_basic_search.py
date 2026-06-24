"""Example: Basic engine usage — search for the best move."""

from chess_engine import Board, Search

def main():
    board = Board()
    print("Starting position:")
    print(board.to_string(unicode=True))
    print()

    # Search for the best move
    search = Search()
    move, score = search.search(board, depth=4)

    print(f"Best move: {move.uci()}")
    print(f"Score: {score}")
    print(f"Nodes searched: {search.nodes}")

    # Show the principal variation
    info = search.get_info()
    if info.get("pv"):
        print(f"Principal variation: {' '.join(info['pv'])}")


if __name__ == "__main__":
    main()
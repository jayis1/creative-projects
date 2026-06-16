% Towers of Hanoi — Classic recursive puzzle
% ===========================================

% hanoi(N, From, To, Via, Moves) solves N-disk Tower of Hanoi
% Moves is a list of move(From, To) terms
hanoi(0, _, _, _, []).
hanoi(N, From, To, Via, Moves) :-
    N > 0,
    N1 is N - 1,
    hanoi(N1, From, Via, To, Moves1),
    hanoi(N1, Via, To, From, Moves2),
    append(Moves1, [move(From, To)|Moves2], Moves).

% Try:
% ?- hanoi(3, left, right, middle, Moves).
%   Moves = [move(left, right), move(left, middle), move(right, middle),
%            move(left, right), move(middle, left), move(middle, right),
%            move(left, right)]

% Print moves using write/1:
hanoi_print(N) :-
    hanoi(N, left, right, middle, Moves),
    print_moves(Moves).

print_moves([]).
print_moves([move(From, To)|Rest]) :-
    writeln(move(From, To)),
    print_moves(Rest).
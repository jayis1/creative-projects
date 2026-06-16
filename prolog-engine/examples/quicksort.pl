% Quicksort — Demonstrates list manipulation and recursion
% =========================================================

qsort([], []).
qsort([H|T], Sorted) :-
    partition(H, T, Less, Greater),
    qsort(Less, SortedLess),
    qsort(Greater, SortedGreater),
    append(SortedLess, [H|SortedGreater], Sorted).

partition(_, [], [], []).
partition(Pivot, [H|T], [H|Less], Greater) :-
    H =< Pivot,
    partition(Pivot, T, Less, Greater).
partition(Pivot, [H|T], Less, [H|Greater]) :-
    H > Pivot,
    partition(Pivot, T, Less, Greater).

% Try this query:
% ?- qsort([3, 1, 4, 1, 5, 9, 2, 6], R).
%   R = [1, 1, 2, 3, 4, 5, 6, 9]
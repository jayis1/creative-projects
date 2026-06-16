% Fibonacci Sequence — Demonstrates arithmetic and recursion
% ============================================================

fib(0, 0).
fib(1, 1).
fib(N, R) :- N > 1, N1 is N - 1, N2 is N - 2, fib(N1, R1), fib(N2, R2), R is R1 + R2.

% Try these queries:
% ?- fib(6, X).
%   X = 8
%
% ?- fib(10, X).
%   X = 55
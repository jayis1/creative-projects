% Dynamic Database — Demonstrates assert/retract and meta-programming
% ====================================================================

% Facts about what people like
likes(alice, bob).
likes(bob, carol).
likes(carol, dave).

% Add new facts at runtime using assertz
% ?- assertz(likes(dave, alice)).

% Query the dynamic database
% ?- likes(X, Y).

% Use findall to collect all pairs
% ?- findall(X-Y, likes(X, Y), Pairs).

% Introspect clauses
% ?- clause(likes(X, Y), Body).

% Retract a fact
% ?- retract(likes(alice, bob)).
% ?- likes(alice, X).  % Should now fail
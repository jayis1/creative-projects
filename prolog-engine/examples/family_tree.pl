% Family Tree — Classic Prolog Example
% =====================================
% This example demonstrates basic facts, rules, and recursive queries.

parent(tom, bob).
parent(tom, liz).
parent(bob, ann).
parent(bob, pat).
parent(pat, jim).

grandparent(X, Z) :- parent(X, Y), parent(Y, Z).
ancestor(X, Y) :- parent(X, Y).
ancestor(X, Y) :- parent(X, Z), ancestor(Z, Y).

sibling(X, Y) :- parent(Z, X), parent(Z, Y), X \= Y.

% Try these queries:
% ?- grandparent(tom, X).
%   X = ann ;
%   X = pat
%
% ?- ancestor(tom, X).
%   X = bob ;
%   X = liz ;
%   X = ann ;
%   X = pat ;
%   X = jim
%
% ?- sibling(bob, X).
%   X = liz
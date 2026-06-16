% Map Coloring — Classic constraint satisfaction problem
% ========================================================
% Color a map of regions so no two adjacent regions share a color.

color(red).
color(green).
color(blue).

% Adjacent regions
adjacent(wa, nt).
adjacent(wa, sa).
adjacent(nt, wa).
adjacent(nt, sa).
adjacent(nt, q).
adjacent(sa, wa).
adjacent(sa, nt).
adjacent(sa, q).
adjacent(sa, nsw).
adjacent(sa, v).
adjacent(q, nt).
adjacent(q, sa).
adjacent(q, nsw).
adjacent(nsw, sa).
adjacent(nsw, q).
adjacent(nsw, v).
adjacent(v, sa).
adjacent(v, nsw).

% A valid coloring: no adjacent regions have the same color
coloring(WA, NT, SA, Q, NSW, V) :-
    color(WA), color(NT), color(SA), color(Q), color(NSW), color(V),
    WA \= NT, WA \= SA,
    NT \= SA, NT \= Q,
    SA \= Q, SA \= NSW, SA \= V,
    Q \= NSW,
    NSW \= V.

% Try:
% ?- coloring(WA, NT, SA, Q, NSW, V).
%   WA = red, NT = green, SA = blue, Q = red, NSW = green, V = red ;
%   ... (many solutions)
"""PreVote optimization (Raft thesis §6).

The PreVote optimization prevents disruptive elections when a node
becomes disconnected and then reconnects.  Without PreVote, a
partitioned node's term keeps increasing as it starts elections.
When it reconnects, its high term causes the current leader to step
down unnecessarily.

With PreVote, a candidate first runs a *pre-vote* round using term+1
**without** actually incrementing its term.  It only starts a real
election if it can get a majority of pre-votes, proving that it can
communicate with the cluster.

This module adds the PreVote RPC messages and a handler mixin used by
:class:`raft.node.RaftNode`.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PreVoteRequest:
    """PreVote RPC request.

    The candidate asks: "If I were to start an election with *term*,
    would you grant me your vote?"

    Attributes:
        term: The term the candidate *would* use (current_term + 1).
        candidate_id: The candidate's node id.
        last_log_index: Candidate's last log index.
        last_log_term: Candidate's last log term.
    """

    term: int
    candidate_id: int
    last_log_index: int
    last_log_term: int


@dataclass
class PreVoteResponse:
    """PreVote RPC response.

    Attributes:
        term: The responder's current term (for staleness detection).
        vote_granted: Whether the responder *would* vote for this candidate.
        voter_id: The responder's node id.
    """

    term: int
    vote_granted: bool
    voter_id: int


__all__ = ["PreVoteRequest", "PreVoteResponse"]
"""Run the model-checker demonstration: python3 -m modelcheck.cli"""
from .ctl import Formula as F, check, satisfying
from .system import TransitionSystem


def demo():
    # A producer may be idle, then send; the receiver eventually acknowledges.
    ts = TransitionSystem.build('idle', {'idle': ['sent'], 'sent': ['ack', 'sent'], 'ack': ['idle']},
        {'idle': ['ready'], 'sent': ['pending'], 'ack': ['delivered']})
    print(f'Reachable states: {len(ts.states)}')
    print(f'Eventually delivered: {check(ts, F.EF(F.atom("delivered")))}')
    print(f'Always ready or pending or delivered: {check(ts, F.AG(F.either(F.atom("ready"), F.either(F.atom("pending"), F.atom("delivered")))))}')
    print('Shortest delivery trace:', ' -> '.join(ts.shortest_path(lambda s: 'delivered' in ts.labels.get(s, ())) or []))

if __name__ == '__main__': demo()

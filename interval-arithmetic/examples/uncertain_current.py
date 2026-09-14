from interval_arithmetic import Interval

voltage = Interval(4.9, 5.1)
resistance = Interval(99, 101)
print("current bounds:", voltage / resistance)

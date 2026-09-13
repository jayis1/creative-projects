from neural_net_lab import MLP, Adam
x=[[0,0],[0,1],[1,0],[1,1]]; y=[[0],[1],[1],[0]]
n=MLP([2,4,1],seed=7); h=n.train(x,y,epochs=2000,lr=.08,batch_size=4,optimizer=Adam(),clip=5,patience=300)
assert h.losses[-1] < .01, h.losses[-1]
p=n.predict_batch(x); assert p[1][0] > .8 and p[3][0] < .2
n.save('/tmp/model.json'); m=MLP.load('/tmp/model.json'); assert m.predict([1,0]) == n.predict([1,0])
try: MLP([2,0])
except ValueError: pass
else: raise AssertionError('validation')
print('checks passed', len(h.losses), h.losses[-1])

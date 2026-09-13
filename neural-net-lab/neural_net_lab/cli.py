import argparse
from .core import MLP
from .optim import Adam

def main():
 p=argparse.ArgumentParser(description='Train a tiny neural network on XOR'); p.add_argument('--epochs',type=int,default=2000); p.add_argument('--loss',choices=['mse','bce'],default='mse'); p.add_argument('--save'); a=p.parse_args()
 x=[[0,0],[0,1],[1,0],[1,1]]; y=[[0],[1],[1],[0]]; n=MLP([2,4,1],seed=7); h=n.train(x,y,a.epochs,.08,4,Adam(),loss_name=a.loss); print(f'final {a.loss} loss: {h.losses[-1]:.6f}; accuracy: {n.accuracy(x,y):.2%}')
 for xi,yi in zip(x,y): print(xi, '=>', round(n.predict(xi)[0],4), 'target',yi[0])
 if a.save: n.save(a.save)
if __name__=='__main__': main()

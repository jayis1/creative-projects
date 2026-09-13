"""A dependency-free dense neural network with mini-batch training."""
from __future__ import annotations
import json, math, random
from dataclasses import dataclass
from typing import Sequence


def _act(name: str, x: float) -> tuple[float, float]:
    if name == "relu": return (max(0.0, x), 1.0 if x > 0 else 0.0)
    if name == "tanh":
        y = math.tanh(x); return y, 1.0-y*y
    if name == "sigmoid":
        y = 1.0/(1.0+math.exp(-max(-60.0, min(60.0, x)))); return y, y*(1-y)
    if name == "linear": return x, 1.0
    raise ValueError(f"unknown activation: {name}")

@dataclass
class TrainingHistory:
    losses: list[float]
    val_losses: list[float]

class Layer:
    def __init__(self, inputs: int, outputs: int, activation="tanh", rng=None):
        if inputs < 1 or outputs < 1: raise ValueError("layer dimensions must be positive")
        self.activation=activation; r=rng or random.Random()
        scale=math.sqrt(2/inputs) if activation == "relu" else math.sqrt(1/inputs)
        self.w=[[r.gauss(0, scale) for _ in range(inputs)] for _ in range(outputs)]
        self.b=[0.0]*outputs
    def forward(self, x):
        if len(x) != len(self.w[0]): raise ValueError("input width does not match layer")
        z=[sum(a*v for a,v in zip(row,x))+b for row,b in zip(self.w,self.b)]
        out=[]; slopes=[]
        for v in z:
            y,d=_act(self.activation,v); out.append(y); slopes.append(d)
        return out, (x, z, slopes)

class MLP:
    def __init__(self, sizes: Sequence[int], activations=None, seed=0):
        if len(sizes)<2 or any(not isinstance(n,int) or n<1 for n in sizes): raise ValueError("sizes must contain positive integers")
        acts=list(activations or ["tanh"]*(len(sizes)-2)+["sigmoid"])
        if len(acts)!=len(sizes)-1: raise ValueError("one activation per layer required")
        self.layers=[]; rng=random.Random(seed)
        for i,(a,b) in enumerate(zip(sizes,sizes[1:])): self.layers.append(Layer(a,b,acts[i],rng))
        self.sizes=list(sizes)
    def predict(self,x):
        y=list(map(float,x))
        for layer in self.layers: y,_=layer.forward(y)
        return y
    def _grad(self,x,target,loss_name="mse"):
        acts=[list(map(float,x))]; caches=[]
        for l in self.layers:
            y,c=l.forward(acts[-1]); acts.append(y); caches.append(c)
        if len(target)!=len(acts[-1]): raise ValueError("target width does not match output")
        if loss_name not in ("mse", "bce"): raise ValueError("loss must be mse or bce")
        if loss_name == "bce" and self.layers[-1].activation != "sigmoid":
            raise ValueError("bce requires a sigmoid output layer")
        # BCE's sigmoid derivative cancels, avoiding vanishing gradients at the extremes.
        delta=[(y-t) if loss_name == "bce" else 2*(y-t)*d for y,t,d in zip(acts[-1],target,caches[-1][2])]
        grads=[]
        for i in range(len(self.layers)-1,-1,-1):
            inp,_,slopes=caches[i]
            grads.append((None, None))
            gw=[[delta[o]*inp[j] for j in range(len(inp))] for o in range(len(delta))]
            gb=delta[:]; grads[-1]=(gw,gb)
            if i:
                delta=[sum(self.layers[i].w[o][j]*delta[o] for o in range(len(delta)))*caches[i-1][2][j] for j in range(len(inp))]
        if loss_name == "bce":
            cost=-sum(t*math.log(max(y,1e-15))+(1-t)*math.log(max(1-y,1e-15)) for y,t in zip(acts[-1],target))
        else: cost=0.5*sum((a-b)**2 for a,b in zip(acts[-1],target))
        return list(reversed(grads)), cost
    def predict_batch(self, xs):
        """Predict every row while preserving input order."""
        return [self.predict(x) for x in xs]
    def train(self,xs,ys,epochs=1000,lr=.1,batch_size=16,optimizer=None,validation=None,shuffle=True,seed=1,clip=None,patience=None,loss_name="mse"):
        if len(xs)!=len(ys) or not xs: raise ValueError("xs and ys must be non-empty and equal length")
        if epochs<1 or lr<=0 or batch_size<1 or (clip is not None and clip<=0) or (patience is not None and patience<1): raise ValueError("invalid training parameters")
        if loss_name not in ("mse", "bce"): raise ValueError("loss must be mse or bce")
        if loss_name == "bce" and self.layers[-1].activation != "sigmoid": raise ValueError("bce requires a sigmoid output layer")
        opt=optimizer
        rng=random.Random(seed); hist=TrainingHistory([],[]); ids=list(range(len(xs)))
        best=float("inf"); stale=0; best_weights=None
        for _ in range(epochs):
            if shuffle: rng.shuffle(ids)
            for start in range(0,len(ids),batch_size):
                sums=[([[0.0]*len(l.w[0]) for _ in l.w],[0.0]*len(l.b)) for l in self.layers]; count=0
                for k in ids[start:start+batch_size]:
                    gs,_=self._grad(xs[k],ys[k],loss_name); count+=1
                    for i,(gw,gb) in enumerate(gs):
                        for o in range(len(gw)):
                            for j in range(len(gw[o])): sums[i][0][o][j]+=gw[o][j]
                            sums[i][1][o]+=gb[o]
                for i,(gw,gb) in enumerate(sums):
                    if clip is not None:
                        norm=math.sqrt(sum(v*v for row in gw for v in row)+sum(v*v for v in gb))
                        if norm>clip:
                            factor=clip/norm
                            gw=[[v*factor for v in row] for row in gw]; gb=[v*factor for v in gb]
                    opt.step(self.layers[i],gw,gb,lr,count) if opt else self._apply(self.layers[i],gw,gb,lr,count)
            hist.losses.append(self.loss(xs,ys,loss_name)); current=self.loss(*validation,loss_name=loss_name) if validation else hist.losses[-1]; hist.val_losses.append(current if validation else float("nan"))
            if current < best-1e-12:
                best,stale=current,0
                best_weights=[([row[:] for row in l.w], l.b[:]) for l in self.layers]
            else: stale+=1
            if patience is not None and stale>=patience:
                if best_weights:
                    for l,(w,b) in zip(self.layers,best_weights): l.w,l.b=[row[:] for row in w],b[:]
                break
        return hist
    @staticmethod
    def _apply(l,gw,gb,lr,n):
        for o in range(len(l.w)):
            for j in range(len(l.w[o])): l.w[o][j]-=lr*gw[o][j]/n
            l.b[o]-=lr*gb[o]/n
    def loss(self,xs,ys,loss_name="mse"):
        if not xs or len(xs)!=len(ys): raise ValueError("loss data must be non-empty and aligned")
        return sum(self._grad(x,y,loss_name)[1] for x,y in zip(xs,ys))/len(xs)
    def accuracy(self,xs,ys,threshold=.5):
        """Binary accuracy for one-output sigmoid models."""
        if not xs or len(xs)!=len(ys) or len(self.layers[-1].b)!=1 or not 0<=threshold<=1: raise ValueError("accuracy requires aligned data, one output, and a valid threshold")
        return sum((self.predict(x)[0]>=threshold)==(y[0]>=threshold) for x,y in zip(xs,ys))/len(xs)
    def to_dict(self): return {"sizes":self.sizes,"activations":[l.activation for l in self.layers],"weights":[l.w for l in self.layers],"biases":[l.b for l in self.layers]}
    def save(self,path):
        with open(path,"w",encoding="utf8") as f: json.dump(self.to_dict(),f,indent=2)
    @classmethod
    def load(cls,path):
        with open(path,encoding="utf8") as f: d=json.load(f)
        if not isinstance(d,dict) or not all(k in d for k in ("sizes","activations","weights","biases")): raise ValueError("invalid model file")
        net=cls(d["sizes"],d["activations"])
        if len(d["weights"])!=len(net.layers) or len(d["biases"])!=len(net.layers): raise ValueError("model layer count mismatch")
        for l,w,b in zip(net.layers,d["weights"],d["biases"]):
            if (not isinstance(w,list) or len(w)!=len(l.w) or any(not isinstance(row,list) or len(row)!=len(l.w[0]) for row in w) or not isinstance(b,list) or len(b)!=len(l.b)):
                raise ValueError("invalid model dimensions")
            l.w=w; l.b=b
        return net

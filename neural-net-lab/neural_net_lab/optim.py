"""Optimizers kept separate so experiments can swap them."""
class SGD:
    def step(self, layer, gw, gb, lr, n):
        for o in range(len(layer.w)):
            for j in range(len(layer.w[o])): layer.w[o][j] -= lr*gw[o][j]/n
            layer.b[o] -= lr*gb[o]/n
class Adam:
    def __init__(self,beta1=.9,beta2=.999,epsilon=1e-8):
        if not 0<beta1<1 or not 0<beta2<1 or epsilon<=0: raise ValueError("invalid Adam parameters")
        self.b1,self.b2,self.eps=beta1,beta2,epsilon; self.t=0; self.state={}
    def step(self,l,gw,gb,lr,n):
        self.t+=1; key=id(l)
        m_w, m_b, v_w, v_b=self.state.setdefault(key,([[0.]*len(r) for r in l.w],[0.]*len(l.b),[[0.]*len(r) for r in l.w],[0.]*len(l.b)))
        for o in range(len(l.w)):
            for j in range(len(l.w[o])):
                g=gw[o][j]/n; m_w[o][j]=self.b1*m_w[o][j]+(1-self.b1)*g; v_w[o][j]=self.b2*v_w[o][j]+(1-self.b2)*g*g
                l.w[o][j]-=lr*(m_w[o][j]/(1-self.b1**self.t))/((v_w[o][j]/(1-self.b2**self.t))**.5+self.eps)
            g=gb[o]/n; m_b[o]=self.b1*m_b[o]+(1-self.b1)*g; v_b[o]=self.b2*v_b[o]+(1-self.b2)*g*g
            l.b[o]-=lr*(m_b[o]/(1-self.b1**self.t))/((v_b[o]/(1-self.b2**self.t))**.5+self.eps)

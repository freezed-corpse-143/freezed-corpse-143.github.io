
# 单头，无 batch

```python
import torch
import torch.nn.functional as F

def self_attention_single_head(X, W_q, W_k, W_v):
	
	Q = X @ W_q
	K = X @ W_k
	V = X @ W_v
	
	d_k = Q.size(-1)
	
	scores = Q @ K.T / (d_k ** 0.5)
	
	attn_weights = F.softmax(scores, dim=-1)
	
	output = attn_weights @ V
	
	return output, attn_weights
```
from __future__ import annotations
from dataclasses import asdict
import json
FEATURE_ORDER=["margin10","coherence10","anchor_top3_share","anchor_novel_ratio","body_top1_score","body_top10_mean_score","body_top10_score_cv","log_query_token_count","anchor_top1_score","anchor_nonempty_ratio"]
class InterventionController:
    def __init__(self,config=None):self.config=config
    @classmethod
    def from_json(cls,path):return cls(json.load(open(path)))
    def score(self,state):
        c=self.config
        if not c:return float('-inf')
        d=asdict(state);x=[float(d[k]) for k in FEATURE_ORDER];z=[(v-m)/s for v,m,s in zip(x,c['means'],c['stds'])];dn=sum((a-b)**2 for a,b in zip(z,c['negative_centroid']));dp=sum((a-b)**2 for a,b in zip(z,c['positive_centroid']));return dn-dp
    def decide(self,state):
        s=self.score(state)
        if not self.config:return 'none',s
        return ('external_rescue' if s>=self.config['threshold_tau'] else 'none'),s

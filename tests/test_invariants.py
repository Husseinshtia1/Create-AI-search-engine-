from g97.graph import LinkGraph
def test_graph_does_not_manufacture_zero_relevance():
    g=LinkGraph();g.add('s','d');out=g.local_corroboration([('s',1.0)],{'d':0.0,'x':1.0});assert out['d']==0.0
def test_graph_bounded_boost():
    g=LinkGraph();g.add('s','d');out=g.local_corroboration([('s',1.0)],{'d':2.0},lam=.5);assert 2.0<=out['d']<3.0

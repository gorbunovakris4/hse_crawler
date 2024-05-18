import json
import pandas as pd
import numpy as np
import numpy.linalg as ln
from scipy.sparse import csr_matrix


class Ranker:
    def __init__(self):
        self.n_vertex = 0
        with open("web_graph/id_to_info.json") as f:
            data = json.load(f)
            self.n_vertex = data.keys()[-1]
        self.m_edges = 0
        with open("web_graph/edges.txt") as f:
            self.m_edges = len(f.readlines()) - 1

    def make_ranks(self):
        data = pd.read_csv("web_graph/edges.txt", names = ['i','j'], sep=" ", header=None)
        graph = csr_matrix((np.ones(len(data['i'])),(data['i'],data['j'])),shape=(self.n_vertex, self.n_vertex))
        pages_cnt = graph.sum(axis=1)
        graph = graph.transpose()
        ranks_init = np.ones((self.n_vertex,1))/self.n_vertex
        current_ranks = ranks_init.copy()
        delta = 0.85
        while True:
            tmp = current_ranks / pages_cnt
            ranks_update = delta * graph.dot(csr_matrix(tmp)) + (1-delta) * ranks_init
            if ln.norm(ranks_update-current_ranks) < 1e-6:
                break
            current_ranks = ranks_update
        self.ranks = current_ranks

    def save_ranks(self):
        data = pd.DataFrame({"id": np.arange(self.n_vertex), "rank": np.ones(self.n_vertex)})
        data["rank"] = self.ranks
        data.to_csv(f'./ranking/pages_ranked.csv')

    def run(self):
        self.make_ranks()
        self.save_ranks()


if __name__ == '__main__':
    ranker = Ranker()
    ranker.run()

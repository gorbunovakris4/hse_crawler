import os
import json
import logging
from gexfpy import Gexf, Graph, Node, Nodes, Edges, Edge, EdgetypeType, xmlserialize


class WebGraphProcessor:
    def __init__(self):
        self.link_to_id = {}
        self.id_to_info = {}
        self.edges = []
        self.directory_path = "pages/"
        if not os.path.exists(self.directory_path):
            logging.error("Invalid directory for pages data")
        self.web_graph_path = "web_graph/"
        if not os.path.exists(self.web_graph_path):
            os.makedirs(self.web_graph_path, exist_ok=True)

    def create_edges_list(self):
        for file_path in os.listdir(self.directory_path):
            with open(self.directory_path + file_path, encoding='utf-8') as f:
                doc = json.load(f)
                url = doc["url"]
                new_id = len(self.link_to_id)
                if url not in self.link_to_id:
                    self.link_to_id[url] = new_id
                    self.id_to_info[new_id] = {"url": url, "processed": False, "has_links": False}
                from_id = self.link_to_id[url]
                self.id_to_info[from_id]["processed"] = True

                if "links" not in doc or len(doc["links"]) == 0:
                    continue
                self.id_to_info[from_id]["has_links"] = True
                for link in doc["links"]:
                    new_id = len(self.link_to_id)
                    if link not in self.link_to_id:
                        self.link_to_id[link] = new_id
                        self.id_to_info[new_id] = {"url": link, "processed": False, "has_links": False}
                    to_id = self.link_to_id[link]
                    self.edges.append((from_id, to_id))

    def save_edges_list_with_artifacts(self):
        with open("web_graph/link_to_id.json", "w") as f:
            json.dump(self.link_to_id, f)
        with open("web_graph/id_to_info.json", "w") as f:
            json.dump(self.id_to_info, f)

        with open('web_graph/edges.txt', 'w') as f:
            for edge in self.edges:
                f.write(f'{edge[0]} {edge[1]}\n')

    def make_edges_list(self):
        self.create_edges_list()
        self.save_edges_list_with_artifacts()

    def make_save_gexf(self):
        self.create_edges_list()
        nodes = []
        edges = []
        for node_id in self.id_to_info.keys():
            nodes.append(Node(id=f'{node_id}'))
        for i, edge in enumerate(self.edges):
            edges.append(Edge(id=f'{i}',
                              source=f'{edge[0]}',
                              target=f'{edge[1]}',
                              type=EdgetypeType.DIRECTED,
                              weight=1))
        gexf_graph = Gexf(graph=Graph(nodes=[Nodes(node=nodes, count=len(nodes))],
                                      edges=[Edges(edge=edges, count=len(edges))]))

        save_path_file = f"web_graph/gexf_graph.gexf"
        xmlserialize(gexf_graph, save_path_file)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, filename="web_graph_log", filemode="a+",
                        format="%(asctime)-15s %(levelname)-8s %(message)s")
    saver = WebGraphProcessor()
    saver.make_edges_list()

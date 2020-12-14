import matplotlib.pyplot as plt
import networkx as nx
from paraview import simple


def use_networkx():
    def print_graph_stats(G):
        cc_size = dict()
        n_cc = nx.number_connected_components(G)
        print(nx.info(G))
        print("#Neighs\t#Nodes")
        for i, v in enumerate(nx.degree_histogram(G)):
            if v != 0:
                print(f" {i}\t{v}")
        density = nx.density(G)
        print(f"Density: {density}")
        print(f"#Connected Components: {n_cc}")
        print("#Nodes\t#Components")
        for cc in nx.connected_components(G):
            cc_size[len(cc)] = cc_size.get(len(cc), 0) + 1
        for k, v in sorted(cc_size.items(), key=lambda item: item[1]):
            print(f" {k}\t{v}")

    def get_neighs(G, nodes, acc=set()):
        for node in nodes:
            for neigh in nx.all_neighbors(G, node):
                acc.add(neigh)

    def get_neighborhood(G, seeds, radius=1):
        neighs = set(seeds)
        for i in range(radius):
            get_neighs(G, neighs.copy(), neighs)
        return nx.subgraph(G, neighs)

    def display_graph(G):
        color_map = list()
        for node in G:
            if "_s1" in node:
                color_map.append("cyan")
            elif "_s2" in node:
                color_map.append("orange")
            else:
                color_map.append("green")
        nx.draw_networkx(
            G,
            # nx.spectral_layout(G),
            node_color=color_map,
            node_size=100,
            font_size=8,
        )
        plt.show()

    with open("saddle2_graph.csv", "rb") as src:
        G = nx.readwrite.edgelist.read_edgelist(src, nodetype=str)
        # graph is bipartite
        nx.set_node_attributes(
            G, {node: (0 if "_s1" in node else 1) for node in G}, name="bipartite"
        )
        # src = "597_s1"
        # dst = "431_s2"
        # visited_bfs = [src, dst]
        # with open("visited") as vis:
        #     for line in vis:
        #         visited_bfs.append(line.strip())
        # G = nx.subgraph(G, visited_bfs)
        paths = list(nx.all_simple_paths(G, "592544_s1", "672529_s2", cutoff=10))
        for path in paths:
            print(path)
        nodes_path = set(sum(paths, list()))
        # G = nx.subgraph(G, nodes_path)
        G = get_neighborhood(G, nodes_path, 1)
        display_graph(G)


def use_mds():
    DistMat = simple.CSVReader(FileName=["saddle2_graph.csv"])
    DimRed = simple.TTKDimensionReduction(Input=DistMat)
    DimRed.SelectFieldswithaRegexp = 1
    DimRed.Regexp = "Dist.*"
    DimRed.Components = 3
    DimRed.InputIsaDistanceMatrix = 1
    DimRed.UseAllCores = 0
    # exclude distance matrix from the result, too many columns for SQLite
    Compress = simple.TTKCinemaQuery(InputTable=[DimRed])
    Compress.ExcludecolumnswithaRegexp = 1
    Compress.Regexp = "Dist.*"
    Compress.SQLStatement = "SELECT * FROM InputTable0"
    simple.SaveData("saddle2_red.csv", Input=Compress, Precision=8)


if __name__ == "__main__":
    use_networkx()

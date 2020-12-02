import matplotlib.pyplot as plt
import networkx as nx
from paraview import simple


def use_networkx():
    def print_cc(G):
        cc_size = dict()
        n_cc = nx.number_connected_components(G)
        print(f"#Connected Components: {n_cc}")
        print("#Nodes\t#Components")
        for cc in nx.connected_components(G):
            cc_size[len(cc)] = cc_size.get(len(cc), 0) + 1
        for k, v in cc_size.items():
            print(f" {k}\t{v}")

    def get_neighs(G, nodes, acc=set()):
        for node in nodes:
            for neigh in nx.all_neighbors(G, node):
                acc.add(neigh)

    with open("saddle2_graph.csv", "rb") as src:
        G = nx.readwrite.edgelist.read_edgelist(
            src, nodetype=str, create_using=nx.DiGraph
        )
        unG = nx.Graph(G)
        paths = list(nx.all_shortest_paths(unG, "149267_s1", "162498_s2"))
        paths += list(nx.all_shortest_paths(unG, "149267_s1", "121833_s2"))
        for path in paths:
            print(path)
        # neighs = set([src, dst])
        # get_neighs(G, [src], neighs)
        # get_neighs(G, neighs.copy(), neighs)
        # get_neighs(G, neighs.copy(), neighs)
        G = nx.subgraph(G, sum(paths, list()))
        color_map = list()
        for node in G:
            if "_s1" in node:
                color_map.append("cyan")
            elif "_s2" in node:
                color_map.append("orange")
            else:
                color_map.append("green")
        nx.draw_networkx(G, nx.spectral_layout(G), node_color=color_map)
        plt.show()


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

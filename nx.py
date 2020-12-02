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
            src, nodetype=int, create_using=nx.DiGraph
        )
        unG = nx.Graph(G)
        visited = [
            60341,
            74564,
            77880,
            159085,
            81420,
            72359,
            115214,
            103211,
            199306,
            60341,
            104284,
            33998,
            120664,
            123056,
            242452,
            60341,
            81420,
            105936,
            121869,
            126873,
            35162,
            77787,
            245584,
            60341,
            81420,
            125215,
            160047,
            200174,
            59768,
            72362,
            111967,
            81420,
            60913,
            77866,
            158070,
            81420,
            102584,
            144993,
            72321,
            240350,
            103211,
            103660,
            200171,
            104284,
            126888,
            103660,
            104284,
            126844,
            63835,
            79067,
            83049,
            33089,
            37354,
            123215,
            165646,
            104284,
            126888,
            38688,
            119608,
            103660,
            104284,
            63191,
            105936,
            126873,
            126920,
            126848,
            126873,
            83487,
            161109,
            126873,
            38144,
            39767,
            125215,
            38144,
            103662,
            125215,
            59768,
            59768,
            144993,
            60913,
            84077,
            126359,
            244748,
            126888,
            60913,
            124732,
            29923,
            15592,
            29842,
            120681,
            121833,
            144993,
            38144,
            144993,
            103660,
            103662,
            63835,
            83049,
            85158,
            37306,
            16738,
            33091,
            83049,
            83049,
            85158,
            148248,
            245902,
            17384,
            75905,
            19041,
            79268,
            19568,
            83049,
            83121,
            80365,
            118765,
            159273,
            63911,
            83049,
            148248,
            38688,
            104781,
            15592,
            83487,
            126359,
            147742,
            243788,
            124732,
            15592,
            103718,
            15592,
            127403,
            15592,
            17272,
            160197,
            41473,
            124182,
            85158,
            128569,
            16738,
            82547,
            16806,
            74749,
            204765,
            244894,
            148248,
            148295,
            17384,
            19041,
            127589,
            121020,
            122218,
            63911,
            63937,
            83121,
            83121,
            82547,
            83121,
            125332,
            159319,
            147238,
            118855,
            147742,
            17272,
            41473,
            149267,
            205701,
            16806,
            16806,
            148295,
            148297,
            16806,
            147791,
            148295,
            62769,
            122225,
            162498,
            244814,
            127589,
            127589,
            127614,
            146742,
            160523,
            125332,
            146734,
            242826,
            147238,
            128074,
            163506,
            245779,
            149267,
            41095,
            37564,
            62769,
            62769,
            127570,
            164661,
            62769,
            147704,
            146742,
            146734,
            127570,
            128074,
            105392,
            77938,
            128074,
            148737,
            41095,
            148904,
            79371,
            123478,
            41646,
            124479,
            248130,
            127570,
            105392,
            148375,
            204924,
            148904,
            83752,
            34494,
            106741,
            148904,
            41646,
            85841,
            41646,
            128746,
            38718,
            147846,
            121269,
            148375,
            17485,
            33483,
            83752,
            107241,
            128746,
            147846,
            147893,
            205018,
            17485,
            147893,
            148422,
            60913,
            124732,
            103211,
            102636,
            117927,
        ]
        G = nx.subgraph(G, visited)
        unG = nx.Graph(G)
        paths = list(nx.all_shortest_paths(unG, 102636, 117927))
        for path in paths:
            print(path)
        # neighs = set([src, dst])
        # get_neighs(G, [src], neighs)
        # get_neighs(G, neighs.copy(), neighs)
        # get_neighs(G, neighs.copy(), neighs)
        G = nx.subgraph(G, sum(paths, list()))
        color_map = list()
        for node in G:
            if G.succ[node] and G.pred[node]:
                color_map.append("red")
            elif G.succ[node]:
                color_map.append("cyan")
            elif G.pred[node]:
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

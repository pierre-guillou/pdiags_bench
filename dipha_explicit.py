import struct
import sys


def main(file):
    with open(file, "rb") as src:
        magic = int.from_bytes(src.read(8), "little", signed=True)
        if magic != 8067171840:
            print("Not a Dipha file")
            return
        dtype = int.from_bytes(src.read(8), "little", signed=True)
        if dtype != 0:
            print("Not a Dipha Explicit Complex")
            return
        mtype = int.from_bytes(src.read(8), "little", signed=True)
        if mtype == 0:
            print("Boundary matrix")
        elif mtype == 1:
            print("Co-boundary matrix")
        else:
            print("Incorrect matrix type")
            return
        ncells = int.from_bytes(src.read(8), "little", signed=True)
        print(f"Number of cells: {ncells}")
        dim = int.from_bytes(src.read(8), "little", signed=True)
        print(f"Global dataset dimension: {dim}")
        dims = [0, 0, 0, 0]
        for i in range(ncells):
            cdim = int.from_bytes(src.read(8), "little", signed=True)
            dims[cdim] += 1
        for i in range(dim + 1):
            print(f"  {dims[i]} cells of dimension {i}")
        values = list()
        for i in range(ncells):
            values.append(struct.unpack("d", src.read(8))[0])
        print(f"Min: {min(values)}, max: {max(values)}")
        offsets = list()
        for i in range(ncells):
            offsets.append(int.from_bytes(src.read(8), "little", signed=True))
        offsets_simplices = [
            offsets[slice(0, dims[0])],
            offsets[slice(dims[0], dims[0] + dims[1])],
            offsets[slice(dims[0] + dims[1], dims[0] + dims[1] + dims[2])],
        ]
        if dim == 3:
            offsets_simplices.append(
                offsets[slice(dims[0] + dims[1] + dims[2], ncells)]
            )
        for i in range(dim + 1):
            os = offsets_simplices[i]
            print(os)
            if len(os):
                print(f"  Offsets {i}-cells: {os[0]}, {os[-1]}")
        nentries = int.from_bytes(src.read(8), "little", signed=True)
        print(f"Non-null boundary matrix entries: {nentries}")
        bmat = list()
        for i in range(nentries):
            bmat.append(int.from_bytes(src.read(8), "little", signed=True))
        assert len(bmat) == nentries
        # assert nentries == offsets[-1] + dim + 1
        for i in range(dim + 1):
            os = offsets_simplices[i]
            if len(os):
                print(bmat[os[0] : os[-1]])



if __name__ == "__main__":
    main(sys.argv[1])

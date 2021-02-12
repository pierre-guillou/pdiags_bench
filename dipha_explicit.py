import struct
import sys


def check_type(src):
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


def check_cells(src):
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
    vals_per_dim = values[0 : dims[0]]
    print(f"  Values {0}-cells: {vals_per_dim}")
    off = dims[0]
    for i in range(1, dim + 1):
        vals_per_dim = values[off : off + dims[i]]
        off += dims[i]
        print(f"  Values {i}-cells: {vals_per_dim}")
    return ncells, dim, dims


def main(file):
    with open(file, "rb") as src:
        check_type(src)
        ncells, dim, dims = check_cells(src)
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
            if len(os):
                print(f"  Offsets {i}-cells: {os}")
        nentries = int.from_bytes(src.read(8), "little", signed=True)
        print(f"Non-null boundary matrix entries: {nentries}")
        bmat = list()
        for i in range(nentries):
            bmat.append(int.from_bytes(src.read(8), "little", signed=True))
        assert len(bmat) == nentries
        off = 0
        for i in range(1, dim):
            os = offsets_simplices[i + 1]
            if len(os):
                print(f"  Entries {i}-cells: {bmat[off : os[0]]}")
            off = os[0]
        print(f"  Entries {dim}-cells: {bmat[off : nentries]}")


def test(file):
    """Generate an explicit complex with arbitrary cells

    The cells are:
    * a triangle ABE
    * a quadrangle BCIE
    * a pentagon BCFGH
    * an hexagon EIDKJL
    with values A = 0, B = 1, ..., L = 11.
    """
    with open(file, "wb") as dst:
        magic = 8067171840  # DIPHA magic number
        dst.write(magic.to_bytes(8, "little", signed=True))
        dtype = 0  # explicit complex
        dst.write(dtype.to_bytes(8, "little", signed=True))
        mtype = 0  # boundary matrix
        dst.write(mtype.to_bytes(8, "little", signed=True))
        nverts = 12
        nedges = 15
        nfaces = 4
        ncells = nverts + nedges + nfaces  # number of cells
        dst.write(ncells.to_bytes(8, "little", signed=True))
        gl_dim = 2  # global dimension
        dst.write(gl_dim.to_bytes(8, "little", signed=True))
        # dimension of each cell
        dims = [nverts, nedges, nfaces]
        for dim in range(len(dims)):
            for _ in range(dims[dim]):
                dst.write(dim.to_bytes(8, "little", signed=True))
        # cell values
        for i in range(nverts):
            dst.write(struct.pack("<d", i))
        for i in [1, 4, 4, 8, 2, 8, 5, 6, 7, 7, 8, 10, 10, 11, 11]:
            dst.write(struct.pack("<d", i))
        for i in [4, 8, 7, 11]:
            dst.write(struct.pack("<d", i))
        # cell offset in boundary matrix
        off = 0
        for _ in range(nverts):
            dst.write(off.to_bytes(8, "little", signed=True))
        for _ in range(nedges):
            dst.write(off.to_bytes(8, "little", signed=True))
            off += 2
        dst.write(off.to_bytes(8, "little", signed=True))
        off += 3
        dst.write(off.to_bytes(8, "little", signed=True))
        off += 4
        dst.write(off.to_bytes(8, "little", signed=True))
        off += 5
        dst.write(off.to_bytes(8, "little", signed=True))
        # total number of non-zero entries in the boundary matrix
        off += 6
        dst.write(off.to_bytes(8, "little", signed=True))
        # boundary matrix values
        edges = [
            [0, 1],  # AB
            [0, 4],  # AE
            [1, 4],  # BE
            [4, 8],  # EI
            [1, 2],  # BC
            [2, 8],  # CI
            [2, 5],  # CF
            [5, 6],  # FG
            [6, 7],  # GH
            [1, 7],  # BH
            [3, 8],  # DI
            [3, 10],  # DK
            [9, 10],  # JK
            [9, 11],  # JL
            [4, 11],  # EL
        ]
        faces = [
            [0, 1, 4],  # ABE
            [1, 2, 8, 4],  # BCIE
            [1, 2, 5, 6, 7],  # BCFGH
            [4, 8, 3, 10, 9, 11],  # EIDKJL
        ]
        for e in edges:
            for v in e:
                dst.write(v.to_bytes(8, "little", signed=True))
        for f in faces:
            for v in f:
                dst.write(v.to_bytes(8, "little", signed=True))


if __name__ == "__main__":
    test("hello.dipha")
    main("hello.dipha")

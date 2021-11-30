import numpy as np
import pandas as pd
from paraview import servermanager, simple
from paraview.vtk.numpy_interface import dataset_adapter as dsa


def get_sfcp_arrays(vtp, dimrange=None):
    if dimrange is not None:
        thr = simple.Threshold(Input=vtp)
        thr.Scalars = ["POINTS", "CriticalType"]
        thr.ThresholdRange = dimrange
    else:
        thr = vtp

    calc0 = simple.Calculator(Input=thr)
    calc0.Function = "coordsX"
    calc0.ResultArrayName = "X"
    calc1 = simple.Calculator(Input=calc0)
    calc1.Function = "coordsY"
    calc1.ResultArrayName = "Y"
    calc2 = simple.Calculator(Input=calc1)
    calc2.Function = "coordsZ"
    calc2.ResultArrayName = "Z"

    vtk_thr = servermanager.Fetch(calc2)
    data = dsa.WrapDataObject(vtk_thr)

    vsf = data.PointData["ttkVertexScalarField"]
    iob = data.PointData["IsOnBoundary"]
    ct = data.PointData["CriticalType"]
    x = data.PointData["X"]
    y = data.PointData["Y"]
    z = data.PointData["Z"]
    res = np.array(list(zip(vsf, iob, ct, x, y, z)))
    print(f"{res.shape[0]} critical points")
    return pd.DataFrame(
        res,
        columns=["ttkVertexScalarField", "IsOnBoundary", "CriticalType", "X", "Y", "Z"],
    )


def get_dg_arrays(vtp, dimrange=None):
    if dimrange is not None:
        thr = simple.Threshold(Input=vtp)
        thr.Scalars = ["POINTS", "CellDimension"]
        thr.ThresholdRange = dimrange
    else:
        thr = vtp

    calc0 = simple.Calculator(Input=thr)
    calc0.Function = "coordsX"
    calc0.ResultArrayName = "X"
    calc1 = simple.Calculator(Input=calc0)
    calc1.Function = "coordsY"
    calc1.ResultArrayName = "Y"
    calc2 = simple.Calculator(Input=calc1)
    calc2.Function = "coordsZ"
    calc2.ResultArrayName = "Z"

    vtk_thr = servermanager.Fetch(calc2)
    data = dsa.WrapDataObject(vtk_thr)

    cell_id = data.PointData["CellId"]
    cell_dim = data.PointData["CellDimension"]
    vsf = data.PointData["ttkVertexScalarField"]
    iob = data.PointData["IsOnBoundary"]
    x = data.PointData["X"]
    y = data.PointData["Y"]
    z = data.PointData["Z"]

    res = np.array(list(zip(cell_id, vsf, iob, cell_dim, x, y, z)))
    print(f"{res.shape[0]} critical simplices")
    return pd.DataFrame(
        res,
        columns=[
            "CellId",
            "ttkVertexScalarField",
            "IsOnBoundary",
            "CellDimension",
            "X",
            "Y",
            "Z",
        ],
    )


def main():
    dg0 = simple.XMLPolyDataReader(FileName=["foot_old.vtp"])
    dg1 = simple.XMLPolyDataReader(FileName=["foot_new.vtp"])
    sfcp = simple.XMLPolyDataReader(FileName=["foot_sfcp.vtp"])
    for i in range(0, 2):
        continue
        print()
        test = get_dg_arrays(dg1, (i, i))
        ref = get_sfcp_arrays(sfcp, (i, i))
        print(f"  {test.shape[0]} critical simplices of dim {i} not on boundary")
        print(f"  {ref.shape[0]} critical points of dim {i} not on boundary")
        print(
            pd.merge(test, ref, on="ttkVertexScalarField", how="outer", indicator=True)
            .query("_merge == 'left_only'")
            .drop("_merge", 1)
        )
        print(
            pd.merge(ref, test, on="ttkVertexScalarField", how="outer", indicator=True)
            .query("_merge == 'left_only'")
            .drop("_merge", 1)
        )

        # res1 = get_dg_arrays(i, vtp1)
        # print(np.count_nonzero(np.not_equal(res0, res1)))

    # saddles & maxima from DiscreteGradient
    saddg = get_dg_arrays(dg1, (0, 3))
    # aggregated by ttkVertexScalarField
    saddg = saddg.drop_duplicates(subset="ttkVertexScalarField")
    print(saddg.sort_values("ttkVertexScalarField"))

    # saddles, maxima & multi-saddles from ScalarFieldCriticalPoints
    sadsf = get_sfcp_arrays(sfcp, (0, 4))
    print(sadsf.sort_values("ttkVertexScalarField"))

    rem_dg = (
        pd.merge(
            saddg,
            sadsf,
            on="ttkVertexScalarField",
            how="outer",
            indicator=True,
        )
        .query("_merge == 'left_only'")
        .drop("_merge", 1)
        .sort_values("ttkVertexScalarField")
    )
    # rem_dg = rem_dg[rem_dg["IsOnBoundary_x"] == 0]
    rem_dg = rem_dg[rem_dg["X_x"] > 1]
    rem_dg = rem_dg[rem_dg["Y_x"] > 1]
    rem_dg = rem_dg[rem_dg["Z_x"] > 1]

    rem_sf = (
        pd.merge(
            sadsf,
            saddg,
            on="ttkVertexScalarField",
            how="outer",
            indicator=True,
        )
        .query("_merge == 'left_only'")
        .drop("_merge", 1)
        .sort_values("ttkVertexScalarField")
    )
    rem_sf = rem_sf[rem_sf["IsOnBoundary_x"] == 0]

    print(rem_dg)
    print(rem_sf)


if __name__ == "__main__":
    main()

using Eirene
using Printf

input_csv = "eirene.csv"
output_diag = "diag_eirene.gudhi"

if size(ARGS, 1) >= 1
    output_diag = ARGS[2]
end
if size(ARGS, 1) >= 2
    input_csv = ARGS[1]
end

@time C = eirene(input_csv, model="complex", entryformat="ev", maxdim=2)

open(output_diag, "w") do io
    for d in 0:2
        A = barcode(C, dim=d)
        for i = 1:size(A, 1)
            println(io, @sprintf "%d %.3f %.3f" d A[i, 1] A[i, 2])
        end
    end
end

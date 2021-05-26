import edu.stanford.math.plex4.api.Plex4;
import edu.stanford.math.plex4.homology.barcodes.*;
import edu.stanford.math.plex4.homology.interfaces.AbstractPersistenceAlgorithm;
import edu.stanford.math.plex4.homology.chain_basis.Simplex;
import edu.stanford.math.plex4.streams.impl.ExplicitSimplexStream;

import java.io.*;
import java.nio.*;

public class jplex_persistence {
    static void writePairs(String outputFile, BarcodeCollection<Double> intervals)
        throws IOException {
        FileWriter wr = new FileWriter(outputFile);
        for(int i = 0; i < 3; ++i) {
            for(Interval<Double> pair: intervals.getIntervalsAtDimension(i)) {
                if(pair.isRightInfinite()) {
                    wr.write(i + " " + pair.getStart() + " inf\n");
                } else {
                    wr.write(i + " " + pair.getStart() + " " + pair.getEnd() + "\n");
                }
            }
        }
        wr.close();
    }

    public static void main(String[] args) throws IOException {
        if (args.length < 2) {
            System.out.println("Please provide input and output files");
            System.exit(0);
        }
        SimplicialComplex cpx = new SimplicialComplex(args[0]);
        ExplicitSimplexStream s = cpx.fillStream();
        AbstractPersistenceAlgorithm<Simplex> algo = Plex4.getDefaultSimplicialAlgorithm(3);
        long startTime = System.nanoTime();
        BarcodeCollection<Double> intervals = algo.computeIntervals(s);
        long endTime = System.nanoTime();
        double duration = (endTime - startTime) / 10e9;
        System.out.println("Computed diagram in " + duration + " seconds");
        writePairs(args[1], intervals);
    }
}

class SimplicialComplex {
    public int[] dims;
    public double[] values;
    public int[] edges;
    public int[] triangles;
    public int[] tetras;

    int readInt(InputStream is) throws IOException {
        byte[] ints = new byte[4];
        ByteBuffer buff = ByteBuffer.wrap(ints);
        buff.order(ByteOrder.LITTLE_ENDIAN);
        is.read(ints);
        return buff.getInt();
    }

    double[] readDoubleArray(InputStream is, int size) throws IOException {
        byte[] doubles = new byte[size * 8];
        ByteBuffer buff = ByteBuffer.wrap(doubles);
        buff.order(ByteOrder.LITTLE_ENDIAN);
        is.read(doubles);
        double[] res = new double[size];
        for(int i = 0; i < res.length; i++) {
            res[i] = buff.getDouble();
        }
        return res;
    }

    int[] readIntArray(InputStream is, int size) throws IOException {
        byte[] ints = new byte[size * 4];
        ByteBuffer buff = ByteBuffer.wrap(ints);
        buff.order(ByteOrder.LITTLE_ENDIAN);
        is.read(ints);
        int[] res = new int[size];
        for(int i = 0; i < res.length; i++) {
            res[i] = buff.getInt();
        }
        return res;
    }

    public SimplicialComplex(String inputFile) throws IOException {
        InputStream is = new FileInputStream(inputFile);
        byte[] magic = new byte[20];
        is.read(magic);
        String magic_str = new String(magic);
        if (!magic_str.equals("TTKSimplicialComplex")) {
            System.out.println("Not a TTK Simplicial Complex file");
            return;
        }
        int ncells = readInt(is);
        System.out.println("Number of cells: " + ncells);

        int dim = readInt(is);
        System.out.println("Global dataset dimension: " + dim);

        this.dims = new int[4];
        for(int i = 0; i < dims.length; ++i) {
            this.dims[i] = readInt(is);
            System.out.println("  " + this.dims[i] + " cells of dimension " + i);
        }

        this.values = readDoubleArray(is, ncells);

        int num_entries = readInt(is);
        System.out.println("Number of entries in boundary matrix: " + num_entries);

        this.edges = readIntArray(is, 2 * dims[1]);
        this.triangles = readIntArray(is, 3 * dims[2]);
        this.tetras = readIntArray(is, 4 * dims[3]);
        is.close();
    }

    ExplicitSimplexStream fillStream() {
        ExplicitSimplexStream s = new ExplicitSimplexStream();
        for(int i = 0; i < this.dims[0]; ++i) {
            s.addVertex(i, this.values[i]);
        }
        for(int i = 0; i < this.dims[1]; ++i) {
            int[] a = new int[]{
                this.edges[2 * i + 0],
                this.edges[2 * i + 1],
            };
            s.addElement(a, this.values[this.dims[0] + i]);
        }
        for(int i = 0; i < this.dims[2]; ++i) {
            int[] a = new int[]{
                this.triangles[3 * i + 0],
                this.triangles[3 * i + 1],
                this.triangles[3 * i + 2],
            };
            s.addElement(a, this.values[this.dims[0] + this.dims[1] + i]);
        }
        for(int i = 0; i < this.dims[3]; ++i) {
            int[] a = new int[]{
                this.tetras[4 * i + 0],
                this.tetras[4 * i + 1],
                this.tetras[4 * i + 2],
                this.tetras[4 * i + 3],
            };
            s.addElement(a, this.values[this.dims[0] + this.dims[1] + this.dims[2] + i]);
        }
        s.finalizeStream();
        return s;
    }

}


#include <stdint.h>
#include <string.h>

/* N=32 square FDN sample loop.
 * bufs: concatenated circular buffers; offsets[i], sizes[i]
 * H: row-major 32x32 ±1 as double
 * inject: n_samp x 32 row-major
 * peaking optional via use_peak + biquad state
 */
void fdn32_process(
    double *bufs_flat,       /* sum(sizes) */
    const int *sizes,        /* 32 */
    int *idx,                /* 32 */
    const double *H,         /* 32*32 */
    double g,
    const double *inject,    /* n_samp*32 */
    int n_samp,
    double *Lch,
    double *Rch,
    int do_peak,
    const int *use_peak,
    const double *b0,
    const double *b1,
    const double *b2,
    const double *a1,
    const double *a2,
    double *z1,
    double *z2
) {
    double reads[32];
    double filtered[32];
    double mixed[32];
    int offsets[32];
    int off = 0;
    for (int i = 0; i < 32; i++) { offsets[i] = off; off += sizes[i]; }

    for (int t = 0; t < n_samp; t++) {
        for (int i = 0; i < 32; i++) {
            reads[i] = bufs_flat[offsets[i] + idx[i]];
        }
        if (do_peak) {
            for (int i = 0; i < 32; i++) {
                if (use_peak[i]) {
                    double x = reads[i];
                    double yi = b0[i]*x + z1[i];
                    z1[i] = b1[i]*x - a1[i]*yi + z2[i];
                    z2[i] = b2[i]*x - a2[i]*yi;
                    filtered[i] = yi;
                } else {
                    filtered[i] = reads[i];
                }
            }
        } else {
            memcpy(filtered, reads, sizeof(filtered));
        }
        for (int row = 0; row < 32; row++) {
            double s = 0.0;
            const double *Hr = H + row*32;
            for (int col = 0; col < 32; col++) s += Hr[col] * filtered[col];
            mixed[row] = g * s;
        }
        const double *inj = inject + t*32;
        for (int i = 0; i < 32; i++) {
            int wi = idx[i];
            bufs_flat[offsets[i] + wi] = mixed[i] + inj[i];
            int ni = wi + 1;
            idx[i] = (ni >= sizes[i]) ? 0 : ni;
        }
        double sL = 0.0, sR = 0.0;
        for (int i = 0; i < 32; i += 2) {
            sL += filtered[i];
            sR += filtered[i+1];
        }
        Lch[t] = sL;
        Rch[t] = sR;
    }
}

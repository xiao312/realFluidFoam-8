# Registered mesh input qualification

The bounded read-only canonical-asset audit executed on SCNet at
2026-10-30T17:05:49Z using source `cef19779b0262b1c909f6148ac9e7f161a76ef8d`.
It read the original registered asset without modifying or downloading mesh
bytes. No CFD or Slurm admission occurred. All eight file sizes and SHA256 values
matched manifest `a9407929f9559bf2bf6b2082acc4c0e05d9aeaa721abd645ceedc3ed1999ca70`.
The decoded mesh contains 402882 points and 802928 faces; its immutable identity
is `1802701301b481669595ffd4550f64cffbd40461bd4aedd8f15023e99a484de9`.

| Quantity | CH4 inlet | O2 inlet |
|---|---:|---:|
| Faces | 54 | 49 |
| Measured area, m² | 7.477962844114543e-7 | 1.1155935404174525e-7 |
| Minimum radius, m | 0.0027999999523162836 | 7.46377785965091e-14 |
| Maximum radius, m | 0.005000000000000001 | 0.0016000000238418583 |
| Measured area / full annulus area | 0.013871267277135398 | 0.01387126727713727 |
| Aggregate lateral/axial area ratio | 0 | 6.554746128088441e-8 |

Both inlet areas agree with `../mesh-audit.json` within its 1e-12 m² rounding
precision. The area fraction uses actual wedge face geometry; it differs
slightly from simply dividing the nominal 5-degree angle by 360 degrees.
The retained oxygen diameter is 3.2 mm. This does not qualify the mesh as the
paper's 3.6-to-5 mm oxygen injector or resolve the axial-origin comparison.

The audit took 717.85 ms. Node24.14.1 executable SHA256 was
`bf9112eb83a827dc9f9c8d19bb7bddcbf00f7b2fedae18fdcaee05406981f20a`, using the
retained image's ld-2.31 loader and libraries. Direct execution against the old
login-host glibc failed before mutation. An earlier staged archive inherited
Windows CRLF conversion and was rejected by raw-Git-blob hash checks. The final
archive disabled that conversion and matched every member to its frozen blob.

An earlier geometry check also rejected the final oxygen face's 5.25e-11 m CAD
offset. The retained failure contains the exact vertices and area vector. The
corrected reader measures actual face area, reports the tilt and checks the
aggregate inlet plane. No mesh, physical acceptance threshold or paper data was
changed. Full operator receipts and retained failed inputs remain outside Git
under `state/forge-direct-20261030/execution` and the direct trial's input root.

APEC flux attribution

The one-dimensional flux adapts flux_terashima_etal from Trixi.jl,
commit 3ffaf4b91885fd3ede90d54476263ad3073a722d, nonideal_compressible_euler_2d.jl.
https://github.com/trixi-framework/Trixi.jl/blob/3ffaf4b91885fd3ede90d54476263ad3073a722d/src/equations/nonideal_compressible_euler_2d.jl

Method: Terashima, Ly and Ihme (2025), JCP 524, 113701,
https://doi.org/10.1016/j.jcp.2024.113701

The pressure derivatives, SRK recovery and OpenFOAM adaptation are local work.
The fork's existing license applies to local code; retain this upstream notice.

MIT License

Copyright (c) 2020-present The Trixi.jl Authors (see [AUTHORS.md](AUTHORS.md))

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.


#ifndef fgmMatrixResidual_H
#define fgmMatrixResidual_H

#include "fvCFD.H"

namespace Foam
{

// Cell-integrated source - A*psi, including each coupled neighbour once.
// Unlike fvScalarMatrix::residual(), this does not both update interfaces and
// subsequently add their same neighbour contribution as another source.
inline tmp<scalarField> fgmIntegratedResidual(const fvScalarMatrix& matrix)
{
    const scalarField& psi = matrix.psi().primitiveField();
    tmp<scalarField> result(new scalarField(matrix.source() - matrix.diag()*psi));
    scalarField& residual = result.ref();
    if (!matrix.diagonal())
    {
        const scalarField& upper = matrix.upper();
        const scalarField& lower = matrix.lower();
        const labelUList& owner = matrix.lduAddr().lowerAddr();
        const labelUList& neighbour = matrix.lduAddr().upperAddr();
        forAll(upper, facei)
        {
            residual[owner[facei]] -= upper[facei]*psi[neighbour[facei]];
            residual[neighbour[facei]] -= lower[facei]*psi[owner[facei]];
        }
    }
    forAll(matrix.psi().boundaryField(), patchi)
    {
        const fvPatchScalarField& patch = matrix.psi().boundaryField()[patchi];
        const labelUList& cells = patch.patch().faceCells();
        const scalarField& diagonal = matrix.internalCoeffs()[patchi];
        const scalarField& boundary = matrix.boundaryCoeffs()[patchi];
        forAll(cells, facei) residual[cells[facei]] -= diagonal[facei]*psi[cells[facei]];
        if (patch.coupled())
        {
            const tmp<scalarField> neighbour = patch.patchNeighbourField();
            forAll(cells, facei) residual[cells[facei]] += boundary[facei]*neighbour()[facei];
        }
        else
        {
            forAll(cells, facei) residual[cells[facei]] += boundary[facei];
        }
    }
    return result;
}

inline tmp<scalarField> fgmCoupledBoundarySource(const fvScalarMatrix& matrix)
{
    tmp<scalarField> result(new scalarField(matrix.psi().size(), scalar(0)));
    forAll(matrix.psi().boundaryField(), patchi)
    {
        const fvPatchScalarField& patch = matrix.psi().boundaryField()[patchi];
        if (patch.coupled())
        {
            const labelUList& cells = patch.patch().faceCells();
            const tmp<scalarField> neighbour = patch.patchNeighbourField();
            forAll(cells, facei)
                result.ref()[cells[facei]] += matrix.boundaryCoeffs()[patchi][facei]*neighbour()[facei];
        }
    }
    return result;
}

// Reconstruct lduMatrix::solver::normFactor for a scalar equation without
// changing matrix storage. This is a diagnostic of its near-constant-field
// scale, not a replacement stopping criterion or a tunable acceptance limit.
inline scalar fgmScalarNormalization(const fvScalarMatrix& matrix)
{
    const scalarField& psi = matrix.psi().primitiveField();
    scalarField rowSum(matrix.diag());
    scalarField source(matrix.source());
    if (!matrix.diagonal())
    {
        const labelUList& owner = matrix.lduAddr().lowerAddr();
        const labelUList& neighbour = matrix.lduAddr().upperAddr();
        forAll(matrix.upper(), facei)
        {
            rowSum[owner[facei]] += matrix.upper()[facei];
            rowSum[neighbour[facei]] += matrix.lower()[facei];
        }
    }
    forAll(matrix.psi().boundaryField(), patchi)
    {
        const fvPatchScalarField& patch = matrix.psi().boundaryField()[patchi];
        const labelUList& cells = patch.patch().faceCells();
        forAll(cells, facei)
        {
            rowSum[cells[facei]] += matrix.internalCoeffs()[patchi][facei];
            if (patch.coupled()) rowSum[cells[facei]] -= matrix.boundaryCoeffs()[patchi][facei];
            else source[cells[facei]] += matrix.boundaryCoeffs()[patchi][facei];
        }
    }
    const scalarField Apsi(source - fgmIntegratedResidual(matrix)());
    rowSum *= gAverage(psi, matrix.mesh().comm());
    return gSum((mag(Apsi - rowSum) + mag(source - rowSum))(), matrix.mesh().comm())
        + solverPerformance::small_;
}

}
#endif

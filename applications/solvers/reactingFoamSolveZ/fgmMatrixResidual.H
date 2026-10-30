#ifndef fgmMatrixResidual_H
#define fgmMatrixResidual_H

#include "fvCFD.H"
#include <limits>

namespace Foam
{

// Cell-integrated source - A*psi, including each coupled neighbour once.
// Unlike fvScalarMatrix::residual(), this does not both update interfaces and
// subsequently add their same neighbour contribution as another source.
inline tmp<scalarField> fgmIntegratedResidual(fvScalarMatrix& matrix)
{
    // OF8 exposes boundary/internal coefficients only through non-const
    // accessors. Keep their owner mutable, but read ldu storage through its
    // const interface so a symmetric/diagonal operator is never expanded.
    const fvScalarMatrix& coefficients = matrix;
    const scalarField& psi = matrix.psi().primitiveField();
    tmp<scalarField> result(new scalarField(coefficients.source() - coefficients.diag()*psi));
    scalarField& residual = result.ref();
    if (!matrix.diagonal())
    {
        const scalarField& upper = coefficients.upper();
        const scalarField& lower = coefficients.lower();
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

inline tmp<scalarField> fgmCoupledBoundarySource(fvScalarMatrix& matrix)
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
inline scalar fgmScalarNormalization(fvScalarMatrix& matrix)
{
    const fvScalarMatrix& coefficients = matrix;
    const scalarField& psi = matrix.psi().primitiveField();
    scalarField rowSum(coefficients.diag());
    scalarField source(coefficients.source());
    if (!matrix.diagonal())
    {
        const labelUList& owner = matrix.lduAddr().lowerAddr();
        const labelUList& neighbour = matrix.lduAddr().upperAddr();
        forAll(coefficients.upper(), facei)
        {
            rowSum[owner[facei]] += coefficients.upper()[facei];
            rowSum[neighbour[facei]] += coefficients.lower()[facei];
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

struct fgmResidualArithmeticAudit
{
    scalar summandL1W;
    scalar roundoffBoundW;
    label operationsPerCell;
};

// Forward-error bound for evaluating source - A*psi from the stored scalar
// coefficients, not for matrix assembly, thermo or time discretization.
inline fgmResidualArithmeticAudit fgmResidualArithmetic(fvScalarMatrix& matrix)
{
    const fvScalarMatrix& coefficients = matrix;
    const scalarField& psi = matrix.psi().primitiveField();
    scalarField scale(mag(coefficients.source()) + mag(coefficients.diag()*psi));
    labelList operations(psi.size(), 3);
    if (!matrix.diagonal())
    {
        const labelUList& owner = matrix.lduAddr().lowerAddr();
        const labelUList& neighbour = matrix.lduAddr().upperAddr();
        forAll(coefficients.upper(), facei)
        {
            scale[owner[facei]] += mag(coefficients.upper()[facei]*psi[neighbour[facei]]);
            scale[neighbour[facei]] += mag(coefficients.lower()[facei]*psi[owner[facei]]);
            operations[owner[facei]] += 2;
            operations[neighbour[facei]] += 2;
        }
    }
    forAll(matrix.psi().boundaryField(), patchi)
    {
        const fvPatchScalarField& patch = matrix.psi().boundaryField()[patchi];
        const labelUList& cells = patch.patch().faceCells();
        forAll(cells, facei)
        {
            scale[cells[facei]] += mag(matrix.internalCoeffs()[patchi][facei]*psi[cells[facei]]);
            operations[cells[facei]] += 2;
        }
        if (patch.coupled())
        {
            const tmp<scalarField> neighbour = patch.patchNeighbourField();
            forAll(cells, facei)
            {
                scale[cells[facei]] += mag(matrix.boundaryCoeffs()[patchi][facei]*neighbour()[facei]);
                operations[cells[facei]] += 2;
            }
        }
        else forAll(cells, facei)
        {
            scale[cells[facei]] += mag(matrix.boundaryCoeffs()[patchi][facei]);
            operations[cells[facei]] += 1;
        }
    }
    // Use the largest row count for a simple reproducible global bound.
    const label count = gMax(operations);
    const scalar unitRoundoff = std::numeric_limits<scalar>::epsilon()/2;
    const scalar gamma = count*unitRoundoff/(1 - count*unitRoundoff);
    const scalar total = gSum(scale);
    return {total, gamma*total, count};
}

}
#endif

#include <array>
#include <vector>
#include <algorithm>
#include <fstream>
#include <iomanip>

inline void writeSpatialSpeedFields
(
    const char* stage, const Foam::fvMesh& mesh,
    const Foam::volScalarField& rho, const Foam::volVectorField& U,
    const Foam::volScalarField& T, const Foam::volScalarField& p,
    const Foam::volScalarField& OH, const Foam::scalarField& source,
    const Foam::scalarField& diffusion
)
{
    using namespace Foam;
    const auto& D=mesh.lookupObject<volScalarField>("Dimix_OH");
    const auto& W=mesh.lookupObject<volScalarField>("Wmix");
    volScalarField fick("spatialFick",fvc::laplacian(rho*D,OH)
        +fvc::laplacian(rho*D*OH/W,W));
    volVectorField grad("spatialGrad",fvc::grad(OH));
    List<scalarField> buffers(Pstream::nProcs());
    auto& local=buffers[Pstream::myProcNo()];local.setSize(10*mesh.nCells());
    forAll(OH,i)
    {
        const double values[]={mesh.C()[i].x(),OH[i],grad[i].x(),rho[i],
            U[i].x(),T[i],p[i],source[i],diffusion[i],fick[i]};
        for (int k=0;k<10;++k) local[10*i+k]=values[k];
    }
    Pstream::gatherList(buffers);
    if (!Pstream::master()) return;
    std::vector<std::array<double,10>> points;
    forAll(buffers,rank)
    {
        const auto& values=buffers[rank];
        for (label i=0;i<values.size();i+=10)
        {
            std::array<double,10> point;
            for (int k=0;k<10;++k) point[k]=values[i+k];
            points.push_back(point);
        }
    }
    std::sort(points.begin(),points.end(),
        [](const std::array<double,10>& a,const std::array<double,10>& b){return a[0]<b[0];});
    const std::size_t coldCount=points.size()/20;
    if (!coldCount) FatalErrorInFunction << "Too few cells" << exit(FatalError);
    double freshLeft=0,freshRight=0;
    for (std::size_t i=0;i<coldCount;++i)
    {freshLeft+=points[i][3];freshRight+=points[points.size()-1-i][3];}
    freshLeft/=coldCount;freshRight/=coldCount;
    const double mid=(points.front()[0]+points.back()[0])/2;
    const fileName path(mesh.time().path()/
        ("spatial-"+word(stage)+"-"+mesh.time().timeName()+".csv"));
    if (isFile(path)) FatalErrorInFunction << "Refusing overwrite " << path << exit(FatalError);
    std::ofstream out(path.c_str());out<<std::setprecision(17)
        <<"x_m,YOH,gradOH_1_m,rho_kg_m3,U_m_s,T_K,p_Pa,omegaOH_kg_m3_s,"
        <<"diffusion_used_kg_m3_s,diffusion_Fick_kg_m3_s,rho_unburned_kg_m3\n";
    for (const auto& point:points)
    {
        for (int k=0;k<10;++k) out<<point[k]<<',';
        out<<(point[0]<mid?freshLeft:freshRight)<<'\n';
    }
    out.close();
    if (!out) FatalErrorInFunction << "Cannot write " << path << exit(FatalError);
}

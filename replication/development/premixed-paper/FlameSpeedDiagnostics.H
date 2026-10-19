// SPDX-License-Identifier: GPL-3.0-or-later
#include "sampling.H"
#include "basicChemistryModel.H"
#include <fstream>
#include <iomanip>
#include <memory>

class FlameSpeedDiagnostics
{
    const Foam::fvMesh& mesh_;
    Foam::IOdictionary settings_;
    bool enabled_;
    Foam::label interval_;
    Foam::scalarList levels_;
    Foam::scalar initialDensity_;
    std::unique_ptr<std::ofstream> stream_;
public:
    explicit FlameSpeedDiagnostics(const Foam::fvMesh& mesh)
    : mesh_(mesh), settings_(Foam::IOobject("flameSpeedProperties",
        mesh.time().constant(),mesh,Foam::IOobject::MUST_READ,Foam::IOobject::NO_WRITE)),
      enabled_(settings_.lookupOrDefault<Foam::Switch>("enabled",true)),
      interval_(settings_.lookup<Foam::label>("interval")),
      levels_(settings_.lookup("levels")),
      initialDensity_(settings_.lookup<Foam::scalar>("initialFreshDensity"))
    {
        if (interval_<1 || levels_.empty() || initialDensity_<=0)
            FatalErrorInFunction << "Invalid flameSpeedProperties" << Foam::exit(Foam::FatalError);
        if (enabled_ && Foam::Pstream::master())
        {
            const Foam::fileName path(mesh.time().path()/"flame-speed.csv");
            if (Foam::isFile(path))
                FatalErrorInFunction << "Refusing existing history " << path << Foam::exit(Foam::FatalError);
            stream_.reset(new std::ofstream(path.c_str()));
            *stream_ << std::setprecision(17)
                << "time_s,delta_t_s,stage,side,OH_level,status,crossings,x_m,"
                << "rho_unburned,T_unburned,p_unburned,U_unburned,initial_rho_unburned,"
                << "rho_local,U_local,grad_OH,chemistry_m_s,diffusion_m_s,speed_m_s\n";
        }
    }
    bool due() const
    {
        return enabled_ && (mesh_.time().timeIndex()%interval_==0 || mesh_.time().writeTime());
    }
    void write(const char* stage, const Foam::volScalarField& rho,
        const Foam::volVectorField& U, const Foam::volScalarField& T,
        const Foam::volScalarField& p, const Foam::volScalarField& OH,
        const Foam::scalarField& source, const Foam::scalarField& diffusion)
    {
        Foam::volVectorField gradient("diagnosticOHGradient",Foam::fvc::grad(OH));
        Foam::List<Foam::scalarField> buffers(Foam::Pstream::nProcs());
        Foam::scalarField& local=buffers[Foam::Pstream::myProcNo()];
        local.setSize(9*mesh_.nCells());
        forAll(OH,i)
        {
            const double values[]={mesh_.C()[i].x(),OH[i],gradient[i].x(),rho[i],
                U[i].x(),T[i],p[i],source[i],diffusion[i]};
            for (int k=0;k<9;++k) local[9*i+k]=values[k];
        }
        Foam::Pstream::gatherList(buffers);
        if (!Foam::Pstream::master()) return;
        std::vector<paperFlame::Point> points;
        forAll(buffers,rank)
        {
            const auto& b=buffers[rank];
            for (Foam::label i=0;i<b.size();i+=9)
                points.push_back({b[i],b[i+1],b[i+2],b[i+3],b[i+4],b[i+5],b[i+6],b[i+7],b[i+8]});
        }
        std::sort(points.begin(),points.end(),[](const paperFlame::Point& a,const paperFlame::Point& b){return a.x<b.x;});
        forAll(levels_,k) for (bool left : {true,false})
        {
            const auto s=paperFlame::sample(points,levels_[k],left);
            *stream_ << mesh_.time().value() << ',' << mesh_.time().deltaTValue()
                << ',' << stage << ',' << (left?"left":"right") << ',' << levels_[k]
                << ',' << s.status << ',' << s.crossings << ',' << s.x
                << ',' << s.freshRho << ',' << s.freshT << ',' << s.freshP
                << ',' << s.freshU << ',' << initialDensity_ << ',' << s.rho
                << ',' << s.U << ',' << s.gradient << ',' << s.chemical
                << ',' << s.diffusive << ',' << s.speed << '\n';
        }
        stream_->flush();
        if (!*stream_) FatalErrorInFunction << "History write failed" << Foam::exit(Foam::FatalError);
    }
};

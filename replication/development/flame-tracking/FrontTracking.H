#include "trackingCore.H"
#include <fstream>
#include <iomanip>
#include <memory>
class FrontTracking
{
    const Foam::fvMesh& mesh_;
    Foam::IOdictionary config_;
    bool enabled_;
    Foam::label interval_;
    double window_,freshTemperature_;
    Foam::scalarList temperatures_,oh_;
    std::vector<flameTracking::History> histories_;
    std::unique_ptr<std::ofstream> stream_;
public:
    explicit FrontTracking(const Foam::fvMesh& mesh)
    :mesh_(mesh),config_(Foam::IOobject("frontTrackingProperties",mesh.time().constant(),mesh,
         Foam::IOobject::MUST_READ,Foam::IOobject::NO_WRITE)),
     enabled_(config_.lookupOrDefault<Foam::Switch>("enabled",true)),
     interval_(config_.lookup<Foam::label>("interval")),
     window_(config_.lookup<Foam::scalar>("windowSeconds")),
     freshTemperature_(config_.lookup<Foam::scalar>("freshTemperature")),
     temperatures_(config_.lookup("temperatureLevels")),oh_(config_.lookup("ohLevels")),
     histories_(2*(temperatures_.size()+oh_.size()))
    {
        if(interval_<1 || window_<=0 || temperatures_.empty() || oh_.empty())
            FatalErrorInFunction<<"Invalid front tracking configuration"<<Foam::exit(Foam::FatalError);
        if(enabled_ && Foam::Pstream::master())
        {
            const Foam::fileName path(mesh.time().path()/"front-tracking.csv");
            if(Foam::isFile(path))FatalErrorInFunction<<"Refusing existing "<<path<<Foam::exit(Foam::FatalError);
            stream_.reset(new std::ofstream(path.c_str()));
            *stream_<<std::setprecision(17)<<"time_s,side,marker,level,primary,status,crossings,x_m,rho_local,U_local,rho_unburned,U_unburned,T_unburned,window_start_s,window_end_s,samples,lab_outward_m_s,fresh_relative_m_s,density_weighted_m_s,secant_density_weighted_m_s,fit_max_residual_m\n";
        }
    }
    bool due()const{return enabled_&&(mesh_.time().timeIndex()%interval_==0||mesh_.time().writeTime());}
    void write(const Foam::volScalarField& rho,const Foam::volVectorField& U,
               const Foam::volScalarField& T,const Foam::volScalarField& OH)
    {
        if(!enabled_)return;
        Foam::List<Foam::scalarField> buffers(Foam::Pstream::nProcs());
        auto& local=buffers[Foam::Pstream::myProcNo()];local.setSize(5*mesh_.nCells());
        forAll(T,i)
        {
            const double values[]={mesh_.C()[i].x(),T[i],OH[i],rho[i],U[i].x()};
            for(int j=0;j<5;++j)local[5*i+j]=values[j];
        }
        Foam::Pstream::gatherList(buffers);
        if(!Foam::Pstream::master())return;
        std::vector<flameTracking::Point> points;
        forAll(buffers,rank)
        {const auto& b=buffers[rank];for(Foam::label i=0;i<b.size();i+=5)points.push_back({b[i],b[i+1],b[i+2],b[i+3],b[i+4]});}
        std::sort(points.begin(),points.end(),[](const flameTracking::Point&a,const flameTracking::Point&b){return a.x<b.x;});
        std::size_t index=0;
        for(bool temperature:{true,false})
        {
            const auto& levels=temperature?temperatures_:oh_;
            forAll(levels,k)for(bool left:{true,false})
            {
                const auto sample=flameTracking::sample(points,temperature,levels[k],left,freshTemperature_);
                const auto result=histories_[index++].add(mesh_.time().value(),sample,left,window_);
                const bool primary=temperature?k==0:std::abs(levels[k]-2e-5)<1e-15;
                *stream_<<mesh_.time().value()<<','<<(left?"left":"right")<<','<<(temperature?"T":"OH")<<','<<levels[k]<<','<<primary
                    <<','<<result.status<<','<<sample.crossings<<','<<sample.x<<','<<sample.rho<<','<<sample.U<<','<<sample.freshRho<<','<<sample.freshU<<','<<sample.freshT
                    <<','<<result.start<<','<<result.end<<','<<result.count<<','<<result.laboratory<<','<<result.freshRelative<<','<<result.weighted<<','<<result.secant<<','<<result.fitResidual<<'\n';
            }
        }
        stream_->flush();
        if(!*stream_)FatalErrorInFunction<<"Tracking history write failed"<<Foam::exit(Foam::FatalError);
    }
};

#include "fvMeshFunctionObject.H"
#include "basicChemistryModel.H"
#include "volFields.H"
#include "addToRunTimeSelectionTable.H"
#include "PstreamReduceOps.H"
#include <fstream>
#include <iomanip>

namespace Foam { namespace functionObjects {
class rfHeatReleaseMonitor : public fvMeshFunctionObject
{
    scalar area_, lastTime_;
public:
    TypeName("rfHeatReleaseMonitor");
    rfHeatReleaseMonitor(const word& name, const Time& runTime, const dictionary& dict)
    : fvMeshFunctionObject(name,runTime,dict),
      area_(readScalar(dict.lookup("crossSectionArea"))), lastTime_(-GREAT)
    {
        if (area_<=0) FatalErrorInFunction << "Positive crossSectionArea required" << exit(FatalError);
    }
    virtual bool execute()
    {
        const scalar now=mesh_.time().value();
        if (now<=0 || now==lastTime_) return true;
        if (!mesh_.foundObject<basicChemistryModel>("chemistryProperties"))
        {
            WarningInFunction << "No chemistryProperties; heat-release sample skipped" << endl;
            return false;
        }
        const auto& chemistry=mesh_.lookupObject<basicChemistryModel>("chemistryProperties");
        tmp<volScalarField> values=chemistry.Qdot();
        const scalarField& q=values().primitiveField();
        const scalarField& volumes=mesh_.V();
        const vectorField& centres=mesh_.C().primitiveField();
        scalar lo=GREAT,hi=-GREAT,xlo=GREAT,xhi=-GREAT;
        forAll(q,i) {lo=min(lo,q[i]);hi=max(hi,q[i]);xlo=min(xlo,centres[i].x());xhi=max(xhi,centres[i].x());}
        reduce(lo,minOp<scalar>());reduce(hi,maxOp<scalar>());
        reduce(xlo,minOp<scalar>());reduce(xhi,maxOp<scalar>());
        scalar net=0,positive=0,negative=0,left=0,right=0,peakX=GREAT;
        const scalar mid=(xlo+xhi)/2;
        forAll(q,i)
        {
            const scalar power=q[i]*volumes[i];net+=power;
            positive+=max(power,scalar(0));negative+=min(power,scalar(0));
            if (centres[i].x()<mid) left+=power; else right+=power;
            if (q[i]==hi) peakX=min(peakX,centres[i].x());
        }
        reduce(net,sumOp<scalar>());reduce(positive,sumOp<scalar>());reduce(negative,sumOp<scalar>());
        reduce(left,sumOp<scalar>());reduce(right,sumOp<scalar>());reduce(peakX,minOp<scalar>());
        const auto& T=mesh_.lookupObject<volScalarField>("T");
        const auto& p=mesh_.lookupObject<volScalarField>("p");
        const scalar Tmax=gMax(T.primitiveField()),pmin=gMin(p.primitiveField()),pmax=gMax(p.primitiveField());
        if (Pstream::master())
        {
            const fileName path=mesh_.time().path()/"heat-release-used.csv";
            std::ifstream existing(path.c_str());const bool header=!existing.good();existing.close();
            std::ofstream out(path.c_str(),std::ios::app);
            if (!out.good()) {WarningInFunction << "Cannot write " << path << endl;return false;}
            if (header) out << "time_s,delta_t_s,Qdot_min_W_m3,Qdot_max_W_m3,peak_x_m,net_W,positive_W,negative_W,left_W,right_W,net_W_m2,Tmax_K,pmin_Pa,pmax_Pa\n";
            out << std::setprecision(17) << now << ',' << mesh_.time().deltaTValue() << ','
                << lo << ',' << hi << ',' << peakX << ',' << net << ',' << positive << ',' << negative
                << ',' << left << ',' << right << ',' << net/area_ << ',' << Tmax << ',' << pmin << ',' << pmax << '\n';
        }
        lastTime_=now;
        return true;
    }
    virtual bool write()
    {
        execute();
        if (mesh_.time().value()<=0 || !mesh_.foundObject<basicChemistryModel>("chemistryProperties")) return true;
        tmp<volScalarField> q=mesh_.lookupObject<basicChemistryModel>("chemistryProperties").Qdot();
        q.ref().rename("Qdot_used");
        return q().write();
    }
};
defineTypeNameAndDebug(rfHeatReleaseMonitor,0);
addToRunTimeSelectionTable(functionObject,rfHeatReleaseMonitor,dictionary);
}}

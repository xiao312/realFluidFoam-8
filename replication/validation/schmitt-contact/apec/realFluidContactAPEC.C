#include "fvCFD.H"
#include "psiReactionThermo.H"
#include "uniformDimensionedFields.H"
#include "apecFlux.H"
#include "../../../../applications/solvers/reactingFoamSolveZ/fgmThermoClosure.H"

using namespace Foam;
using namespace ContactDF;
using namespace ContactAPEC;

int main(int argc,char* argv[])
{
    #include "setRootCase.H"
    #include "createTime.H"
    #include "createMesh.H"
    if(Pstream::parRun()||runTime.value()!=0)
        FatalErrorInFunction<<"Fresh serial time-zero contact required"<<exit(FatalError);
    if(!runTime.controlDict().lookupOrDefault<Switch>("contactAPECInviscid",false))
        FatalErrorInFunction<<"Select contactAPECInviscid yes explicitly; Fourier diffusion is not advanced"<<exit(FatalError);
    IOdictionary combustion(IOobject("combustionProperties",runTime.constant(),mesh,IOobject::MUST_READ,IOobject::NO_WRITE));
    IOdictionary momentum(IOobject("momentumTransport",runTime.constant(),mesh,IOobject::MUST_READ,IOobject::NO_WRITE));
    if(combustion.lookup<word>("combustionModel")!="none"||momentum.lookup<word>("simulationType")!="laminar")
        FatalErrorInFunction<<"Only inviscid nonreacting contacts are implemented"<<exit(FatalError);
    uniformDimensionedVectorField gravity(IOobject("g",runTime.constant(),mesh,IOobject::MUST_READ,IOobject::NO_WRITE));
    if(mag(gravity.value())>SMALL)FatalErrorInFunction<<"Gravity is unsupported"<<exit(FatalError);
    autoPtr<psiReactionThermo> model(psiReactionThermo::New(mesh));
    psiReactionThermo& thermo=model();thermo.validate(args.executable(),"h");
    basicSpecieMixture& composition=thermo.composition();
    const ContactDF::Mixture* mixture=dynamic_cast<const ContactDF::Mixture*>(&composition);
    if(!mixture||composition.species().size()!=2||composition.species()[0]!="H2"||composition.species()[1]!="O2")
        FatalErrorInFunction<<"Exact H2/O2 sensible-enthalpy SRK Chung mixture required"<<exit(FatalError);
    volVectorField U(IOobject("U",runTime.timeName(),mesh,IOobject::MUST_READ,IOobject::AUTO_WRITE),mesh);
    volScalarField rho(IOobject("rho",runTime.timeName(),mesh,IOobject::NO_READ,IOobject::AUTO_WRITE),thermo.rho());
    volScalarField Ha(IOobject("Ha",runTime.timeName(),mesh,IOobject::NO_READ,IOobject::AUTO_WRITE),thermo.he());
    volScalarField rhoEnergy(IOobject("rhoEnergyAPEC",runTime.timeName(),mesh,IOobject::NO_READ,IOobject::AUTO_WRITE),rho*(thermo.he()-thermo.p()/rho+.5*magSqr(U)));
    surfaceScalarField phi(IOobject("phi",runTime.timeName(),mesh,IOobject::NO_READ,IOobject::AUTO_WRITE),fvc::flux(rho*U));
    Info().precision(16);
    const unsigned n=mesh.nCells();
    if(n<2)FatalErrorInFunction<<"At least two ordered uniform x cells required"<<exit(FatalError);
    const scalar dx=mesh.C()[1].x()-mesh.C()[0].x(),area=mesh.V()[0]/dx;
    if(!(dx>0&&area>0))FatalErrorInFunction<<"Positive uniform x spacing required"<<exit(FatalError);
    for(unsigned i=0;i<n;++i)
        if(mag(mesh.C()[i].x()-(mesh.C()[0].x()+i*dx))>1e-8*dx
         ||mag(mesh.C()[i].y()-mesh.C()[0].y())>1e-8*dx
         ||mag(mesh.C()[i].z()-mesh.C()[0].z())>1e-8*dx
         ||mag(mesh.V()[i]/(area*dx)-1)>1e-8||mag(U[i].y())+mag(U[i].z())>1e-12)
            FatalErrorInFunction<<"Only ordered uniform one-dimensional x meshes/velocities are supported"<<exit(FatalError);
    const word reconstruction=runTime.controlDict().lookupOrDefault<word>
        ("contactAPECReconstruction","firstOrder");
    if(reconstruction!="firstOrder" && reconstruction!="limitedLinear")
        FatalErrorInFunction<<"Use firstOrder or limitedLinear reconstruction"<<exit(FatalError);
    const bool limitedLinear=reconstruction=="limitedLinear";
    const scalar cfl=runTime.controlDict().lookupOrDefault<scalar>("maxAcousticCo",.3);
    const scalar maxDt=runTime.controlDict().lookupOrDefault<scalar>("maxDeltaT",1e-5);
    if(!(cfl>0&&cfl<=.5&&maxDt>0))FatalErrorInFunction<<"Require0<maxAcousticCo<=0.5 and positive maxDeltaT"<<exit(FatalError);
    std::vector<Conserved> state(n);
    std::vector<Primitive> primitive(n);
    for(unsigned i=0;i<n;++i)
    {
        std::array<scalar,2> y{{composition.Y()[0][i],composition.Y()[1][i]}};
        const ContactDF::Thermo& point=mixture->cellMixture(i);
        primitive[i]=physicalState(point,rho[i],U[i].x(),thermo.p()[i],thermo.T()[i],y);
        state[i].rho=rho[i];state[i].momentum=rho[i]*U[i].x();
        state[i].energy=rho[i]*(primitive[i].absoluteH-thermo.p()[i]/rho[i]+.5*sqr(U[i].x()));
        for(unsigned k=0;k<2;++k)state[i].species[k]=rho[i]*y[k];
        Ha[i]=primitive[i].absoluteH;rhoEnergy[i]=state[i].energy;
    }
    const Primitive leftFar=primitive.front(),rightFar=primitive.back();
    auto integral=[&](const std::vector<Conserved>& values,int quantity)->scalar
    {
        scalar result=0;for(unsigned i=0;i<n;++i)result+=mesh.V()[i]*(quantity==0?values[i].rho:quantity==1?values[i].momentum:values[i].energy);return result;
    };
    // Conservative rho/e recovery: no frozen-gamma projection or energy reset.
    const ContactDF::Thermo& oxygen=mixture->cellMixture(0);
    const bool applyAPEC=runTime.controlDict().lookupOrDefault<Switch>("contactAPECEnabled",true);
    for(unsigned i=0;i<n;++i)if(mag(primitive[i].species[0])>1e-14||mag(primitive[i].species[1]-1)>1e-14)
        FatalErrorInFunction<<"APEC prototype supports pure O2 only"<<exit(FatalError);
    if(limitedLinear)FatalErrorInFunction<<"APEC prototype uses two-point central face flux"<<exit(FatalError);
    const scalar analytic=pressureEnergyDerivative(oxygen,primitive[0]),delta=1e-4;
    const auto& v=primitive[0];
    const scalar rp=oxygen.rho(v.p,v.T+delta),rm=oxygen.rho(v.p,v.T-delta);
    const scalar numerical=(rp*oxygen.Ha(v.p,v.T+delta)-rm*oxygen.Ha(v.p,v.T-delta))/(rp-rm);
    const scalar derivativeError=mag(analytic-numerical)/max(scalar(1),mag(numerical));
    Info<<"APEC_DERIVATIVE analytic="<<analytic<<" finiteDifference="<<numerical<<" relativeError="<<derivativeError<<endl;
    if(derivativeError>1e-5)FatalErrorInFunction<<"APEC derivative check failed"<<exit(FatalError);
    auto project=[&](const std::vector<Conserved>& values,const std::vector<Primitive>&)->std::vector<Primitive>
    {
        std::vector<Primitive> result(n);
        for(unsigned i=0;i<n;++i)
        {
            result[i]=recover(oxygen,values[i],thermo.T()[i]);
            const Primitive& v=result[i];thermo.p()[i]=v.p;thermo.T()[i]=v.T;
            composition.Y()[0][i]=0;composition.Y()[1][i]=1;
            rho[i]=v.rho;U[i]=vector(v.u,0,0);thermo.he()[i]=oxygen.Hs(v.p,v.T);
            Ha[i]=v.absoluteH;rhoEnergy[i]=values[i].energy;
        }
        return result;
    };
    auto stage=[&](const std::vector<Conserved>& base,const Evaluation& evaluation,scalar dt)->std::vector<Conserved>
    {
        std::vector<Conserved> result(n);for(unsigned i=0;i<n;++i)result[i]=combine(base[i],evaluation.cells[i],1,dt);return result;
    };
    auto updatePhi=[&](const Evaluation& evaluation)->void
    {
        const scalar edge=mesh.C()[0].x()-.5*dx;
        auto value=[&](scalar x,scalar sx)->scalar{if(mag(sx)<1e-12*area)return scalar(0);const long face=std::lround((x-edge)/dx);if(face<0||face>long(n))FatalErrorInFunction<<"Face outside uniform1D recipe"<<exit(FatalError);return evaluation.faces[face].mass*sx;};
        forAll(phi,face)phi[face]=value(mesh.Cf()[face].x(),mesh.Sf()[face].x());
        forAll(phi.boundaryField(),patch)
            forAll(phi.boundaryField()[patch],face)phi.boundaryFieldRef()[patch][face]=value(mesh.Cf().boundaryField()[patch][face].x(),mesh.Sf().boundaryField()[patch][face].x());
    };
    scalar cumulativeDefect=0,cumulativeMassBoundary=0,cumulativeEnergyBoundary=0;
    const scalar initialMass=integral(state,0),initialEnergy=integral(state,2);
    label steps=0;
    Info<<"CONTACT_APEC_INIT cells="<<n<<" dx="<<dx<<" area="<<area
        <<" massKg="<<initialMass<<" absoluteEnergyJ="<<initialEnergy
        <<" apecCorrection="<<applyAPEC<<" acousticCo="<<cfl<<" reconstruction="<<reconstruction<<" time=SSPRK3 energy=absoluteHa quasiConservative=0"<<endl;
    while(runTime.run())
    {
        std::vector<Primitive> frozen=primitive;
        scalar dt=maxDt;for(const Primitive& v:primitive)dt=min(dt,cfl*dx/(mag(v.u)+v.sound));
        dt=min(dt,runTime.endTime().value()-runTime.value());
        runTime.setDeltaT(dt);dt=runTime.deltaTValue();runTime++;
        const std::vector<Conserved> old=state;
        const Evaluation l0=evaluate(primitive,frozen,leftFar,rightFar,dx,area,oxygen,applyAPEC);
        const std::vector<Conserved> w1=stage(old,l0,dt);
        const std::vector<Primitive> v1=project(w1,frozen);
        const Evaluation l1=evaluate(v1,frozen,leftFar,rightFar,dx,area,oxygen,applyAPEC);
        const std::vector<Conserved> e1=stage(w1,l1,dt);
        std::vector<Conserved> w2(n);for(unsigned i=0;i<n;++i)w2[i]=combine(old[i],e1[i],.75,.25);
        const std::vector<Primitive> v2=project(w2,frozen);
        const Evaluation l2=evaluate(v2,frozen,leftFar,rightFar,dx,area,oxygen,applyAPEC);
        const std::vector<Conserved> e2=stage(w2,l2,dt);
        for(unsigned i=0;i<n;++i)state[i]=combine(old[i],e2[i],1.0/3,2.0/3);
        primitive=project(state,frozen);
        updatePhi(evaluate(primitive,frozen,leftFar,rightFar,dx,area,oxygen,applyAPEC));
        thermo.p().correctBoundaryConditions();U.correctBoundaryConditions();
        forAll(composition.Y(),k)composition.Y()[k].correctBoundaryConditions();
        thermo.T().correctBoundaryConditions();thermo.he().correctBoundaryConditions();thermo.correct();
        auditFgmThermoClosure(thermo);
        scalar sync=0,maxDensityError=0;
        for(unsigned i=0;i<n;++i)
        {
            const ContactDF::Thermo& point=mixture->cellMixture(i);
            maxDensityError=max(maxDensityError,mag(point.rho(thermo.p()[i],thermo.T()[i])-state[i].rho)/state[i].rho);
            Ha[i]=point.Ha(thermo.p()[i],thermo.T()[i]);
            const scalar actual=state[i].rho*(Ha[i]-thermo.p()[i]/state[i].rho+.5*sqr(U[i].x()));
            const scalar recoveryError=mag(actual-state[i].energy)/max(scalar(1),mag(state[i].energy));
            if(recoveryError>1e-8)FatalErrorInFunction<<"Conservative recovery energy mismatch="<<recoveryError<<exit(FatalError);
            rhoEnergy[i]=state[i].energy; // Retain transported energy, never synchronize it.
            primitive[i]=physicalState(point,state[i].rho,U[i].x(),thermo.p()[i],thermo.T()[i],primitive[i].species);
        }
        if(maxDensityError>1e-8)FatalErrorInFunction<<"Actual EOS density closure failed"<<exit(FatalError);
        const scalar boundaryMass=dt*(l0.boundaryMass+l1.boundaryMass+4*l2.boundaryMass)/6;
        const scalar boundaryEnergy=dt*(l0.boundaryEnergy+l1.boundaryEnergy+4*l2.boundaryEnergy)/6;
        const scalar interfaceDefect=dt*(l0.internalEnergyDefect+l1.internalEnergyDefect+4*l2.internalEnergyDefect)/6;
        cumulativeMassBoundary+=boundaryMass;cumulativeEnergyBoundary+=boundaryEnergy;cumulativeDefect+=interfaceDefect+sync;++steps;
        runTime.write();
        if(steps==1||steps%100==0||runTime.writeTime())
            Info<<"CONTACT_APEC t="<<runTime.value()<<" dt="<<dt<<" pMin="<<min(thermo.p()).value()<<" pMax="<<max(thermo.p()).value()
                <<" uMin="<<min(U.component(0)).value()<<" uMax="<<max(U.component(0)).value()
                <<" rhoEOSrelative="<<maxDensityError<<" massResidualStepKg="<<integral(state,0)-integral(old,0)-boundaryMass
                <<" energySyncJ="<<sync<<" energyInterfaceDefectJ="<<interfaceDefect
                <<" energyBalanceResidualStepJ="<<integral(state,2)-integral(old,2)-boundaryEnergy-interfaceDefect-sync
                <<" cumulativeMassResidualKg="<<integral(state,0)-initialMass-cumulativeMassBoundary
                <<" cumulativeEnergyDefectJ="<<cumulativeDefect
                <<" cumulativeEnergyBalanceResidualJ="<<integral(state,2)-initialEnergy-cumulativeEnergyBoundary-cumulativeDefect
                <<" elapsedWall_s="<<runTime.elapsedClockTime()<<endl;
    }
    Info<<"CONTACT_APEC_END t="<<runTime.value()<<" steps="<<steps<<" scientificAcceptance=0"<<nl<<"End"<<endl;
    return 0;
}

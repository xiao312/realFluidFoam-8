#include "fvCFD.H"
#include "psiReactionThermo.H"
#include "uniformDimensionedFields.H"
#include "contactFlux.H"
#include "../../../../applications/solvers/reactingFoamSolveZ/fgmThermoClosure.H"

using namespace Foam;
using namespace ContactDF;

int main(int argc,char* argv[])
{
    #include "setRootCase.H"
    #include "createTime.H"
    #include "createMesh.H"
    if(Pstream::parRun()||runTime.value()!=0)
        FatalErrorInFunction<<"Fresh serial time-zero contact required"<<exit(FatalError);
    if(!runTime.controlDict().lookupOrDefault<Switch>("contactDFInviscid",false))
        FatalErrorInFunction<<"Select contactDFInviscid yes explicitly; Fourier diffusion is not advanced"<<exit(FatalError);
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
    volScalarField rhoEnergy(IOobject("rhoEnergyDF",runTime.timeName(),mesh,IOobject::NO_READ,IOobject::AUTO_WRITE),rho*(thermo.he()-thermo.p()/rho+.5*magSqr(U)));
    surfaceScalarField phi(IOobject("phi",runTime.timeName(),mesh,IOobject::NO_READ,IOobject::AUTO_WRITE),fvc::flux(rho*U));
    Info.precision(16);
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
    auto integral=[&](const std::vector<Conserved>& values,int quantity)
    {
        scalar result=0;for(unsigned i=0;i<n;++i)result+=mesh.V()[i]*(quantity==0?values[i].rho:quantity==1?values[i].momentum:values[i].energy);return result;
    };
    // Convert the frozen numerical energy to p, then query the true SRK model
    // at that p/rho/Y. Energy is not synchronized during SSP-RK stages.
    auto project=[&](const std::vector<Conserved>& values,const std::vector<Primitive>& frozen)
    {
        std::vector<Primitive> result(n);
        scalarField& p=thermo.p().primitiveFieldRef();scalarField& T=thermo.T().primitiveFieldRef();
        scalarField& h=thermo.he().primitiveFieldRef();
        scalarField& y0=composition.Y()[0].primitiveFieldRef();scalarField& y1=composition.Y()[1].primitiveFieldRef();
        for(unsigned i=0;i<n;++i)
        {
            const Conserved& c=values[i];
            if(!(c.rho>0))FatalErrorInFunction<<"Nonpositive transported density"<<exit(FatalError);
            const scalar velocity=c.momentum/c.rho;
            p[i]=(frozen[i].gamma-1)*(c.energy-c.rho*(frozen[i].e0+.5*sqr(velocity)));
            std::array<scalar,2> y{{c.species[0]/c.rho,c.species[1]/c.rho}};
            if(mag(y[0]+y[1]-1)>1e-10||min(y[0],y[1]) < -1e-14)
                FatalErrorInFunction<<"Species transport lost mass/positivity"<<exit(FatalError);
            y0[i]=y[0];y1[i]=y[1];
            const ContactDF::Thermo& point=mixture->cellMixture(i);
            T[i]=temperatureAtDensity(point,c.rho,p[i],T[i]);
            result[i]=physicalState(point,c.rho,velocity,p[i],T[i],y);
            rho[i]=c.rho;U[i]=vector(velocity,0,0);h[i]=point.Hs(p[i],T[i]);
            Ha[i]=result[i].absoluteH;rhoEnergy[i]=c.energy;
        }
        return result;
    };
    auto stage=[&](const std::vector<Conserved>& base,const Evaluation& evaluation,scalar dt)
    {
        std::vector<Conserved> result(n);for(unsigned i=0;i<n;++i)result[i]=combine(base[i],evaluation.cells[i],1,dt);return result;
    };
    auto updatePhi=[&](const Evaluation& evaluation)
    {
        const scalar edge=mesh.C()[0].x()-.5*dx;
        auto value=[&](scalar x,scalar sx){if(mag(sx)<1e-12*area)return scalar(0);const long face=std::lround((x-edge)/dx);if(face<0||face>long(n))FatalErrorInFunction<<"Face outside uniform1D recipe"<<exit(FatalError);return evaluation.faces[face].mass*sx;};
        forAll(phi,face)phi[face]=value(mesh.Cf()[face].x(),mesh.Sf()[face].x());
        forAll(phi.boundaryField(),patch)
            forAll(phi.boundaryField()[patch],face)phi.boundaryFieldRef()[patch][face]=value(mesh.Cf().boundaryField()[patch][face].x(),mesh.Sf().boundaryField()[patch][face].x());
    };
    scalar cumulativeDefect=0,cumulativeMassBoundary=0,cumulativeEnergyBoundary=0;
    const scalar initialMass=integral(state,0),initialEnergy=integral(state,2);
    label steps=0;
    Info<<"CONTACT_DF_INIT cells="<<n<<" dx="<<dx<<" area="<<area
        <<" massKg="<<initialMass<<" absoluteEnergyJ="<<initialEnergy
        <<" acousticCo="<<cfl<<" reconstruction=firstOrder time=SSPRK3 energy=absoluteHa quasiConservative=1"<<endl;
    while(runTime.run())
    {
        std::vector<Primitive> frozen=primitive;
        scalar dt=maxDt;for(const Primitive& v:primitive)dt=min(dt,cfl*dx/(mag(v.u)+v.sound));
        dt=min(dt,runTime.endTime().value()-runTime.value());
        runTime.setDeltaT(dt);dt=runTime.deltaTValue();runTime++;
        const std::vector<Conserved> old=state;
        const Evaluation l0=evaluate(primitive,frozen,leftFar,rightFar,dx,area);
        const std::vector<Conserved> w1=stage(old,l0,dt);
        const std::vector<Primitive> v1=project(w1,frozen);
        const Evaluation l1=evaluate(v1,frozen,leftFar,rightFar,dx,area);
        const std::vector<Conserved> e1=stage(w1,l1,dt);
        std::vector<Conserved> w2(n);for(unsigned i=0;i<n;++i)w2[i]=combine(old[i],e1[i],.75,.25);
        const std::vector<Primitive> v2=project(w2,frozen);
        const Evaluation l2=evaluate(v2,frozen,leftFar,rightFar,dx,area);
        const std::vector<Conserved> e2=stage(w2,l2,dt);
        for(unsigned i=0;i<n;++i)state[i]=combine(old[i],e2[i],1.0/3,2.0/3);
        primitive=project(state,frozen);
        updatePhi(evaluate(primitive,frozen,leftFar,rightFar,dx,area));
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
            sync+=(actual-state[i].energy)*mesh.V()[i];state[i].energy=actual;rhoEnergy[i]=actual;
            primitive[i]=physicalState(point,state[i].rho,U[i].x(),thermo.p()[i],thermo.T()[i],primitive[i].species);
        }
        if(maxDensityError>1e-8)FatalErrorInFunction<<"Actual EOS density closure failed"<<exit(FatalError);
        const scalar boundaryMass=dt*(l0.boundaryMass+l1.boundaryMass+4*l2.boundaryMass)/6;
        const scalar boundaryEnergy=dt*(l0.boundaryEnergy+l1.boundaryEnergy+4*l2.boundaryEnergy)/6;
        const scalar interfaceDefect=dt*(l0.internalEnergyDefect+l1.internalEnergyDefect+4*l2.internalEnergyDefect)/6;
        cumulativeMassBoundary+=boundaryMass;cumulativeEnergyBoundary+=boundaryEnergy;cumulativeDefect+=interfaceDefect+sync;++steps;
        runTime.write();
        if(steps==1||steps%100==0||runTime.writeTime())
            Info<<"CONTACT_DF t="<<runTime.value()<<" dt="<<dt<<" pMin="<<min(thermo.p()).value()<<" pMax="<<max(thermo.p()).value()
                <<" uMin="<<min(U.component(0)).value()<<" uMax="<<max(U.component(0)).value()
                <<" rhoEOSrelative="<<maxDensityError<<" massResidualStepKg="<<integral(state,0)-integral(old,0)-boundaryMass
                <<" energySyncJ="<<sync<<" energyInterfaceDefectJ="<<interfaceDefect
                <<" energyBalanceResidualStepJ="<<integral(state,2)-integral(old,2)-boundaryEnergy-interfaceDefect-sync
                <<" cumulativeMassResidualKg="<<integral(state,0)-initialMass-cumulativeMassBoundary
                <<" cumulativeEnergyDefectJ="<<cumulativeDefect
                <<" cumulativeEnergyBalanceResidualJ="<<integral(state,2)-initialEnergy-cumulativeEnergyBoundary-cumulativeDefect
                <<" elapsedWall_s="<<runTime.elapsedClockTime()<<endl;
    }
    Info<<"CONTACT_DF_END t="<<runTime.value()<<" steps="<<steps<<" scientificAcceptance=0"<<nl<<"End"<<endl;
    return 0;
}

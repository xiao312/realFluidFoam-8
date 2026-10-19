#ifndef CanteraTransport_H
#define CanteraTransport_H
#include "fvCFD.H"
#include "bridge.h"
#include <dlfcn.h>
#include <algorithm>
#include <cmath>
#include <vector>

// One rank-local context. CP chemistry is explicit opt-in, ideal gas only.
class CanteraTransport {
    void* library_;
    rf_ct_context* context_;
    decltype(&rf_ct_destroy) destroy_;
    decltype(&rf_ct_evaluate) evaluate_;
    decltype(&rf_ct_error) error_;
    decltype(&rf_ct_advance_cp) advance_=nullptr;
    bool integrate_=false;
    double relativeTolerance_=0,absoluteTolerance_=0;
    Foam::PtrList<Foam::volScalarField> sources_;
    Foam::scalarField formationHeats_;
    std::vector<double> y_, diffusion_;
    rf_ct_properties properties_;
    template<class T>T symbol(const char* name) {
        void* address=dlsym(library_,name);
        if(!address)FatalErrorInFunction << dlerror() << Foam::exit(Foam::FatalError);
        return reinterpret_cast<T>(address);
    }
    void evaluate(Foam::scalar temperature,Foam::scalar pressure) {
        if(evaluate_(context_,temperature,pressure,y_.data(),y_.size(),
                     &properties_,nullptr,diffusion_.data(),nullptr))
            FatalErrorInFunction << error_(context_) << Foam::exit(Foam::FatalError);
    }
public:
    CanteraTransport(const Foam::fvMesh& mesh,const Foam::speciesTable& names)
    :library_(nullptr),context_(nullptr),destroy_(nullptr),evaluate_(nullptr),error_(nullptr),
     y_(names.size()),diffusion_(names.size()) {
        Foam::IOdictionary config(Foam::IOobject("canteraBridge",mesh.time().constant(),mesh,
            Foam::IOobject::MUST_READ,Foam::IOobject::NO_WRITE));
        const Foam::fileName path(config.lookup("libraryPath"));
        const Foam::fileName inputs(config.lookup("inputDirectory"));
        const Foam::label stage=Foam::readLabel(config.lookup("stage"));
        const Foam::word options(config.lookup("options"));
        if(stage!=1 || options!="full")
            FatalErrorInFunction << "Only stage 1/full transport is qualified for this draft"
                << Foam::exit(Foam::FatalError);
        library_=dlopen(path.c_str(),RTLD_NOW|RTLD_LOCAL);
        if(!library_)FatalErrorInFunction << dlerror() << Foam::exit(Foam::FatalError);
        auto create=symbol<decltype(&rf_ct_create)>("rf_ct_create");
        destroy_=symbol<decltype(&rf_ct_destroy)>("rf_ct_destroy");
        evaluate_=symbol<decltype(&rf_ct_evaluate)>("rf_ct_evaluate");
        error_=symbol<decltype(&rf_ct_error)>("rf_ct_error");
        auto count=symbol<decltype(&rf_ct_species_count)>("rf_ct_species_count");
        auto name=symbol<decltype(&rf_ct_species_name)>("rf_ct_species_name");
        char message[4096];context_=create(inputs.c_str(),stage,options.c_str(),message,sizeof(message));
        if(!context_)FatalErrorInFunction << message << Foam::exit(Foam::FatalError);
        if(count(context_)!=static_cast<size_t>(names.size()))
            FatalErrorInFunction << "Species count mismatch" << Foam::exit(Foam::FatalError);
        forAll(names,k) {
            if(name(context_,k,message,sizeof(message)) || names[k]!=message)
                FatalErrorInFunction << "Species ordering mismatch at " << k
                    << Foam::exit(Foam::FatalError);
        }
        const Foam::word chemistryMode=config.lookupOrDefault<Foam::word>("chemistryMode","native");
        if(chemistryMode!="native" && chemistryMode!="adiabaticCP")
            FatalErrorInFunction << "Unknown chemistryMode" << Foam::exit(Foam::FatalError);
        integrate_=chemistryMode=="adiabaticCP";
        if(integrate_) {
            relativeTolerance_=Foam::readScalar(config.lookup("chemistryRtol"));
            absoluteTolerance_=Foam::readScalar(config.lookup("chemistryAtol"));
            if(!(relativeTolerance_>0 && relativeTolerance_<=1e-3 && absoluteTolerance_>0 && absoluteTolerance_<=1e-6))
                FatalErrorInFunction << "Invalid chemistry tolerances" << Foam::exit(Foam::FatalError);
            advance_=symbol<decltype(&rf_ct_advance_cp)>("rf_ct_advance_cp");
            sources_.setSize(names.size());
            forAll(names,k) sources_.set(k,new Foam::volScalarField
            (
                Foam::IOobject("canteraRR_"+names[k],mesh.time().timeName(),mesh,
                    Foam::IOobject::NO_READ,Foam::IOobject::NO_WRITE),mesh,
                Foam::dimensionedScalar("zero",Foam::dimMass/Foam::dimVolume/Foam::dimTime,0)
            ));
        }
        Foam::Info << "Cantera conductivity and diffusion enabled: " << path << Foam::endl;
        Foam::Info << "Chemistry mode: " << chemistryMode << Foam::endl;
    }
    ~CanteraTransport(){if(context_)destroy_(context_);if(library_)dlclose(library_);}
    CanteraTransport(const CanteraTransport&)=delete;
    void operator=(const CanteraTransport&)=delete;
    bool integratesChemistry() const {return integrate_;}
    const Foam::volScalarField& source(Foam::label k) const {return sources_[k];}
    void setFormationHeats(const Foam::scalarField& heats,const Foam::scalarField& nativeWeights) {
        if(!integrate_)return;
        formationHeats_=heats;
        // Partial ideal-gas enthalpies are composition independent. Keep a
        // mixed state because this evaluation also validates mixture diffusion.
        std::fill(y_.begin(),y_.end(),1./y_.size());
        std::vector<double> enthalpies(y_.size());
        if(evaluate_(context_,298.15,101325,y_.data(),y_.size(),&properties_,
                     enthalpies.data(),diffusion_.data(),nullptr))
            FatalErrorInFunction << error_(context_) << Foam::exit(Foam::FatalError);
        auto weight=symbol<decltype(&rf_ct_species_weight)>("rf_ct_species_weight");
        double maximumWeightDifference=0;
        forAll(heats,k) {
            double canteraWeight=0;
            if(weight(context_,k,&canteraWeight))
                FatalErrorInFunction << error_(context_) << Foam::exit(Foam::FatalError);
            maximumWeightDifference=std::max(maximumWeightDifference,std::abs(canteraWeight/nativeWeights[k]-1));
            const double nativeMolar=heats[k]*nativeWeights[k];
            const double canteraMolar=enthalpies[k]*canteraWeight;
            if(std::abs(nativeMolar-canteraMolar)>std::max(1e-3,1e-8*std::abs(nativeMolar)))
                FatalErrorInFunction << "Molar formation enthalpy mismatch at species " << k
                    << ": native=" << nativeMolar << " bridge=" << canteraMolar
                    << Foam::exit(Foam::FatalError);
        }
        // The independently audited legacy molecular weights differ by <=5.007e-5.
        // This bounded, recorded mass-basis difference is not silently normalized.
        if(maximumWeightDifference>6e-5)
            FatalErrorInFunction << "Molecular weights exceed audited difference" << Foam::exit(Foam::FatalError);
        Foam::Info << "Cantera/native molar formation enthalpies verified; maximum MW relative difference="
            << maximumWeightDifference << Foam::endl;
    }
    void correctChemistry(const Foam::volScalarField& temperature,const Foam::volScalarField& pressure,
                          const Foam::volScalarField& density,const Foam::PtrList<Foam::volScalarField>& species,
                          Foam::scalar duration,Foam::volScalarField& heatRelease) {
        if(!integrate_ || formationHeats_.size()!=species.size())
            FatalErrorInFunction << "CP chemistry context not initialized" << Foam::exit(Foam::FatalError);
        heatRelease*=0.;
        std::vector<double> finalY(y_.size());double finalTemperature=0;
        forAll(temperature,cell) {
            forAll(species,k)y_[k]=species[k][cell];
            if(advance_(context_,temperature[cell],pressure[cell],y_.data(),y_.size(),duration,
                        relativeTolerance_,absoluteTolerance_,&finalTemperature,finalY.data()))
                FatalErrorInFunction << "Cell " << cell << ": " << error_(context_)
                    << Foam::exit(Foam::FatalError);
            forAll(species,k) {
                sources_[k][cell]=density[cell]*(finalY[k]-y_[k])/duration;
                heatRelease[cell]-=formationHeats_[k]*sources_[k][cell];
            }
        }
    }
    void update(const Foam::volScalarField& temperature,const Foam::volScalarField& pressure,
                const Foam::PtrList<Foam::volScalarField>& species,
                Foam::volScalarField& conductivity,Foam::PtrList<Foam::volScalarField>& diffusion) {
        forAll(temperature,cell) {
            forAll(species,k)y_[k]=species[k][cell];
            evaluate(temperature[cell],pressure[cell]);
            conductivity[cell]=properties_.conductivity;
            forAll(diffusion,k)diffusion[k][cell]=diffusion_[k];
        }
        forAll(temperature.boundaryField(),patch) {
            forAll(temperature.boundaryField()[patch],face) {
                forAll(species,k)y_[k]=species[k].boundaryField()[patch][face];
                evaluate(temperature.boundaryField()[patch][face],pressure.boundaryField()[patch][face]);
                conductivity.boundaryFieldRef()[patch][face]=properties_.conductivity;
                forAll(diffusion,k)diffusion[k].boundaryFieldRef()[patch][face]=diffusion_[k];
            }
        }
    }
};
#endif

#ifndef CanteraTransport_H
#define CanteraTransport_H
#include "fvCFD.H"
#include "bridge.h"
#include <dlfcn.h>
#include <vector>

// One rank-local context. Only conductivity and Dimix are replaced.
class CanteraTransport {
    void* library_;
    rf_ct_context* context_;
    decltype(&rf_ct_destroy) destroy_;
    decltype(&rf_ct_evaluate) evaluate_;
    decltype(&rf_ct_error) error_;
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
        Foam::Info << "Cantera conductivity and diffusion enabled: " << path << Foam::endl;
    }
    ~CanteraTransport(){if(context_)destroy_(context_);if(library_)dlclose(library_);}
    CanteraTransport(const CanteraTransport&)=delete;
    void operator=(const CanteraTransport&)=delete;
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

"""Create a timing-only solver copy; never modify the qualified source build."""
import json
from pathlib import Path
import shutil
import sys

action, build_arg, output_arg = sys.argv[1:]
assert action in ('plan', 'apply')
build, output = Path(build_arg).resolve(), Path(output_arg).resolve()
source = build / 'applications/solvers/realFluidReactingFoam'
assert source.is_dir() and not output.exists()
assert str(output).startswith('/work/jobs/')
print(json.dumps(dict(source=str(source), output=str(output), physics_changes=False)))
if action == 'plan':
    sys.exit(0)
output.mkdir(parents=True)
for path in source.glob('*'):
    if path.is_file():
        shutil.copy2(path, output/path.name)
(output/'Make').mkdir()
for name in ('files', 'options'):
    shutil.copy2(source/'Make'/name, output/'Make'/name)
p=output/'Make/files'
p.write_text(p.read_text().replace('/realFluidReactingFoam','/rfProfileReactingFoam'))

header = r'''
#include <chrono>
#include <map>
#include <string>
#include <fstream>
#include <iomanip>
namespace rfProfile {
using Clock = std::chrono::steady_clock;
std::map<std::string, Clock::time_point> starts;
std::map<std::string, double> totals;
void begin(const std::string& name) { starts[name]=Clock::now(); }
void end(const std::string& name) {
    totals[name]+=std::chrono::duration<double>(Clock::now()-starts.at(name)).count();
}
void dump(const Foam::Time& time) {
    std::ofstream out((time.path()/"rf-profile.csv").c_str(),std::ios::app);
    for (const auto& entry: totals)
        out << std::setprecision(14) << time.value() << ',' << entry.first << ',' << entry.second << '\n';
    totals.clear();
}
}
'''
def patch(name, old, new):
    p=output/name;s=p.read_text();assert s.count(old)==1,(name,old,s.count(old))
    p.write_text(s.replace(old,new))
def timed(name, statement, label):
    patch(name,statement,f'rfProfile::begin("{label}");\n{statement}\nrfProfile::end("{label}");')
main='realFluidReactingFoam.C'
patch(main,'int main(int argc, char *argv[])',header+'\nint main(int argc, char *argv[])')
patch(main,'        runTime++;','        rfProfile::begin("step");\n        runTime++;')
for include,label in [('rhoEqn.H','continuity'),('UEqn.H','momentum'),('YEqn.H','species_total'),('EEqn.H','energy_total'),('pEqn.H','pressure')]:
    timed(main,f'#include "{include}"',label)
timed(main,'turbulence->correct();','turbulence')
timed(main,'thermophysicalTransport->correct();','transport_correct')
for expression in ['rho = thermo.rho();','mu = thermo.mu();','Cp = thermo.Cp();','Cv = thermo.Cv();','kappa = thermo.kappa();','Wmix = thermo.W();','HE = thermo.he();']:
    timed(main,expression,'property_'+expression.split()[0])
timed(main,'Dimix[i] = thermo.Dimix(i);','property_Dimix')
timed(main,'hei[i] = thermo.hei(i);','property_hei')
timed(main,'runTime.write();','write')
patch(main,'        Info<< "ExecutionTime = "','        rfProfile::end("step");\n        rfProfile::dump(runTime);\n        Info<< "ExecutionTime = "')
timed('YEqn.H','reaction->correct();','chemistry')
patch('YEqn.H','        // calculate correction term','        rfProfile::begin("diffusion_pair_corrections");\n        // calculate correction term')
# There are two active-species branches; instrument only the first one.
p=output/'YEqn.H';s=p.read_text();s=s.replace('        if (i != inertIndex && composition.active(i))','        rfProfile::end("diffusion_pair_corrections");\n        if (i != inertIndex && composition.active(i))',1);p.write_text(s)
timed('YEqn.H','YiEqn.solve("Yi");','species_linear_solve')
timed('EEqn.H','EEqn.solve();','energy_linear_solve')
timed('EEqn.H','thermo.correct();','thermo_correct')
print('Timing-only source generated.')

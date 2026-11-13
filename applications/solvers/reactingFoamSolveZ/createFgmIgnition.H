// Optional cold-flow/ignition protocol. Disabled unless explicitly configured.
const scalar fgmIgnitionTime = runTime.controlDict().lookupOrDefault<scalar>("fgmIgnitionTime", -1);
bool fgmColdFlowActive = fgmIgnitionTime >= 0;
const scalar fgmIgnitionLength = runTime.controlDict().lookupOrDefault<scalar>("fgmIgnitionAxialLength", .004);
const scalar fgmIgnitionZMin = runTime.controlDict().lookupOrDefault<scalar>("fgmIgnitionZMin", .08);
const scalar fgmIgnitionZMax = runTime.controlDict().lookupOrDefault<scalar>("fgmIgnitionZMax", .18);
const word fgmIgnitionMode(runTime.controlDict().lookupOrDefault<word>("fgmIgnitionMode", "sourcePeak"));
if (fgmIgnitionMode != "sourcePeak" && fgmIgnitionMode != "upperProgress")
    FatalErrorInFunction << "Unknown fgmIgnitionMode " << fgmIgnitionMode << exit(FatalError);
autoPtr<fgm::fgmTableReader> fgmIgnitionTable;
scalar fgmColdLastTime = runTime.value();
scalarField fgmColdPreviousZ;
vectorField fgmColdPreviousU;
if (fgmColdFlowActive)
{
    if (!splitFgmSource || !absoluteEnthalpyFGM || runTime.value() != 0
        || fgmIgnitionLength <= 0 || fgmIgnitionZMin < 0
        || fgmIgnitionZMax > 1 || fgmIgnitionZMin >= fgmIgnitionZMax)
        FatalErrorInFunction << "Scheduled ignition requires fresh timezero split FGM/Ha and a valid ignition region" << exit(FatalError);
    fileName tablePath(runTime.controlDict().lookup("fgmIgnitionTable"));
    if (!tablePath.isAbsolute()) tablePath = runTime.path()/tablePath;
    fgmIgnitionTable.reset(new fgm::fgmTableReader(tablePath, fgm::fgmTableReader::CLAMP_TO_BOUNDS));
    fgmColdPreviousZ = fgmSourceModel->Z().primitiveField();
    fgmColdPreviousU = U.primitiveField();
    Info<< "fgmColdFlow start=0 scheduledIgnition=" << fgmIgnitionTime
        << " sourceEnabled=0 sameProcess=1" << endl;
}

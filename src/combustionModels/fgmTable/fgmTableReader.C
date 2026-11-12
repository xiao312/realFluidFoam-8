/*---------------------------------------------------------------------------*\
  =========                 |
  \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox
   \\    /   O peration     | Website:  https://openfoam.org
    \\  /    A nd           | Version:  8
     \\/     M anipulation  |
-------------------------------------------------------------------------------
License
    This file is part of OpenFOAM.

    OpenFOAM is free software: you can redistribute it and/or modify it
    under the terms of the GNU General Public License as published by the
    Free Software Foundation, either version 3 of the License, or (at your
    option) any later version.

    OpenFOAM is distributed in the hope that it will be useful, but WITHOUT
    ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
    FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
    for more details.

    You should have received a copy of the GNU General Public License
    along with OpenFOAM.  If not, see <http://www.gnu.org/licenses/>.

\*---------------------------------------------------------------------------*/

#include "fgmTableReader.H"
#include "fgmTableSourceI.H"

#include "error.H"

#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <cmath>

// * * * * * * * * * * * * * * Local helpers  * * * * * * * * * * * * * * * * //

namespace
{

//- Split a line on whitespace
std::vector<std::string> tokenise(const std::string& line)
{
    std::vector<std::string> out;
    std::istringstream iss(line);
    std::string token;
    while (iss >> token)
    {
        out.push_back(token);
    }
    return out;
}

//- Parse a token as a scalar; returns false on trailing garbage
bool parseScalar(const std::string& token, Foam::scalar& value)
{
    std::istringstream iss(token);
    iss >> value;
    return !iss.fail() && iss.eof();
}

//- Parse a token as a non-negative label; returns false on trailing garbage
//- Format a scalar at full precision without going through an OpenFOAM
//  stream (whose default is six digits, too coarse for a 1e-12 cross-check)
std::string numStr(const Foam::scalar value)
{
    std::ostringstream os;
    os.precision(17);
    os << value;
    return os.str();
}


//- Join a word list on one line; the OpenFOAM list writer breaks lines
std::string joinWords(const Foam::wordList& words)
{
    std::ostringstream os;
    for (Foam::label i = 0; i < words.size(); ++i)
    {
        if (i)
        {
            os << " ";
        }
        os << words[i];
    }
    return os.str();
}


bool parseLabel(const std::string& token, Foam::label& value)
{
    Foam::scalar s = 0;
    if (!parseScalar(token, s) || s < 0 || s != Foam::scalar(Foam::label(s)))
    {
        return false;
    }
    value = Foam::label(s);
    return true;
}

//- True when the string is one of the whitespace-insensitive block names
bool isBlockName(const std::string& s)
{
    return s == "Sc" || s == "Q" || s == "Tdiag" || s.compare(0, 2, "Y ") == 0;
}

} // End anonymous namespace


// * * * * * * * * * * * * * * * * Constructors  * * * * * * * * * * * * * * //

Foam::fgm::fgmTableReader::fgmTableReader
(
    const Foam::fileName& path,
    const Foam::fgm::fgmTableReader::boundsPolicy policy
)
:
    path_(path),
    source_("unset"),
    profileSha256_("none"),
    schema_("unset"),
    nZ_(0),
    nC_(0),
    worstSpeciesSum_(0),
    policy_(policy),
    progressCoordinate_("unset"),
    progressDYc_(1),
    lookupCount_(0),
    clipCount_(0),
    maxProgressExcursion_(0),
    maxZExcursion_(0)
{
    std::ifstream is(path_.c_str());

    if (!is.good())
    {
        refuse("cannot be opened for reading");
    }

    bool haveSchema = false;
    bool haveUnitsSc = false;
    bool haveUnitsQ = false;
    bool haveOwnerRho = false;
    bool haveOwnerT = false;
    bool haveOwnerH = false;
    bool haveSpecies = false;
    bool haveZ = false;
    bool haveC = false;
    bool haveProgressCoordinate = false;
    bool haveProgressDYc = false;

    static const std::string thermoOwner = "thermophysicalModel";

    std::vector<std::string> blockNames;
    std::vector< std::vector< std::vector<Foam::scalar> > > blockRows;
    bool inBlock = false;
    std::string current;

    std::string line;
    Foam::label lineNo = 0;

    while (std::getline(is, line))
    {
        ++lineNo;

        // Strip comments and leading/trailing space
        const std::string::size_type hash = line.find('#');
        if (hash != std::string::npos)
        {
            line.erase(hash);
        }

        const std::vector<std::string> tok = tokenise(line);
        if (tok.empty())
        {
            continue;
        }

        const std::string key = tok[0];

        if (key == "block")
        {
            if (inBlock)
            {
                refuse
                (
                    "line " + std::to_string(lineNo)
                  + ": nested block"
                );
            }

            if (tok.size() < 2)
            {
                refuse("line " + std::to_string(lineNo) + ": block needs a name");
            }

            current.clear();
            for (Foam::label t = 1; t < Foam::label(tok.size()); ++t)
            {
                if (!current.empty())
                {
                    current += " ";
                }
                current += tok[t];
            }

            if (!isBlockName(current))
            {
                refuse
                (
                    "unknown block '" + current
                  + "'; expected one of Q, Sc, Tdiag, Y <species>"
                );
            }

            for (Foam::label b = 0; b < Foam::label(blockNames.size()); ++b)
            {
                if (blockNames[b] == current)
                {
                    refuse("duplicate block '" + current + "'");
                }
            }

            blockNames.push_back(current);
            blockRows.push_back(std::vector< std::vector<Foam::scalar> >());
            inBlock = true;
            continue;
        }

        if (key == "end")
        {
            if (!inBlock)
            {
                refuse("line " + std::to_string(lineNo) + ": 'end' without a block");
            }
            inBlock = false;
            current.clear();
            continue;
        }

        if (inBlock)
        {
            std::vector<Foam::scalar> row;
            for (Foam::label t = 0; t < Foam::label(tok.size()); ++t)
            {
                Foam::scalar value = 0;
                if (!parseScalar(tok[t], value))
                {
                    refuse
                    (
                        "block '" + current + "' line "
                      + std::to_string(lineNo) + ": '" + tok[t]
                      + "' is not a number"
                    );
                }
                row.push_back(value);
            }
            blockRows.back().push_back(row);
            continue;
        }

        if (key == "schema")
        {
            if (tok.size() != 2 ||
                (tok[1] != "forge-fgm-table-v1" && tok[1] != "forge-fgm-table-v2"
                 && tok[1] != "forge-fgm-table-v3"))
            {
                refuse
                (
                    "schema '" + (tok.size() > 1 ? tok[1] : std::string(""))
                  + "' is not forge-fgm-table-v1, forge-fgm-table-v2 or forge-fgm-table-v3"
                );
            }
            haveSchema = true;
            schema_ = tok[1];
            continue;
        }

        if (key == "species" || key == "progress-species")
        {
            wordList& list = key == "species" ? species_ : progressSpecies_;
            list.setSize(Foam::label(tok.size()) - 1);
            for (Foam::label t = 1; t < Foam::label(tok.size()); ++t)
            {
                list[t - 1] = tok[t];
            }
            if (key == "species") haveSpecies = true;
            continue;
        }

        if (key == "nZ" || key == "nC")
        {
            Foam::label value = 0;
            if (tok.size() != 2 || !parseLabel(tok[1], value))
            {
                refuse(key + " must be an integer");
            }
            if (key == "nZ")
            {
                nZ_ = value;
            }
            else
            {
                nC_ = value;
            }
            continue;
        }

        if (key == "z" || key == "c" || key == "c-min" || key == "c-max" || key == "progress-weights")
        {
            Foam::scalarField grid(Foam::label(tok.size()) - 1);
            for (Foam::label t = 1; t < Foam::label(tok.size()); ++t)
            {
                if (!parseScalar(tok[t], grid[t - 1]) || !std::isfinite(grid[t - 1]))
                {
                    refuse(key + " grid contains '" + tok[t] + "', which is not a number");
                }
            }
            if (key == "z")
            {
                z_ = grid;
                haveZ = true;
            }
            else if (key == "c")
            {
                c_ = grid;
                haveC = true;
            }
            else if (key == "c-min") progressMin_ = grid;
            else if (key == "c-max") progressMax_ = grid;
            else progressWeights_ = grid;
            continue;
        }

        if (key == "source")
        {
            source_.clear();
            for (Foam::label t = 1; t < Foam::label(tok.size()); ++t)
            {
                if (!source_.empty())
                {
                    source_ += " ";
                }
                source_ += tok[t];
            }
            continue;
        }

        if (key == "profile-sha256")
        {
            profileSha256_ = (tok.size() > 1 ? tok[1] : "none");
            continue;
        }

        if (key == "progress-coordinate")
        {
            const std::string value = (tok.size() > 1 ? tok[1] : "");
            if (value != "mass-fraction" && value != "normalised" && value != "mass-fraction-mapped"
                && value != "weighted-mass-fraction-mapped")
            {
                refuse
                (
                    "progress-coordinate is '" + value + "'; this format "
                    "admits mass-fraction, normalised, v2 mass-fraction-mapped or v3 weighted-mass-fraction-mapped; "
                    "source block Sc is the source of Yc and only an explicit "
                    "declaration says whether the transported coordinate is "
                    "Yc or a normalized function of it"
                );
            }
            progressCoordinate_ = value;
            haveProgressCoordinate = true;
            continue;
        }

        if (key == "progress-dYc")
        {
            Foam::scalar value = 0;
            if (tok.size() != 2 || !parseScalar(tok[1], value))
            {
                refuse
                (
                    "progress-dYc is '"
                  + (tok.size() > 1 ? tok[1] : std::string())
                  + "', not a number"
                );
            }
            if (!(value > 0))
            {
                refuse
                (
                    "progress-dYc is " + std::to_string(value)
                  + "; a normalization width must be positive"
                );
            }
            progressDYc_ = value;
            haveProgressDYc = true;
            continue;
        }

        if (key == "units-progress-source")
        {
            const std::string value = (tok.size() > 1 ? tok[1] : "");
            if (value != "kg/m3/s")
            {
                refuse
                (
                    "units-progress-source must be kg/m3/s, got '" + value + "'"
                );
            }
            haveUnitsSc = true;
            continue;
        }

        if (key == "units-heat-release")
        {
            const std::string value = (tok.size() > 1 ? tok[1] : "");
            if (value != "W/m3")
            {
                refuse("units-heat-release must be W/m3, got '" + value + "'");
            }
            haveUnitsQ = true;
            continue;
        }

        if
        (
            key == "density-owner"
         || key == "temperature-owner"
         || key == "enthalpy-owner"
        )
        {
            const std::string value = (tok.size() > 1 ? tok[1] : "");
            if (value != thermoOwner)
            {
                refuse
                (
                    key + " is '" + value + "'; this format only admits '"
                  + thermoOwner + "', because the thermophysical model owns "
                    "that quantity"
                );
            }
            if (key == "density-owner")
            {
                haveOwnerRho = true;
            }
            else if (key == "temperature-owner")
            {
                haveOwnerT = true;
            }
            else
            {
                haveOwnerH = true;
            }
            continue;
        }

        refuse("line " + std::to_string(lineNo) + ": unknown header key '" + key + "'");
    }

    if (inBlock)
    {
        refuse("data rows after the last block; missing 'end'");
    }

    // ---- required header ---------------------------------------------------
    if (!haveSchema)
    {
        refuse("missing required header 'schema'");
    }
    if (!haveUnitsSc)
    {
        refuse("missing required header 'units-progress-source'");
    }
    if (!haveUnitsQ)
    {
        refuse("missing required header 'units-heat-release'");
    }
    if (!haveOwnerRho || !haveOwnerT || !haveOwnerH)
    {
        refuse("missing one of the ownership declarations");
    }
    if (!haveProgressCoordinate)
    {
        refuse("missing required header 'progress-coordinate'");
    }
    if (progressCoordinate_ == "normalised" && !haveProgressDYc)
    {
        refuse
        (
            "progress-coordinate is normalised but progress-dYc is missing; "
            "c = (Yc - Yc_min)/dYc and the source of c is Sc/dYc, so dYc is "
            "required rather than assumed to be one"
        );
    }
    if (!normalisedCoordinate() && haveProgressDYc)
    {
        refuse
        (
            "progress-dYc is declared for a mass-fraction coordinate; dYc "
            "would then be an unused number standing where a physical "
            "quantity is expected"
        );
    }
    if (!haveSpecies || species_.empty())
    {
        refuse("no species list");
    }
    if (!haveZ || !haveC)
    {
        refuse("z and c grids are required");
    }
    if (nZ_ < 2 || nC_ < 2)
    {
        refuse
        (
            "need at least a 2x2 grid to interpolate, got "
          + std::to_string(nZ_) + "x" + std::to_string(nC_)
        );
    }
    if (z_.size() != nZ_ || c_.size() != nC_)
    {
        refuse
        (
            "grid sizes disagree with nZ/nC: len(z)=" + std::to_string(z_.size())
          + " nZ=" + std::to_string(nZ_)
          + " len(c)=" + std::to_string(c_.size())
          + " nC=" + std::to_string(nC_)
        );
    }

    for (Foam::label i = 1; i < nZ_; ++i)
    {
        if (z_[i] <= z_[i - 1])
        {
            refuse("z grid is not strictly increasing");
        }
    }
    for (Foam::label j = 1; j < nC_; ++j)
    {
        if (c_[j] <= c_[j - 1])
        {
            refuse("c grid is not strictly increasing");
        }
    }

    // ---- blocks ------------------------------------------------------------
    std::vector<std::string> expected;
    for (Foam::label s = 0; s < species_.size(); ++s)
    {
        expected.push_back(std::string("Y ") + species_[s]);
    }
    expected.push_back("Sc");
    expected.push_back("Q");

    for (Foam::label b = 0; b < Foam::label(blockNames.size()); ++b)
    {
        const std::string& name = blockNames[b];
        const std::vector< std::vector<Foam::scalar> >& rows = blockRows[b];

        if (Foam::label(rows.size()) != nZ_)
        {
            refuse
            (
                "block '" + name + "' has " + std::to_string(rows.size())
              + " rows, expected nZ=" + std::to_string(nZ_)
            );
        }

        for (Foam::label i = 0; i < nZ_; ++i)
        {
            if (Foam::label(rows[i].size()) != nC_)
            {
                refuse
                (
                    "block '" + name + "' row " + std::to_string(i) + " has "
                  + std::to_string(rows[i].size()) + " values, expected nC="
                  + std::to_string(nC_)
                );
            }

            for (Foam::label j = 0; j < nC_; ++j)
            {
                const Foam::scalar v = rows[i][j];
                const Foam::scalar huge = 1e300;
                if (!(v == v) || v > huge || v < -huge)
                {
                    refuse("block '" + name + "' contains a non-finite value");
                }
            }
        }
    }

    for (Foam::label e = 0; e < Foam::label(expected.size()); ++e)
    {
        bool found = false;
        for (Foam::label b = 0; b < Foam::label(blockNames.size()); ++b)
        {
            if (blockNames[b] == expected[e])
            {
                found = true;
                break;
            }
        }
        if (!found)
        {
            refuse("missing blocks: " + expected[e]);
        }
    }

    // ---- collect -----------------------------------------------------------
    const Foam::label nNodes = nZ_*nC_;
    Y_.setSize(species_.size());
    for (Foam::label s = 0; s < species_.size(); ++s)
    {
        Y_[s].setSize(nNodes);
    }
    Sc_.setSize(nNodes);
    Q_.setSize(nNodes);

    for (Foam::label b = 0; b < Foam::label(blockNames.size()); ++b)
    {
        const std::string& name = blockNames[b];
        const std::vector< std::vector<Foam::scalar> >& rows = blockRows[b];

        if (name == "Sc" || name == "Q" || name == "Tdiag")
        {
            Foam::scalarField field(nNodes);
            for (Foam::label i = 0; i < nZ_; ++i)
            {
                for (Foam::label j = 0; j < nC_; ++j)
                {
                    field[i*nC_ + j] = rows[i][j];
                }
            }
            if (name == "Sc")
            {
                Sc_ = field;
            }
            else if (name == "Q")
            {
                Q_ = field;
            }
            else
            {
                Tdiag_ = field;
            }
            continue;
        }

        for (Foam::label s = 0; s < species_.size(); ++s)
        {
            if (name == std::string("Y ") + species_[s])
            {
                for (Foam::label i = 0; i < nZ_; ++i)
                {
                    for (Foam::label j = 0; j < nC_; ++j)
                    {
                        Y_[s][i*nC_ + j] = rows[i][j];
                    }
                }
                break;
            }
        }
    }

    // ---- species consistency ----------------------------------------------
    for (Foam::label i = 0; i < nZ_; ++i)
    {
        for (Foam::label j = 0; j < nC_; ++j)
        {
            Foam::scalar sum = 0;
            for (Foam::label s = 0; s < species_.size(); ++s)
            {
                const Foam::scalar y = Y_[s][i*nC_ + j];
                if (y < -1e-12)
                {
                    refuse
                    (
                        "negative mass fraction " + std::to_string(y) + " for "
                      + species_[s] + " at node (" + std::to_string(i) + ","
                      + std::to_string(j) + ")"
                    );
                }
                sum += y;
            }
            worstSpeciesSum_ = Foam::max(worstSpeciesSum_, Foam::mag(sum - 1.0));
        }
    }

    if (worstSpeciesSum_ > 1e-8)
    {
        refuse
        (
            "tabulated species do not sum to one at some node (worst |sum-1| = "
          + std::to_string(worstSpeciesSum_)
          + ", limit 1e-8); this is a table defect, not a tolerance to widen"
        );
    }

    validateProgressMapping();
}


// * * * * * * * * * * * * * * * * Destructor  * * * * * * * * * * * * * * * //

Foam::fgm::fgmTableReader::~fgmTableReader()
{}


// * * * * * * * * * * * * * * Private Member Functions  * * * * * * * * * * //

void Foam::fgm::fgmTableReader::refuse(const Foam::string& reason) const
{
    FatalErrorInFunction
        << "FGM table '" << path_.c_str() << "': " << reason.c_str() << Foam::nl
        << "The table is refused; nothing is clamped, rescaled or repaired."
        << Foam::abort(FatalError);
}


void Foam::fgm::fgmTableReader::cell
(
    const Foam::scalarField& grid,
    const Foam::scalar value,
    const char* labelName,
    Foam::label& i,
    Foam::scalar& w
) const
{
    const Foam::label n = grid.size();
    if (!std::isfinite(value)) refuse(Foam::string(labelName) + " is non-finite");

    if (value < grid[0])
    {
        if (policy_ == CLAMP_TO_BOUNDS)
        {
            ++clipCount_;
            if (Foam::string(labelName) == "Z") maxZExcursion_ = max(maxZExcursion_, grid[0] - value);
            else maxProgressExcursion_ = max(maxProgressExcursion_, grid[0] - value);
            i = 0;
            w = 0;
            return;
        }

        refuse
        (
            Foam::string(labelName) + "=" + numStr(value)
          + " is below the tabulated lower bound " + numStr(grid[0])
        );
    }

    if (value > grid[n - 1])
    {
        if (policy_ == CLAMP_TO_BOUNDS)
        {
            ++clipCount_;
            if (Foam::string(labelName) == "Z") maxZExcursion_ = max(maxZExcursion_, value - grid[n - 1]);
            else maxProgressExcursion_ = max(maxProgressExcursion_, value - grid[n - 1]);
            i = n - 2;
            w = 1;
            return;
        }

        refuse
        (
            Foam::string(labelName) + "=" + numStr(value)
          + " is above the tabulated upper bound " + numStr(grid[n - 1])
        );
    }

    Foam::label lo = 0;
    Foam::label hi = n - 1;
    while (hi - lo > 1)
    {
        const Foam::label mid = (lo + hi)/2;
        if (value < grid[mid])
        {
            hi = mid;
        }
        else
        {
            lo = mid;
        }
    }

    i = lo;
    w = (value - grid[lo])/(grid[lo + 1] - grid[lo]);
}


Foam::scalar Foam::fgm::fgmTableReader::interpolate
(
    const Foam::scalarField& block,
    const Foam::label nC,
    const Foam::label i,
    const Foam::label j,
    const Foam::scalar wZ,
    const Foam::scalar wc
)
{
    const Foam::scalar v00 = block[i*nC + j];
    const Foam::scalar v01 = block[i*nC + j + 1];
    const Foam::scalar v10 = block[(i + 1)*nC + j];
    const Foam::scalar v11 = block[(i + 1)*nC + j + 1];

    const Foam::scalar low = v00*(1 - wc) + v01*wc;
    const Foam::scalar high = v10*(1 - wc) + v11*wc;

    return low*(1 - wZ) + high*wZ;
}


// * * * * * * * * * * * * * * * Member Functions  * * * * * * * * * * * * * //

void Foam::fgm::fgmTableReader::lookup
(
    const Foam::scalar Z,
    const Foam::scalar c,
    Foam::scalarField& Y,
    Foam::scalar& Sc,
    Foam::scalar& Q,
    Foam::scalar& Tdiag
) const
{
    Foam::label i = 0;
    Foam::label j = 0;
    Foam::scalar wZ = 0;
    Foam::scalar wc = 0;

    ++lookupCount_;
    cell(z_, Z, "Z", i, wZ);
    const scalar lookupC = mappedMassFraction() ? mappedProgress(i, wZ, c) : c;
    cell(c_, lookupC, "c", j, wc);

    Y.setSize(species_.size());
    for (Foam::label s = 0; s < species_.size(); ++s)
    {
        Y[s] = interpolate(Y_[s], nC_, i, j, wZ, wc);
    }

    Sc = interpolate(Sc_, nC_, i, j, wZ, wc);
    Q = interpolate(Q_, nC_, i, j, wZ, wc);
    Tdiag = hasTdiag() ? interpolate(Tdiag_, nC_, i, j, wZ, wc) : 0;
}


void Foam::fgm::fgmTableReader::writeSummary(Foam::Ostream& os) const
{
    os  << "fgm-table path=" << path_.c_str()
        << " schema=" << schema_.c_str()
        << " source=\"" << source_.c_str() << "\""
        << " profile-sha256=" << profileSha256_.c_str()
        << " species=\"" << joinWords(species_).c_str() << "\""
        << " nZ=" << nZ_ << " nC=" << nC_
        << " progress-coordinate=" << progressCoordinate_.c_str()
        << " dYc=" << numStr(progressDYc_).c_str()
        << " hasTdiag=" << (hasTdiag() ? "yes" : "no")
        << " worst-species-sum=" << numStr(worstSpeciesSum_).c_str()
        << " bounds-policy="
        << (policy_ == CLAMP_TO_BOUNDS ? "clamp" : "error")
        << Foam::endl;
}

#include "fgmTableProgressI.H"

// ************************************************************************* //

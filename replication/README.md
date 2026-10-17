# Controlled replication

This directory owns environment recipes, replication inputs, and result summaries
for Nguyen's 2022 library and 2025 solver papers. The first scientific stages are
properties, counterflow flames, and premixed flame speed. No result is accepted yet.

The [Lark project record](https://qcnwovvb1xop.feishu.cn/docx/KgobdGw8CoIfRCxI2BvcoFYEnCf)
holds decisions and dated work logs. Git holds executable inputs and reviewed records.
Large images, build trees, and raw results remain in the configured project workspace.

## Scope and interfaces

- Inputs: this source revision, `environment/lock.json`, and an explicit project root.
- Outputs: an OF8 container, build products, preflight receipts, and later case results.
- Configuration: copy `environment/site.example.json` to an ignored local profile.
- Dependencies: Git, Bash, Python 3 for image preparation, Apptainer, and Slurm.
- Dependents: later property and flame cases. There is no FlamePilot runtime dependency.
- Non-goals: turbulent reacting-flow qualification, multi-node MPI, and spray extensions.

Credentials remain outside Git. This public fork must not contain private host
profiles, tokens, commercial data, or downloaded papers. The project root is a
placement boundary for trusted work, not a security sandbox against hostile code.
Cluster accounting and system audit files remain managed by the cluster.

## Workflow

1. Inspect `environment/lock.json` and the local site profile.
2. Run `bash replication/environment/workspace.sh plan /absolute/project/root`.
3. Run the same command with `prepare` after reviewing its paths.
4. Stage the pinned image and an exact source release under that root; extract the
   reusable directory container with `stage-runtime.sh` on SCNet.
5. Run `submit.sh plan ROOT IMAGE SOURCE PREFLIGHT_OR_BUILD PARTITION`.
6. Use `submit.sh apply` with the same arguments to submit the bounded job.

`IMAGE` is the staged directory container and `SOURCE` is the exact source release;
both are absolute paths inside `ROOT`. `PREFLIGHT_OR_BUILD` is
`preflight` or `build`. The image conversion command is documented in the
[environment guide](environment/README.md).

Use branch `work/environment-bootstrap` for setup and `work/2022-replication` for
the authorized scientific stages. Use scoped Conventional Commits.
Keep environment changes, solver changes, and scientific case changes separate.
Tag a tested source revision after its evidence record is committed. Retain the
original upstream revision for comparisons with publication-era releases.

## Verification

Run `git diff --check` and
`for script in replication/environment/*.sh; do bash -n "$script" || exit; done`.
Run `python3 -B replication/environment/check_lock.py` from the repository root.
Expected result: valid recipe pins and no shell or whitespace errors.
The Slurm preflight must confirm OF8, compiler, wmake, MPI, and writable output paths.
The build stage must compile all targets and inspect executable dependencies.
These checks do not validate thermophysical models or flame predictions.

See [architecture](docs/architecture.md), [writing](docs/writing.md), and
[validation stages](docs/validation-plan.md). The
[2026-10-16 environment record](docs/environment-qualification-20261016.md)
identifies the tested source, deployed image, scheduler jobs, and limits.

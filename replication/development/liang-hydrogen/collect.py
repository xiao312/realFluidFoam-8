"""Read selected Slurm job artifacts into a new local snapshot; never writes remotely."""
import argparse
import json
import re
import shlex
import subprocess
import tarfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["plan", "apply"])
    parser.add_argument("jobs", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--host", required=True)
    parser.add_argument("--root", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", args.host) or not args.root.startswith("/"):
        raise ValueError("Use an SSH configuration alias and absolute project root")
    rows = json.loads(args.jobs.read_text(encoding="utf-8-sig"))
    jobs = [int(r["job"]) for r in rows]
    if len(set(jobs)) != len(jobs) or any(j <= 0 for j in jobs):
        raise ValueError("Expected unique positive job ids")
    if args.output.exists():
        raise ValueError("Choose a new snapshot directory")
    print(json.dumps({"jobs": jobs, "output": str(args.output.resolve()), "remote_writes": False}))
    if args.action == "plan":
        return
    root = shlex.quote(args.root)
    script = f"""set -eu
cd {root}
test "$(pwd -P)" = {root}
for id in {' '.join(map(str, jobs))}; do
 for file in jobs/$id/source-revision.txt jobs/$id/input-sha256.txt jobs/$id/guess-sha256.txt jobs/$id/build-path.txt jobs/$id/sdk-path.txt jobs/$id/executable.sha256 jobs/$id/command.txt jobs/$id/resources.txt jobs/$id/result/*.csv jobs/$id/result/completed.txt jobs/$id/result/configuration.txt jobs/$id/result/numerics.txt jobs/$id/result/callbacks.txt; do
  if test -f "$file"; then printf '%s\\n' "$file"; fi
 done
done | tar -czf - -T -
"""
    result = subprocess.run(["ssh", args.host, "bash", "-s"], input=script.encode(),
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=180)
    args.output.mkdir(parents=True)
    archive = args.output/"snapshot.tar.gz"
    archive.write_bytes(result.stdout)
    with tarfile.open(archive) as tar:
        for member in tar.getmembers():
            target = (args.output/member.name).resolve()
            if not target.is_relative_to(args.output.resolve()):
                raise ValueError("Archive path escaped snapshot")
        tar.extractall(args.output, filter="data")
    status = subprocess.check_output(
        ["ssh", args.host, "sacct", "-j", ",".join(map(str, jobs)),
         "--format=JobID,State,Elapsed,ExitCode", "--parsable2"], timeout=60)
    (args.output/"scheduler.txt").write_bytes(status)
    for row in rows:
        row["result"] = str((args.output/"jobs"/str(row["job"])/"result").resolve())
    (args.output/"manifest.json").write_text(json.dumps(rows, indent=2)+"\n", newline="\n")


if __name__ == "__main__":
    main()

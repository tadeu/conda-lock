#!/usr/bin/env python3
"""
Somewhat hacky solution to create conda lock files.
"""
from __future__ import absolute_import, print_function

import json
import sys

if sys.version_info.major < 3:
    print("conda_lock needs to run under python 3")
    sys.exit(1)

import pathlib
import subprocess
import sys
import yaml
import os

DEFAULT_PLATFORMS = ["osx-64", "linux-64", "win-64"]
FAKE_PREFIX_NAME = "__magicmarker"
FAKE_PKGS_ROOT = "/something/that/does/not/exist"


def solve_specs_for_arch(channels, specs, platform):
    # type: (typing.List[str], typing.List[str], str) -> dict
    args = [
        "conda",
        "create",
        "-p",
        FAKE_PREFIX_NAME,
        "--override-channels",
        "--dry-run",
        "--json",
    ]
    for channel in channels:
        args.extend(["-c", channel])
    args.extend(specs)

    env = dict(os.environ)
    env.update({"CONDA_SUBDIR": platform, "CONDA_PKGS_DIRS": FAKE_PKGS_ROOT})
    json_output = subprocess.check_output(args, encoding="utf-8", env=env)
    # print(json_output)
    return json.loads(json_output)


def parse_environment_file(environment_file):
    # type: (pathlib.Path) -> list
    if not environment_file.exists():
        raise FileNotFoundError("{} not found".format(environment_file))
    with environment_file.open("r") as fo:
        env_yaml_data = yaml.safe_load(fo)
    # TODO: we basically ignore most of the fields for now.
    #       notable pip deps are not supported
    specs = env_yaml_data["dependencies"]
    channels = env_yaml_data.get("channels", [])
    return {"specs": specs, "channels": channels}


def fn_to_dist_name(fn):
    fn, _, _ = fn.partition('.conda')
    fn, _, _ = fn.partition('.tar.bz2')
    return fn

def make_lock_files(platforms, channels, specs):
    for platform in platforms:
        print("generating lockfile for {}".format(platform), file=sys.stderr)
        dry_run_install = solve_specs_for_arch(
            platform=platform, channels=channels, specs=specs
        )
        with open("conda-{}.lock".format(platform), "w") as fo:
            fo.write("# platform: {platform}\n".format(platform=platform))
            fo.write("@EXPLICIT\n")
            urls = {
                fn_to_dist_name(pkg['fn']): pkg['url'] for pkg in dry_run_install["actions"]["FETCH"]
            }
            for pkg in dry_run_install["actions"]["LINK"]:
                fo.write(urls[pkg["dist_name"]])
                fo.write("\n")

    print("To use the generated lock files create a new environment:", file=sys.stderr)
    print("", file=sys.stderr)
    print("     conda create -n YOURENV --file conda-linux-64.lock", file=sys.stderr)
    print("", file=sys.stderr)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-p",
        "--platform",
        nargs="?",
        action="append",
        help="generate lock files for the following platforms",
    )
    parser.add_argument(
        "-f",
        "--file",
        default="environment.yml",
        help="path to a conda environment specification",
    )

    args = parser.parse_args()

    environment_file = pathlib.Path(args.file)
    desired_env = parse_environment_file(environment_file)
    make_lock_files(
        channels=desired_env["channels"] or [],
        specs=desired_env["specs"],
        platforms=args.platform or DEFAULT_PLATFORMS,
    )

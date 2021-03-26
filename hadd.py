import argparse
import shutil
import subprocess
import sys
import venv
import os
import stat

from pathlib import Path
from sys import stdout
from os import environ

STEPS_GIT = ["git-srctools", "git-hammeraddons"]
STEPS_VENV = ["venv-create", "venv-srctools", "venv-pyinstaller"]
STEPS = [
    "all",
    "git", *STEPS_GIT,
    "venv", *STEPS_VENV,
    "postcompiler",
    "fgd",
    "final",
]

def step_header(msg, name, skip, reset):
    if name in skip:
        if name in reset:
            print(f"! {msg} (SKIPPED) (RESET)")
        else:
            print(f"- {msg} (SKIPPED)")
    elif name in reset:
        print(f"+ {msg} (RESET)")
    else:
        print(f"* {msg}")


def rmtree_git_onerror(_, path, __):
    # git does weird permission stuff
    os.chmod(path, stat.S_IWRITE)
    os.unlink(path)

def setup_repo(git, branch, path: Path, name, skip, cap, reset):
    step_header(f"Cloning/Pulling {git} {branch} in '{path}'", name, skip, reset)
    if name in reset and path.exists():
        shutil.rmtree(path, onerror=rmtree_git_onerror)

    if not name in skip:
        try:
            subprocess.run("git", capture_output=True)
        except FileNotFoundError:
            print("Error: Git is not installed or not on the path")
            sys.exit(-1)

        capture_output = name in cap

        path.mkdir(parents=True, exist_ok=True)

        if (path / Path(".git")).exists():
            remote = subprocess.check_output("git remote get-url origin", cwd=path).decode(stdout.encoding)[:-1]

            if remote == git:
                current_branch = subprocess.check_output("git branch --show-current", cwd=path).decode(stdout.encoding)[:-1]
            
                if current_branch == branch:
                    subprocess.run(f"git fetch origin {branch}", cwd=path, capture_output=capture_output)
                    subprocess.run(f"git reset --hard origin/{branch}", cwd=path, capture_output=capture_output)
                else:
                    subprocess.run(f"git switch {branch}", cwd=path, capture_output=capture_output)
                return
        
        if path.exists():
            shutil.rmtree(path)
        
        subprocess.run(f"git clone --single-branch --branch {branch} {git} {path}", capture_output=capture_output)

def process_steps(in_steps, all_if_empty):
    if in_steps is not None:
        out = set(in_steps)

        if (all_if_empty and not out) or "all" in out:
            out.update(STEPS)
        else:
            if "git" in in_steps:
                out.update(STEPS_GIT)
            if "venv" in in_steps:
                out.update(STEPS_VENV)
    else:
        out = set()

    return out

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-s", "--skip",
        nargs="+",
        choices=STEPS,
        help="Skips the steps provided. "
        + "'all' will skip all steps. "
        + f"'git' will skip {STEPS_GIT}. "
        + f"'venv' will skip {STEPS_VENV}. "
    )

    parser.add_argument(
        "-c", "--capture-output",
        nargs="*",
        choices=STEPS,
        help="Supresses the output of the steps provided. Supresses all steps if none are given. "
        + "'all' will supress all steps. "
        + f"'git' will supress {STEPS_GIT}. "
        + f"'venv' will supress {STEPS_VENV}. "
    )

    parser.add_argument(
        "-r", "--reset",
        nargs="*",
        choices=STEPS,
        help="Resets the steps provided. Resets all steps if none are given. "
        + "'all' will reset all steps. "
        + f"'git' will reset {STEPS_GIT}. "
        + f"'venv' will reset {STEPS_VENV}. "
        + "This will ask for confirmation. Use --noconfirm to suppress this. "
        + "WARNING: this may delete --out, --git, --srctools-dir, --hammeraddons-dir and --venv! "
    )

    parser.add_argument(
        "-d", "--dir",
        type=Path,
        default=".",
        help="The working directory. Defaults to '.'",
    )

    parser.add_argument(
        "-o", "--out",
        type=Path,
        default="build",
        help="The directory where the final build will be copied to. Relative to '--dir'. Defaults to 'build'."
    )

    parser.add_argument(
        "-g", "--git",
        type=Path,
        default="git",
        help="The directory where the git repos are placed. Relative to '--dir'. Defaults to 'git'.",
    )

    parser.add_argument(
        "--srctools-dir",
        type=Path,
        default="srctools",
        help="The directory where the srctools repo is. Relative to '--git'. Defaults to 'srctools'.",
    )

    parser.add_argument(
        "--srctools-git",
        default="https://github.com/TeamSpen210/srctools.git",
        help="The git repo of srctools. Defaults to 'https://github.com/TeamSpen210/srctools.git'",
    )

    parser.add_argument(
        "--srctools-branch",
        default="master",
        help="The branch of --srctools-git to use. Defaults to 'master'",
    )

    parser.add_argument(
        "--hammeraddons-dir",
        type=Path,
        default="hammeraddons",
        help="The directory where the HammerAddons repo is. Relative to '--git'. Defaults to 'HammerAddons'."
    )

    parser.add_argument(
        "--hammeraddons-git",
        default="https://github.com/TeamSpen210/HammerAddons.git",
        help="The git repo of HammerAddons. Defaults to 'https://github.com/TeamSpen210/HammerAddons.git'",
    )

    parser.add_argument(
        "--hammeraddons-branch",
        default="dev",
        help="The branch of --hammeraddons-git to use. Defaults to 'dev'",
    )

    parser.add_argument(
        "-v", "--venv",
        type=Path,
        default="venv",
        help="The directory where the venv is. Realtive to '--dir'. Defaults to 'venv'."
    )

    parser.add_argument(
        "--noconfirm",
        action="store_true",
        help="Skips confirmation of destructive actions like --reset."
    )

    result = parser.parse_args()

    work_dir = result.dir
    build_dir = work_dir / result.out
    git_dir = work_dir / result.git
    srctools_dir = git_dir / result.srctools_dir
    hammeraddons_dir = git_dir / result.hammeraddons_dir

    build_bat = hammeraddons_dir / "build.bat"

    venv_dir = work_dir / result.venv
    venv_scripts = venv_dir / "Scripts"
    venv_py = venv_scripts / "python.exe"
    venv_pip = venv_scripts / "pip.exe"

    skip = process_steps(result.skip, False)
    cap = process_steps(result.capture_output, True)
    reset = process_steps(result.reset, True)

    if reset and not result.noconfirm:
        print("The following directories will be deleted:")
        
        if "git-srctools" in reset:
            print(srctools_dir.resolve(False))
        elif "postcompiler" in reset:
            print((srctools_dir / "build").resolve(False))
            print((srctools_dir / "dist").resolve(False))

        if "git-hammeraddons" in reset:
            print(hammeraddons_dir.resolve(False))
        elif "fgd" in reset:
            print((hammeraddons_dir / "build").resolve(False))

        if "venv-create" in reset:
            print(venv_dir.resolve(False))
        if "final" in reset:
            print(build_dir.resolve(False))

        if input(f"Are you sure you want to reset? (y/n) ").startswith("y".casefold()):
            print("(Use --noconfirm to skip this prompt)")
        else:
            print("Aborting.")
            sys.exit(-1)

    setup_repo(result.srctools_git, result.srctools_branch, srctools_dir, "git-srctools", skip, cap, reset)
    setup_repo(result.hammeraddons_git, result.hammeraddons_branch, hammeraddons_dir, "git-hammeraddons", skip, cap, reset)

    step_header(f"Creating venv in '{venv_dir}'", "venv-create", skip, reset)
    if "venv-create" in reset and venv_dir.exists():
        shutil.rmtree(venv_dir)
    if not "venv-create" in skip:
        venv.create(venv_dir, with_pip=True)
    
    step_header(f"Installing srctools in '{venv_dir}'", "venv-srctools", skip, reset)
    if "venv-srctools" in reset and venv_dir.exists():
        subprocess.run([venv_pip, "uninstall", "srctools"], capture_output="venv-srctools" in cap)
    if not "venv-srctools" in skip:
        subprocess.run([venv_pip, "install", srctools_dir], capture_output="venv-srctools" in cap)

    step_header(f"Installing pyinstaller in '{venv_dir}'", "venv-pyinstaller", skip, reset)
    if "venv-pyinstaller" in reset and venv_dir.exists():
        subprocess.run([venv_pip, "uninstall", "pyinstaller"], capture_output="venv-pyinstaller" in cap)
    if not "venv-pyinstaller" in skip:
        subprocess.run([venv_pip, "install", "pyinstaller"], capture_output="venv-pyinstaller" in cap)

    modfified_env = environ.copy()
    modfified_env["HAMMER_ADDONS"] = str(hammeraddons_dir.resolve())
    modfified_env["PATH"] = str(venv_scripts.resolve()) + ";" + modfified_env["PATH"]

    step_header(f"Building postcompiler in '{srctools_dir}'", "postcompiler", skip, reset)
    if "postcompiler" in reset:
        if (srctools_dir / "build").exists():
            shutil.rmtree(srctools_dir / "build")
        if (srctools_dir / "dist").exists():
            shutil.rmtree(srctools_dir / "dist")
    if not "postcompiler" in skip:
        subprocess.run([venv_py, "-m", "PyInstaller", "postcompiler.spec", "--noconfirm"], cwd=srctools_dir, env=modfified_env, capture_output="postcompiler" in cap)

    step_header(f"Building FGD in '{hammeraddons_dir}'", "fgd", skip, reset)
    if "fgd" in reset and (hammeraddons_dir / "build").exists():
        shutil.rmtree(hammeraddons_dir / "build")
    if not "fgd" in skip:
        subprocess.run(str(build_bat.resolve()), cwd=hammeraddons_dir, env=modfified_env, capture_output="fgd" in cap)

    step_header(f"Finalizing build in '{build_dir}'", "final", skip, reset)
    if "final" in reset:
        if build_dir.exists():
            shutil.rmtree(build_dir)

    if not "final" in skip:
        if os.listdir(build_dir) and not result.noconfirm:
            if input(f"Build dir not empty. Delete it? (y/n) ").startswith("y".casefold()):
                print("(Use --noconfirm to skip this prompt)")
            else:
                print("Aborting.")
                sys.exit(-1)
        
        if build_dir.exists():
            shutil.rmtree(build_dir)

        shutil.copytree(srctools_dir / "dist", build_dir)
        shutil.copytree(hammeraddons_dir / "build", build_dir, dirs_exist_ok=True)

    print("Done!")

if __name__ == "__main__":
    main()
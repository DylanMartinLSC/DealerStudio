from release_common import ROOT, run, launch_check, archive

run("powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "package.ps1")
folder = ROOT / "dist" / "DealerStudio"
launch_check(folder / "DealerStudio.exe", "--smoke-test")
archive(folder, "DealerStudio-windows.zip")

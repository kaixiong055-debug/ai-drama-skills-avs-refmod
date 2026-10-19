"""Folder selection and path handling for the asset library."""
import ipaddress
import json
import os
import subprocess
from pathlib import Path, PureWindowsPath


def compatible_path(value):
    value = str(value or "").strip().strip('"')
    if not value:
        return False
    if os.name != "nt" and (PureWindowsPath(value).drive or "\\" in value):
        return False
    if os.name == "nt" and value.startswith("/") and not value.startswith("//"):
        return False
    return True


def browser_directory(requested, configured, input_directory):
    # A workflow can come from another OS or a directory which was removed.
    for value in (requested, configured, input_directory, str(Path.home())):
        if compatible_path(value):
            path = Path(value).expanduser().resolve()
            if path.is_dir():
                return path
    return Path(Path.cwd().anchor)


def native_picker_available(remote):
    try:
        return os.name == "nt" and ipaddress.ip_address(remote).is_loopback
    except ValueError:
        return False


def pick_windows_directory(initial):
    script = r'''
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.Application]::EnableVisualStyles()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$picker = [System.Windows.Forms.FolderBrowserDialog]::new()
$picker.Description = 'Select permanent asset library folder'
$picker.ShowNewFolderButton = $true
if (Test-Path -LiteralPath $env:AVS_LIBRARY_INITIAL -PathType Container) {
    $picker.SelectedPath = $env:AVS_LIBRARY_INITIAL
}
try {
    $selected = if ($picker.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { $picker.SelectedPath } else { '' }
    @{path=$selected;cancelled=($selected -eq '')} | ConvertTo-Json -Compress
} finally { $picker.Dispose() }
'''
    environment = dict(os.environ, AVS_LIBRARY_INITIAL=str(initial or ""))
    result = subprocess.run(["powershell.exe", "-NoProfile", "-STA", "-Command", script],
                            env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            encoding="utf-8", creationflags=subprocess.CREATE_NO_WINDOW, check=True)
    return json.loads(result.stdout)


def import_target(input_directory, import_id, relative_path):
    if len(import_id) != 32 or any(c not in "0123456789abcdef" for c in import_id):
        raise ValueError("无效的文件夹导入编号。")
    relative = str(relative_path or "").replace("\\", "/")
    parts = relative.split("/")
    if len(parts) < 2 or any(p in ("", ".", "..") or ":" in p or "\x00" in p for p in parts):
        raise ValueError("无效的素材相对路径。")
    base = Path(input_directory).resolve()
    root = (base / "AI_Video_Studio" / "libraries" / import_id).resolve()
    if not root.is_relative_to(base):
        raise ValueError("导入目录超出 ComfyUI input。")
    target = (root / relative).resolve()
    if not target.is_relative_to(root):
        raise ValueError("素材路径超出导入目录。")
    return root / parts[0], target

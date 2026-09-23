HELPERS = {
"system": r'''
def __boa_environment(mode, name, value=""):
    if mode == "read": return os.environ.get(str(name), ""), str(name) in os.environ
    if mode == "write": os.environ[str(name)] = str(value); return True
    if mode == "delete": return os.environ.pop(str(name), None) is not None
    return False

def __boa_run_program(program, arguments, input_text="", timeout=0, hide_window=True):
    command = [str(program), *[str(item) for item in (arguments or [])]]
    startupinfo = None
    if hide_window and sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO(); startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    result = subprocess.run(command, input=str(input_text or ""), text=True, capture_output=True, timeout=timeout or None, startupinfo=startupinfo, check=False)
    return result.stdout, result.stderr, result.returncode, result.returncode == 0

def __boa_open_external(mode, target):
    target = str(target)
    if mode == "url": return bool(webbrowser.open(target))
    if sys.platform == "win32": os.startfile(target)
    elif sys.platform == "darwin": subprocess.Popen(["open", target])
    else: subprocess.Popen(["xdg-open", target])
    return True
''',
}


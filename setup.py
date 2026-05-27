from setuptools import setup

APP = ["status_monitor.py"]

OPTIONS = {
    "argv_emulation": False,   # must be False on macOS 12+ or app crashes at launch
    "semi_standalone": False,
    "packages": [
        "rumps",
        "requests",
        "certifi",
        "urllib3",
        "charset_normalizer",
        "idna",
    ],
    "plist": {
        # LSUIElement = 1 → menu-bar-only app, no Dock icon
        "LSUIElement": True,
        "CFBundleName": "Status Monitor",
        "CFBundleDisplayName": "Status Monitor",
        "CFBundleIdentifier": "com.apliqo.statusmonitor",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        "NSHighResolutionCapable": True,
        "NSHumanReadableCopyright": "Apliqo",
    },
}

setup(
    name="Status Monitor",
    app=APP,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)

import json
import os

settings_path = os.path.expandvars(r"%APPDATA%\Code\User\settings.json")
with open(settings_path, "r", encoding="utf-8") as f:
    data = json.load(f)

if "workbench.colorCustomizations" not in data:
    data["workbench.colorCustomizations"] = {}

data["workbench.colorCustomizations"].update({
    "editor.background": "#0a0a0a",
    "sideBar.background": "#0d0d0d",
    "editor.foreground": "#ff9500", 
    "editorLineNumber.foreground": "#663300",
    "editorLineNumber.activeForeground": "#ffcc00",
    "editorError.foreground": "#ff0000",
    "editorWarning.foreground": "#ffaa00",
    "editorInfo.foreground": "#00ffcc",
    "editor.selectionBackground": "#ff950044",
    "list.activeSelectionBackground": "#331a00",
    "list.activeSelectionForeground": "#ffcc00",
    "statusBar.background": "#1a1a1a",
    "statusBar.foreground": "#ff9500"
})

if "editor.tokenColorCustomizations" not in data:
    data["editor.tokenColorCustomizations"] = {}

data["editor.tokenColorCustomizations"]["textMateRules"] = [
    {
        "scope": ["comment", "punctuation", "keyword"],
        "settings": { "foreground": "#cc5500" }
    },
    {
        "scope": ["string", "variable"],
        "settings": { "foreground": "#ffd500" }
    },
    {
        "scope": ["constant", "number"],
        "settings": { "foreground": "#ff4400" }
    }
]

with open(settings_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
print("Settings updated successfully.")

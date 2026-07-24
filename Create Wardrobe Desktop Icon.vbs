' One-time (re-)setup: creates a "Wardrobe" icon on your Windows Desktop
' that launches the app with no console window at all, in your normal
' browser. Run this once after extracting a new copy of Wardrobe, or again
' now if you already had a Wardrobe icon pointing at the old Start
' Wardrobe.bat, to switch it over to the instant, no-terminal launcher.
' Safe to run again later (e.g. after moving the folder) — it just
' recreates the icon pointing at wherever this script currently lives.

Set oFSO = CreateObject("Scripting.FileSystemObject")
scriptDir = oFSO.GetParentFolderName(WScript.ScriptFullName)

Set oWS = CreateObject("WScript.Shell")
sLinkFile = oWS.SpecialFolders("Desktop") & "\Wardrobe.lnk"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = scriptDir & "\launch_desktop.pyw"
oLink.WorkingDirectory = scriptDir
oLink.IconLocation = scriptDir & "\wardrobe.ico, 0"
oLink.Description = "Wardrobe - Closet & Fit Studio"
oLink.Save

MsgBox "Done! Your ""Wardrobe"" Desktop icon now opens instantly - no console window." & vbCrLf & vbCrLf & _
       "Just double-click it any time to open Wardrobe.", 64, "Wardrobe Setup"

' One-time setup: creates a "Wardrobe Updater" icon on your Windows Desktop.
' Double-click it any time to fetch the latest version of Wardrobe, install
' it, and clean up after itself automatically. Safe to re-run this setup
' script again later (e.g. after moving the folder) — it just recreates the
' icon pointing at wherever this script currently lives.

Set oFSO = CreateObject("Scripting.FileSystemObject")
scriptDir = oFSO.GetParentFolderName(WScript.ScriptFullName)

Set oWS = CreateObject("WScript.Shell")
sLinkFile = oWS.SpecialFolders("Desktop") & "\Wardrobe Updater.lnk"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = scriptDir & "\wardrobe_updater.pyw"
oLink.WorkingDirectory = scriptDir
oLink.IconLocation = scriptDir & "\wardrobe.ico, 0"
oLink.Description = "Wardrobe Updater - fetches and installs the latest Wardrobe"
oLink.Save

MsgBox "Done! A ""Wardrobe Updater"" icon was added to your Desktop." & vbCrLf & vbCrLf & _
       "From now on, double-click it any time you want to update Wardrobe - " & _
       "it downloads the latest version, installs it, stops any running " & _
       "copy for you, and cleans up after itself. No more extracting ZIPs " & _
       "by hand.", 64, "Wardrobe Updater Setup"

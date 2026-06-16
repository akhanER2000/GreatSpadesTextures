' ===========================================================
'  Editor del Soldado — lanzador silencioso (doble clic)
'  Abre dist\EditorSoldado.exe sin mostrar consola.
' ===========================================================
Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(WScript.ScriptFullName)
exePath = root & "\dist\EditorSoldado.exe"
Set sh = CreateObject("WScript.Shell")
If fso.FileExists(exePath) Then
    sh.Run """" & exePath & """", 1, False
Else
    MsgBox "No se encontro dist\EditorSoldado.exe." & vbCrLf & _
           "Ejecuta primero construir_exe.bat para generarlo.", 48, "Editor del Soldado"
End If

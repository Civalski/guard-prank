' Inicia o Guardiao de Tela em segundo plano, sem janela de terminal.
' Portavel: usa a pasta onde este arquivo esta e o pythonw do PATH.
Set WShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
pasta = fso.GetParentFolderName(WScript.ScriptFullName)
WShell.Run "pythonw """ & pasta & "\guardiao.py""", 0, False

Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\Users\Marat\wb-unit-economics"
WshShell.Run """C:\Users\Marat\AppData\Local\Python\pythoncore-3.15-64\pythonw.exe"" main.py", 0, False
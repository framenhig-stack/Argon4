Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\Users\Franco\Documents\argon4-agent"
WshShell.Run """C:\Users\Franco\Documents\argon4-agent\.venv\Scripts\pythonw.exe"" ""C:\Users\Franco\Documents\argon4-agent\main_agent.py""", 0, False

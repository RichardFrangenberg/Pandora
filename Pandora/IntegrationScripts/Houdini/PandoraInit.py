import sys, os
if os.path.basename(sys.executable) != "hython.exe":
	Dir = os.path.join(os.getenv('LocalAppdata'), "Pandora", "Scripts")
	if Dir not in sys.path:
		sys.path.append(Dir)
	
	import PandoraCore
	pandoraCore = PandoraCore.PandoraCore()
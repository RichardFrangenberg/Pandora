import sys, os
if os.path.basename(sys.executable) != "hython.exe":
	Dir = os.path.join(PANDORAROOT, "Scripts")
	if Dir not in sys.path:
		sys.path.append(Dir)
	
	import PandoraCore
	core = PandoraCore.PandoraCore(app="Houdini")
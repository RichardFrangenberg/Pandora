# >>>PandoraStart
from maya import OpenMaya as omya

if omya.MGlobal.mayaState() != omya.MGlobal.kBatch:
    try:
        import PandoraInit

        Pandora = PandoraInit.pandoraInit()
    except:
        print("Error occured while loading Pandora")
# <<<PandoraEnd

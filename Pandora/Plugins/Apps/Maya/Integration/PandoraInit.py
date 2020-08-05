import sys, os


def pandoraInit():
    Dir = os.path.join(PANDORAROOT, "Scripts")
    if Dir not in sys.path:
        sys.path.append(Dir)

    import PandoraCore

    Pandora = PandoraCore.PandoraCore(app="Maya")
    return Pandora

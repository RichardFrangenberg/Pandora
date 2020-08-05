import sys, os

if os.path.basename(sys.executable) != "hython.exe":
    pandoraScripts = os.path.join(
        os.path.abspath(
            os.path.join(
                __file__,
                os.pardir,
                os.pardir,
                os.pardir,
                os.pardir,
                os.pardir,
                os.pardir,
                "Scripts",
            )
        )
    )

    if pandoraScripts not in sys.path:
        sys.path.append(pandoraScripts)

    import PandoraCore

    core = PandoraCore.PandoraCore(app="Houdini")

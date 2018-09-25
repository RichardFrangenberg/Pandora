macroScript PandoraSubmitter category:"Pandora" tooltip:"Open the Pandora job submitter" buttontext:"Submit job..."
(
	python.Execute "pandoraCore.openSubmitter()"
)

macroScript PandoraRenderHandler category:"Pandora" tooltip:"Open the Pandora Render-Handler" buttontext:"Render-Handler"
(
	python.Execute "pandoraCore.openRenderHandler()"
)

macroScript PandoraSettings category:"Pandora" tooltip:"Open the Pandora settings" buttontext:"Settings"
(
	python.Execute "pandoraCore.openSettings()"
)

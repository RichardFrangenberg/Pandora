if menuMan.findMenu "Pandora" != undefined then
(
menuMan.unRegisterMenu (menuMan.findMenu "Pandora")
)
(
local mainMenuBar = menuMan.getMainMenuBar()
local subMenu = menuMan.createMenu "Pandora"
local psubmitItem = menuMan.createActionItem "PandoraSubmitter" "Pandora"
subMenu.addItem psubmitItem -1
local prhItem = menuMan.createActionItem "PandoraRenderHandler" "Pandora"
subMenu.addItem prhItem -1
local psettingsItem = menuMan.createActionItem "PandoraSettings" "Pandora"
subMenu.addItem psettingsItem -1
local subMenuItem = menuMan.createSubMenuItem "Pandora" subMenu
local subMenuIndex = mainMenuBar.numItems()
mainMenuBar.addItem subMenuItem subMenuIndex
menuMan.updateMenuBar()
menuMan.saveMenuFile (menuMan.getMenuFile())
)
# >>>PandoraStart
class TOPBAR_MT_pandora(Menu):
    bl_label = "Pandora"

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        row.operator("object.pandora_submitter")

        row = layout.row()
        row.operator("object.pandora_renderhandler")

        row = layout.row()
        row.operator("object.pandora_settings")


# <<<PandoraEnd

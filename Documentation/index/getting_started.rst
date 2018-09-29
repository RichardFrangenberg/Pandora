Getting Started
*****************

Installation
===================

Go to the downloads page and download the latest version of Pandora: https://prism-pipeline.com/pandora/
Follow the instructions of the :ref:`Installation<Installation>` section to set up Pandora on your PC.

You want to install Pandora on all your computers, where you want to use a part of Pandora. If you want to use the PC as a job submitter or as a renderslave can be defined later.


Configuring Pandora
====================

After the installation you want to configure Pandora in the "Pandora Settings" dialog. You can open this dialog by typing "PandoraSettings" in the windows startmenu search or from the context menu of the Pandora TrayIcon:


.. image:: images/TrayIcon.png


In the "General" tab of the Pandora Settings you have to set a path for the Pandora Root. This path must be accessable from all submitters and renderslaves. If you have multiple computers, this is typically a network location.

You can change the local repository if you like. By default this will be set to your windows documents folder.

The last thing to do is to enable the component of Pandora, which you want to use on the PC. In the tabs "Submissions", "Slave" and "Coordinator" you have an "enable" checkbox to enable each component. You can enable all of them on one computer or just one or two or even none of them. Keep in mind that only one computer in your network should have the "Coordinator" enabled, but you can have as many submitter and slaves as you like.

Save the settings and on the computers, where you have enabled the "Slave" or "Coordinator" component, you can start the slave/coordinator from the context menu of the tray icon now.

The coordinator must be running to see the submitted renderjobs and their current status. At least one renderslave needs to be enabled in order to render a job.


Submitting a job
===================

To sumit a renderjob start your DCC app and open a scenefile, which you want to render.
From the Pandora shelf/menu open the Submitter tool. In this tool you have to set an outputpath, a projectname and a jobname. Then you can press "Submit" to send the job to Pandora.

If you use the Prism Pipeline, you don't need to use the Pandora submitter tool. Instead you can open the StateManager, create an ImageRender state in there you can enable the Pandora job submission. When you publish your scene now, Prism will send the job to Pandora.


Tracking the progress of the job
=================================

In the RenderHandler tool you can monitor the status and the progress of all your renderjobs. You can open the RenderHandler from the Pandora shelf/menu, from the start menu or from the Pandora Tray Icon.

In the top left list all renderjobs are listed and in the bottom left list you can see all your renderslaves. In the "Task List" tab at the upper right corner you can see a list of all tasks of the currently selected renderjob. There you can see whether a task is assigned to a slave or if it is already done.

You can open the output folder from the context menu of a job to view the final renderings. If you have RV installed you can also play the renderings in RV directly from the context menu in the RenderHandler
Overview
*****************

Introduction
===================

Pandora is a Renderfarm Manager, which can manage renderjobs and simulationjobs. It automatically distibutes these jobs across all available renderslaves. You can define various settings to control how the jobs are assigned to the renderslaves. Pandora can be used on a single computer to queue renderjobs or on multiple computers to distribute the renderjobs between all computers.
You can submit your scenefile in a DCC app (Digital Content Creation Application) like Houdini or Maya as a renderjob. The job can be splitted into multiple tasks. Each task can be rendered by a different renderslave. When more slaves can render the job simultaneously, the renderings will be finished quicker of course.

Pandora is well integrated in the Prism Pipeline, which makes it easy to submit jobs from your Prism project, but you can use Pandora without Prism, too.

The images in this documentation were mostly taken from Prism Standalone, Houdini- or Maya- integration of Prism, but the Prism user interface in other DCC applications is almost identical. The features described in this documentation can be applied to the integration of all supported programs.



Supported Software
===================

You can open the Pandora tools as a separate software (standalone) and many tools are also available inside your DCC apps from the Pandora menu/shelf. The job submitter is only available in the DCC apps and the Renderslave and SlaveCoordinator are only accessable from the standalone tools.

Pandora works on Windows 64bit in these DCC apps:

* Autodesk 3dsMax
* Autodesk Maya
* Blender
* SideEffects Houdini (render and simulation)

The Pandora Coordinator, who is responsible for assigning jobs to renderslaves, can also run on Linux.
Linux, macOS and Docker
***********************

Supported platforms
===================

+---------------------------------+---------+-------+-------+--------+
| Component                       | Windows | Linux | macOS | Docker |
+=================================+=========+=======+=======+========+
| Coordinator                     | yes     | yes   | yes   | yes    |
+---------------------------------+---------+-------+-------+--------+
| Renderslave                     | yes     | no    | no    | no     |
+---------------------------------+---------+-------+-------+--------+
| Submitter, Render-Handler, Tray | yes     | no    | no    | no     |
+---------------------------------+---------+-------+-------+--------+

The Coordinator needs Python 3.7 or later and no additional Python modules.


Running the Coordinator
=======================

The Coordinator is a script without a user interface. On Windows it is usually started from the Pandora Tray. On every platform it can be started manually:

.. code-block:: bash

   python Pandora/Scripts/PandoraCoordinator.py

The Coordinator reads the Pandora root folder from the Pandora user preferences (``Pandora.json``). The preferences are located in:

* Windows: ``%USERPROFILE%\Documents\Pandora``
* Linux: ``$XDG_CONFIG_HOME/Pandora`` (default: ``~/.config/Pandora``)
* macOS: ``~/Library/Application Support/Pandora``

On a machine without Pandora user preferences, e.g. a server, the Coordinator can be configured with environment variables:

``PANDORA_ROOT``
   The Pandora root folder. If this variable is set, the Coordinator doesn't need any user preferences.

``PANDORA_LOCAL_MODE``
   ``true`` if all slaves and workstations access the Pandora root folder directly (e.g. a network share). ``false`` if they use a synchronized copy of it.

``PANDORA_REPOSITORY``
   The folder, in which the Coordinator stores the jobs. The default is the ``JobRepository`` folder in the Pandora root.

``PANDORA_CONFIG``
   The path to a ``Pandora.json``, which is used instead of the user preferences in the default location.

Environment variables have priority over the settings in the Render-Handler, which have priority over the user preferences.

To stop the Coordinator send it a ``SIGTERM`` or ``SIGINT`` signal (e.g. ``Ctrl+C``). It finishes the current cycle and closes. After every cycle the Coordinator updates the file ``Scripts/PandoraCoordinator/heartbeat`` in the Pandora root, which can be used to monitor it.


Docker
======

The Coordinator can run in a container, e.g. on a NAS, which shares the Pandora root folder with all slaves and workstations.

#. Copy ``.env.example`` to ``.env`` and set ``PANDORA_ROOT_HOST`` to the Pandora root folder on the host. Set ``PUID`` and ``PGID`` to the user and group, who own the files in that folder.
#. Start the Coordinator:

   .. code-block:: bash

      docker compose up -d

``docker compose logs -f`` shows the log of the Coordinator. ``docker compose ps`` shows if the Coordinator is healthy.

To build the image from the source code instead of downloading it, use ``docker compose up -d --build``.

.. note::

   On hosts with SELinux (e.g. Fedora, RHEL) the container is not allowed to access the Pandora root folder by default. Append ``:z`` to the volume in ``docker-compose.yml`` or label the folder manually.


Path mapping
============

On a renderfarm with different operating systems the same folder has a different path on each of them. Pandora converts paths with the rules in the file ``Scripts/PandoraCoordinator/PathMapping.json`` in the Pandora root folder:

.. code-block:: json

   {
       "mappings": [
           {"windows": "P:/", "linux": "/mnt/projects", "darwin": "/Volumes/projects"},
           {"windows": "//nas/pandora", "linux": "/pandora", "darwin": "/Volumes/pandora"}
       ]
   }

Each rule describes one location. A path, which starts with one of the prefixes of a rule, is converted to the prefix of the current operating system. If multiple rules match, the rule with the longest prefix is used. Windows prefixes are not case sensitive. A rule doesn't need to contain all operating systems.

A machine, which mounts a location differently than the rest of the farm, can have its own ``PathMapping.json`` in the folder of the Pandora user preferences. Its rules have priority.

Currently the Coordinator applies the mapping to its repository path (``Repository`` in the Coordinator settings of the Render-Handler), so that a repository, which was set on a Windows workstation, is found by a Coordinator on Linux. Without a ``PathMapping.json`` no paths are changed.


Security
========

The Coordinator reads its commands from text files in the Pandora root folder. In previous versions the content of these files was executed as Python code, so everyone with write access to the Pandora root could run code on the Coordinator machine. Now the Coordinator reads the command files as data only.

The ``Command`` setting of the Coordinator in the Render-Handler accepts calls to these functions: ``searchUncollectedRnd``, ``collectOutput``, ``notifyWorkstations``, ``notifySlaves``, ``restartGDrive``, e.g. ``self.searchUncollectedRnd()``. Other commands are rejected and a warning is shown in the Render-Handler.

Renderslaves still execute the commands they receive. Only give trusted users write access to the Pandora root folder.

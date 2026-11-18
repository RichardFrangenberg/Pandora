Linux, macOS and Docker
***********************

Supported platforms
===================

+---------------------------------+---------+-------+-------+--------+
| Component                       | Windows | Linux | macOS | Docker |
+=================================+=========+=======+=======+========+
| Coordinator                     | yes     | yes   | yes   | yes    |
+---------------------------------+---------+-------+-------+--------+
| Renderslave                     | yes     | yes*  | yes*  | no     |
+---------------------------------+---------+-------+-------+--------+
| Submitter, Render-Handler, Tray | yes     | no    | no    | no     |
+---------------------------------+---------+-------+-------+--------+

\* without user interface, see :ref:`headlessSlave`.

The Coordinator needs Python 3.7 or later and no additional Python modules. The Renderslave additionally needs the ``psutil`` module.


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


.. _headlessSlave:

Renderslave without user interface
==================================

On Linux and macOS, and on Windows machines without a desktop session, the Renderslave can run without user interface:

.. code-block:: bash

   python -m pip install psutil
   python Pandora/Scripts/PandoraSlave.py --headless

In this mode the slave has no tray icon and doesn't ask a user before it starts rendering. All other features are the same: the slave appears in the Render-Handler, where it can be configured, paused and restarted like every other slave. The slave also starts without user interface if the environment variable ``PANDORA_HEADLESS`` is set to ``1`` or if Qt is not installed.

The slave reads the Pandora user preferences or the environment variables described above. ``PANDORA_REPOSITORY`` is the local folder, in which the slave stores the jobs it renders. A typical render node only needs:

.. code-block:: bash

   export PANDORA_ROOT=/mnt/pandora
   export PANDORA_REPOSITORY=/var/lib/pandora
   python Pandora/Scripts/PandoraSlave.py --headless

The slave stops rendering and closes when it receives a ``SIGTERM`` or ``SIGINT`` signal, so it can run as a service, e.g. with systemd:

.. code-block:: ini

   [Unit]
   Description=Pandora Renderslave
   After=network-online.target remote-fs.target

   [Service]
   User=render
   Environment=PANDORA_ROOT=/mnt/pandora
   Environment=PANDORA_REPOSITORY=/var/lib/pandora
   ExecStart=/usr/bin/python3 /opt/Pandora/Pandora/Scripts/PandoraSlave.py --headless
   Restart=on-failure

   [Install]
   WantedBy=multi-user.target

Blender, Houdini and Maya jobs can be rendered on Linux and macOS. The slave searches the render executable (``blender``, ``hython``, ``Render``) in this order:

#. the path override in the Pandora settings (``dccoverrides`` in ``Pandora.json``, e.g. ``"Blender_override": true, "Blender_path": "/opt/blender-4.2/blender"``)
#. the default install location of the version, which was used to submit the job
#. the environment (``HFS``, ``MAYA_LOCATION``)
#. the ``PATH``
#. the default install location of any version

3ds Max jobs can only be rendered on Windows.

.. note::

   Update Pandora on the slaves by updating the whole Pandora installation. The Renderslave consists of multiple files now, so replacing only ``PandoraSlave.py`` in the ``Scripts/PandoraSlaves`` folder of the Pandora root doesn't work for slaves with an older Pandora version.


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

The Coordinator applies the mapping to its repository path (``Repository`` in the Coordinator settings of the Render-Handler), so that a repository, which was set on a Windows workstation, is found by a Coordinator on Linux. The Renderslave applies the mapping to the paths of a job (e.g. the output path) before it starts rendering, so that a job, which was submitted on Windows, can be rendered on Linux. Paths inside of the scenefile are not converted. Without a ``PathMapping.json`` no paths are changed.


Security
========

The Coordinator and the Renderslaves read their commands from text files in the Pandora root folder. In previous versions the content of these files was executed as Python code, so everyone with write access to the Pandora root could run code on the Coordinator and on every slave. Now the command files are read as data only.

The ``Command`` setting of the Coordinator in the Render-Handler accepts calls to these functions: ``searchUncollectedRnd``, ``collectOutput``, ``notifyWorkstations``, ``notifySlaves``, ``restartGDrive``, e.g. ``self.searchUncollectedRnd()``. Other commands are rejected and a warning is shown in the Render-Handler.

The ``Command`` setting of a slave accepts calls to these functions: ``shutdownPC``, ``stopRender``, ``restartLogic``, ``exitLogic``, ``uploadCurJob``, ``startTeamviewer``, ``writeScreenshot``, ``clearLog``, ``pauseSlave``, ``activateSlave``, ``setSlave``, e.g. ``self.pauseSlave(60)``.

Jobs still define what a slave renders, and the slaves update their scripts from the Pandora root folder. Only give trusted users write access to the Pandora root folder.

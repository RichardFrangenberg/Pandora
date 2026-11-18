# Pandora

This is the official repository of the Pandora Renderfarmmanager.

Pandora manages renderjobs from multiple 3d applications and assigns them to available renderslaves.

You can find more information on the website:

https://prism-pipeline.com/pandora

## Getting Started

On the [website](https://prism-pipeline.com/pandora) you can find the latest official installer.

Pandora runs on Windows. The Coordinator also runs on Linux, macOS and in a Docker container.


## Coordinator in Docker

The Coordinator can run in a container, e.g. on a NAS:

* Copy `.env.example` to `.env` and set `PANDORA_ROOT_HOST` to your Pandora root folder.
* Run `docker compose up -d`

See [Linux, macOS and Docker](Documentation/index/cross_platform.rst) for details.


## Tests

```
python -m pip install -r requirements-dev.txt
python -m pytest tests
```


## Installing

* To install the latest development version download or clone this repository and the Pandora dependencies:

[Pandora-dependencies](https://dl.dropboxusercontent.com/s/poi0prze4xwyhgy/Pandora_v1.1.0_dependencies.zip?dl=1)

* Extract the dependencies and copy the extracted folders into Pandora/PandoraFiles of this repository.

* Now the "PandoraFiles" folder should contain the folders like:
"Python37", "PythonLibs", "Scripts" ...

* Now go two folders up and execute the Pandora_Setup.bat.

## License

This project is licensed under the GNU GPL-3.0 License - see the [LICENSE](LICENSE) file for details
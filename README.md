Make a small copies of photos and videos.

## Installation

```
cd <project_directory>
pip install .
```

Dependencies installed from *pyproject.toml*:
- pillow
- opencv-python-headless

## Usage

```
./pvo.py -s <source_directory> -d <destination_directory>
```

For example, start `./pvo.py` and it will make small copies from *./tests/examples* directory to *./tests/examples-thumbnails.tar.gz*.
Default \<source\> and \<destination\> are setts in *pyproject.toml* file (Section "[project-settings]").

## ToDo

- a dummy for broken video
- process animated gifs as video thumbnails
- instead pillow libruary try to use opencv for images
- delete empty dirrectories
- add a feature to delete a file in the source directory if it is deleted in the destination directory

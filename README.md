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

For example, start `./pvo.py` and it will make small copies from *./tests/source* directory to *./tests/temp*.
Default \<source\> and \<destination\> are setts in *pyproject.toml* file (Section "[project-settings]").

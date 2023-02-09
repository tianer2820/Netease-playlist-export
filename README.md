# Netease-playlist-export
Export netease cloud music playlist to json files or m3u8



## Usage

### Export Cloud Playlist to Json

This project depends on https://github.com/Binaryify/NeteaseCloudMusicApi

1. Download the NeteaseCloudMusicApi repo from https://github.com/Binaryify/NeteaseCloudMusicApi
2. Setup the API project according to their instructions
3. Start the API server locally, the server should start with an url like `http://localhost:3000`
4. Install dependency, run `pip3 install qrcode requests pillow`
5. Edit the main.py file, change the directory and url settings accordingly
6. run `python3 main.py`

### Match Json Playlist to local files (Create m3u8)

TODO
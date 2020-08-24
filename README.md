# AutoXSeeder
Parses torrent files and creates symlinks for matching Movies and TV local data

This script is intended to be used in a Windows environment. Check out [Autotorrent](https://github.com/JohnDoee/autotorrent) for Linux/MacOS usage.

# Setup

Run `pip3 install -r requirements.txt` to install the required libraries

# Usage

	usage: AutoXSeeder.py [-h] -i INPUT_PATH -r ROOT_PATH -s SAVE_PATH

	Creates symlinks for existing data given torrent file(s) as inputs

	optional arguments:
	  -h, --help     show this help message and exit
	  -i INPUT_PATH  Torrent file or directory containing torrent files
	  -r ROOT_PATH   Root folder (eg. your torrent client download directory) containing downloaded content which will be
	                 checked for cross-seedable files
	  -s SAVE_PATH   Root folder (eg. your torrent client download directory) where symlinks will be created

Examples:

	py AutoXSeeder.py -i "D:\torrentfiles" -r "D:\TorrentClientDownloads\complete" -s "D:\TorrentClientDownloads\complete"

	py AutoXSeeder.py -i "D:\torrentfiles\MyTorrentFile.torrent" -r "D:\TorrentClientDownloads\complete" -s "D:\TorrentClientDownloads\complete"


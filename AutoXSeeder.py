from fuzzywuzzy import fuzz
import json
import os
import re
import torrent_parser as tp
from ctypes import windll, wintypes

###########
# edit variables corresponding to your working environment

# directory where the downloaded torrent files are located, to be parsed and find matching existing files
TORRENTS_LOCATION = ''

# parent directory whose child files/folders will be used to conduct the search for cross-seedable content.
TRACKER1_DATA_LOCATION = ''

# directory where torrent client for tracker #2 will store downloaded content, and as such, where matched cross-seedable content will be symlinked
TRACKER2_DATA_LOCATION = ''

#############


DISC_FOLDERS = ['BDMV', 'CERTIFICATE', 'PLAYLIST', 'STREAM', 'VIDEO_TS', 'AUDIO_TS']
SEASON_EP_RE = r's(\d+)[ \.]?e(\d+)\b|\b(\d+) ?x ?(\d+)\b'

FILE_ATTRIBUTE_REPARSE_POINT = 0x0400
GetFileAttributes = windll.kernel32.GetFileAttributesW


def main():
	if not os.path.isdir(os.path.join(TORRENTS_LOCATION, 'matched')):
		os.mkdir(os.path.join(TORRENTS_LOCATION, 'matched'))

	for torrent in os.listdir(TORRENTS_LOCATION):
		if not torrent.endswith('.torrent'):
			continue
		torrentPath = os.path.join(TORRENTS_LOCATION, torrent)
		try:
			torrentData = tp.parse_torrent_file(torrentPath)
		except Exception:
			badTorrentDir = os.path.join(TORRENTS_LOCATION, 'bad_torrents')
			badtorrentPath = os.path.join(badTorrentDir, torrent)
			badtorrentPath = validatePath(badtorrentPath)
			os.rename(torrentPath, badtorrentPath)

		torrentDataRootName = torrentData['info']['name']
		torrentDataFileList = torrentData['info'].get('files', None)

		if torrentDataFileList == None:
			filesize_torrent = torrentData['info']['length']

			matchedFilepath = findMatchingDownloadedFile(torrentDataRootName, filesize_torrent, torrentDataRootName)
			if matchedFilepath == None:
				continue

			linkPath = os.path.join(TRACKER2_DATA_LOCATION, torrentDataRootName)
			targetPath = matchedFilepath
			
			if islink(targetPath):
				targetPath = os.readlink(targetPath)

			try:
				os.symlink(targetPath, linkPath)
			except FileExistsError:
				print(f'Skipping... Symlink already exists: "{linkPath}"\n')
				pass
			except OSError:
				print('Admin privileges not held. Cannot create symlink.')
				exit()

			try:
				os.rename(torrentPath, os.path.join(os.path.join(TORRENTS_LOCATION, 'matched'), torrent))
			except Exception:
				pass
		else:
			n = 1
			failedTotalSize = 0
			matchedFiles = {}
			isDisc = isDiscTorrent(torrentDataFileList)
			isTV = isTVTorrent(torrentDataFileList)
			for torrentDataFile in torrentDataFileList:
				torrentDataFilePath = '\\'.join([torrentDataRootName] + torrentDataFile['path'])
				torrentDataListedFilePath = '\\'.join(torrentDataFile['path'])
				filename_torrent = torrentDataFile['path'][-1]
				matchedFilepath = findMatchingDownloadedFile(torrentDataRootName, torrentDataFile['length'], torrentDataListedFilePath, isDisc=isDisc, isTV=isTV)
				if matchedFilepath == None:
					failedTotalSize += torrentDataFile['length']
					continue
				matchedFiles[torrentDataFilePath] = matchedFilepath
			# print(json.dumps(matchedFiles, indent=4))
			# print(matchedFiles)

			for i, filepath in enumerate(matchedFiles):
				dirname = os.path.dirname(filepath)
				if dirname == '':
					continue

				dirPath = os.path.join(TRACKER2_DATA_LOCATION, dirname)
				try:
					os.makedirs(dirPath)
				except FileExistsError:
					pass

				targetPath = matchedFiles[filepath]
				if islink(targetPath):
					targetPath = os.readlink(targetPath)
				linkPath = os.path.join(TRACKER2_DATA_LOCATION, filepath)

				print(f'Symlinking {i + 1} of {len(matchedFiles)}: {linkPath}')
				try:
					os.symlink(targetPath, linkPath)
				except FileExistsError:
					print(f'Skipping... Symlink already exists: "{linkPath}"\n')
					pass
				except OSError:
					print('Admin privileges not held. Cannot create symlink.')
					exit()

			if matchedFiles:
				try:
					os.rename(torrentPath, os.path.join(os.path.join(TORRENTS_LOCATION, 'matched'), torrent))
				except:
					pass


def findMatchingDownloadedFile(torrentDataRootName, torrentDataFilesize, torrentDataFilePath, isDisc=False, isTV=False):
	torrentDataFilename = os.path.basename(torrentDataFilePath)
	# maximum difference, in MB, the downloaded filesize and listed file size can be
	MAX_FILESIZE_DIFFERENCE = 2 * 1000000
	if isTV or torrentDataFilesize < 100 * 1000000:
		MAX_FILESIZE_DIFFERENCE = 0

	listings = os.listdir(TRACKER1_DATA_LOCATION)
	for listing in listings:
		listingPath = os.path.join(TRACKER1_DATA_LOCATION, listing)
		# if 'planet' in listing.lower():
		# 	print(listing)
		# 	print(fuzz.token_set_ratio(listing, torrentDataFilename))
		if os.path.isfile(listingPath) and fuzz.token_set_ratio(listing, torrentDataFilename) > 80:
			localFilesize = get_file_size(listingPath)
			# print((localFilesize - torrentDataFilesize)/1000000)
			if localFilesize == None:
				return None
			if abs(localFilesize - torrentDataFilesize) <= MAX_FILESIZE_DIFFERENCE:
				return listingPath
		elif fuzz.token_set_ratio(listing, torrentDataRootName) > 85:
			for root, dirs, filenames in os.walk(listingPath):
				for filename in filenames:
					localFilePath = os.path.join(root, filename)
					localFilesize = get_size(localFilePath)
					if localFilesize == None:
						continue

					if isDisc and areRootPathsSimilar(localFilePath, listingPath, torrentDataFilePath) and filename == torrentDataFilename:
						if abs(localFilesize - torrentDataFilesize) <= MAX_FILESIZE_DIFFERENCE:
							return localFilePath
					elif re.search(SEASON_EP_RE, torrentDataFilePath, re.IGNORECASE):
						season_ep_str_torrent = getSeasonEpisodeStr(torrentDataFilePath)
						season_ep_str_filename = getSeasonEpisodeStr(filename)
						if season_ep_str_torrent == season_ep_str_filename and abs(localFilesize - torrentDataFilesize) <= MAX_FILESIZE_DIFFERENCE:
							return localFilePath
					elif fuzz.token_set_ratio(filename, torrentDataFilename) > 95:
						if abs(localFilesize - torrentDataFilesize) <= MAX_FILESIZE_DIFFERENCE:
							return localFilePath
	return None


def areRootPathsSimilar(localFilePath, localFileRootPath, torrentDataFilePath):
	localFilePath = localFilePath.replace(localFileRootPath + '\\', '')
	# if fuzz.ratio(localFilePath, torrentDataFilePath) > 97:
	# 	return True
	if localFilePath == torrentDataFilePath:
		return True
	return False


def isDiscTorrent(torrentDataFileList):
	for torrentDataFile in torrentDataFileList:
		for torrentDataFilePathPart in torrentDataFile['path']:
			if torrentDataFilePathPart in DISC_FOLDERS:
				return True
	return False

def isTVTorrent(torrentDataFileList):
	for torrentDataFile in torrentDataFileList:
		if re.search(SEASON_EP_RE, torrentDataFile['path'][-1], re.IGNORECASE):
			return True
	return False

def getSeasonEpisodeStr(filename):
	m = re.search(SEASON_EP_RE, filename, re.IGNORECASE)
	if m:
		season = m.group(1)
		episode = m.group(2)
		return f'S{season.zfill(3)}E{episode.zfill(3)}'
	return None


def get_size(path):
	tempPath = path
	if os.path.isfile(path):
		return get_file_size(path)
	elif os.path.isdir(path):
		totalSize = 0
		for root, dirs, filenames in os.walk(path):
			for filename in filenames:
				filesize = get_file_size(os.path.join(root, filename))
				if filesize == None:
					return None
				totalSize += filesize
		return totalSize
	return None

def get_file_size(filepath):
	if islink(filepath):
		targetPath = os.readlink(filepath)
		if os.path.isfile(targetPath):
			return os.path.getsize(targetPath)
	else:
		return os.path.getsize(filepath)
	return None


def islink(filepath):
    # assert os.path.isdir(filepath), filepath
    if GetFileAttributes(filepath) & FILE_ATTRIBUTE_REPARSE_POINT:
        return True
    else:
        return False


def validatePath(filepath):
	path_filename, ext = os.path.splitext(filepath)
	n = 1

	if not os.path.isfile(filepath):
		return filepath

	filepath = f'{path_filename} ({n}){ext}'
	while os.path.isfile(filepath):
		n += 1
		filepath = f'{path_filename} ({n}){ext}'

	return filepath


if __name__ == '__main__':
	main()

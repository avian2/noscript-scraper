#!/usr/bin/python

import datetime
import glob
import HTMLParser
import os
import re
import shutil
import stat
import subprocess
import sys
import urllib
import urlparse
from xml.dom.minidom import parse
from optparse import OptionParser
import logging

logger = logging.getLogger(__name__)

NOSCRIPT_AMO_ID = 722

def download_changelog():
	f = urllib.urlopen("https://addons.mozilla.org/en-US/firefox/addon/noscript/versions/format:rss")
	dom = parse(f)

	def text(node):
		if not node.childNodes:
			return ""

		# O_o
		data = node.childNodes[0].data
		data = re.sub("<[^>]*>", "", data)
		data = HTMLParser.HTMLParser().unescape(data)
		data = data.strip()
		return data

	changelog = {}

	for item in dom.getElementsByTagName("item"):
		title = text(item.getElementsByTagName("title")[0])

		descl = item.getElementsByTagName("description")
		if descl:
			desc = text(descl[0])
		else:
			desc = ""

		changelog[title] = desc

	return changelog

changelog_cache = None

def get_changelog():
	global changelog_cache

	if changelog_cache is None:
		changelog_cache = download_changelog()

	return changelog_cache

def get_version_changelog(changelog, version):
	s = ' ' + version + ' '
	cl = ''
	for title, desc in changelog.iteritems():
		if s in title:
			cl = desc

	ni = cl.find("\nv")
	if(ni > 0):
		cl = cl[:ni]

	cl = cl.strip()

	return cl

def download_latest():
	f = urllib.urlopen("https://services.addons.mozilla.org/en-US/firefox/api/1.5/addon/%d" % NOSCRIPT_AMO_ID)

	dom = parse(f)

	for i in dom.getElementsByTagName("install"):
		xpi_url = i.childNodes[0].data

		xpi_path = urlparse.urlparse(xpi_url)[2]
		release = xpi_path.split('/')[-1]

		logging.info("found release %r" % release)

		# ignore android versions
		if 'android' in release.lower():
			continue

		if not os.path.exists(os.path.join("../old", release)):
			f = urllib.urlopen(xpi_url)
			data = f.read()

			f = open(os.path.join("../new", release), "wb")
			f.write(data)

def get_version(release):
	basename = os.path.basename(release)
	basename = basename.split("?")[0]

	assert basename.startswith("noscript_security_suite-")

	version = basename.split("-")[1]
	version = re.sub(r"\.xpi$", "", version)

	# workaround for an apparent typo in 10.1.3c1, 10.1.3c2, ...
	version = re.sub(r"(\d+)c(\d+)$", r"\1rc\2", version)

	if "rc" in version:
		version, rc = version.split("rc")
		rc = [0, int(rc)]
	else:
		rc = [1, 0]

	fields = map(int, version.split("."))
	fields += [0] * (10 - len(fields)) + rc

	return tuple(fields)

def log_message(changelog, release):

	version = release.split("-")[1]
	header = "NoScript addons.mozilla.org release %s" % version

	changelog = get_version_changelog(changelog, version)
	if not changelog:
		print "WARNING: empty changelog for release", version

	return "%s\n\n%s" % (header, changelog)

def get_line_count():

	cmd = "find . -name '*.js' -print0 | xargs -0 wc -l | grep 'total$'"

	p = subprocess.Popen(cmd, shell=True,
		stdout=subprocess.PIPE, 
		close_fds=True)

	wc = p.stdout.read()

	return int(wc.split()[0])

def commit_new():
	releases = glob.glob("../new/*.xpi*")

	releases.sort(key=get_version)

	topdir = os.getcwd()

	stats = open("../stats.dat", "w")
	stats.write("date\txpi size\n")

	for release in releases:

		version = release.split("-")[1]

		if re.match(r'^5\.1', version):
			subprocess.call(["git", "checkout", "-q", "noscript-5.1"])
		else:
			subprocess.call(["git", "checkout", "-q", "master"])

		try:
			shutil.rmtree("xpi")
		except OSError:
			pass

		os.mkdir("xpi")

		os.chdir("xpi")
		subprocess.call(["unzip", "-q", "../" + release])

		# Releases after 2.6.6.9 do not have META-INF directory.
		try:
			shutil.rmtree("META-INF")
		except OSError:
			pass

		# Releases after 10.1.1 do not have a chrome directory.
		if os.path.exists("chrome"):
			os.chdir("chrome")

			# Releases after 2.6.9.38 have .jar already unpacked.
			if os.path.exists("noscript.jar"):
				subprocess.call(["unzip", "-q", "noscript.jar"])
				os.unlink("noscript.jar")

		os.chdir(topdir)

		subprocess.check_call(["./version.py", "--strip", version, "xpi"])

		relstat = os.stat(release)
		
		time = datetime.datetime.fromtimestamp(relstat[stat.ST_MTIME])

		changelog = get_changelog()

		subprocess.call(["git", "add", "-A", "xpi"])
		subprocess.call(["git", "commit", 
			"-q",
			"-m", log_message(changelog, release),
			"--date", time.isoformat()])

		lc = get_line_count()

		size = relstat[stat.ST_SIZE]

		stats.write("%s\t%s\t%d\t%d\n" % (
			time.strftime("%Y-%m-%d"), 
			version,
			size,
			lc))

		os.rename(	release, 
				os.path.join("../old", os.path.basename(release)))

def checkdir():
	if not os.path.exists("noscript/xpi"):
		print 'Can\'t find "noscript/xpi"! Make sure it exists in the current repository.'
		sys.exit(1)

	os.chdir("noscript")

def main():

	logging.basicConfig(level=logging.WARNING)

	parser = OptionParser()
	parser.add_option("-n", "--dry-run", dest="dryrun", action="store_true",
			  help="Don't push to GitHub")
	parser.add_option("-c", "--commit-only", dest="commitonly", action="store_true",
			help="Only commit already downloaded releases")

	(options, args) = parser.parse_args()

	checkdir()
	commit_new()
	if not options.commitonly:
		download_latest()
		commit_new()

	if not options.dryrun:
		subprocess.call(["git", "push", "-q", "github", "noscript-5.1"])
		subprocess.call(["git", "push", "-q", "github", "master"])

main()

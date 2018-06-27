This is the scraper script that was used to update the repository at
https://github.com/avian2/noscript until around March 2018.

When run, it fetches new releases of the NoScript extension from
addons.mozilla.org, gets the changelog and commits each release into a git
repository. It also performs some clean-up for nicer looking commits.

Note that as-is this script doesn't work anymore due to changes in
addons.mozilla.org and has been publicly released for anyone interested in
updating it.

See https://github.com/avian2/noscript/issues/13 for a related discussion.

Setup
=====

The script expects to run in a folder like this:

```
topdir
├── new              (freshly downloaded .xpis, yet to be commited)
├── old              (old .xpis already in git)
├── noscript         (git repository, must have a "github" remote)
│   ├── README.md
│   ├── makexpi.sh
│   ├── version.py
│   └── xpi
│       ...
├── noscript-scraper (this repository)
│   ├── README.md
│   └── commit-releases.py
```

The `noscript` repository should be setup so that a push to the `github` remote
works without password entry.

The script was run from crontab with a line like this:

```
13 */3 * * *	cd /.../topdir && noscript-scraper/commit-releases.py
```

License
=======

Released into public domain by Tomaž Šolc. Feel free to update/re-use.

Not affiliated in any way with the developers of the NoScript add-on.

Please do not report bugs. I am not interested in maintaining this script
anymore.

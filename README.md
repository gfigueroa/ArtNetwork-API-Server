ArtMeGo API - Tornado Web Server
===============================================================================

## Description

ArtMeGo API
Tornado Web Server for serving the ArtMeGo API, which connects to the ArtMeGo MySQL database.
ArtMeGo is a social network and platform for artists, art lovers and critics.
The following functions are provided by this server:
*ArtMeGo API for mobile apps (iOS and Android)
*ArtMeGo API for MySQL database manipulation (ADD, DELETE, UPDATE)

Tested with Tornado v4.1 

### Related Projects

## Acknowledgements

Engineers and designers at ArtMeGo team

## Directory Structure

    ArtMeGo_API_Tornado/
        handlers/
        lib/
        logconfig/
        requirements/
            common.txt
            dev.txt
            production.txt
        static/
            css/
            exportfiles/
            images/
            javascript/
            vendor/
        templates/
        tests/
        vendor/
        app.py
        environment.py
        README.md
        settings.py
        urls.py

### handlers

All Tornado RequestHandlers go in this directory.

Everything in this directory is added to the `PYTHONPATH` when the
`environment.py` file is imported.

### lib

Python packages and modules that aren't really Tornado request handlers. These
are just regular Python classes and methods.

Everything in this directory is added to the `PYTHONPATH` when the
`environment.py` file is imported.

### logconfig

An extended version of the
[log_settings](https://github.com/jbalogh/zamboni/blob/master/log_settings.py)
module from Mozilla's [zamboni](https://github.com/jbalogh/zamboni).

This package includes an `initialize_logging` method meant to be called from the
project's `settings.py` that sets Python's logging system. The default for
server deployments is to log to syslog, and the default for solo development is
simply to log to the console.

All loggers should be children of your app's root logger (defined in
`settings.py`). This works well at the top of every file that needs logging:

    import logging
    logger = logging.getLogger('five.' + __name__)

### static

A subfolder each for CSS, Javascript and images. Third-party files (e.g. the
960.gs CSS or jQuery) go in a `vendor/` subfolder to keep your own code
separate.

### requirements

pip requirements files, optionally one for each app environment. The
`common.txt` is installed in every case.

We specifically avoid listing the dependencies in the README of
the project, since a list there isn't checked programmatically or ever actually
installed, so it tends to quickly become out of date.

### templates

Project-wide templates (i.e. those not belonging to any specific app in the
`handlers/` folder). The boilerplate includes a `base.html` template that defines
these blocks:

#### <head>

`title` - Text for the browser title bar. You can set a default here and
append/prepend to it in sub-templates using `{{ super }}`.

`site_css` - Primary CSS files for the site. By default, includes
`static/css/reset.css` and `static/css/base.css`.

`css` - Optional page-specific CSS - empty by default. Use this block if a page
needs an extra CSS file or two, but doesn't want to wipe out the files already
linked via the `site_css` block.

`extra_head` - Any extra content for between the `<head>` tags.

#### <body>

`header` -Top of the body, inside a `div` with the ID `header`.

`content` - After the `header`, inside a `div` with the ID `content`.

`footer` - After `content`, inside a `div` with the ID `footer`.

`site_js` - After all body content, includes site-wide Javascript files. By
default, includes `static/js/application.js` and jQuery. In deployed
environments, links to a copy of jQuery on Google's CDN. If running in solo
development mode, links to a local copy of jQuery from the `static/` directory -
because the best way to fight snakes on a plane is with jQuery on a plane.

`js` - Just like the `css` block, use the `js` block for page-specific
Javascript files when you don't want to wipe out the site-wide defaults in
`site_js`.

### vendor

Python package dependencies loaded as git submodules. pip's support for git
repositories is somewhat unreliable, and if the specific package is your own
code it can be a bit easier to debug if it's all in one place (and not off in a
virtualenv).

Any directory in `vendor/` is added to the `PYTHONPATH` by `environment.py`. The
packages are *not* installed with pip, however, so if they require any
compilation (e.g. C/C++ extensions) this method will not work.

### Files

#### app.py

The main Tornado application, and also a runnable file that starts the Tornado
server.
To start the server, this file must be executed in the command line, as shown in the following example:
	python app.py --host=yourserveraddres.com  --port=3000

#### environment.py

Modifies the `PYTHONPATH` to allow importing from the `apps/`, `lib/` and
`vendor/` directories. This module is imported at the top of `settings.py` to
make sure it runs for both local development (using Django's built-in server)
and in production (run through mod-wsgi, gunicorn, etc.).

#### settings.py

A place to collect application settings (e.g. host address, port number, cookie secret, etc.).
Other project-specific application settings are also configured here, such as:
* Database host address and port number
* Other database connection parameters

## Authors

* [Smart Personalized Service Technology Inc.](http://www.smasrv.com)
 * Gerardo Figueroa, gfigueroa@smasrv.com
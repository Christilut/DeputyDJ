DeputyDJ
=========

DeputyDJ is a tool to make the life of a DJ a little easier.  
Written in Python 2.7, the GUI is created with PyQT.

Requests module
---
Help fulfill audience requests.  
Simply fill in the artist and track name and DeputyDJ will automatically download the track (in 320kbps if available) from What.CD.  
Note that this module requires a valid What.CD account.

Module status: Beta

History module
---
Automatically keep track of the tracks that are played. This is achieved through audio fingerprinting.
Note that this module is not yet finished and may have inaccurate results or even crash the program.

Module status: Pre-alpha

Future development
---
Sadly I have little time to continue but I may fix issues, so add them to the issues here on Github. Pull requests are also very welcomed!  
If demand is high enough I may or may not work hard on it ;)  
  
Should you have a great idea that really fits well in this tool, create an issue with the request in it.  
  
Note for OSX users: currently there is no osx version of this tool but since its Python and PyQt it should not be a problem. An OSX version was always the plan but since I like an OSX device, I never bothered. Anyone is welcome to edit the project to fit OSX needs.

Usage
---
With the dependencies installed, you can use pyinstaller to build a Windows exectubale (technically OSX possible too, but code is completely OSX untested).  Use the build_executable.bat for a 1 click build (if Python 2.7 is in C:\Python2.7\ and you have pyinstaller installed). The resulting .exe will be in the dist folder. It contains everything to run DeputyDJ.
Pressing "Remember me" in the Requests module, will save the What.CD cookie in a temp folder. Your password is not saved.

Dependencies
---
- PyQt4
- appdirs
- libtorrent
- lastfmapi
- requests
(if I missed anything, do not hesitate to edit this readme)

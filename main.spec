# -*- mode: python -*-
a = Analysis(['DeputyDJ.py'],
             pathex=['C:\\Users\\Christiaan\\Dropbox\\Programming\\Python\\DeputyDJ'],
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None)
pyz = PYZ(a.pure)

def extra_datas(mydir):
    def rec_glob(p, files):
        import os
        import glob
        for d in glob.glob(p):
            if os.path.isfile(d):
                files.append(d)
            rec_glob("%s/*" % d, files)
    files = []
    rec_glob("%s/*" % mydir, files)
    extra_datas = []
    for f in files:
        extra_datas.append((f, f, 'DATA'))

    return extra_datas

a.datas.append(('cacert.pem', 'cacert.pem', 'DATA'))
a.datas.append(('LICENSE.txt', 'LICENSE.txt', 'DATA'))
a.datas += extra_datas('interface')
a.datas += extra_datas('res')


exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='DeputyDJ.exe',
          debug=False,
          strip=None,
          upx=True,
          console=False )



import os
import urllib.request

url = 'https://raw.githubusercontent.com/jererc/svcutils/refs/heads/main/svcutils/bootstrap.py'
exec(urllib.request.urlopen(url).read().decode('utf-8'))
Bootstrapper(
    name='parze',
    cmd_args=['parze.main', '-p', os.getcwd(), 'collect', '--task'],
    install_requires=[
        # 'git+https://github.com/jererc/parze.git',
        'parze @ https://github.com/jererc/parze/archive/refs/heads/main.zip',
    ],
    force_reinstall=True,
).setup_task()

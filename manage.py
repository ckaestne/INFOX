import os
import platform

from flask import Flask
from app import create_app
from flask_script import Server, Manager

CONFIGURE_MODE = "default"
if platform.system() == 'Linux':
    CONFIGURE_MODE = "production"
print("configure mode = ", CONFIGURE_MODE)

app = create_app(CONFIGURE_MODE)

manager = Manager(app)
manager.add_command("runserver", Server(host='0.0.0.0'))

if __name__ == "__main__":
    manager.run()

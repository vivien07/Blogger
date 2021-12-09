import os
SECRET_KEY = '0g7pvr#949lk5r=65c28+&72pwb=vh^!)mj7#tk*(p=c$*f)w!'

# Database initialization
if os.environ.get('DATABASE_URL') is None:
    basedir = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app.db')
else:
    SQLALCHEMY_DATABASE_URI = os.environ['DATABASE_URL']

'''
Created on Jul 20, 2011

@author: kykamath
'''
import cherrypy, sys

class HelloWorld:
    def index(self):
        return "Hello world!"
    index.exposed = True
    
if "--fastcgi" in sys.argv:
    app = cherrypy.tree.mount(HelloWorld())
    # CherryPy autoreload must be disabled for the flup server to work
    cherrypy.config.update({'engine.autoreload_on':False})
    cherrypy.config.update({
            "tools.sessions.on": True,
            "tools.sessions.timeout": 5,
            "log.screen": False,
            "log.access_file": "/tmp/cherry_access.log",
            "log.error_file": "/tmp/cherry_error.log",
    })
    from flup.server.fcgi import WSGIServer
    cherrypy.config.update({'engine.autoreload_on':False})
    WSGIServer(app).run()
else:
    cherrypy.config.update("etc/crowdy.conf")
#    cherrypy.tree.mount(api,"/api/1",config="etc/api.conf")
    cherrypy.quickstart(HelloWorld(), config="hello.conf")
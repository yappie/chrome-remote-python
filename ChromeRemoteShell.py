import socket
import json

class ChromeTab(object):
    def __init__(self, crs, tab_id, url):
        self.crs = crs
        self.tab_id = int(tab_id)
        self.url = url
    
    def __repr__(self):
        return "ChromeTab(tab_id = %d, url = '%s')" % (self.tab_id, self.url)

    def v8_cmd(self, cmd, no_response = False):
        res = self.crs.send_raw(
            cmd, 
            tool = 'V8Debugger', 
            destination = self.tab_id, 
            no_response = no_response)
        if not no_response:
            assert res['result'] == 0
            return res

    def v8_attach(self):
        return self.v8_cmd({ "command": "attach" })

    def v8_detach(self):
        return self.v8_cmd({ "command": "detach" })

    def v8_eval_expr(self, expr):
        debugger_json = {
            "type": "request",
            "command": "evaluate",
            "arguments":
            {
                "expression": expr
            }
        }
        res = self.v8_cmd({ 
            "command": "debugger_command", 
            "data": debugger_json
        })
        if res['data']['success']:
            return res['data']['body']['value']
        else:
            raise Exception('V8 Error: ' + res['data']['message'])

    def v8_evaluate_js(self, js):
        return self.v8_cmd(
            {"command": "evaluate_javascript", "data": js},
            no_response = True,
        )

class ChromeRemoteShell(object):
    def __init__(self, host = '127.0.0.1', port = 9222):
        self.verbose = False
        self.sock = socket.socket()
        try:
            self.sock.connect((host, port))
        except:
            raise Exception(
                "Can't connect.\n"
                "Did you forget to run shell?\n"
                " google-chrome --remote-shell-port=9222"
            )
            
        self.sock.send('ChromeDevToolsHandshake\r\n')
        assert self.sock.recv(4096) == 'ChromeDevToolsHandshake\r\n' 

    def send_raw(self, cmd, tool = 'DevToolsService', destination = None,
                    no_response = False):
        js = json.dumps(cmd)

        headers = {
            'Content-Length': len(js),
            'Tool': tool,
        }
        if destination:
            headers['Destination'] = destination

        if self.verbose: print '--- ******************* ---'
        for h,v in headers.items():
            self.sock.send('%s:%s\r\n' % (h,v))
            if self.verbose: print 'SENT> %s:%s\r\n' % (h,v),
        self.sock.send('\r\n')
        if self.verbose: print 'SENT> '

        self.sock.send(js)
        if self.verbose: print 'SENT> %s' % js
        if self.verbose: print '---\nGot back:'
        
        if not no_response:
            txt = self.sock.recv(40960)
            _, _, js_res = txt.partition('\r\n\r\n')
            if self.verbose: print txt
            if self.verbose: print '---'
            return json.loads(js_res)

    def ping(self):
        return self.send_raw({ "command": "ping" })

    def version(self):
        return self.send_raw({ "command": "version" })['data']

    def tabs(self):
        return list(ChromeTab(self, tab_id, url) for tab_id, url in 
                self.send_raw({ "command": "list_tabs" })['data'])
    
    def tab_by_url(self, url):
        for tab in self.tabs():
            if tab.url == url:
                return tab
        raise LookupError("Tab not found")

    def attach(self, tab_id):
        return self.send_raw({ "command": "version" })['data']

if __name__ == '__main__':
    from ChromeRemoteShell import ChromeRemoteShell
    crs = ChromeRemoteShell()

    tab = crs.tabs()[0]
    tab.v8_evaluate_js('window.open("http://new_site.com/");')
    
    import time; time.sleep(.2) # give it a time to open
    print tab

    print crs.tab_by_url('http://new_site.com/')

    tab.v8_attach()

    print tab.v8_eval_expr('1+2')
    tab.v8_eval_expr('1+x') # raises Exception with description
    tab.v8_detach()


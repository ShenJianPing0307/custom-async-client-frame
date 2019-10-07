import socket
from IO多路复用 import select

# ########################## HTTP请求本质，阻塞 ##########################
"""
sk = socket.socket()
# 1.连接
sk.connect(('www.baidu.com',80,)) # IO阻塞
print('连接成功了...')

# 2. 连接成功发送消息
sk.send(b'GET / HTTP/1.0\r\nHost:www.baidu.com\r\n\r\n')
# sk.send(b'POST / HTTP/1.0\r\nHost:www.baidu.com\r\n\r\nk1=v1&k2=v2')

# 3. 等待着服务端响应
data = sk.recv(8096) # IO阻塞
print(data)

# 关闭连接
sk.close()
"""
# ########################## HTTP请求本质，非阻塞 ##########################
"""
sk = socket.socket()
sk.setblocking(False)
# 1.连接
try:
    sk.connect(('www.baidu.com',80,)) # IO阻塞
    print('连接成功了...')
except BlockingIOError as e:
    print(e)
# 2. 连接成功发送消息
sk.send(b'GET / HTTP/1.0\r\nHost:www.baidu.com\r\n\r\n')
# sk.send(b'POST / HTTP/1.0\r\nHost:www.baidu.com\r\n\r\nk1=v1&k2=v2')

# 3. 等待着服务端响应
data = sk.recv(8096) # IO阻塞
print(data)

# 关闭连接
sk.close()
"""

class HttpRequest:
    """
    主要用于封装host、callback
    """
    def __init__(self,sk,host,callback):
        self.socket = sk
        self.host = host
        self.callback = callback
    def fileno(self):
        return self.socket.fileno()

class HttpResponse:
    """
    处理服务端响应内容
    """
    def __init__(self,recv_data):
        self.recv_data = recv_data
        self.header_dict = {}
        self.body = None
        self.initialize()

    def initialize(self):
        """
        处理请求头和请求体
        :return:
        """
        headers, body = self.recv_data.split(b'\r\n\r\n', 1)
        self.body = body
        header_list = headers.split(b'\r\n')
        for h in header_list:
            h_str = str(h,encoding='utf-8')
            v = h_str.split(':',1)
            if len(v) == 2:
                self.header_dict[v[0]] = v[1]

class AsyncRequest:
    def __init__(self):
        self.conn = []
        self.connection = [] # 用于检测是否已经连接成功

    def add_request(self,host,callback):
        """
        因为使用setblocking，connect不会阻塞，如果不进行异常处理就会报错
        :param host:
        :param callback:
        :return:
        """
        try:
            sk = socket.socket()
            sk.setblocking(False)
            sk.connect((host,80,))
        except BlockingIOError as e:
            pass
        #需要将host与回调函数callback传入，所以在使用HttpRequest进行封装
        request = HttpRequest(sk,host,callback)
        #HttpRequest中实现了fileno方法并且返回文件描述符，所以可以加入列表self.conn、self.connection进行监听
        self.conn.append(request)
        self.connection.append(request)

    def run(self):

        while True:
            #注意这是客户端的select监听，所以self.connection表示是否已经连接上服务端，它先有数据
            rlist,wlist,elist = select.select(self.conn, self.connection, self.conn, 0.05)
            #连接服务端成功，并且可以发送请求
            for w in wlist:
                print(w.host,'连接成功...')
                # 只要能循环到，表示socket和服务器端已经连接成功
                tpl = "GET / HTTP/1.0\r\nHost:%s\r\n\r\n"  %(w.host,)
                w.socket.send(bytes(tpl,encoding='utf-8'))
                self.connection.remove(w)
            #获取服务端的响应
            for r in rlist:
                # r,是HttpRequest
                recv_data = bytes()
                while True:
                    #进行异常处理，防止数据接收完毕报错
                    try:
                        chunck = r.socket.recv(8096)
                        recv_data += chunck
                    except Exception as e:
                        break
                #对响应的数据进行处理
                response = HttpResponse(recv_data)
                #调用回调函数，并且将服务端返回的数据传给每一个请求对应的回调函数
                r.callback(response)
                #关闭socket,HTTP是短链接，无状态
                r.socket.close()
                #不再监听self.conn
                self.conn.remove(r)
            #而非self.connection，只有当响应完成才能退出
            if len(self.conn) == 0:
                break

#每一个请求地址对应的回调函数
def func1(response):
    print('保存到文件',response.header_dict)

def func2(response):
    print('保存到数据库', response.body)

#客户端访问的请求地址
url_list = [
    {'host':'www.baidu.com','callback': func1},
    {'host':'www.cnblogs.com','callback': func2},
]

req = AsyncRequest()
for item in url_list:
    req.add_request(item['host'],item['callback'])

req.run()









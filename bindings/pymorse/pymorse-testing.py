#!/usr/bin/python

import unittest
import threading
import time
import socket
import select
import json

from pymorse import MorseStream, Morse, pymorselogger

class SocketWriter(threading.Thread):
    def __init__(self, port = 60000):
        threading.Thread.__init__(self)
        
        self._client_sockets = []
        
        self._running = True
        
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind((str(socket.INADDR_ANY), port))
        self._server.listen(1)
        
        self.start()
        
        self.i = 0
    
    def run(self):
        
        print("Starting the server.")
        
        while self._running:
            sockets = self._client_sockets + [self._server]
            try:
                inputready, outputready, exceptready = select.select(sockets, sockets, [], 0)
            except select.error:
               pass
            except socket.error:
               pass

            if self._server in inputready:
                print("Got a connection to the socket writer")
                sock, addr = self._server.accept()
                self._client_sockets.append(sock)

            if outputready != []:
                message = (self.get_data() + '\n').encode()
                for o in outputready:
                    try:
                        print("Writing " + message + " to the socket")
                        o.send(message)
                    except socket.error:
                        self.close_socket(o)
        
        if self._client_sockets:
            print("Closing client sockets...")
            for s in self._client_sockets:
                s.close()

        if self._server:
            print("Shutting down connections to server...")
            self._server.shutdown(socket.SHUT_RDWR)
            print("Closing socket server...")
            self._server.close()
    
    def close_socket(self, sock):
        self._client_sockets.remove(sock)
        try:
            sock.close()
        except socket.error as error_info:
            logger.warning("Socket error catched while closing: " + str(error_info))

    def close(self):
        print("Closing the socket server")
        self._running = False
        self.join()
        print("Done")
        
    def get_data(self):
        
        data = json.dumps([self.i])
        self.i += 1
        time.sleep(0.1)
        return data
    
    def reset(self):
        self.i = 0

class TestPyMorseStream(unittest.TestCase):

    def setUp(self):
        self._server = SocketWriter()
        self.stream = MorseStream('localhost', 60000, maxlength = 3)
        
    def test_get(self):

        self.assertEqual(self.stream.get(), [0])
        self.assertEqual(self.stream.get(), [1])
        
    def test_last(self):

        self.assertIsNone(self.stream.last())
        self.stream.get()
        self.assertEqual(self.stream.last(), [0])
        self.stream.get()
        self.assertEqual(self.stream.last(), [1])
    
    def test_last_n(self):

        self.assertIsNone(self.stream.last())
        self.assertIsNone(self.stream.last(2))
        self.assertIsNone(self.stream.last(10))
        self.stream.get()
        self.assertEqual(self.stream.last(1), [[0]])
        self.assertEqual(self.stream.last(2), [[0]])
        self.stream.get()
        self.assertEqual(self.stream.last(1), [[1]])
        self.assertEqual(self.stream.last(2), [[1],[0]])
        
        self.stream.get()
        self.assertEqual(self.stream.last(3), [[2],[1],[0]])
        
        self.stream.get()
        self.assertEqual(self.stream.last(3), [[3], [2],[1]])
        self.assertEqual(self.stream.last(4), [[3], [2],[1]])

    def test_subscribe(self):
        
        self.ok = False
        self.i = 0
        
        self.stream.subscribe(self.on_data)
        self.stream.get()
        
        time.sleep(0.2)        
        self.assertTrue(self.ok)
        
        self.ok = False
        
        self.stream.get()
        
        time.sleep(0.2)
        self.assertTrue(self.ok)
    
    def test_unsubscribe(self):
        
        self.ok = False
        self.i = 0
        
        self.stream.subscribe(self.on_data)
        self.stream.get()
        
        time.sleep(0.2)        
        self.assertTrue(self.ok)
        
        self.ok = False
        
        self.stream.unsubscribe(self.on_data)
        self.stream.get()
        
        time.sleep(0.2)
        self.assertFalse(self.ok)
        
    def on_data(self, record):
        
        self.ok = True
        self.assertEqual(record, [self.i])
        self.i += 1
        
    def tearDown(self):
        self.stream.close()
        self._server.close()

if __name__ == '__main__':
    
    import logging
    
    console = logging.StreamHandler()
    console.setLevel(4)

    # set a format which is simpler for console use
    formatter = logging.Formatter('%(asctime)-15s %(name)s: %(levelname)s - %(message)s')
    # tell the handler to use this format
    console.setFormatter(formatter)
    # add the handler to the root logger
    pymorselogger.addHandler(console)
        
    unittest.main()

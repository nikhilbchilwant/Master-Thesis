from openiotfog_sgui import guiapp, socketio, guiendpointhost,guiendpointport


if __name__ == '__main__':
    socketio.run(guiapp,host=guiendpointhost,port=guiendpointport)





